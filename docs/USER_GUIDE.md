# PassFX User Guide

**Your passwords. Offline. Encrypted. Yours.**

Welcome to PassFX, a terminal-based password manager that keeps your secrets where they belong: on your machine, under your control.

This guide will walk you through everything you need to know to get started and make the most of PassFX. Whether you are new to password managers or a seasoned security enthusiast, you are in the right place.

---

## Table of Contents

1. [Welcome to PassFX](#welcome-to-passfx)
2. [Getting Started](#getting-started)
3. [Your First Credential](#your-first-credential)
4. [Everyday Usage](#everyday-usage)
5. [Password Generation and Strength](#password-generation-and-strength)
6. [Security Basics](#security-basics)
7. [Locking, Exiting, and Safety](#locking-exiting-and-safety)
8. [Tips, Tricks, and Best Practices](#tips-tricks-and-best-practices)
9. [Troubleshooting and FAQ](#troubleshooting-and-faq)
10. [Final Words](#final-words)

---

## Welcome to PassFX

PassFX is a password manager built for people who care about where their data lives.

### What Problem Does It Solve?

You have dozens of accounts, each demanding a unique password. Reusing passwords is risky. Writing them on sticky notes is worse. Cloud-based password managers are convenient, but you are trusting someone else with your secrets.

PassFX takes a different approach:

- **Your data stays on your machine.** There is no cloud sync, no remote servers, no "someone else's computer."
- **Everything is encrypted.** Your vault is locked with proven cryptography (Fernet: AES-128-CBC + HMAC-SHA256).
- **No recovery mechanism.** If you forget your master password, your data is gone. This sounds harsh, but it means no one can "reset" their way into your vault. Not even you.

### What Makes It Different?

PassFX is not trying to be everything for everyone. It is a focused tool with specific values:

- **Offline by design.** Network isolation is a feature, not a limitation.
- **Terminal-native.** If you spend your day in a terminal, PassFX feels like home.
- **Security first.** Every design decision prioritizes protecting your data over convenience.

If you want seamless browser integration and mobile apps, PassFX might not be for you. But if you want a password manager that respects your paranoia, keep reading.

---

## Getting Started

Let's get you set up. This should take about five minutes.

### Installing PassFX

PassFX requires Python 3.10 or later. Install it with pip:

```bash
pip install passfx
```

Or, if you prefer to install from source:

```bash
git clone https://github.com/DineshDK03/passfx.git
cd passfx
pip install -e .
```

### Launching for the First Time

Open your terminal and run:

```bash
passfx
```

You will see the login screen with a cyberpunk-styled interface. If this is your first time, PassFX will prompt you to create a vault.

### Creating Your Vault

When you launch PassFX without an existing vault, you will be asked to create a master password. This is the single most important password you will ever create for PassFX.

**What makes a good master password?**

- At least 12 characters (longer is better)
- Mix of uppercase, lowercase, numbers, and symbols
- Something you can remember but others cannot guess
- Definitely not "password123" or your birthday

PassFX enforces these requirements, so you cannot accidentally choose something too weak.

**A word of caution:** PassFX has no password recovery. None. This is intentional. If you forget your master password, your data is mathematically unrecoverable. Write it down somewhere safe if you need to, but keep that backup secure.

Once you confirm your password, PassFX creates your encrypted vault at `~/.passfx/vault.enc`. You are now ready to start storing credentials.

### The Command Center

After unlocking your vault, you arrive at the main menu, which we call the Command Center. Here is what you will see:

**Left side: Navigation menu**
- KEY: Passwords (email/login credentials)
- PIN: Phone numbers and PINs
- CRD: Credit cards
- MEM: Secure notes
- ENV: Environment variables
- SOS: Recovery codes
- GEN: Password generator
- SET: Settings
- ?: Help
- EXIT: Quit

**Right side: Dashboard**
- Vault status showing counts of each credential type
- Vault health score (more on this later)
- Security metrics

**Bottom: System Terminal**
- Press `/` to focus the terminal for quick navigation

Take a moment to explore. Press the arrow keys to navigate the menu and Enter to select.

---

## Your First Credential

Let's add your first password. This walkthrough uses the Passwords section, but the process is similar for all credential types.

### Step 1: Navigate to Passwords

From the Command Center, use the arrow keys to highlight "KEY" (Passwords) and press Enter. Alternatively, press `/` to focus the terminal and type `/key`.

You will see a split-view screen:
- **Left pane:** A table listing all your saved passwords (empty for now)
- **Right pane:** An inspector showing details of the selected entry

### Step 2: Add a New Entry

Press `A` to add a new credential. A modal dialog will appear asking for:

- **Label:** A name for this entry (e.g., "Gmail Personal")
- **Email:** The email or username associated with this account
- **Password:** The password itself
- **Notes:** Optional additional information

Fill in the fields. When you are done, press Enter to save (or Escape to cancel).

### Step 3: What Just Happened?

Your credential is now encrypted and stored in your vault. Here is what PassFX did behind the scenes:

1. Took your password and encrypted it using the key derived from your master password
2. Added integrity protection (HMAC) so tampering can be detected
3. Wrote the encrypted data to disk with restrictive file permissions
4. Created a backup of the previous vault state (just in case)

All of this happens automatically. You just see your new entry appear in the table.

### Step 4: View Your Entry

With your new entry selected, press `V` to view the full details. You will see a styled "Identity Card" showing:
- Your label and email
- A visual password strength indicator
- The full password (masked until you copy it)
- Any notes you added

Press Escape to close the modal.

---

## Everyday Usage

Now that you have some credentials stored, here is how to use PassFX day-to-day.

### Viewing Credentials

Navigate to the appropriate section (Passwords, Cards, etc.) and use the arrow keys to select an entry. The right-side inspector updates automatically to show details.

For a full-screen view, press `V` to open the detailed modal.

### Copying to Clipboard

Select an entry and press `C` to copy the secret (password, PIN, card number, etc.) to your clipboard.

**Heads up:** PassFX automatically clears your clipboard after 15 seconds. If you paste and get nothing, that is the security feature doing its job. You can always copy again.

### Editing Entries

Select an entry and press `E` to edit. Make your changes and press Enter to save.

**Pro tip:** When editing a password entry, you can leave the password field blank to keep the existing password. Handy when you only need to update the notes.

### Deleting Entries

Select an entry and press `D` to delete. PassFX will ask for confirmation because deletions are permanent. There is no recycle bin.

### Searching and Navigating

Use the arrow keys to scroll through entries. For quick navigation from the Command Center, press `/` and type a slash command:

| Command | Destination |
|---------|-------------|
| `/key` | Passwords |
| `/pin` | Phone PINs |
| `/crd` | Credit Cards |
| `/env` | Environment Variables |
| `/sos` | Recovery Codes |
| `/gen` | Password Generator |
| `/set` | Settings |
| `/exit` | Quit |

Commands are case-insensitive, so `/KEY` and `/key` both work.

### Credential Types

PassFX supports six types of credentials, each with their own section:

**Passwords (KEY)**
For email/username and password combinations. Includes strength analysis.

**Phone PINs (PIN)**
For storing phone numbers with associated PINs or access codes.

**Credit Cards (CRD)**
For storing card details including number, expiry, CVV, and cardholder name. Card numbers are validated and formatted automatically.

**Secure Notes (MEM)**
For freeform text that needs encryption. Store license keys, important information, or anything else that does not fit other categories.

**Environment Variables (ENV)**
For developers storing API keys, database credentials, and configuration secrets. Stop putting sensitive values in plaintext `.env` files.

**Recovery Codes (SOS)**
For storing 2FA backup codes from services like Google, GitHub, or AWS. Multi-line support for lists of codes.

---

## Password Generation and Strength

Strong passwords are the foundation of good security. PassFX helps you create them.

### The Password Generator

Navigate to GEN (Generator) from the Command Center or type `/gen`. You will see three generation modes:

**Mode 1: Strong Password**
Configurable random passwords with options for:
- Length (default 16, minimum 4, up to 128)
- Uppercase letters (A-Z)
- Lowercase letters (a-z)
- Digits (0-9)
- Symbols (!@#$%^&* etc.)
- Exclude ambiguous characters (0, O, 1, l, I)
- Use only safe symbols (for systems that choke on certain characters)

**Mode 2: Passphrase**
Word-based passwords that are easier to remember:
- Choose the number of words (default 4)
- Pick a separator character (default -)
- Toggle capitalization

Example output: `Castle-Arrow-Beach-Thunder`

Passphrases are surprisingly strong. Four random words from a decent wordlist can be stronger than a short random password.

**Mode 3: PIN**
Simple numeric codes for when you need them:
- Choose the length (default 4, minimum 4)
- Pure digits, nothing else

### Understanding Password Strength

PassFX uses the zxcvbn library to analyze password strength. This is the same library used by Dropbox and many other services.

**What the strength meter shows:**
- A score from 0 (very weak) to 4 (strong)
- Color coding: red (weak) through green (strong)
- An estimated crack time (from seconds to centuries)
- Suggestions for improvement

**What the meter actually measures:**
- Pattern detection (keyboard walks like "qwerty", common substitutions like "p@ssw0rd")
- Dictionary words and common passwords
- Repeated characters and sequences
- Overall entropy

A 16-character random password will almost always score "Strong." But zxcvbn is smarter than just counting characters. It knows that "aaaaaaaaaaaaaaaa" is not a good password.

### Saving Generated Passwords

When you generate a password you like, you can save it directly to your vault without copying it first. The generator offers a "Save" option that lets you attach the password to a new credential entry.

---

## Security Basics

PassFX is designed to protect your data. Here is what that means in practice, without the scary technical jargon.

### What PassFX Protects Against

**Stolen laptops and backups**
If someone steals your laptop or gets a copy of your vault file, they cannot read your passwords without your master password. The encryption is strong enough that brute-forcing would take longer than the age of the universe (assuming a decent password).

**Unauthorized access**
PassFX sets restrictive file permissions on your vault. Other users on your system cannot read it.

**Vault tampering**
If someone modifies your vault file, PassFX will detect it and refuse to decrypt. You cannot be tricked into using a corrupted vault.

**Clipboard snooping**
Passwords are automatically cleared from your clipboard after 15 seconds. Someone looking over your shoulder cannot just paste your password later.

### What PassFX Cannot Protect Against

Let's be honest about limitations:

**Compromised computers**
If your machine has malware, keyloggers, or a rootkit, PassFX cannot help. The attacker can see everything you type.

**Physical access to an unlocked vault**
If someone sits down at your computer while PassFX is unlocked, they can see your passwords. Always lock your vault when stepping away.

**Memory forensics**
A sophisticated attacker with root access could potentially read passwords from RAM while the vault is open. This is a theoretical concern for most people, but worth knowing.

**Forgotten master passwords**
There is no recovery. No security questions. No email reset. If you forget your master password, your data is gone. This is a feature, not a bug.

### Why No Recovery?

Password recovery mechanisms are security holes. If there is a way to recover your password, there is a way for an attacker to exploit that mechanism.

PassFX deliberately has no recovery option because:
- Support staff cannot be social-engineered into resetting your password
- There is no "forgot password" endpoint to attack
- Your data is only accessible to someone who knows the master password

The tradeoff is responsibility. You must remember your master password (or store it somewhere very safe).

### The Master Password Matters

Your master password is the key to everything. PassFX uses it to derive an encryption key through PBKDF2 with 480,000 iterations. This means:

- The same password always produces the same key (deterministic)
- The process is intentionally slow (to make guessing expensive)
- Even a small change in password produces a completely different key

Choose a strong master password and protect it carefully.

---

## Locking, Exiting, and Safety

PassFX has several layers of protection for when you are done working.

### Locking the Vault

The vault locks automatically after a period of inactivity (configurable in settings, default 5 minutes). When locked:

- The encryption key is wiped from memory
- All decrypted credentials are cleared
- You must re-enter your master password to continue

You can also quit the application entirely (press `Q` or use `/exit`), which locks and cleans up everything.

### Clipboard Clearing

When you copy a password, it stays in your clipboard for 15 seconds, then gets automatically replaced with empty content.

**Why 15 seconds?**
It is long enough to paste somewhere, short enough to limit exposure. If you need to paste multiple times, just copy again.

**What about clipboard managers?**
Some operating systems and third-party tools keep clipboard history. PassFX cannot control these. If you use a clipboard manager, consider configuring it to exclude PassFX or not record passwords.

### What Happens on Exit

When PassFX exits (normally or via Ctrl+C):

1. The clipboard is cleared if it contains a recently-copied secret
2. All sensitive data in memory is overwritten (best-effort)
3. The vault file remains encrypted on disk
4. Signal handlers ensure cleanup even on crashes

### Safe Shutdown

If something goes wrong (power outage, system crash), your vault is still safe:

- PassFX uses atomic writes, so partial saves cannot corrupt your vault
- A backup of the previous vault state exists
- The worst case is losing the most recent unsaved changes

---

## Tips, Tricks, and Best Practices

Here are some things that will make your life easier and more secure.

### Password Hygiene

**Use unique passwords everywhere**
If one site gets breached, unique passwords mean only that account is compromised.

**Let PassFX generate passwords**
The generator creates random passwords that are much stronger than anything you would come up with (no offense).

**Rotate compromised passwords**
If you learn a service was breached, change that password immediately.

**Check your vault health score**
The dashboard shows password reuse, old passwords, and weak entries. Aim for a high score.

### Backup Your Vault

Your vault consists of two files:
- `~/.passfx/vault.enc` (the encrypted data)
- `~/.passfx/salt` (used in key derivation)

**You need both files to restore your vault.** The vault file is useless without the salt. Back them up together.

Backup suggestions:
- Encrypted USB drive stored somewhere safe
- Encrypted cloud storage (the vault is already encrypted, but defense in depth)
- Regular, automated backups

### Use the Keyboard

PassFX is optimized for keyboard use. Learning the shortcuts will make you much faster:

| Key | Action |
|-----|--------|
| `A` | Add new entry |
| `E` | Edit selected entry |
| `D` | Delete selected entry |
| `C` | Copy secret to clipboard |
| `V` | View full details |
| `/` | Focus terminal for slash commands |
| `?` | Help screen |
| `ESC` | Go back / Cancel |
| `Q` | Quit |

### Keep PassFX Updated

Updates often include security fixes. Check for updates regularly:

```bash
pip install --upgrade passfx
```

### Things Future You Will Thank You For

- Add notes to credentials explaining what they are for
- Use descriptive labels ("Gmail - Personal" not just "Google")
- Store recovery codes for all your 2FA-enabled accounts
- Review your vault health score monthly

---

## Troubleshooting and FAQ

**Q: I forgot my master password. Can you help?**

No. There is no recovery mechanism. If you forgot your master password, your data is gone. This is by design. Consider using a strong, memorable passphrase next time and storing a backup somewhere very secure.

**Q: PassFX says my vault is corrupted. What happened?**

The vault file or salt file may have been modified outside PassFX. If you have a backup, restore both files together. If you do not have a backup, the data is likely unrecoverable.

**Q: My clipboard cleared before I could paste. Is this a bug?**

No, that is the auto-clear feature protecting you. Passwords are cleared after 15 seconds. Just copy again.

**Q: PassFX is not starting. What do I check?**

- Make sure Python 3.10+ is installed (`python --version`)
- Try reinstalling: `pip install --upgrade passfx`
- Check if the vault directory exists: `ls -la ~/.passfx/`
- Look for permission issues on vault files

**Q: Can I use PassFX on multiple computers?**

PassFX is offline-only, so there is no automatic sync. You can manually copy your vault files (`~/.passfx/vault.enc` and `~/.passfx/salt`) to another machine, but keep them in sync yourself. Be careful about version conflicts.

**Q: Why can't I see my password in the list?**

Passwords are masked in the table view for security. Press `V` to view full details, or `C` to copy.

**Q: Is there a way to change my master password?**

Yes, through the Settings menu. You will need to enter your current password to authorize the change.

**Q: I got locked out after too many wrong passwords. What now?**

PassFX implements rate limiting to prevent brute-force attacks. After 3 failed attempts, you will need to wait before trying again. The wait time increases exponentially (2, 4, 8 seconds...) up to a maximum of 1 hour. This is for your protection.

**Q: Can I import from other password managers?**

PassFX can import its own JSON backup format. For other password managers, you may need to export to CSV and convert to PassFX format. Check the Settings menu for import options.

**Q: Where can I get help?**

- Open an issue on GitHub: https://github.com/DineshDK03/passfx/issues
- Check the help screen in the app: press `?`

---

## Final Words

You made it to the end. That means you care about your security, and that is worth something.

PassFX was built with a simple philosophy: your passwords are yours. They should stay on your machine, encrypted, under your control. No cloud sync. No recovery mechanisms. No compromises.

This approach requires more responsibility from you. You must remember your master password. You must maintain backups. You must keep your machine secure.

But in return, you get something valuable: the knowledge that your secrets are truly yours.

Thank you for trusting PassFX with your data. Stay secure out there.

---

*"Security is not a product, but a process." - Bruce Schneier*

---

**Need help?** Press `?` in the app or visit the [GitHub repository](https://github.com/DineshDK03/passfx).

**Found a security issue?** Please report it responsibly at security@dineshd.dev.
