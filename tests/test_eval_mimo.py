"""Parser, path resolution and checkpoint handling for the OpenAI-compatible adapter."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'eval_mimo.py'
spec = importlib.util.spec_from_file_location('eval_mimo', SCRIPT)
mimo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mimo)


class ParseModelOutputTests(unittest.TestCase):
    def test_plain_json_object(self):
        parsed, err = mimo.parse_model_output(
            '{"answer":"C","visual_evidence":[{"time":"[00:01,00:05]"}],"audio_evidence":[]}')
        self.assertIsNone(err)
        self.assertEqual(parsed['answer'], 'C')
        self.assertEqual(parsed['visual_evidence'], [{'time': '[00:01,00:05]', 'description': ''}])

    def test_fenced_json_object(self):
        parsed, err = mimo.parse_model_output(
            '```json\n{"answer":"B","visual_evidence":[],"audio_evidence":[]}\n```')
        self.assertIsNone(err)
        self.assertEqual(parsed['answer'], 'B')

    def test_json_embedded_in_prose(self):
        parsed, err = mimo.parse_model_output('Here it is: {"answer":"A"} done.')
        self.assertIsNone(err)
        self.assertEqual(parsed['answer'], 'A')

    def test_lowercase_answer_is_normalized(self):
        parsed, _ = mimo.parse_model_output(
            '{"answer":"c","visual_evidence":[],"audio_evidence":[]}')
        self.assertEqual(parsed['answer'], 'C')

    def test_letter_only_fallback_is_flagged(self):
        parsed, err = mimo.parse_model_output('The answer is D')
        self.assertEqual(parsed['answer'], 'D')
        self.assertEqual(err, 'non-JSON output, only letter extracted')

    def test_unparseable_output_reports_error(self):
        parsed, err = mimo.parse_model_output('no answer here')
        self.assertEqual(parsed, {})
        self.assertTrue(err.startswith('cannot parse JSON'))

    def test_empty_output_reports_error(self):
        self.assertEqual(mimo.parse_model_output(''), ({}, 'empty content'))

    def test_evidence_accepts_strings_and_skips_empty_items(self):
        parsed, _ = mimo.parse_model_output(json.dumps({
            'answer': 'A',
            'visual_evidence': ['[00:01,00:02]', {'time': ''}, {'description': 'x'}],
            'audio_evidence': 'not a list'}))
        self.assertEqual(parsed['visual_evidence'],
                         [{'time': '', 'description': '[00:01,00:02]'},
                          {'time': '', 'description': 'x'}])
        self.assertEqual(parsed['audio_evidence'], [])

    def test_out_of_range_answer_is_dropped(self):
        parsed, _ = mimo.parse_model_output(
            '{"answer":"Z","visual_evidence":[],"audio_evidence":[]}')
        self.assertEqual(parsed['answer'], '')


class ResolveVideoPathTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_flat_layout(self):
        (self.root / '001.mp4').write_bytes(b'x')
        self.assertEqual(mimo.resolve_video_path(self.root, '001'), self.root / '001.mp4')

    def test_prefix_layout(self):
        (self.root / 'hxx').mkdir()
        (self.root / 'hxx' / 'hxx_001.mp4').write_bytes(b'x')
        self.assertEqual(mimo.resolve_video_path(self.root, 'hxx_001'),
                         self.root / 'hxx' / 'hxx_001.mp4')

    def test_missing_video_returns_none(self):
        self.assertIsNone(mimo.resolve_video_path(self.root, '999'))


class CheckpointTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'results.jsonl'

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, rows):
        self.path.write_text(''.join(json.dumps(r) + '\n' for r in rows), encoding='utf-8')

    def test_missing_file_has_no_attempts(self):
        self.assertEqual(mimo.load_attempts(self.path), {})
        self.assertEqual(mimo.load_done_qa_ids(self.path), set())

    def test_latest_attempt_wins(self):
        self.write([
            {'qa_id': 1, 'status': 'infer_error'},
            {'qa_id': 1, 'status': 'ok'},
            {'qa_id': 2, 'status': 'infer_error'},
        ])
        attempts = mimo.load_attempts(self.path)
        self.assertEqual(len(attempts), 2)
        self.assertEqual(attempts['1']['status'], 'ok')
        self.assertEqual(mimo.load_done_qa_ids(self.path), {'1'})

    def test_malformed_lines_are_skipped(self):
        self.path.write_text('{"qa_id": 1, "status": "ok"}\nnot json\n\n', encoding='utf-8')
        self.assertEqual(mimo.load_done_qa_ids(self.path), {'1'})

    def test_summary_counts_each_question_once(self):
        self.write([
            {'qa_id': 1, 'status': 'ok', 'level': 1, 'pred_answer': 'A', 'gt_answer': 'A'},
            {'qa_id': 1, 'status': 'ok', 'level': 1, 'pred_answer': 'A', 'gt_answer': 'A'},
            {'qa_id': 2, 'status': 'infer_error', 'level': 2},
        ])
        self.assertEqual(len(mimo.load_attempts(self.path)), 2)


if __name__ == '__main__':
    unittest.main()
