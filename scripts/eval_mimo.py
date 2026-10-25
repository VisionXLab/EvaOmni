"""Batch-evaluate an annotation file through an OpenAI-compatible video endpoint.

This adapter targets the MiMo family (MiMo-V2.6-Pro, MiMo-V2.6-Flash) served
over an OpenAI-compatible chat completions API. It also works for any other
provider exposing the same request shape.

Set ``BASE_URL``, ``API_KEY``, and ``MODEL_NAME`` in the environment before
running. The ``EVAOMNI_*`` names are accepted as aliases. Videos are inline
base64 data URLs, so no upload step is required. No credentials are written to
the output files.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from openai import OpenAI

DEFAULT_ANNOTATION = Path("data/test_file.json")
DEFAULT_VIDEO_ROOT = Path("data/resized_video")
DEFAULT_RESULTS_DIR = Path("outputs/mimo")
DEFAULT_TAG = "mimo"

BASE_URL_ENV = "BASE_URL"
API_KEY_ENV = "API_KEY"
MODEL_NAME_ENV = "MODEL_NAME"


def _environment_value(name: str) -> str:
    """Read a required setting, allowing namespaced aliases for convenience."""
    for candidate in (name, f"EVAOMNI_{name}"):
        value = os.getenv(candidate)
        if value:
            return value
    return ""


PROMPT_TEMPLATE = """You are answering a multiple-choice question based on the Video and Audio provided.
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


def resolve_video_path(video_root: Path, video_id: str) -> Path | None:
    """Find a video in either supported directory layout.

    1. Flat: <root>/<video_id>.mp4
    2. Prefix: <root>/<prefix>/<video_id>.mp4
    3. Recursive fallback: any <root>/**/<video_id>.mp4
    """
    root = Path(video_root)
    candidates = [root / f"{video_id}.mp4"]
    if "_" in video_id:
        candidates.append(root / video_id.rsplit("_", 1)[0] / f"{video_id}.mp4")
    for p in candidates:
        if p.exists():
            return p
    matches = sorted(root.rglob(f"{video_id}.mp4"))
    return matches[0] if matches else None


_JSON_OBJ_RE = re.compile(r"\{.*\}", re.S)
_LETTER_RE = re.compile(r"\b([A-H])\b", re.IGNORECASE)


def _strip_markdown_fence(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z]*\s*", "", s)
        s = re.sub(r"\s*```\s*$", "", s)
    return s.strip()


def parse_model_output(content: str) -> tuple[dict, str | None]:
    """Parse a model reply into ``(prediction, error)``.

    Accepts a bare JSON object, a fenced object, or a JSON object embedded in
    prose. Falls back to extracting a single option letter.
    """
    if not content:
        return ({}, "empty content")
    s = _strip_markdown_fence(content)
    obj = None
    try:
        obj = json.loads(s)
    except Exception:
        m = _JSON_OBJ_RE.search(s)
        if m:
            try:
                obj = json.loads(m.group(0))
            except Exception:
                obj = None
    if not isinstance(obj, dict):
        m = _LETTER_RE.search(s)
        if m:
            return ({"answer": m.group(1).upper(), "visual_evidence": [], "audio_evidence": []},
                    "non-JSON output, only letter extracted")
        return ({}, f"cannot parse JSON: {s[:200]}")

    def _norm_evidence(x):
        if not isinstance(x, list):
            return []
        out = []
        for it in x:
            if isinstance(it, dict):
                t = str(it.get("time", "")).strip()
                d = str(it.get("description", "")).strip()
            elif isinstance(it, str):
                t, d = "", it.strip()
            else:
                continue
            if t or d:
                out.append({"time": t, "description": d})
        return out

    ans = str(obj.get("answer", "")).strip()
    m = _LETTER_RE.search(ans)
    ans_letter = m.group(1).upper() if m else ans[:1].upper() if ans else ""
    if ans_letter and ans_letter not in "ABCDEFGH":
        ans_letter = ""

    return (
        {
            "answer": ans_letter,
            "visual_evidence": _norm_evidence(obj.get("visual_evidence", [])),
            "audio_evidence": _norm_evidence(obj.get("audio_evidence", [])),
        },
        None,
    )


def run_one(client: OpenAI, model: str, video_path: str, prompt: str,
            max_tokens: int, retries: int, fps: float = 0.0) -> tuple[str, str | None]:
    """Call the endpoint once per attempt and return ``(text, error)``."""
    try:
        with open(video_path, "rb") as f:
            video_b64 = base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:  # noqa: BLE001
        return "", f"read video failed: {type(e).__name__}: {e}"

    video_url: dict = {"url": f"data:video/mp4;base64,{video_b64}"}
    if fps and fps > 0:
        video_url["fps"] = fps
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "video_url",
                    "video_url": video_url,
                    "media_resolution": "default",
                },
                {"type": "text", "text": prompt},
            ],
        }
    ]

    last_err = None
    for attempt in range(retries):
        try:
            completion = client.chat.completions.create(
                model=model,
                messages=messages,
                stream=True,
                max_tokens=max_tokens,
            )
            full_text = ""
            for chunk in completion:
                if chunk.choices and chunk.choices[0].delta.content:
                    full_text += chunk.choices[0].delta.content
            if not full_text.strip():
                raise RuntimeError("empty response")
            return full_text, None
        except Exception as e:  # noqa: BLE001
            last_err = f"{type(e).__name__}: {e}".strip()
            if attempt + 1 < retries:
                wait = min(2 ** attempt * 5, 60)
                print(f"    [retry {attempt + 1}/{retries}] {last_err} -> sleep {wait}s", flush=True)
                time.sleep(wait)
            else:
                print(f"    [retry {attempt + 1}/{retries}] {last_err} -> giving up", flush=True)
    return "", last_err


def load_attempts(jsonl_path: Path) -> dict[str, dict]:
    """Load the latest attempt per qa_id.

    Failed records are retried on every run, so the same qa_id can appear more
    than once. Keeping the last attempt prevents double counting and gives
    summary statistics one row per question.
    """
    latest: dict[str, dict] = {}
    if not jsonl_path.exists():
        return latest
    with jsonl_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            if rec.get("qa_id") is not None:
                latest[str(rec["qa_id"])] = rec
    return latest


def load_done_qa_ids(jsonl_path: Path) -> set[str]:
    return {qa_id for qa_id, rec in load_attempts(jsonl_path).items()
            if rec.get("status") == "ok"}


def _fmt_evidence(ev) -> str:
    """Format evidence items for the human-readable report."""
    if not isinstance(ev, list):
        return ""
    parts = []
    for it in ev:
        if isinstance(it, dict):
            t = str(it.get("time", "")).strip()
            d = str(it.get("description", "")).strip()
            if t or d:
                parts.append(f"[{t}] {d}" if t else d)
        elif isinstance(it, str) and it.strip():
            parts.append(it.strip())
    return "; ".join(parts)


_TIME_RE = re.compile(r"\[\d{1,2}:\d{2}(?:\.\d+)?,\d{1,2}:\d{2}(?:\.\d+)?\]")


def _ev_times(ev) -> str:
    """Extract timestamp ranges from evidence items or formatted text."""
    if isinstance(ev, str):
        return " ".join(_TIME_RE.findall(ev))
    if not isinstance(ev, list):
        return ""
    out = []
    for it in ev:
        if isinstance(it, dict):
            t = str(it.get("time", "")).strip()
            if t:
                out.append(t)
        elif isinstance(it, str):
            out.extend(_TIME_RE.findall(it))
    return " ".join(out)


def _gt_block(rec: dict) -> dict:
    ev = rec.get("evidence") or {}
    return {
        "qa_id": rec["qa_id"],
        "level": rec["level"],
        "video_id": rec["video_id"],
        "capability": rec.get("capability", ""),
        "question": rec["question"],
        "options": rec["options"],
        "gt_answer": rec.get("answer", ""),
        "gt_visual_evidence": _fmt_evidence(ev.get("visual", [])),
        "gt_audio_evidence": _fmt_evidence(ev.get("audio", [])),
    }


def _append_result(out_jsonl: Path, out_txt: Path, result: dict) -> str:
    with out_jsonl.open("a", encoding="utf-8") as f:
        f.write(json.dumps(result, ensure_ascii=False) + "\n")
    if result["status"] == "ok":
        correct = "✓" if result["pred_answer"] and result["pred_answer"] == result["gt_answer"] else "✗"
    else:
        correct = "?"
    block = (
        "=" * 100 + "\n"
        f"{result['qa_id']} | level={result['level']} | {result['video_id']} | {result['capability']}\n"
        f"Question: {result['question']}\n"
        + "-" * 100 + "\n"
        f"Options:\n{result['options']}\n"
        + "-" * 100 + "\n"
        f"GT answer: {result['gt_answer']}    Pred answer: {result['pred_answer']}    [{correct}]\n"
        f"Status: {result['status']}  Error: {result['error']}  Latency: {result['latency_s']}s\n"
        + "-" * 100 + "\n"
        f"GT visual evidence  : {result.get('gt_visual_evidence', '')}\n"
        f"GT audio evidence   : {result.get('gt_audio_evidence', '')}\n"
        f"Pred visual evidence: {json.dumps(result['pred_visual_evidence'], ensure_ascii=False)}\n"
        f"Pred audio evidence : {json.dumps(result['pred_audio_evidence'], ensure_ascii=False)}\n"
        + "-" * 100 + "\n"
        f"Raw output:\n{result['pred_raw']}\n"
        + "=" * 100 + "\n\n"
    )
    with out_txt.open("a", encoding="utf-8") as f:
        f.write(block)
    return correct


def _progress_line(done: int, total: int, t_start: float, ok: int, correct: int,
                   infer_err: int, parse_err: int, last_item: str):
    elapsed = max(time.time() - t_start, 1e-6)
    eta = elapsed / done * (total - done)
    pct = done / total * 100
    width = 30
    filled = int(width * done / total)
    bar = "#" * filled + "-" * (width - filled)
    acc = correct / ok * 100 if ok else 0.0
    line = (
        f"[{bar}] {done}/{total} ({pct:.1f}%)"
        f" | ok={ok} acc={correct}/{ok}={acc:.1f}%"
        f" | infer_err={infer_err} parse_err={parse_err}"
        f" | {elapsed / 60:.1f}min elapsed, ETA {eta / 60:.1f}min"
        f" | last: {last_item}"
    )
    sys.stdout.write("\r\033[K" + line[:250])
    sys.stdout.flush()


def _print_summary(out_jsonl: Path, total_questions: int | None = None):
    if not out_jsonl.exists():
        return
    # Count each question once; repeated attempts for failed records are not
    # separate questions.
    rows = list(load_attempts(out_jsonl).values())
    ok = correct = infer_err = parse_err = 0
    by_level: dict = {}
    for r in rows:
        lv = r.get("level", 0)
        by_level.setdefault(lv, [0, 0])
        by_level[lv][1] += 1
        if r.get("status") == "ok":
            ok += 1
            if r.get("pred_answer") and r["pred_answer"] == r.get("gt_answer"):
                correct += 1
                by_level[lv][0] += 1
        elif r.get("status") == "infer_error":
            infer_err += 1
        elif r.get("status") == "parse_error":
            parse_err += 1
    total = total_questions if total_questions is not None else len(rows)
    print("\n========== Summary ==========")
    print(f"Total       : {total}")
    print(f"OK          : {ok}")
    print(f"Infer errors: {infer_err}")
    print(f"Parse errors: {parse_err}")
    if ok:
        print(f"Accuracy (over ok)    : {correct}/{ok} = {correct/ok*100:.1f}%")
    if total:
        print(f"Accuracy (over total) : {correct}/{total} = {correct/total*100:.1f}%")
    for lv in sorted(by_level):
        c, t = by_level[lv]
        acc = (c / t * 100) if t else 0.0
        print(f"  Level{lv}: {c}/{t} = {acc:.1f}%")
    print(f"Results: {out_jsonl}")


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate annotation.json with an OpenAI-compatible video endpoint "
                    "(MiMo-V2.6-Pro, MiMo-V2.6-Flash, or any equivalent API)."
    )
    parser.add_argument("--annotation", type=Path, default=DEFAULT_ANNOTATION)
    parser.add_argument("--video-root", type=Path, default=DEFAULT_VIDEO_ROOT,
                        help="Video root: <root>/<video_id>.mp4 or <root>/<prefix>/<video_id>.mp4")
    parser.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS_DIR)
    parser.add_argument("--tag", type=str, default=DEFAULT_TAG,
                        help="Suffix used for result filenames")
    parser.add_argument("--workers", type=int, default=4,
                        help="Number of concurrent requests")
    parser.add_argument("--retries", type=int, default=3,
                        help="Retry attempts per question")
    parser.add_argument("--max-tokens", type=int, default=16384)
    parser.add_argument("--fps", type=float, default=1.0,
                        help="Video sampling rate; <=0 uses the server default")
    parser.add_argument("--limit", type=int, default=0, help="Run only the first N records (0 means all)")
    parser.add_argument("--qa-ids", type=str, default="",
                        help="Only run these comma-separated qa_id values")
    parser.add_argument("--levels", type=str, default="",
                        help="Only run these comma-separated levels, for example 1,2")
    parser.add_argument("--rerun", action="store_true")
    args = parser.parse_args()

    missing = [name for name in (BASE_URL_ENV, API_KEY_ENV, MODEL_NAME_ENV)
               if not _environment_value(name)]
    if missing:
        print(f"[ERROR] Missing required environment variables: {', '.join(missing)}",
              file=sys.stderr)
        sys.exit(1)
    base_url = _environment_value(BASE_URL_ENV).rstrip("/")
    api_key = _environment_value(API_KEY_ENV)
    model = _environment_value(MODEL_NAME_ENV)
    if args.workers < 1 or args.retries < 1 or args.limit < 0:
        parser.error("workers and retries must be positive; limit must be non-negative")

    if not args.annotation.exists():
        print(f"[ERROR] annotation not found: {args.annotation}", file=sys.stderr)
        sys.exit(1)
    if not args.video_root.is_dir():
        print(f"[ERROR] video root not found: {args.video_root}", file=sys.stderr)
        sys.exit(1)

    out_jsonl = args.results_dir / f"{args.tag}.jsonl"
    out_txt = args.results_dir / f"{args.tag}.txt"
    args.results_dir.mkdir(parents=True, exist_ok=True)

    with args.annotation.open("r", encoding="utf-8") as f:
        records: list[dict] = json.load(f)

    if args.qa_ids:
        keep = {x.strip() for x in args.qa_ids.split(",") if x.strip()}
        records = [r for r in records if str(r["qa_id"]) in keep]
    if args.levels:
        keep_lv = {x.strip() for x in args.levels.split(",") if x.strip()}
        records = [r for r in records if str(r["level"]) in keep_lv]
    if args.limit > 0:
        records = records[: args.limit]

    path_map: dict[str, Path | None] = {}
    for rec in records:
        vid = rec["video_id"]
        if vid not in path_map:
            p = resolve_video_path(args.video_root, vid)
            if p is None:
                print(f"[warn] video not found for {vid} under {args.video_root}")
            path_map[vid] = p

    done_ids = set() if args.rerun else load_done_qa_ids(out_jsonl)
    todo = [r for r in records if str(r["qa_id"]) not in done_ids]

    print(f"Annotation total: {len(records)}, already done: {len(done_ids)}, to run: {len(todo)}")
    print(f"Model: {model} @ {base_url}")
    print(f"Output jsonl: {out_jsonl}")
    print(f"Output txt  : {out_txt}")
    if not todo:
        _print_summary(out_jsonl, len(records))
        return

    if args.rerun:
        if out_jsonl.exists():
            out_jsonl.unlink()
        if out_txt.exists():
            out_txt.unlink()

    if not out_txt.exists():
        with out_txt.open("w", encoding="utf-8") as f:
            f.write(f"Model: {model}\nAnnotation: {args.annotation}\n")
            f.write("=" * 100 + "\n\n")

    client = OpenAI(api_key=api_key, base_url=base_url, timeout=1800)

    # Separate runnable records from records with missing local media.
    runnable: list[tuple[dict, str, str]] = []  # (rec, video_path, prompt)
    for rec in todo:
        vid = rec["video_id"]
        video_path = path_map.get(vid)
        if not video_path:
            print(f"[skip] {rec['qa_id']} | {vid}: no local video file")
            _append_result(out_jsonl, out_txt, {
                **_gt_block(rec),
                "pred_raw": "",
                "pred_answer": "",
                "pred_visual_evidence": [],
                "pred_audio_evidence": [],
                "status": "infer_error",
                "error": f"no local video file for video_id {vid}",
                "latency_s": 0.0,
            })
            continue
        prompt = PROMPT_TEMPLATE.format(
            question=rec["question"].strip(), options=rec["options"].strip()
        )
        runnable.append((rec, video_path, prompt))

    if not runnable:
        print("No runnable samples.")
        _print_summary(out_jsonl, len(records))
        return

    print(f"\nRunnable: {len(runnable)}, workers: {args.workers}, retries: {args.retries}")

    done_cnt = 0
    ok_cnt = correct_cnt = infer_cnt = parse_cnt = 0
    t_start = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(run_one, client, model,
                            video_path, prompt, args.max_tokens, args.retries, args.fps):
                (rec, video_path)
            for rec, video_path, prompt in runnable
        }
        for future in as_completed(futures):
            rec, _ = futures[future]
            t0 = time.time()
            try:
                text, err = future.result()
            except Exception as e:  # noqa: BLE001
                text, err = "", f"unexpected: {type(e).__name__}: {e}"
            latency = round(time.time() - t0, 2)

            if err is not None:
                result = {
                    **_gt_block(rec),
                    "pred_raw": "",
                    "pred_answer": "",
                    "pred_visual_evidence": [],
                    "pred_audio_evidence": [],
                    "status": "infer_error",
                    "error": err,
                    "latency_s": latency,
                }
            else:
                parsed, parse_err = parse_model_output(text)
                result = {
                    **_gt_block(rec),
                    "pred_raw": text,
                    "pred_answer": parsed.get("answer", ""),
                    "pred_visual_evidence": parsed.get("visual_evidence", []),
                    "pred_audio_evidence": parsed.get("audio_evidence", []),
                    "status": "parse_error" if parse_err else "ok",
                    "error": parse_err or "",
                    "latency_s": latency,
                }
            mark = _append_result(out_jsonl, out_txt, result)

            if result["status"] == "ok":
                ok_cnt += 1
                if mark == "✓":
                    correct_cnt += 1
                last_item = f"{rec['qa_id']} {mark}"
            elif result["status"] == "infer_error":
                infer_cnt += 1
                last_item = f"{rec['qa_id']} INFER_ERR {result['error'][:60]}"
            else:
                parse_cnt += 1
                last_item = f"{rec['qa_id']} PARSE_ERR"

            # Print a compact live view; complete records remain in JSONL and TXT.
            print(f"[{result['qa_id']}] {result['status']} {mark}")
            print(f"  Pred: {result['pred_answer']} | vis: {_ev_times(result['pred_visual_evidence'])}"
                  f" | aud: {_ev_times(result['pred_audio_evidence'])}")
            print(f"  GT  : {result['gt_answer']} | vis: {_ev_times(result.get('gt_visual_evidence', ''))}"
                  f" | aud: {_ev_times(result.get('gt_audio_evidence', ''))}", flush=True)

            done_cnt += 1
            _progress_line(done_cnt, len(runnable), t_start, ok_cnt, correct_cnt,
                           infer_cnt, parse_cnt, last_item)

    sys.stdout.write("\n")
    sys.stdout.flush()
    _print_summary(out_jsonl, len(records))


if __name__ == "__main__":
    main()
