## Summary

<!-- Provide a concise description of the changes in this PR -->

## Motivation

<!-- Why is this change needed? Link to related issues if applicable -->

Fixes #

## Type of Change

<!-- Mark the relevant option with an "x" -->

- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to change)
- [ ] Documentation update
- [ ] Infrastructure / CI / tooling
- [ ] Refactoring (no functional changes)

## Testing

<!-- Describe how you tested these changes -->

- [ ] Unit tests added/updated
- [ ] Manual testing performed
- [ ] N/A (documentation only)

## Risk Assessment

<!-- What could go wrong? What is the blast radius? -->

**Risk level:** Low / Medium / High

**Areas affected:**

## Security Considerations

<!-- For changes touching core/, crypto, or vault operations -->

- [ ] No credentials or secrets exposed
- [ ] Sensitive data properly cleared from memory
- [ ] File permissions verified (0600/0700)
- [ ] N/A (no security-sensitive changes)

## Checklist

- [ ] Code follows project style guidelines
- [ ] `ruff check passfx/` passes
- [ ] `mypy passfx/` passes
- [ ] `bandit -r passfx/` passes (for security-sensitive changes)
- [ ] Tests pass locally
- [ ] Self-reviewed code for obvious issues
- [ ] No print statements or debug code
- [ ] Commit messages follow conventional format
