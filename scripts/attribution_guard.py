#!/usr/bin/env python3
"""
Pre-commit hook to detect and block AI/LLM attribution in source files.
Prevents accidental commits containing references to AI-generated code.
"""

import re
import sys
from pathlib import Path

# Patterns that indicate AI attribution (case-insensitive)
FORBIDDEN_PATTERNS = [
    r"\bclaude\b",
    r"\banthropic\b",
    r"\bgenerated\s+by\s+claude\b",
    r"\bgenerated\s+by\s+ai\b",
    r"\bai[- ]generated\b",
    r"\bllm[- ]generated\b",
    r"\bgenerated\s+by\s+llm\b",
    r"\bgenerated\s+by\s+gpt\b",
    r"\bgenerated\s+by\s+copilot\b",
    r"\bco-authored-by:.*claude\b",
    r"\bco-authored-by:.*anthropic\b",
    r"\bwritten\s+by\s+ai\b",
    r"\bai\s+assistant\b",
    r"\bchatgpt\b",
    r"\bopenai\b",
]

# Files to exclude from checking (relative to repo root)
# These files legitimately need to reference forbidden terms
EXCLUDED_FILES = {
    "CLAUDE.md",
    ".claude/settings.json",
    "attribution_guard.py",
    ".pre-commit-config.yaml",
    "code-quality.yml",
    "docs/ARCHITECTURE.md",
    "docs/CONTRIBUTING.md",
    "docs/CHANGELOG.md",
    "README.md",
}

# Compile patterns for efficiency
COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in FORBIDDEN_PATTERNS]


def check_file(filepath: Path) -> list[tuple[int, str, str]]:
    """
    Check a file for forbidden attribution patterns.

    Returns list of (line_number, line_content, matched_pattern) tuples.
    """
    violations = []

    # Skip excluded files
    if filepath.name in EXCLUDED_FILES or str(filepath) in EXCLUDED_FILES:
        return violations

    try:
        content = filepath.read_text(encoding="utf-8", errors="ignore")
    except (OSError, UnicodeDecodeError):
        return violations

    for line_num, line in enumerate(content.splitlines(), start=1):
        for pattern in COMPILED_PATTERNS:
            match = pattern.search(line)
            if match:
                violations.append((line_num, line.strip(), match.group()))
                break  # One violation per line is enough

    return violations


def main() -> int:
    """
    Main entry point for the attribution guard hook.
    Returns 0 if no violations, 1 if violations found.
    """
    if len(sys.argv) < 2:
        print("Usage: attribution_guard.py <file1> [file2] ...")
        return 1

    all_violations: dict[str, list[tuple[int, str, str]]] = {}

    for filepath_str in sys.argv[1:]:
        filepath = Path(filepath_str)

        if not filepath.exists():
            continue

        if not filepath.is_file():
            continue

        violations = check_file(filepath)
        if violations:
            all_violations[filepath_str] = violations

    if all_violations:
        print("\n" + "=" * 70)
        print("ATTRIBUTION GUARD: COMMIT BLOCKED")
        print("=" * 70)
        print("\nForbidden AI/LLM attribution detected in the following files:\n")

        for filepath, violations in all_violations.items():
            print(f"  {filepath}:")
            for line_num, line_content, matched in violations:
                # Truncate long lines
                display_line = (
                    line_content[:60] + "..."
                    if len(line_content) > 60
                    else line_content
                )
                print(f"    Line {line_num}: '{matched}' in: {display_line}")
            print()

        print("=" * 70)
        print(
            "ACTION REQUIRED: Remove all AI attribution references before committing."
        )
        print("=" * 70 + "\n")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
