#!/usr/bin/env python3
"""Illustrative API evaluation pipeline.

Run the simulation from the repository root:
    python scripts/eval_example.py --mock --limit 8 --workers 4 --batch-size 8

Repeat the same command to resume; successful qa_ids are skipped and errors
are retried. Use a different --output-dir for a new experiment.

For real inference, set ``MODEL_NAME``, ``BASE_URL``, and ``API_KEY`` in the
environment, then implement call_api() for your provider's video+audio
interface. The mock returns a fixed answer
and empty evidence, never reads reference answers, and produces no benchmark
claims. Video preprocessing (480 pixels, 1 FPS, retaining audio) is supplied
by the caller/provider, rather than performed by this orchestration example.

Outputs: results.jsonl (durable per-attempt checkpoint + raw responses),
results.txt (readable attempt log), predictions.json (successful predictions),
summary.json (accuracy, statuses, level breakdown), run_config.json (resume
configuration, excluding credentials), grounded_scores.json (final overall,
per-level, per-capability and per-question grounded scores). Aggregate scores
are percentages; per-question scores are fractions. Failed/missing predictions
score zero and remain in the denominator. Reference labels are used only locally.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import math
import os
from pathlib import Path
import re
import time


MODEL_NAME_ENV = 'MODEL_NAME'
BASE_URL_ENV = 'BASE_URL'
API_KEY_ENV = 'API_KEY'

VIDEO_AUDIO_PROMPT = """\
You are answering a multiple-choice question based on the Video and Audio provided.
Answer the multiple-choice question and identify the evidence that directly supports your answer.

Question:
{question}
Options:
{options}

Evidence requirements:
* Each evidence item MUST contain a precise timestamp range in the format "[mm:ss,mm:ss]".
* Include only evidence that directly supports the answer.
* Keep each timestamp range as precise and minimal as possible.

Strict output format:
Return ONLY a valid JSON object with the following fields:
{{
  "answer": "<single option letter>",
  "visual_evidence": [
    {{"time": "[mm:ss,mm:ss]"}}
  ],
  "audio_evidence": [
    {{"time": "[mm:ss,mm:ss]"}}
  ]
}}
"""


def call_api(video_path: Path, prompt: str, *, mock: bool) -> str:
    """Return response text. Never pass the annotation record to the API."""
    if mock:
        # Only exercise orchestration; do not read video content or ground truth.
        time.sleep(0.05)
        return json.dumps({"answer": "A", "visual_evidence": [], "audio_evidence": []})

    # Provider-specific pseudocode; SDKs and media schemas differ:
    # client = ProviderClient(base_url=os.environ[BASE_URL_ENV],
    #                         api_key=os.environ[API_KEY_ENV], timeout=1800)
    # media = client.upload_video(video_path, include_audio=True, fps=1.0)
    # response = client.generate(model=os.environ[MODEL_NAME_ENV], video=media, text=prompt)
    # return response.text
    # If video input discards audio, extract and attach the audio separately.
    raise NotImplementedError("Implement your provider's video+audio API adapter here.")


def parse_response(raw: str, qa_id) -> dict:
    """Accept a JSON object (optionally fenced), validating both evidence lists."""
    text = raw.strip()
    if text.startswith('```'):
        text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\s*```$', '', text)
    obj = json.loads(text)
    if not isinstance(obj, dict):
        raise ValueError('Response must be a JSON object')
    answer = obj.get('answer')
    if not isinstance(answer, str) or not re.fullmatch(r'[A-H]', answer.strip().upper()):
        raise ValueError('answer must be a single option letter A-H')
    prediction = {'qa_id': qa_id, 'answer': answer.strip().upper()}
    for key in ('visual_evidence', 'audio_evidence'):
        items = obj.get(key)
        if not isinstance(items, list):
            raise ValueError(f'{key} must be a list')
        intervals = []
        for item in items:
            timestamp = item.get('time', '') if isinstance(item, dict) else ''
            match = re.fullmatch(r'\[(\d{2,}):([0-5]\d),(\d{2,}):([0-5]\d)\]', str(timestamp))
            if not match:
                raise ValueError(f'Invalid timestamp: {timestamp!r}')
            start_min, start_sec, end_min, end_sec = map(int, match.groups())
            start, end = start_min * 60 + start_sec, end_min * 60 + end_sec
            if end <= start:
                raise ValueError('Evidence end must be greater than start')
            intervals.append([start, end])
        prediction[key] = intervals
    return prediction


def evaluate_one(record: dict, args) -> dict:
    """One question; only question, options, and media reach call_api()."""
    started = time.monotonic()
    result = {'qa_id': record['qa_id'], 'video_id': record['video_id'],
              'level': record.get('level'), 'question': record['question'],
              'options': record['options'], 'status': 'infer_error',
              'raw_response': '', 'prediction': None, 'error': '', 'attempts': 0}
    video_id = str(record['video_id']).zfill(3)
    video_path = args.video_dir / f'{video_id}.mp4'
    prompt = VIDEO_AUDIO_PROMPT.format(question=record['question'], options=record['options'])
    if not args.mock and not video_path.is_file():
        result['error'] = f'Video not found: {video_path}'
    else:
        for attempt in range(1, args.retries + 1):
            result['attempts'] = attempt
            result['raw_response'] = ''
            result['status'] = 'infer_error'
            try:
                result['raw_response'] = call_api(video_path, prompt, mock=args.mock)
                result['status'] = 'parse_error'
                result['prediction'] = parse_response(result['raw_response'], record['qa_id'])
                result.update(status='ok', error='')
                break
            except NotImplementedError:
                raise  # Configuration error; do not retry a missing adapter.
            except Exception as exc:
                result['error'] = f'{type(exc).__name__}: {exc}'
                if attempt < args.retries:
                    time.sleep(min(2 ** (attempt - 1), 30))
    # Reference answers are accessed only AFTER inference, for local reporting.
    result['reference_answer'] = record['answer']
    result['correct'] = result['status'] == 'ok' and result['prediction']['answer'] == record['answer']
    result['latency_s'] = round(time.monotonic() - started, 3)
    return result


def load_checkpoint(path: Path) -> dict:
    """Last saved attempt per qa_id. Remove a torn final line before appending."""
    latest = {}
    if path.exists():
        with path.open('r+b') as stream:
            while True:
                offset = stream.tell()
                line = stream.readline()
                if not line:
                    break
                if not line.endswith(b'\n'):
                    stream.truncate(offset)
                    print('Removed incomplete final checkpoint line.', flush=True)
                    break
                result = json.loads(line)
                latest[str(result['qa_id'])] = result
    return latest


def write_json(path: Path, data) -> None:
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    temporary.replace(path)


def save_result(output_dir: Path, result: dict) -> None:
    # Only the main thread writes files. Each completed question is checkpointed.
    with (output_dir / 'results.jsonl').open('a', encoding='utf-8') as stream:
        stream.write(json.dumps(result, ensure_ascii=False) + '\n')
        stream.flush()
        os.fsync(stream.fileno())
    with (output_dir / 'results.txt').open('a', encoding='utf-8') as stream:
        stream.write(f"\n{'=' * 60}\n" + json.dumps(result, indent=2, ensure_ascii=False) + '\n')


SCORE_NAMES = ('Acc.', 'C.G.', 'B.G.', 'Mean', 'Thr@0.3', 'Thr@0.5', 'Thr@0.7')


def parse_evidence_interval(value) -> tuple[float, float]:
    """Read reference time objects or normalized prediction intervals in seconds."""
    if isinstance(value, dict):
        value = value.get('time')
    if isinstance(value, str):
        match = re.fullmatch(r'\[\s*([^,]+),\s*([^,]+)\s*\]', value)
        if not match:
            raise ValueError(f'Invalid evidence interval: {value!r}')
        value = match.groups()
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError(f'Invalid evidence interval: {value!r}')
    endpoints = []
    for endpoint in value:
        if isinstance(endpoint, bool) or not isinstance(endpoint, (str, int, float)):
            raise ValueError(f'Invalid timestamp: {endpoint!r}')
        parts = str(endpoint).strip().split(':')
        if not 1 <= len(parts) <= 3:
            raise ValueError(f'Invalid timestamp: {endpoint!r}')
        numbers = [float(part) for part in parts]
        if (not all(math.isfinite(n) and n >= 0 for n in numbers)
                or any(n >= 60 for n in numbers[1:])):
            raise ValueError(f'Invalid timestamp: {endpoint!r}')
        seconds = sum(n * 60 ** i for i, n in enumerate(reversed(numbers)))
        if not math.isfinite(seconds):
            raise ValueError(f'Invalid timestamp: {endpoint!r}')
        endpoints.append(seconds)
    start, end = endpoints
    if end <= start:
        raise ValueError(f'Evidence must satisfy 0 <= start < end: {value!r}')
    return start, end


def reference_intervals(record: dict) -> dict:
    """Reject malformed references instead of silently changing the benchmark."""
    intervals = {}
    for modality in ('audio', 'visual'):
        evidence = record.get('evidence')
        items = evidence.get(modality) if isinstance(evidence, dict) else None
        if not isinstance(items, list) or not items:
            raise ValueError(f'qa_id={record["qa_id"]}: missing/empty {modality} reference evidence')
        try:
            intervals[modality] = [parse_evidence_interval(item) for item in items]
        except ValueError as exc:
            raise ValueError(f'qa_id={record["qa_id"]}, {modality}: {exc}') from exc
    return intervals


def merge_intervals(intervals: list) -> list:
    merged = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    return merged


def temporal_iou(predicted: list, reference: list) -> float:
    """IoU of time-set unions, with overlapping intervals counted only once."""
    predicted, reference = merge_intervals(predicted), merge_intervals(reference)
    intersection = math.fsum(max(0.0, min(pe, re_) - max(ps, rs))
                             for ps, pe in predicted for rs, re_ in reference)
    union = math.fsum(end - start for start, end in merge_intervals(predicted + reference))
    return intersection / union if union else 0.0


def evidence_coverage(predicted: list, reference: list) -> float:
    # Keep original reference segments: coverage counts segments, not duration.
    hits = sum(any(min(pe, re_) > max(ps, rs) for ps, pe in predicted)
               for rs, re_ in reference)
    return hits / len(reference) if reference else 0.0


def compute_grounded_scores(records: list, latest: dict) -> dict:
    """Apply grounded_scores.md formulas; never trust cached correctness flags."""
    per_question, invalid_predictions = [], []
    for record in records:
        reference = reference_intervals(record)
        result = latest.get(str(record['qa_id']), {})
        prediction = result.get('prediction') if result.get('status') == 'ok' else None
        predicted = {'audio': [], 'visual': []}
        correct = 0
        if prediction is not None:
            try:
                if not isinstance(prediction, dict):
                    raise ValueError('Prediction must be an object')
                answer = prediction.get('answer')
                if not isinstance(answer, str) or not re.fullmatch(r'[A-H]', answer.strip().upper()):
                    raise ValueError('Prediction answer must be A-H')
                for modality in predicted:
                    items = prediction.get(f'{modality}_evidence')
                    if not isinstance(items, list):
                        raise ValueError(f'Missing/invalid {modality} evidence list')
                    predicted[modality] = [parse_evidence_interval(item) for item in items]
                correct = int(answer.strip().upper() == record['answer'])
            except ValueError as exc:
                predicted = {'audio': [], 'visual': []}
                invalid_predictions.append({'qa_id': record['qa_id'], 'error': str(exc)})
        elif result.get('status') == 'ok':
            invalid_predictions.append({'qa_id': record['qa_id'], 'error': 'Missing prediction'})
        audio_iou = temporal_iou(predicted['audio'], reference['audio'])
        visual_iou = temporal_iou(predicted['visual'], reference['visual'])
        mean_iou = (audio_iou + visual_iou) / 2
        audio_coverage = evidence_coverage(predicted['audio'], reference['audio'])
        visual_coverage = evidence_coverage(predicted['visual'], reference['visual'])
        scores = {'Acc.': correct,
                  'C.G.': correct * (audio_coverage + visual_coverage) / 2,
                  'B.G.': correct * min(audio_iou, visual_iou),
                  'Mean': correct * mean_iou}
        scores.update({f'Thr@{threshold}': int(correct and mean_iou >= threshold)
                       for threshold in (0.3, 0.5, 0.7)})
        per_question.append({'qa_id': record['qa_id'], 'level': record.get('level', 'unknown'),
                             'capability': record.get('capability', 'unknown'),
                             'audio_iou': audio_iou, 'visual_iou': visual_iou,
                             'audio_coverage': audio_coverage, 'visual_coverage': visual_coverage,
                             'mean_iou': mean_iou, 'scores': scores})

    def aggregate(rows):
        return {'count': len(rows), **{
            name: 100 * math.fsum(row['scores'][name] for row in rows) / len(rows) if rows else 0.0
            for name in SCORE_NAMES}}

    def breakdown(field):
        groups = {}
        for row in per_question:
            groups.setdefault(str(row[field]), []).append(row)
        return {key: aggregate(rows) for key, rows in groups.items()}

    return {'aggregate_unit': 'percent', 'per_question_unit': 'fraction',
            'overall': aggregate(per_question), 'by_level': breakdown('level'),
            'by_capability': breakdown('capability'), 'per_question': per_question,
            'invalid_predictions': invalid_predictions}


def export_results(records: list, latest: dict, args, *, score_grounding: bool = False) -> dict:
    # Deduplicate resumed attempts and keep missing/failed questions in denominator.
    rows = [latest[str(r['qa_id'])] for r in records if str(r['qa_id']) in latest]
    predictions = [r['prediction'] for r in rows if r['status'] == 'ok']
    correct = sum(r['correct'] for r in rows)
    levels = {}
    for record in records:
        level = str(record.get('level', 'unknown'))
        group = levels.setdefault(level, {'total': 0, 'correct': 0})
        group['total'] += 1
        group['correct'] += int(latest.get(str(record['qa_id']), {}).get('correct', False))
    summary = {'mock': args.mock, 'model_name': os.getenv(MODEL_NAME_ENV, ''),
               'total': len(records),
               'completed': len(rows), 'ok': len(predictions),
               'errors': sum(r['status'] != 'ok' for r in rows),
               'missing': len(records) - len(rows), 'correct': correct,
               'accuracy_percent': 100 * correct / len(records) if records else 0,
               'by_level': levels,
               'note': 'Mock results are simulated.' if args.mock else 'Aggregate scores are percentages over all selected questions.'}
    if score_grounding:
        grounded = compute_grounded_scores(records, latest)
        grounded['mock'] = args.mock
        write_json(args.output_dir / 'grounded_scores.json', grounded)
        summary['grounded_scores'] = grounded['overall']
        for level, metrics in grounded['by_level'].items():
            summary['by_level'][level]['grounded_scores'] = metrics
    write_json(args.output_dir / 'predictions.json', predictions)
    write_json(args.output_dir / 'summary.json', summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--annotations', type=Path, default=Path('data/test_file.json'))
    parser.add_argument('--video-dir', type=Path, default=Path('data/resized_video'))
    parser.add_argument('--output-dir', type=Path, default=Path('outputs/api_example'))
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--batch-size', type=int, default=16, help='Maximum questions queued per batch')
    parser.add_argument('--retries', type=int, default=3, help='Maximum attempts per question')
    parser.add_argument('--limit', type=int, default=None)
    parser.add_argument('--mock', action='store_true', help='Simulate responses; no API or video reads')
    args = parser.parse_args()
    if min(args.workers, args.batch_size, args.retries) < 1 or (args.limit is not None and args.limit < 1):
        parser.error('workers, batch-size, retries, and limit must be positive')
    if not args.mock:
        model_name = os.getenv(MODEL_NAME_ENV, '')
        base_url = os.getenv(BASE_URL_ENV, '')
        api_key = os.getenv(API_KEY_ENV, '')
        if not all((model_name, base_url, api_key)):
            parser.error(f'Set {MODEL_NAME_ENV}, {BASE_URL_ENV}, and {API_KEY_ENV}, '
                         'then implement call_api(), or use --mock')
        # Remove this guard after implementing the provider-specific adapter above.
        parser.error('Implement call_api() and remove this guard before real inference')

    dataset_bytes = args.annotations.read_bytes()
    records = json.loads(dataset_bytes)
    if not isinstance(records, list) or not all(isinstance(r, dict) for r in records):
        parser.error('Annotations must be a JSON array of question records')
    ids = [str(r['qa_id']) for r in records]
    if len(ids) != len(set(ids)):
        parser.error('Duplicate qa_id in annotations')
    records = records[:args.limit]
    # Validate references before API calls; only the scorer reads their contents.
    try:
        for record in records:
            if not isinstance(record.get('answer'), str) or not re.fullmatch(r'[A-H]', record['answer']):
                raise ValueError(f'qa_id={record["qa_id"]}: reference answer must be A-H')
            reference_intervals(record)
    except ValueError as exc:
        parser.error(str(exc))
    config = {'annotations': str(args.annotations.resolve()),
              'dataset_sha256': hashlib.sha256(dataset_bytes).hexdigest(),
              'video_dir': str(args.video_dir.resolve()), 'mock': args.mock,
              'model_name': os.getenv(MODEL_NAME_ENV, ''),
              'base_url': os.getenv(BASE_URL_ENV, ''),
              'prompt_sha256': hashlib.sha256(VIDEO_AUDIO_PROMPT.encode()).hexdigest()}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    config_path = args.output_dir / 'run_config.json'
    if config_path.exists() and json.loads(config_path.read_text(encoding='utf-8')) != config:
        parser.error('Resume configuration changed; use a different --output-dir')
    if not config_path.exists() and (args.output_dir / 'results.jsonl').exists():
        parser.error('Checkpoint has no run_config.json; use a different --output-dir')
    write_json(config_path, config)  # Never save the API key.
    latest = load_checkpoint(args.output_dir / 'results.jsonl')
    pending = [r for r in records if latest.get(str(r['qa_id']), {}).get('status') != 'ok']
    resumed = len(records) - len(pending)
    print(f'Total={len(records)} | resumed={resumed} | pending={len(pending)} | mock={args.mock}', flush=True)
    started = time.monotonic()
    finished = 0
    try:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            for start in range(0, len(pending), args.batch_size):
                batch = pending[start:start + args.batch_size]
                futures = [pool.submit(evaluate_one, record, args) for record in batch]
                for future in as_completed(futures):
                    result = future.result()
                    save_result(args.output_dir, result)
                    latest[str(result['qa_id'])] = result
                    finished += 1
                    elapsed = time.monotonic() - started
                    eta = elapsed / finished * (len(pending) - finished)
                    print(f"[{resumed + finished}/{len(records)}] qa_id={result['qa_id']} "
                          f"status={result['status']} correct={result['correct']} "
                          f'elapsed={elapsed:.1f}s ETA={eta:.1f}s', flush=True)
                export_results(records, latest, args)  # Refresh snapshots after every batch.
    finally:
        summary = export_results(records, latest, args, score_grounding=True)
        print(json.dumps(summary, indent=2), flush=True)
        print(f'Saved results to {args.output_dir}', flush=True)


if __name__ == '__main__':
    main()
