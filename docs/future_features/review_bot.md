# PassFX Review Bot - Architecture Design

This document describes the proposed GitHub Pull Request Review Bot for the PassFX repository.

---

## Overview & Motivation

PassFX is a security-critical password manager. Every code change touching credentials, encryption, or vault logic requires rigorous review. Human reviewers are essential but face constraints:

1. **Consistency** - Humans miss things. Fatigue, context switching, and time pressure lead to overlooked issues.
2. **Availability** - Maintainers cannot review every PR immediately.
3. **Enforcement** - Repository rules (no secrets, no debug prints, no AI attribution) require automated verification.

A review bot supplements human review by:

- Enforcing deterministic policies before human review begins
- Flagging suspicious patterns that warrant closer inspection
- Providing consistent, tireless coverage of security invariants
- Reducing reviewer cognitive load on routine checks

The bot does not replace human judgment. It amplifies it.

---

## Desired Bot Responsibilities

### Tier 1: Policy-Based Checks (Deterministic)

These checks are rule-based and produce binary pass/fail results. No AI involvement.

| Check | Description | Severity |
|-------|-------------|----------|
| **PR Template Compliance** | Verify all sections filled (Summary, Motivation, Type, Testing, Risk, Security, Checklist) | Blocking |
| **Attribution Guard** | No mentions of Claude, AI, assistant, or similar terms in code/commits | Blocking |
| **Secret Detection** | Scan for hardcoded credentials, API keys, passwords in diffs | Blocking |
| **Debug Statement Detection** | No `print()`, `console.log()`, or debug-only code in production paths | Warning |
| **Forbidden Imports** | No `pickle`, no `random` (for crypto), no disallowed modules | Blocking |
| **File Permission Constants** | Verify 0o600/0o700 permission constants in file I/O code | Warning |
| **TODO/FIXME Audit** | Flag unscoped TODOs in critical paths (`core/`) | Warning |

### Tier 2: Change Scope Analysis (Heuristic)

Categorize the PR based on files touched. Adjust review strictness accordingly.

| Scope | Files | Review Intensity |
|-------|-------|------------------|
| **Critical** | `core/crypto.py`, `core/vault.py`, `core/exceptions.py` | Maximum scrutiny |
| **High** | `core/models.py`, `utils/generator.py`, `utils/io.py` | Elevated attention |
| **Medium** | `screens/*`, `widgets/*`, `ui/*` | Standard review |
| **Low** | `docs/*`, `tests/*`, `.github/*` | Light review |

The bot should explicitly state: "This PR touches critical crypto code. Elevated review recommended."

### Tier 3: AI-Assisted Analysis (Lightweight)

Use a cheap OpenAI model for pattern detection and high-level reasoning. Not for rewriting code.

| Analysis | Purpose | Trigger |
|----------|---------|---------|
| **Diff Summary** | One-paragraph explanation of what changed | Always |
| **Risk Assessment** | Identify potentially risky changes | Critical/High scope PRs |
| **Missing Tests** | Flag new code without corresponding test coverage | When new functions added |
| **Security Pattern Detection** | Identify suspicious patterns (timing attacks, unchecked inputs) | Critical scope PRs |
| **Consistency Check** | Verify changes align with existing patterns in codebase | Medium+ scope PRs |

---

## Non-Goals

The bot will **NOT**:

| Non-Goal | Rationale |
|----------|-----------|
| Rewrite or suggest code | AI-generated code requires human validation; creates noise |
| Block merges on style opinions | Subjective feedback frustrates contributors |
| Review every push | Only review when explicitly requested or CI passes |
| Hallucinate repository rules | Rules are codified in CLAUDE.md and enforced deterministically |
| Replace human reviewers | Bot augments, not replaces, human judgment |
| Auto-approve PRs | All approvals remain human decisions |
| Review draft PRs | Drafts indicate work-in-progress; wait for ready status |
| Operate on failing CI | If CI fails, no point reviewing code that won't pass |

---

## Proposed Architecture Options

### Option 1: GitHub Action (Recommended)

**Implementation**: Workflow triggered by `workflow_dispatch` or PR comment command.

```
[PR Created/Updated]
       |
       v
[CI Passes?] --No--> [Skip Review]
       |
      Yes
       v
[Review Requested?] --No--> [Skip Review]
       |
      Yes
       v
[Run Policy Checks (Tier 1)]
       |
       v
[Analyze Change Scope (Tier 2)]
       |
       v
[Call OpenAI API (Tier 3)]
       |
       v
[Post Review Comment]
```

**Pros**:
- No external infrastructure to maintain
- GitHub Actions minutes are included in plan (2,000-3,000/month for Pro)
- Secrets management via GitHub Secrets
- Native integration with PR events
- Version controlled alongside code
- Easy to audit and modify

**Cons**:
- Cannot be added to CODEOWNERS directly (GitHub limitation)
- Actions-based bots use `github-actions[bot]` identity
- Cannot approve PRs as a formal "reviewer" without PAT workaround

**Mitigation**: Use PR comments for review feedback. Reserve formal approvals for human maintainers.

### Option 2: GitHub App

**Implementation**: Standalone application with webhook listener, hosted externally.

**Pros**:
- First-class GitHub identity (e.g., `passfx-review-bot[bot]`)
- Can be installed across multiple repositories
- More granular permission model
- Can respond to any webhook event

**Cons**:
- Requires external hosting (Lambda, Heroku, VPS)
- Additional infrastructure to secure and maintain
- Private key management for JWT authentication
- Cannot be added to CODEOWNERS (GitHub limitation for bots)
- Overkill for single-repository use case

**Recommendation**: Defer to Option 1. GitHub App complexity is not justified for PassFX's single-repo context.

### Option 3: External Service (SaaS)

**Implementation**: Use existing solution like CodeRabbit, PR-Agent, or similar.

**Pros**:
- Zero implementation effort
- Battle-tested by thousands of repositories
- Maintained by dedicated teams
- Often includes advanced features (codebase-aware analysis)

**Cons**:
- Code leaves repository (security concern for password manager)
- Monthly subscription cost ($15-50/user/month for enterprise features)
- Cannot customize rules to PassFX-specific policies
- Vendor lock-in
- Often noisy (too many comments per PR)

**Recommendation**: Not suitable. PassFX requires custom policy enforcement and cannot send code to external services.

---

## Recommended Approach

**GitHub Action with manual trigger + CI gate**.

### Workflow Trigger Design

```yaml
name: Review Bot

on:
  # Manual trigger via GitHub UI or API
  workflow_dispatch:
    inputs:
      pr_number:
        description: 'PR number to review'
        required: true
        type: number
      skip_ai:
        description: 'Skip AI analysis (policy checks only)'
        required: false
        type: boolean
        default: false

  # Trigger on specific comment command
  issue_comment:
    types: [created]

  # Optional: Auto-trigger when CI passes (disabled by default)
  # check_suite:
  #   types: [completed]
```

### Request Mechanisms

Contributors can request bot review via:

1. **GitHub UI**: Actions tab > "Review Bot" > Run workflow > Enter PR number
2. **PR Comment**: Post `@passfx-bot review` in PR (parsed by workflow)
3. **Maintainer Script**: `gh workflow run review-bot.yml -f pr_number=123`

### CI Gate Logic

```python
# Pseudocode
def should_review(pr):
    if pr.draft:
        return False, "PR is draft"

    if not all_checks_passed(pr):
        return False, "CI has not passed"

    if pr.state != "open":
        return False, "PR is not open"

    return True, None
```

### Review Output Format

```markdown
## PassFX Review Bot

**Scope**: Critical (touches `core/crypto.py`)
**Risk Level**: High
**CI Status**: Passed

---

### Policy Checks

| Check | Status | Details |
|-------|--------|---------|
| PR Template | PASS | All sections filled |
| Attribution Guard | PASS | No AI mentions detected |
| Secret Detection | PASS | No secrets found |
| Debug Statements | WARN | Found `print()` at `line 42` |
| Forbidden Imports | PASS | No prohibited imports |

### AI Analysis

**Summary**: This PR updates the PBKDF2 iteration count from 480,000 to 600,000 to align with OWASP 2024 recommendations. Changes are isolated to `core/crypto.py` with corresponding test updates.

**Risk Assessment**: Low. Change is additive and backward-compatible. Existing vaults will re-derive keys on next unlock.

**Missing Tests**: None detected.

**Confidence**: High

---

**Verdict**: Policy checks passed. Human review recommended for crypto changes.

<sub>Review triggered manually. [View workflow run](#)</sub>
```

---

## OpenAI Model Selection

### Recommendation: GPT-4o-mini

| Factor | GPT-4o-mini | GPT-3.5-turbo | GPT-4o |
|--------|-------------|---------------|--------|
| **Input Cost** | $0.15/1M tokens | $0.50/1M tokens | $2.50/1M tokens |
| **Output Cost** | $0.60/1M tokens | $1.50/1M tokens | $10.00/1M tokens |
| **Context Window** | 128K tokens | 16K tokens | 128K tokens |
| **Code Reasoning** | Good | Adequate | Excellent |
| **Recommendation** | **Selected** | Deprecated | Overkill |

### Cost Projection

Assumptions:
- Average PR diff: ~500 lines = ~2,000 tokens
- System prompt + context: ~1,500 tokens
- Output response: ~500 tokens
- PRs per month: 20

**Monthly Cost Estimate**:
- Input: 20 PRs x 3,500 tokens = 70,000 tokens = $0.01
- Output: 20 PRs x 500 tokens = 10,000 tokens = $0.006
- **Total: < $0.02/month**

Even at 10x volume (200 PRs/month), cost remains under $0.20/month.

### Context Window Strategy

GPT-4o-mini's 128K context window handles most PRs easily. For large PRs:

1. **Prioritize critical files**: Include full diff of `core/*`, summarize others
2. **Chunk by file**: Process large diffs file-by-file, aggregate findings
3. **Exclude binaries**: Skip non-text file diffs
4. **Limit context**: Cap at 100K tokens, warn if truncated

---

## Security & Cost Considerations

### Secrets Management

| Secret | Storage | Access |
|--------|---------|--------|
| `OPENAI_API_KEY` | GitHub Secrets | Workflow only |
| `GITHUB_TOKEN` | Auto-generated | Scoped to workflow |

**Key Protections**:
- API key never logged or exposed
- Use GitHub's masked output for any token references
- Rotate OpenAI key periodically (quarterly)
- Set OpenAI spending limit ($5/month cap)

### Code Exposure Risk

| Risk | Mitigation |
|------|------------|
| Code sent to OpenAI | Only diffs sent, not full codebase. OpenAI API data not used for training (API terms). |
| Sensitive file diffs | Skip files matching `.env*`, `*secret*`, `*credential*` patterns |
| PR author injection | Sanitize PR description before including in prompt |

### Rate Limiting

- OpenAI API: 500 RPM on Tier 1 (default). More than sufficient.
- GitHub API: 5,000 requests/hour with GITHUB_TOKEN. Adequate.
- Self-imposed: One review per PR per workflow run. No rapid re-reviews.

### Cost Controls

1. **OpenAI Spending Limit**: Set $5/month hard cap in OpenAI dashboard
2. **Concurrency Limit**: Max 1 concurrent review workflow
3. **Deduplication**: Skip if identical commit already reviewed
4. **Manual Trigger**: No automatic reviews = predictable costs

---

## Reviewer Interaction Flow

### Scenario 1: Contributor Requests Review

```
1. Contributor opens PR
2. CI runs automatically
3. CI passes
4. Contributor comments: "@passfx-bot review"
5. Bot workflow triggers
6. Bot posts review comment
7. Contributor addresses feedback (if any)
8. Human maintainer performs final review
9. Human maintainer approves and merges
```

### Scenario 2: Maintainer Triggers Review

```
1. PR is opened (external contributor)
2. CI passes
3. Maintainer goes to Actions tab
4. Selects "Review Bot" workflow
5. Enters PR number, clicks "Run"
6. Bot posts review comment
7. Maintainer reviews bot findings + code
8. Maintainer approves and merges
```

### Scenario 3: Bot Finds Blocking Issue

```
1. Bot runs policy checks
2. Secret detected in diff
3. Bot posts review with BLOCKING status
4. PR cannot pass bot check
5. Contributor removes secret
6. Contributor re-requests review
7. Bot re-runs, passes
```

---

## CODEOWNERS Integration

### Limitation

GitHub does not allow bots or GitHub Apps in CODEOWNERS files. Attempting to add `@github-actions[bot]` causes the entire CODEOWNERS file to be ignored.

### Workaround Options

| Option | Approach | Tradeoffs |
|--------|----------|-----------|
| **Status Check** | Bot creates a status check. Branch protection requires status to pass. | Does not appear as "reviewer" but blocks merge. |
| **Team Membership** | Create dedicated bot user, add to team, add team to CODEOWNERS. | Requires GitHub seat, PAT management. |
| **Comment-Based** | Bot reviews via comments only. Humans remain sole approvers. | Clearest separation of responsibilities. |

**Recommendation**: Comment-Based approach. Bot provides analysis; humans retain approval authority. This aligns with PassFX's security-first philosophy where humans make all trust decisions.

### Proposed CODEOWNERS (No Change)

```
# Current CODEOWNERS - no modification needed
* @dinesh-git17
```

The bot enhances review but does not replace the maintainer as code owner.

---

## Future Enhancements (Optional)

### Phase 2: Codebase-Aware Analysis

- Index repository structure and patterns
- Compare PR against established conventions
- Detect architectural regressions

### Phase 3: Incremental Learning

- Track which bot findings led to changes
- Adjust confidence thresholds based on accuracy
- Reduce noise by suppressing consistently-ignored warnings

### Phase 4: Multi-Repo Support

- Extract bot as reusable GitHub Action
- Publish to GitHub Marketplace
- Support custom rule configurations via YAML

### Phase 5: Integration with Issue Tracker

- Link PR reviews to related issues
- Verify claimed "Fixes #N" actually addresses issue
- Cross-reference with security advisories

---

## Open Questions / Inputs Needed from Maintainer

Before implementation, the following decisions are needed:

### 1. Trigger Preference

- **Option A**: Manual only (comment or workflow dispatch)
- **Option B**: Automatic when CI passes (adds potential noise)
- **Recommendation**: Option A initially. Can add Option B later.

### 2. AI Opt-Out

Should contributors be able to request "policy checks only" (skip AI)?

- **Benefit**: Faster feedback, lower cost, no external API call
- **Tradeoff**: Loses risk assessment and summary features

### 3. Blocking vs Advisory

Should policy failures (secrets, attribution) block merge via status check, or remain advisory comments?

- **Blocking**: Creates hard gate, ensures compliance
- **Advisory**: Maintains human discretion, avoids friction

### 4. Review Scope Expansion

Should the bot review:
- Test files? (Currently proposed as "Low" scope)
- CI configuration? (Could catch workflow vulnerabilities)
- Documentation? (Could verify accuracy claims)

### 5. OpenAI Key Ownership

- Repository secret (maintainer-owned)
- Organization secret (if applicable)
- Dedicated bot account's API key (isolation)

### 6. Secret Detection Tooling

- Use existing tool (gitleaks, truffleHog) as subprocess?
- Implement custom regex patterns?
- Rely on GitHub's built-in secret scanning?

---

## Implementation Checklist (For Future Phase)

When approved, implementation would involve:

- [ ] Create `.github/workflows/review-bot.yml`
- [ ] Create `scripts/review_bot/` module structure
- [ ] Implement policy check functions
- [ ] Implement OpenAI API integration
- [ ] Create prompt templates for AI analysis
- [ ] Add `OPENAI_API_KEY` to repository secrets
- [ ] Test on sample PRs
- [ ] Document usage in CONTRIBUTING.md
- [ ] Add review bot section to CI README

---

## References

- [GitHub Actions Manual Triggers](https://github.blog/changelog/2020-07-06-github-actions-manual-triggers-with-workflow_dispatch/)
- [GitHub CODEOWNERS and Bots Discussion](https://github.com/orgs/community/discussions/23064)
- [OpenAI API Pricing](https://openai.com/api/pricing/)
- [GPT-4o-mini Announcement](https://openai.com/index/gpt-4o-mini-advancing-cost-efficient-intelligence/)
- [GitHub Pull Request Reviews API](https://docs.github.com/en/rest/pulls/reviews)
- [CodeRabbit AI Code Reviews](https://www.coderabbit.ai/)
- [Qodo PR-Agent](https://www.qodo.ai/)
- [Fullstory CODEOWNERS with Bots](https://www.fullstory.com/blog/taming-github-codeowners-with-bots/)

---

_This document is a planning artifact. No implementation has been performed._
