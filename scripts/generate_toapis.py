#!/usr/bin/env python3
# Copyright (c) 2026 ToAPIs contributors. SPDX-License-Identifier: MIT
"""Optional ToAPIs image route. Quote by default; --live explicitly creates/resumes a task."""
import argparse
import copy
import json
from pathlib import Path
from generate import load_template
from toapis_client import Client, generate

ROOT = Path(__file__).resolve().parent
MODELS = ('gpt-image-2', 'gpt-image-2.5-flare')

def build_preset(model, aspect, resolution):
    if model not in MODELS or aspect not in ('1:1', '16:9', '9:16') or resolution not in ('1K', '2K', '4K'):
        raise ValueError('Unsupported model/aspect/resolution')
    presets = json.loads((ROOT / 'toapis_presets.json').read_text(encoding='utf-8'))
    preset = copy.deepcopy(presets[model])
    preset['request'].update(size=aspect, resolution=resolution)
    preset['request'].setdefault('metadata', {})['resolution'] = resolution
    preset['pricing_conditions']['resolution'] = resolution
    return preset

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--prompt')
    source.add_argument('--template', type=Path)
    parser.add_argument('--vars', default='{}')
    parser.add_argument('--model', choices=MODELS, default=MODELS[0])
    parser.add_argument('--aspect', choices=('1:1', '16:9', '9:16'), default='1:1')
    parser.add_argument('--size', choices=('1K', '2K', '4K'), default='1K')
    parser.add_argument('--output-dir', type=Path, default=ROOT.parent / 'toapis-output')
    parser.add_argument('--state', type=Path, default=ROOT.parent / '.toapis-state')
    parser.add_argument('--run-id', required=True, help='Keep unchanged to resume the same accepted task')
    parser.add_argument('--max-usd', default='0.10')
    parser.add_argument('--live', action='store_true')
    args = parser.parse_args(argv)
    variables = json.loads(args.vars)
    if not isinstance(variables, dict) or any(not isinstance(v, str) for v in variables.values()):
        parser.error('--vars must be an object of string values')
    prompt = load_template(args.template, variables) if args.template else args.prompt
    result = generate(Client(base='https://toapis.com', state=args.state),
                      build_preset(args.model, args.aspect, args.size), prompt,
                      output_dir=args.output_dir, max_usd=args.max_usd,
                      live=args.live, run_id=args.run_id)
    print(json.dumps(result, ensure_ascii=False))
    return result

if __name__ == '__main__':
    main()
