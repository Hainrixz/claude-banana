"""Offline contracts for the optional script; no network or paid generation."""
import contextlib
import importlib.util
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import generate_toapis as adapter
import toapis_client as client

class Contracts(unittest.TestCase):
    def test_model_specific_resolution_and_count(self):
        for model in adapter.MODELS:
            for resolution in ('1K', '2K', '4K'):
                preset = adapter.build_preset(model, '16:9', resolution)
                self.assertEqual(preset['request']['n'], 1)
                self.assertEqual(preset['request']['resolution'], resolution)
                self.assertEqual(preset['pricing_conditions']['resolution'], resolution)
        with self.assertRaises(ValueError):
            adapter.build_preset('gpt-image-2-vip', '16:9', '1K')

    def test_quote_is_default_and_template_is_reused(self):
        with tempfile.TemporaryDirectory() as temp:
            template = Path(temp) / 'prompt.md'
            template.write_text('## Prompt Template\nA {subject}\n', encoding='utf-8')
            with patch.object(adapter, 'Client') as ctor, patch.object(adapter, 'generate', return_value={'mode':'quote_only'}) as generate, contextlib.redirect_stdout(io.StringIO()):
                adapter.main(['--template',str(template),'--vars','{"subject":"lamp"}','--run-id','fixed'])
                self.assertEqual(generate.call_args.args[2], 'A lamp')
                self.assertFalse(generate.call_args.kwargs['live'])
                self.assertEqual(ctor.call_args.kwargs['base'], 'https://toapis.com')

    def test_uncertain_post_is_not_repeated(self):
        with tempfile.TemporaryDirectory() as temp:
            c = client.Client(key='test-only-not-a-real-key',state=temp,base='https://toapis.com')
            preset = adapter.build_preset('gpt-image-2','1:1','1K')
            quote={'request':{**preset['request'],'prompt':'lamp'},'price':{},'estimated_usd':'0.015'}
            with patch.object(client,'prepare',return_value=quote), patch.object(c,'json',side_effect=TimeoutError('uncertain response')) as post:
                with self.assertRaises(TimeoutError):client.generate(c,preset,'lamp',live=True,run_id='same')
                with self.assertRaisesRegex(RuntimeError,'uncertain'):client.generate(c,preset,'lamp',live=True,run_id='same')
                self.assertEqual(post.call_count,1)

if __name__ == '__main__':unittest.main()
