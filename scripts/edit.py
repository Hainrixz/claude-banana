#!/usr/bin/env python3
"""
Image editing via Gemini API.

Usage:
    python edit.py --image path/to/image.png --instruction "change the background to a sunset"
    python edit.py --image photo.jpg --instruction "make it look like a watercolor painting" --output edited.png
"""

import argparse
import base64
import json
import os
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


def load_image(image_path):
    """Load image and return base64-encoded data with mime type."""
    path = Path(image_path)
    if not path.exists():
        print(f"Error: Image file not found: {image_path}")
        sys.exit(1)

    suffix = path.suffix.lower()
    mime_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }
    mime_type = mime_map.get(suffix, "image/png")

    with open(path, "rb") as f:
        image_data = f.read()

    return base64.b64encode(image_data).decode("utf-8"), mime_type


def edit_with_urllib(image_path, instruction, model_name, image_size, output_path):
    """Edit an image via the REST API using only the standard library."""
    api_key = load_api_key()
    if not api_key:
        print("Error: No API key found. Set GOOGLE_AI_API_KEY environment variable.")
        sys.exit(1)

    image_data_b64, mime_type = load_image(image_path)

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "inlineData": {
                            "mimeType": mime_type,
                            "data": image_data_b64,
                        }
                    },
                    {"text": instruction},
                ]
            }
        ],
        "generationConfig": {
            "responseModalities": ["IMAGE"],
        },
    }
    if image_size:
        payload["generationConfig"]["imageConfig"] = {"imageSize": image_size.upper()}

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

    candidates = result.get("candidates", [])
    if not candidates:
        print("Error: No candidates in response.")
        sys.exit(1)

    for part in candidates[0].get("content", {}).get("parts", []):
        if "inlineData" in part:
            image_bytes = base64.b64decode(part["inlineData"]["data"])
            with open(output_path, "wb") as f:
                f.write(image_bytes)
            return output_path

    print("Error: No image data in response.")
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Edit an image using Gemini API",
    )
    parser.add_argument("--image", required=True, help="Path to source image")
    parser.add_argument("--instruction", required=True, help="Edit instruction")
    parser.add_argument(
        "--model",
        default="gemini-3.1-flash-image-preview",
        help="Model name (default: gemini-3.1-flash-image-preview)",
    )
    parser.add_argument(
        "--size",
        default="2K",
        choices=["512", "1K", "2K", "4K"],
        help="Output image size (default: 2K)",
    )
    parser.add_argument(
        "--output",
        help="Output file path (default: edited_TIMESTAMP.png)",
    )

    args = parser.parse_args()

    if args.output:
        output_path = args.output
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"edited_{timestamp}.png"

    print(f"Source: {args.image}")
    print(f"Instruction: {args.instruction}")
    print(f"Model: {args.model} | Size: {args.size}")
    print(f"Output: {output_path}")
    print()

    edit_with_urllib(args.image, args.instruction, args.model, args.size, output_path)

    print(f"Edited image saved to: {output_path}")


if __name__ == "__main__":
    main()
