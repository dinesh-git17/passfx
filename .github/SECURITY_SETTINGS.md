# Required GitHub Security Settings

This document specifies the GitHub repository security settings that must be enabled.
These settings are configured via the GitHub web interface or API, not via files.

## Secret Scanning

**Location:** Repository Settings > Security > Code security and analysis

### Required Settings

| Setting | Status | Purpose |
|---------|--------|---------|
| Dependency graph | Enabled | Track dependencies for vulnerability detection |
| Dependabot alerts | Enabled | Alert on vulnerable dependencies |
| Dependabot security updates | Enabled | Auto-create PRs for security fixes |
| Secret scanning | Enabled | Detect leaked secrets in commits |
| Push protection | Enabled | Block pushes containing secrets |

### Secret Types Covered (GitHub Defaults)

GitHub's secret scanning covers 200+ secret types including:
- API keys (AWS, GCP, Azure, GitHub, etc.)
- OAuth tokens
- Private keys
- Database connection strings
- Cloud credentials
- Service account keys

### Push Protection Behavior

When push protection is enabled:
1. Commits containing detected secrets are blocked
2. Contributors see a clear error message identifying the secret type
3. Contributors can bypass with justification (if allowed by policy)
4. All bypass attempts are logged for audit

## How to Enable

### Via GitHub Web Interface

1. Navigate to repository Settings
2. Select "Code security and analysis" under Security
3. Enable each setting listed above

### Via GitHub API

```bash
# Enable secret scanning
gh api -X PATCH /repos/{owner}/{repo} \
  -f security_and_analysis.secret_scanning.status=enabled

# Enable push protection
gh api -X PATCH /repos/{owner}/{repo} \
  -f security_and_analysis.secret_scanning_push_protection.status=enabled
```

## Verification

Run the following to verify settings are enabled:

```bash
gh api /repos/{owner}/{repo} --jq '.security_and_analysis'
```

Expected output should show all settings as "enabled".
