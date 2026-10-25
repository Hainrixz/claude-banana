#!/usr/bin/env python3
# Portions Copyright (c) 2026 Enrique Rocha (@soyenriquerocha) - see LICENSE for original authors
# SPDX-License-Identifier: MIT
# id: er-e8b2bc48
"""
Single image generation via Gemini API.

Usage:
    python generate.py --prompt "your prompt here"
    python generate.py --template path/to/template.md --vars '{"subject": "mountain lake"}'
    python generate.py --prompt "your prompt" --aspect 16:9 --size 2K --output my_image.png
"""

import argparse
import base64
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

import urllib.error
import urllib.request


def load_api_key():
    """Load API key from environment or .env file."""
    key = os.environ.get("GOOGLE_AI_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if key:
        return key

    # Try .env file
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("GOOGLE_AI_API_KEY="):
                    return line.split("=", 1)[1].strip().strip("\"'")
                if line.startswith("GEMINI_API_KEY="):
                    return line.split("=", 1)[1].strip().strip("\"'")

    return None


def load_template(template_path, variables):
    """Load a template file and resolve variables."""
    with open(template_path) as f:
        content = f.read()

    # Extract the prompt template section
    match = re.search(
        r"## Prompt Template\s*\n(.*?)(?=\n## |\Z)",
        content,
        re.DOTALL,
    )
    if not match:
        # Try "Example Output" as fallback
        match = re.search(
            r"## Example Output\s*\n(.*?)(?=\n## |\Z)",
            content,
            re.DOTALL,
        )

    if not match:
        print("Error: Could not find 'Prompt Template' section in template file.")
        sys.exit(1)

    prompt = match.group(1).strip()

    # Resolve variables
    if variables:
        for key, value in variables.items():
            prompt = prompt.replace(f"{{{key}}}", value)

    # Check for unresolved variables
    unresolved = re.findall(r"\{(\w+)\}", prompt)
    if unresolved:
        print(f"Warning: Unresolved variables: {', '.join(unresolved)}")
        print("Provide them with --vars '{\"variable\": \"value\"}'")

    return prompt


def generate_with_urllib(prompt, model_name, aspect_ratio, image_size, output_path):
    """Generate an image via the REST API using only the standard library."""
    api_key = load_api_key()
    if not api_key:
        print("Error: No API key found. Set GOOGLE_AI_API_KEY environment variable.")
        sys.exit(1)

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"

    # aspectRatio and imageSize belong inside imageConfig. Placed directly on
    # generationConfig the API replies 400 INVALID_ARGUMENT
    # ("Unknown name \"imageSize\" at 'generation_config'"), which made every
    # generation fail.
    image_config = {}
    if aspect_ratio:
        image_config["aspectRatio"] = aspect_ratio
    if image_size:
        image_config["imageSize"] = image_size.upper()

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseModalities": ["IMAGE"]},
    }
    if image_config:
        payload["generationConfig"]["imageConfig"] = image_config

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
    )

    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        print(f"API Error ({e.code}): {error_body}")
        sys.exit(1)

    # Extract image
    candidates = result.get("candidates", [])
    if not candidates:
        print("Error: No candidates in response.")
        print(json.dumps(result, indent=2))
        sys.exit(1)

    for part in candidates[0].get("content", {}).get("parts", []):
        if "inlineData" in part:
            image_data = base64.b64decode(part["inlineData"]["data"])
            with open(output_path, "wb") as f:
                f.write(image_data)
            return output_path

    print("Error: No image data in response.")
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(epilog='Hecho por Enrique Rocha (@soyenriquerocha) · tododeia.com', 
        description="Generate an image using Gemini API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--prompt", help="Text prompt for image generation")
    group.add_argument("--template", help="Path to a template .md file")

    parser.add_argument(
        "--vars",
        help='JSON string of template variables, e.g. \'{"subject": "mountain"}\'',
    )
    parser.add_argument(
        "--model",
        default="gemini-3.1-flash-image-preview",
        help="Model name (default: gemini-3.1-flash-image-preview)",
    )
    parser.add_argument(
        "--aspect",
        default="1:1",
        help="Aspect ratio (default: 1:1)",
    )
    parser.add_argument(
        "--size",
        default="2K",
        choices=["512", "1K", "2K", "4K"],
        help="Image size (default: 2K)",
    )
    parser.add_argument(
        "--output",
        help="Output file path (default: generated_TIMESTAMP.png)",
    )

    args = parser.parse_args()

    # Build prompt
    if args.template:
        variables = json.loads(args.vars) if args.vars else {}
        prompt = load_template(args.template, variables)
    else:
        prompt = args.prompt

    # Output path
    if args.output:
        output_path = args.output
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"generated_{timestamp}.png"

    print(f"Model: {args.model}")
    print(f"Size: {args.size} | Aspect: {args.aspect}")
    print(f"Prompt ({len(prompt.split())} words): {prompt[:100]}...")
    print(f"Output: {output_path}")
    print()

    generate_with_urllib(prompt, args.model, args.aspect, args.size, output_path)

    print(f"Image saved to: {output_path}")


if __name__ == "__main__":
    main()
