#!/usr/bin/env python3
"""
Commit-msg hook to detect and block AI/LLM attribution in commit messages.
Prevents commits containing references to AI-generated code.
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
    r"\bgenerated\s+with\s+claude\b",
    r"\bclaude[\s-]*code\b",
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

# Compile patterns for efficiency
COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in FORBIDDEN_PATTERNS]


def check_commit_message(message: str) -> list[tuple[int, str, str]]:
    """
    Check a commit message for forbidden attribution patterns.

    Returns list of (line_number, line_content, matched_pattern) tuples.
    """
    violations = []

    for line_num, line in enumerate(message.splitlines(), start=1):
        # Skip comment lines (git uses # for comments in commit messages)
        if line.strip().startswith("#"):
            continue

        for pattern in COMPILED_PATTERNS:
            match = pattern.search(line)
            if match:
                violations.append((line_num, line.strip(), match.group()))
                break  # One violation per line is enough

    return violations


def main() -> int:
    """
    Main entry point for the commit message attribution guard hook.

    The commit message file path is passed as the first argument by git.
    Falls back to .git/COMMIT_EDITMSG if no argument provided.
    Returns 0 if no violations, 1 if violations found.
    """
    if len(sys.argv) >= 2:
        commit_msg_file = Path(sys.argv[1])
    else:
        # Default location for git commit messages
        commit_msg_file = Path(".git/COMMIT_EDITMSG")

    if not commit_msg_file.exists():
        print(f"Error: Commit message file not found: {commit_msg_file}")
        return 1

    try:
        message = commit_msg_file.read_text(encoding="utf-8", errors="ignore")
    except OSError as e:
        print(f"Error reading commit message: {e}")
        return 1

    violations = check_commit_message(message)

    if violations:
        print("\n" + "=" * 70)
        print("COMMIT MESSAGE GUARD: COMMIT BLOCKED")
        print("=" * 70)
        print("\nForbidden AI/LLM attribution detected in commit message:\n")

        for line_num, line_content, matched in violations:
            # Truncate long lines
            display_line = (
                line_content[:60] + "..." if len(line_content) > 60 else line_content
            )
            print(f"  Line {line_num}: '{matched}' in: {display_line}")

        print("\n" + "=" * 70)
        print("ACTION REQUIRED: Remove AI attribution from commit message.")
        print("Edit your commit message and remove references to Claude, AI, etc.")
        print("=" * 70 + "\n")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
