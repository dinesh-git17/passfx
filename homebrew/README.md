# PassFX Homebrew Formula

This directory contains the Homebrew formula for PassFX.

## For Users

### Installation via Tap (Recommended)

Once the tap repository is set up:

```bash
brew tap dinesh-git17/passfx
brew install passfx
```

### Verify Installation

```bash
passfx --version
# Output: passfx 1.0.2

passfx --help
```

### Uninstall

```bash
brew uninstall passfx
brew untap dinesh-git17/passfx
```

## For Maintainers

### Setting Up the Tap Repository

1. Create a new GitHub repository named `homebrew-passfx`

2. Clone it locally:
   ```bash
   git clone https://github.com/dinesh-git17/homebrew-passfx.git
   cd homebrew-passfx
   ```

3. Create the Formula directory and copy the formula:
   ```bash
   mkdir -p Formula
   cp /path/to/passfx/homebrew/passfx.rb Formula/
   ```

4. Commit and push:
   ```bash
   git add Formula/passfx.rb
   git commit -m "feat: add passfx formula v1.0.2"
   git push origin main
   ```

### Testing Locally

```bash
# Create local tap structure
mkdir -p $(brew --repository)/Library/Taps/dinesh-git17/homebrew-passfx/Formula
cp homebrew/passfx.rb $(brew --repository)/Library/Taps/dinesh-git17/homebrew-passfx/Formula/

# Install from local tap
brew install dinesh-git17/passfx/passfx

# Run tests
brew test passfx

# Clean up
brew uninstall passfx
rm -rf $(brew --repository)/Library/Taps/dinesh-git17
```

### Updating the Formula for New Releases

When releasing a new version:

1. Update `url` and `sha256` in `passfx.rb`:
   ```bash
   # Get new SHA256
   curl -sL https://files.pythonhosted.org/packages/.../passfx-X.Y.Z.tar.gz | shasum -a 256
   ```

2. Update version in test block

3. Regenerate resource stanzas if dependencies changed:
   ```bash
   pip install homebrew-pypi-poet
   poet passfx
   ```

4. Run style check:
   ```bash
   brew style Formula/passfx.rb
   ```

5. Test installation:
   ```bash
   brew install --build-from-source passfx
   brew test passfx
   ```

### Formula Design Decisions

- **Python 3.12**: Modern stable Python with best performance
- **virtualenv_install_with_resources**: Standard Homebrew pattern for Python packages
- **PyPI source**: Deterministic builds from official package registry
- **All dependencies vendored**: No network access at runtime, hermetic install
- **Comprehensive test block**: Validates CLI functionality post-install

### Security Notes

- PassFX is local-only by design
- No network access at runtime
- Encrypted vault stored at `~/.passfx/`
- All cryptographic operations use `cryptography` library (not custom implementations)
