"""URL resolution for the generateContent adapter."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location(
    'eval_gemini', Path(__file__).resolve().parents[1] / 'scripts' / 'eval_gemini.py')
gemini = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gemini)


class ResolveUrlTests(unittest.TestCase):
    MODEL = 'gemini-3.8-flash'

    def test_prefix_form_appends_model_and_method(self):
        self.assertEqual(
            gemini.resolve_url('https://host/v1beta/models', self.MODEL),
            f'https://host/v1beta/models/{self.MODEL}:generateContent')

    def test_trailing_slash_on_prefix_is_normalized(self):
        self.assertEqual(
            gemini.resolve_url('https://host/v1beta/models/', self.MODEL),
            f'https://host/v1beta/models/{self.MODEL}:generateContent')

    def test_prefix_with_custom_relay_path(self):
        self.assertEqual(
            gemini.resolve_url('https://relay.example.com/proxy/v1beta/models', self.MODEL),
            f'https://relay.example.com/proxy/v1beta/models/{self.MODEL}:generateContent')

    def test_template_form_is_used_verbatim(self):
        self.assertEqual(
            gemini.resolve_url('https://relay.example.com/api/{model}:generateContent', self.MODEL),
            f'https://relay.example.com/api/{self.MODEL}:generateContent')

    def test_template_form_tolerates_trailing_slash(self):
        self.assertEqual(
            gemini.resolve_url('http://localhost:8080/v1/models/{model}:generateContent/', self.MODEL),
            f'http://localhost:8080/v1/models/{self.MODEL}:generateContent')

    def test_template_placeholder_is_replaced_everywhere(self):
        self.assertEqual(
            gemini.resolve_url('https://host/{model}/run?target={model}', self.MODEL),
            f'https://host/{self.MODEL}/run?target={self.MODEL}')


if __name__ == '__main__':
    unittest.main()
