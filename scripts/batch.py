#!/usr/bin/env python3
"""
Batch image generation from templates.

Usage:
    python batch.py --template path/to/template.md --variations variations.json
    python batch.py --template path/to/template.md --variations variations.json --output-dir ./batch_output
    python batch.py --estimate --template path/to/template.md --variations variations.json

Variations file format (JSON array of variable sets):
[
    {"subject": "mountain lake", "time_of_day": "sunrise"},
    {"subject": "desert canyon", "time_of_day": "sunset"},
    {"subject": "coastal cliff", "time_of_day": "blue hour"}
]
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path


def load_template_prompt(template_path):
    """Extract prompt template from a template file."""
    with open(template_path) as f:
        content = f.read()

    match = re.search(
        r"## Prompt Template\s*\n(.*?)(?=\n## |\Z)",
        content,
        re.DOTALL,
    )
    if not match:
        print(f"Error: No 'Prompt Template' section found in {template_path}")
        sys.exit(1)

    return match.group(1).strip()


def resolve_prompt(template, variables):
    """Replace {placeholders} with variable values."""
    prompt = template
    for key, value in variables.items():
        prompt = prompt.replace(f"{{{key}}}", value)
    return prompt


def estimate_cost(count, size="2K", model="gemini-3.1-flash-image-preview"):
    """Estimate batch generation cost."""
    pricing = {
        "gemini-3.1-flash-image-preview": {"512": 0.034, "1K": 0.067, "2K": 0.134, "4K": 0.268},
        "gemini-2.5-flash-image": {"512": 0.020, "1K": 0.039, "2K": 0.039, "4K": 0.039},
    }

    model_pricing = pricing.get(model, pricing["gemini-3.1-flash-image-preview"])
    cost_per_image = model_pricing.get(size, model_pricing["2K"])
    total = cost_per_image * count

    return cost_per_image, total


def main():
    parser = argparse.ArgumentParser(
        description="Batch generate images from a template with variable sets",
    )
    parser.add_argument("--template", required=True, help="Path to template .md file")
    parser.add_argument("--variations", required=True, help="Path to variations JSON file")
    parser.add_argument(
        "--model",
        default="gemini-3.1-flash-image-preview",
        help="Model name (default: gemini-3.1-flash-image-preview)",
    )
    parser.add_argument("--size", default="2K", choices=["512", "1K", "2K", "4K"])
    parser.add_argument("--aspect", default="1:1", help="Aspect ratio (default: 1:1)")
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Output directory (default: batch_TIMESTAMP/)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="Delay between requests in seconds (default: 2.0)",
    )
    parser.add_argument(
        "--estimate",
        action="store_true",
        help="Only estimate cost, don't generate",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show resolved prompts without generating",
    )

    args = parser.parse_args()

    # Load template and variations
    template = load_template_prompt(args.template)

    with open(args.variations) as f:
        variations = json.load(f)

    if not isinstance(variations, list):
        print("Error: Variations file must contain a JSON array.")
        sys.exit(1)

    count = len(variations)
    print(f"Template: {args.template}")
    print(f"Variations: {count}")
    print(f"Model: {args.model} | Size: {args.size} | Aspect: {args.aspect}")

    # Cost estimate
    cost_per, total_cost = estimate_cost(count, args.size, args.model)
    print(f"Estimated cost: ${total_cost:.3f} ({count} x ${cost_per:.3f})")
    print()

    if args.estimate:
        print("Cost estimate only — no images generated.")
        return

    # Dry run — show prompts
    if args.dry_run:
        for i, var_set in enumerate(variations, 1):
            prompt = resolve_prompt(template, var_set)
            unresolved = re.findall(r"\{(\w+)\}", prompt)
            status = f" [UNRESOLVED: {', '.join(unresolved)}]" if unresolved else ""
            print(f"--- Variation {i}{status} ---")
            print(prompt)
            print()
        return

    # Output directory
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path(f"batch_{timestamp}")

    output_dir.mkdir(parents=True, exist_ok=True)

    # Import generate function
    script_dir = Path(__file__).parent
    sys.path.insert(0, str(script_dir))
    from generate import generate_with_urllib, load_api_key

    if not load_api_key():
        print("Error: No API key found. Set GOOGLE_AI_API_KEY environment variable.")
        sys.exit(1)

    # Generate
    results = []
    for i, var_set in enumerate(variations, 1):
        prompt = resolve_prompt(template, var_set)
        output_path = str(output_dir / f"variation_{i:03d}.png")

        print(f"[{i}/{count}] Generating...")

        try:
            generate_with_urllib(prompt, args.model, args.aspect, args.size, output_path)

            results.append({"index": i, "status": "success", "path": output_path, "variables": var_set})
            print(f"  Saved: {output_path}")
        except Exception as e:
            results.append({"index": i, "status": "error", "error": str(e), "variables": var_set})
            print(f"  Error: {e}")

        # Rate limit delay (skip after last item)
        if i < count:
            time.sleep(args.delay)

    # Summary
    success = sum(1 for r in results if r["status"] == "success")
    errors = count - success
    actual_cost = cost_per * success

    print()
    print(f"Batch complete: {success}/{count} successful, {errors} errors")
    print(f"Actual cost: ~${actual_cost:.3f}")
    print(f"Output directory: {output_dir}")

    # Save manifest
    manifest_path = output_dir / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(
            {
                "template": str(args.template),
                "model": args.model,
                "size": args.size,
                "aspect": args.aspect,
                "timestamp": datetime.now().isoformat(),
                "results": results,
            },
            f,
            indent=2,
        )
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
