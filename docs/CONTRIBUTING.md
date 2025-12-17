<div align="center">

# Contributing to PassFX

**Code. Commit. Squash. Repeat.**

![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)
![Strictness: High](https://img.shields.io/badge/strictness-high-red)
![Pylint: 10.0](https://img.shields.io/badge/pylint-10.0%2F10-blue)

</div>

---

## 👋 Welcome, Traveller

So, you want to contribute to **PassFX**? Excellent choice.

We are building a fortress of solitude for secrets, living entirely in the terminal. We value clean code, linear history, and security paranoia above all else.

This document contains the **Rules of Engagement**. Follow them, and your PRs will be merged with glory. Ignore them, and our CI pipeline will reject you faster than a firewall on a bad day.

---

## 🏛️ Repository Governance

### The Benevolent Dictator

This repository is owned and maintained by **@dinesh-git17**.

- **The Codeowner has the final say.** (Yes, even if you disagree with the variable naming).
- **Approval is mandatory.** No code enters `main` without the Codeowner's blessing.
- **Direct commits to `main` are blocked.** We aren't savages.

### 🛡️ The Ironclad Branches

The `main` branch is protected by ancient magic (and GitHub settings):

- **Linear History Only:** We squash-merge everything. Your 17 "fix typo" commits will become one glorious unit of work.
- **Strict Status Checks:** If the build fails, the merge button physically disappears.
- **Freshness Required:** Your branch must be up-to-date with `main`. Rebase early, rebase often.

---

## 📜 The "Zero-Tolerance" Quality Gate

We run a tight ship. Our CI pipeline is not a suggestion; it is a law.

| Tool                  | The Requirement           | The Consequence                                                    |
| --------------------- | ------------------------- | ------------------------------------------------------------------ |
| **Black**             | Uncompromising formatting | CI Fails.                                                          |
| **Pylint**            | **10.0 / 10.0 Score**     | CI Fails if you get 9.99. We don't do "technical debt."            |
| **Attribution Guard** | No AI/LLM headers         | CI Fails if it smells like ChatGPT wrote it.                       |
| **Type Hints**        | 100% Coverage             | `def foo(bar)` is illegal. `def foo(bar: str) -> None` is the way. |
| **Tests**             | Must Pass                 | If you break it, you buy it.                                       |

> **Pro Tip:** Don't wait for CI to yell at you. Run `pre-commit` locally, or the git hooks will haunt your dreams.

---

## 🛠️ The Workflow

### 1. Clone & Equip

```bash
git clone [https://github.com/dinesh-git17/passfx.git](https://github.com/dinesh-git17/passfx.git)
cd passfx

# Summon the virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install the arsenal (Editable mode + Dev Tools)
pip install -e .
pip install black pylint isort pre-commit

# INSTALL THE HOOKS (Do not skip this)
pre-commit install
```

### 2. Branch Like a Pro

Always branch from the latest `main`.

```bash
git checkout main
git pull origin main
git checkout -b feature/cool-new-widget
```

- `feature/` - New shinies
- `fix/` - Squashing bugs
- `refactor/` - Cleaning up the mess
- `docs/` - Fixing my typos

### 3. Write Code (The Fun Part)

Write clean, secure, typed Python. When you think you're done, ask yourself: _"Would I trust my bank account with this code?"_

### 4. Local Quality Check

Before you commit, run the gauntlet:

```bash
# Format everything
black passfx/
isort passfx/

# The "Ref" (Linter)
pylint passfx/ --rcfile=.pylintrc --fail-under=10.0

# The Security Guard
python scripts/attribution_guard.py passfx/
```

### 5. Commit with Intent

We use **Conventional Commits**. If your commit message is "fixed stuff", we will close your PR.

**Format:** `type(scope): description`

**Examples:**

- ✅ `feat(ui): add matrix rain effect to login screen`
- ✅ `fix(crypto): plug memory leak in key derivation`
- ❌ `updated code`
- ❌ `wip`

---

## 🚀 The Pull Request Process

1.  **Push** your branch to origin.
2.  **Open a PR** against `main`.
3.  **Fill out the template.** If you delete the template, we delete your PR.
4.  **Wait for CI.** Go grab a coffee. If it turns red, fix it.
5.  **Code Review.** Address comments. We aren't criticizing _you_, just your code. (There's a difference).
6.  **Squash & Merge.** Welcome to the codebase!

---

## 🔐 Security Considerations

**This is a password manager. Paranoia is a feature, not a bug.**

1.  **Zero Knowledge:** We never log secrets. `print(password)` is a fireable offense.
2.  **Entropy:** Use `secrets` module only. `import random` is banned for anything security-related.
3.  **Sanitization:** Wipe variables from memory when done. Python GC is lazy; we try not to be.
4.  **No Telemetry:** We don't phone home. We don't even know where "home" is.

### Permitted Crypto Standards

- **Encryption:** AES-256-CBC (Fernet)
- **KDF:** PBKDF2-HMAC-SHA256 (480k iterations)
- **Permissions:** `0o700` for dirs, `0o600` for files.

---

## 🤖 A Note on AI / LLMs

We utilize an **Attribution Guard** in our CI, but we know you use AI. We all do.

### The Golden Rule of AI Assistance

If you are using an AI assistant (Claude, ChatGPT, etc.) to generate or refactor code for this repository, **you MUST prompt it to read `CLAUDE.md` first.**

`CLAUDE.md` is our "context file" designed specifically for LLMs. It contains:

- Our exact Pylint configuration
- Type hinting rules
- Architecture summaries
- The forbidden patterns that will fail CI

**Example Prompt:**

> "Read CLAUDE.md. Using those guidelines, please refactor the `CryptoManager` class to..."

**Remember:** Do not paste code directly if it includes "Generated by..." headers. We want **your** code. If an AI writes it, you better understand every line, because you're the one on the `git blame`.

---

<div align="center">
  <sub>Happy Hacking! 🕵️‍♂️</sub>
</div>
