"""Grounded metric formulas and the API example's final scoring workflow."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'eval_example.py'
spec = importlib.util.spec_from_file_location('eval_example', SCRIPT)
evaluation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evaluation)


class GroundedScoreTests(unittest.TestCase):
    def setUp(self):
        self.record = {
            'qa_id': 1, 'video_id': '001', 'question': 'What happened?',
            'options': 'A. A sound.\nB. Silence.', 'answer': 'A',
            'level': 1, 'capability': 'Temporal Alignment',
            'evidence': {
                'audio': [{'time': '[00:00,00:10]'}],
                'visual': [{'time': '[00:00,00:10]'}],
            },
        }
        self.prediction = {
            'qa_id': 1, 'answer': 'A',
            'audio_evidence': [[0, 10]], 'visual_evidence': [[0, 10]],
        }

    def report(self):
        return evaluation.compute_grounded_scores(
            [self.record], {'1': {'status': 'ok', 'prediction': self.prediction}})

    def test_exact_reference_gets_full_scores(self):
        overall = self.report()['overall']
        self.assertEqual(overall['count'], 1)
        for name in evaluation.SCORE_NAMES:
            self.assertEqual(overall[name], 100)

    def test_document_example_distinguishes_bottleneck_from_mean(self):
        self.prediction['audio_evidence'] = [[0, 9]]
        self.prediction['visual_evidence'] = [[0, 1]]
        self.assertEqual(self.report()['overall'], {
            'count': 1, 'Acc.': 100, 'C.G.': 100, 'B.G.': 10,
            'Mean': 50, 'Thr@0.3': 100, 'Thr@0.5': 100, 'Thr@0.7': 0,
        })

    def test_wrong_answer_zeroes_all_scores(self):
        self.prediction['answer'] = 'B'
        for name in evaluation.SCORE_NAMES:
            self.assertEqual(self.report()['overall'][name], 0)

    def test_wide_prediction_has_full_coverage_but_poor_iou(self):
        self.prediction['audio_evidence'] = [[0, 100]]
        self.prediction['visual_evidence'] = [[0, 100]]
        scores = self.report()['overall']
        self.assertEqual(scores['C.G.'], 100)
        self.assertEqual(scores['B.G.'], 10)
        self.assertEqual(scores['Mean'], 10)
        self.assertEqual(scores['Thr@0.3'], 0)

    def test_overlapping_intervals_are_not_double_counted(self):
        self.prediction['audio_evidence'] = [[0, 7], [3, 10], [0, 7]]
        self.assertEqual(self.report()['overall']['B.G.'], 100)
        self.assertEqual(evaluation.temporal_iou([(0, 10)], [(0, 7), (3, 10)]), 1)
        self.assertAlmostEqual(evaluation.temporal_iou([(0, 2), (8, 10)], [(0, 10)]), 0.4)

    def test_coverage_counts_original_segments_once(self):
        references = [(0, 10), (5, 15), (20, 30)]
        self.assertAlmostEqual(evaluation.evidence_coverage([(6, 7), (6, 7)], references), 2 / 3)
        self.assertEqual(evaluation.evidence_coverage([(10, 20)], [(0, 10), (20, 30)]), 0)

    def test_thresholds_are_inclusive(self):
        for threshold in (0.3, 0.5, 0.7):
            with self.subTest(threshold=threshold):
                interval = [[0, threshold * 10]]
                self.prediction['audio_evidence'] = interval
                self.prediction['visual_evidence'] = interval
                self.assertEqual(self.report()['overall'][f'Thr@{threshold}'], 100)

    def test_empty_prediction_evidence_is_valid(self):
        self.prediction['audio_evidence'] = []
        self.prediction['visual_evidence'] = []
        report = self.report()
        self.assertEqual(report['overall']['Acc.'], 100)
        for name in evaluation.SCORE_NAMES[1:]:
            self.assertEqual(report['overall'][name], 0)
        self.assertEqual(report['invalid_predictions'], [])

    def test_missing_and_failed_predictions_stay_in_denominator(self):
        records = [dict(self.record, qa_id=i, level=i) for i in (1, 2, 3)]
        latest = {
            '1': {'status': 'ok', 'prediction': self.prediction},
            '2': {'status': 'infer_error', 'prediction': self.prediction},
        }
        report = evaluation.compute_grounded_scores(records, latest)
        self.assertEqual(report['overall']['count'], 3)
        for name in evaluation.SCORE_NAMES:
            self.assertAlmostEqual(report['overall'][name], 100 / 3)
        self.assertEqual(report['by_level']['2']['Acc.'], 0)
        self.assertEqual(report['by_level']['3']['Acc.'], 0)
        self.assertEqual(report['by_capability']['Temporal Alignment']['count'], 3)

    def test_invalid_prediction_is_reported_and_scores_zero(self):
        for bad in ([[10, 0]], [[0, float('nan')]], [[0, float('inf')]],
                    [[-1, 5]], [[0, 0]], [[True, 5]], None):
            with self.subTest(evidence=bad):
                self.prediction['audio_evidence'] = bad
                report = self.report()
                self.assertEqual(len(report['invalid_predictions']), 1)
                for name in evaluation.SCORE_NAMES:
                    self.assertEqual(report['overall'][name], 0)

    def test_invalid_reference_raises_even_for_missing_prediction(self):
        for evidence in ([], [{'time': '[00:10,00:00]'}], [{'time': '[00:60,01:10]'}]):
            with self.subTest(evidence=evidence):
                self.record['evidence']['audio'] = evidence
                with self.assertRaisesRegex(ValueError, 'qa_id=1'):
                    evaluation.compute_grounded_scores([self.record], {})

    def test_scores_are_recomputed_from_prediction_not_cached_correct_flag(self):
        report = evaluation.compute_grounded_scores([self.record], {
            '1': {'status': 'ok', 'correct': False, 'prediction': self.prediction},
            'unrelated': {'status': 'ok', 'prediction': self.prediction},
        })
        self.assertEqual(report['overall']['count'], 1)
        self.assertEqual(report['overall']['Acc.'], 100)
        self.assertEqual(report['per_question'][0]['scores']['C.G.'], 1)

    def test_empty_dataset_has_finite_zero_scores(self):
        report = evaluation.compute_grounded_scores([], {})
        self.assertEqual(report['overall']['count'], 0)
        self.assertTrue(all(report['overall'][name] == 0 for name in evaluation.SCORE_NAMES))

    def test_cli_final_scores_and_resume_without_duplicate_questions(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            annotations, output = directory / 'annotations.json', directory / 'outputs'
            second = dict(copy.deepcopy(self.record), qa_id=2, answer='B', level=2)
            annotations.write_text(json.dumps([self.record, second]), encoding='utf-8')
            command = [sys.executable, str(SCRIPT), '--mock', '--annotations', str(annotations),
                       '--output-dir', str(output), '--batch-size', '1', '--workers', '2']
            subprocess.run(command, capture_output=True, text=True, check=True)
            scores = json.loads((output / 'grounded_scores.json').read_text())
            summary = json.loads((output / 'summary.json').read_text())
            self.assertEqual(scores['overall']['Acc.'], 50)
            self.assertEqual(scores['overall']['C.G.'], 0)
            self.assertEqual(scores['overall']['Mean'], 0)
            self.assertTrue(scores['mock'])
            self.assertEqual(summary['grounded_scores'], scores['overall'])
            self.assertEqual(summary['by_level']['1']['grounded_scores']['Acc.'], 100)
            resumed = subprocess.run(command, capture_output=True, text=True, check=True)
            self.assertIn('resumed=2 | pending=0', resumed.stdout)
            self.assertEqual(json.loads((output / 'grounded_scores.json').read_text()), scores)
            self.assertEqual(len((output / 'results.jsonl').read_text().splitlines()), 2)


if __name__ == '__main__':
    unittest.main()
