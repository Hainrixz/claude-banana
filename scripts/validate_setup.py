#!/usr/bin/env python3
# Portions Copyright (c) 2026 Enrique Rocha (@soyenriquerocha) - see LICENSE for original authors
# SPDX-License-Identifier: MIT
# id: er-e8b2bc48
"""
Validate Claude Banana setup — checks environment, dependencies, and API access.

Usage:
    python validate_setup.py
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def check(name, passed, detail=""):
    """Print a check result."""
    status = "PASS" if passed else "FAIL"
    marker = "+" if passed else "-"
    msg = f"  [{marker}] {name}"
    if detail:
        msg += f" — {detail}"
    print(msg)
    return passed


def main():
    print("Claude Banana Setup Validation")
    print("=" * 40)
    print()

    project_root = Path(__file__).parent.parent
    passed = 0
    total = 0

    # 1. Python version
    total += 1
    py_version = sys.version_info
    passed += check(
        "Python version",
        py_version >= (3, 6),
        f"{py_version.major}.{py_version.minor}.{py_version.micro}",
    )

    # 2. Project structure
    total += 1
    required_dirs = ["knowledge", "templates/examples", "presets", "scripts", ".claude/agents"]
    missing_dirs = [d for d in required_dirs if not (project_root / d).is_dir()]
    passed += check(
        "Project structure",
        len(missing_dirs) == 0,
        f"Missing: {', '.join(missing_dirs)}" if missing_dirs else "All directories present",
    )

    # 3. Knowledge base files
    total += 1
    knowledge_files = [
        "prompt-formula.md",
        "prompt-engineering.md",
        "domain-modes.md",
        "techniques-catalog.md",
        "anti-patterns.md",
        "model-notes.md",
        "safety-and-text.md",
        "platform-adaptation.md",
        "post-processing.md",
    ]
    missing_kb = [f for f in knowledge_files if not (project_root / "knowledge" / f).exists()]
    passed += check(
        "Knowledge base",
        len(missing_kb) == 0,
        f"Missing: {', '.join(missing_kb)}" if missing_kb else f"All {len(knowledge_files)} files present",
    )

    # 4. Agent definition
    total += 1
    agent_path = project_root / ".claude" / "agents" / "prompt-architect.md"
    passed += check(
        "Agent definition",
        agent_path.exists(),
        str(agent_path.relative_to(project_root)),
    )

    # 5. Templates
    total += 1
    templates_dir = project_root / "templates" / "examples"
    template_count = len(list(templates_dir.glob("*.md"))) if templates_dir.exists() else 0
    passed += check(
        "Templates",
        template_count >= 25,
        f"{template_count} templates found",
    )

    # 6. API key
    total += 1
    api_key = os.environ.get("GOOGLE_AI_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        env_path = project_root / ".env"
        if env_path.exists():
            with open(env_path) as f:
                for line in f:
                    if line.strip().startswith(("GOOGLE_AI_API_KEY=", "GEMINI_API_KEY=")):
                        api_key = line.split("=", 1)[1].strip().strip("\"'")
                        break

    passed += check(
        "API key",
        bool(api_key),
        "Found" if api_key else "Not found — set GOOGLE_AI_API_KEY env var or create .env file",
    )

    # 8. ImageMagick (optional)
    total += 1
    magick_path = shutil.which("magick") or shutil.which("convert")
    if magick_path:
        try:
            result = subprocess.run(
                [magick_path, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            version_line = result.stdout.split("\n")[0] if result.stdout else "unknown"
            passed += check("ImageMagick", True, version_line[:60])
        except (subprocess.TimeoutExpired, OSError):
            passed += check("ImageMagick", False, "Found but could not get version")
    else:
        check("ImageMagick", False, "Not found (optional — needed for post-processing)")

    # 9. FFmpeg (optional)
    total += 1
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            version_line = result.stdout.split("\n")[0] if result.stdout else "unknown"
            passed += check("FFmpeg", True, version_line[:60])
        except (subprocess.TimeoutExpired, OSError):
            passed += check("FFmpeg", False, "Found but could not get version")
    else:
        check("FFmpeg", False, "Not found (optional — needed for animation)")

    # Summary
    print()
    print(f"Results: {passed}/{total} checks passed")

    if passed < total:
        print()
        print("Required fixes:")
        if not api_key:
            print("  - Set your API key: export GOOGLE_AI_API_KEY='your-key-here'")
            print("    Get a free key at: https://aistudio.google.com/apikey")
    else:
        print("All checks passed. Ready to generate.")

    return 0 if passed >= 6 else 1  # Allow optional tools to fail


if __name__ == "__main__":
    sys.exit(main())
