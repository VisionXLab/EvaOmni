"""Behavioral checks for grounded metrics and validation policies."""
import copy
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('evaluate', Path(__file__).resolve().parents[1] / 'scripts/evaluate.py')
score = importlib.util.module_from_spec(spec)
spec.loader.exec_module(score)


class MetricTests(unittest.TestCase):
    def setUp(self):
        self.ann = {'qa_id': 1, 'answer': 'A', 'level': 1, 'capability': 'test',
                    'evidence': {'audio': [{'time': '[00:10,00:20]'}],
                                 'visual': [{'time': '[00:10,00:20]'}]}}
        self.pred = {'qa_id': 1, 'answer': 'A', 'audio_evidence': [[10, 20]],
                     'visual_evidence': [[10, 20]]}

    def metrics(self):
        return score.evaluate([self.ann], [self.pred])['overall']

    def test_exact_reference(self):
        self.assertEqual(self.metrics(), {'count': 1, 'accuracy': 100, 'cg': 100, 'bg': 100})

    def test_wrong_answer(self):
        self.pred['answer'] = 'B'
        self.assertEqual([self.metrics()[k] for k in ('accuracy', 'cg', 'bg')], [0, 0, 0])

    def test_broad_interval_has_coverage_but_lower_iou(self):
        self.pred['audio_evidence'] = [[0, 100]]
        self.assertEqual(self.metrics()['cg'], 100)
        self.assertEqual(self.metrics()['bg'], 10)

    def test_bottleneck_uses_worse_modality(self):
        self.pred['visual_evidence'] = [[10, 15]]
        self.assertEqual(self.metrics()['cg'], 100)
        self.assertEqual(self.metrics()['bg'], 50)

    def test_union_does_not_double_count(self):
        self.assertEqual(score.iou([(0, 7), (3, 10)], [(0, 10)]), 1)

    def test_endpoint_touch_is_not_a_hit(self):
        self.assertEqual(score.coverage([(0, 10)], [(10, 20)]), 0)

    def test_reference_segments_count_once(self):
        self.assertEqual(score.coverage([(0, 15), (5, 10)], [(0, 10), (20, 30)]), 0.5)

    def test_missing_prediction_stays_in_denominator(self):
        second = copy.deepcopy(self.ann)
        second['qa_id'] = 2
        out = score.evaluate([self.ann, second], [self.pred])
        self.assertEqual(out['overall']['accuracy'], 50)
        self.assertEqual(out['diagnostics']['missing_predictions'], ['2'])

    def test_empty_evidence_is_valid(self):
        self.pred['audio_evidence'] = []
        out = score.evaluate([self.ann], [self.pred])
        self.assertEqual(out['overall']['accuracy'], 100)
        self.assertEqual(out['overall']['cg'], 50)
        self.assertEqual(out['overall']['bg'], 0)

    def test_malformed_prediction_scores_zero_and_is_reported(self):
        self.pred['audio_evidence'] = [[20, 10]]
        out = score.evaluate([self.ann], [self.pred])
        self.assertEqual(out['overall']['accuracy'], 0)
        self.assertEqual(len(out['diagnostics']['invalid_predictions']), 1)

    def test_duplicate_ids_rejected(self):
        with self.assertRaises(ValueError):
            score.evaluate([self.ann], [self.pred, self.pred])

    def test_invalid_reference_errors_by_default(self):
        self.ann['evidence']['audio'][0]['time'] = '[00;10,00:20]'
        with self.assertRaises(ValueError):
            self.metrics()

    def test_explicit_skip_reference_reports_issue_and_keeps_question(self):
        self.ann['evidence']['audio'][0]['time'] = 'bad'
        out = score.evaluate([self.ann], [self.pred], 'skip-intervals')
        self.assertEqual(out['overall'], {'count': 1, 'accuracy': 100, 'cg': 50, 'bg': 0})
        self.assertEqual(len(out['diagnostics']['reference_issues']), 1)

    def test_nonfinite_negative_and_zero_duration_rejected(self):
        for interval in ([0, float('nan')], [0, float('inf')], [-1, 2], [1, 1], [True, 3]):
            with self.subTest(interval=interval), self.assertRaises(ValueError):
                score.parse_interval(interval)

    def test_clock_timestamp_and_answer_normalization(self):
        self.assertEqual(score.parse_interval('[01:00:10,01:00:20]'), (3610, 3620))
        self.pred['answer'] = ' a '
        self.assertEqual(self.metrics()['accuracy'], 100)


if __name__ == '__main__':
    unittest.main()
