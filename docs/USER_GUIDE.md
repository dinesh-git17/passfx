<div align="center">

# PassFX User Guide

**The Manual for the Paranoid.**

![Status: Living Document](https://img.shields.io/badge/status-living_document-blue)
![Reading Time: ~5 min](https://img.shields.io/badge/read_time-~5_min-green)

</div>

---

## ⚡ Quick Start

PassFX is a **Terminal User Interface (TUI)**. If you know how to use a keyboard, you know how to use PassFX. We've optimized every interaction for speed and muscle memory.

### 1. Launching the Vault

Open your terminal and run:

```bash
passfx
```

- **First Run:** You will be prompted to create a **Master Password**. Choose wisely. This key encrypts your entire digital life. If you lose it, your data is gone forever. (We really mean it; we store PBKDF2-HMAC-SHA256 hashes, not the password itself).
- **Subsequent Runs:** Enter your Master Password to decrypt and unlock the vault into memory.

### 2. The Command Center

Once unlocked, you land on the **Security Command Center**. This is your HUD.

- **Sidebar:** Navigation menu (Left).
- **Dashboard:** Vault health, statistics, and security score (Right).
- **System Terminal:** A command-line interface _within_ the interface. Press `/` to focus it.

---

## 🕹️ Navigation & Keybindings

PassFX is designed to be used without a mouse (though mouse support is fully enabled in `Textual`).

### Global Hotkeys

| Key                 | Action                        | Context   |
| :------------------ | :---------------------------- | :-------- |
| `TAB` / `Shift+TAB` | Move focus between widgets    | Global    |
| `ESC`               | Go Back / Cancel / Focus Menu | Global    |
| `Q`                 | Quit Application (Auto-locks) | Global    |
| `/`                 | Focus System Terminal         | Main Menu |
| `?`                 | Open Help Screen              | Global    |

### Data Screen Actions (Passwords, Envs, etc.)

When viewing list screens like Passwords or Environment Variables:

| Key | Action     | Description                                              |
| :-- | :--------- | :------------------------------------------------------- |
| `A` | **Add**    | Create a new entry.                                      |
| `E` | **Edit**   | Modify the selected entry.                               |
| `D` | **Delete** | Permanently remove the entry.                            |
| `V` | **View**   | Open the detailed "Inspector" modal (Identity Card).     |
| `C` | **Copy**   | Copy the primary secret (Password/Content) to clipboard. |

> **Clipboard Security:** When you copy a password, PassFX automatically clears your clipboard after **30 seconds**. Do not panic if your paste buffer suddenly becomes empty. That is a feature.

---

## 🛠️ Core Features

### 🔐 Password Manager (`KEY`)

The bread and butter. Store standard credentials here.

- **Visual Strength:** The "Identity Inspector" panel shows a real-time strength estimation of your password (red to green) using `zxcvbn`.
- **Metadata:** You can store notes (e.g., "Reset security questions") alongside credentials.
- **Identity Access Token:** Press `V` to see a stylized "ID Card" view of your credential with a visual hash avatar.

### ⚙️ Environment Variables (`ENV`)

**For Developers.** Stop putting `.env` files in Slack.

- **Purpose:** Store API keys, database URLs, and complex config blocks.
- **Drag & Drop:** You can drag a file from your OS file manager and drop it onto the "Add/Edit" modal to instantly import its content.
- **Preview:** The inspector masks sensitive values (`KEY=***`) but allows you to view the structure.

### 🆘 Recovery Codes (`SOS`)

**The Fail-Safe Protocol**.

- **Purpose:** Store 2FA backup codes (Google, GitHub, AWS).
- **Security:** Codes are masked in the preview pane (e.g., `1234••••5678`) to prevent shoulder surfing.
- **Content:** Designed for multi-line text blocks.

### 🎲 Generator (`GEN`)

A cryptographically secure random number generator (CSPRNG).

- **Modes:**
  1.  **Strong Password:** Configurable length (8-128), symbols, ambiguity filtering.
  2.  **Passphrase:** XKCD-style (e.g., `correct-horse-battery-staple`).
  3.  **PIN:** For credit cards or door codes.
- **Direct Save:** You can save a generated secret directly to the vault without copying it to the clipboard first.

---

## 💻 The System Terminal

In the Main Menu, press `/` to access the command line. You can navigate quickly using "Slash Commands".

| Command | Destination           |
| :------ | :-------------------- |
| `/key`  | Passwords             |
| `/pin`  | PINs / Phone Numbers  |
| `/crd`  | Credit Cards          |
| `/env`  | Environment Variables |
| `/sos`  | Recovery Codes        |
| `/gen`  | Generator             |
| `/set`  | Settings              |
| `/exit` | Quit                  |

- _Tip: Commands are case-insensitive._

---

## 💾 Import & Export

Accessed via the **Settings** menu.

### Exporting

- **JSON:** Creates a full backup. _Note: Currently exports plaintext JSON. Keep this file safe!_
- **CSV:** Useful for migrating to other password managers (LastPass, 1Password, etc.).

### Importing

- **PassFX JSON:** Restores a backup.
- **Merge Strategy:** Importing will **merge** data. If an ID matches, it updates the entry; otherwise, it creates a new one.

---

## 🛡️ Security Best Practices

1.  **Memory is Volatile:** PassFX tries to wipe secrets from memory, but a sophisticated attacker with root access to your machine _while the vault is open_ could theoretically scrape RAM. Close the app when not in use.
2.  **The Clipboard:** We auto-clear the clipboard, but some clipboard managers (on Linux/Mac) might keep history. Configure your OS clipboard manager to ignore PassFX if possible.
3.  **Backups:** Your vault lives at `~/.passfx/vault.enc` and `~/.passfx/salt`.
    - **CRITICAL:** You must back up **BOTH** files. The `vault.enc` is useless without the `salt`.

---

<div align="center">
  <sub>"Security is not a product, but a process." — Bruce Schneier</sub>
</div>
