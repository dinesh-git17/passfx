# Getting Started with PassFX

**A calm, step-by-step guide for first-time users.**

---

Welcome. If you have never used a password manager before, or if the words "terminal" and "Python" make you nervous, you are in exactly the right place.

This guide will walk you through everything, one step at a time. No programming knowledge required. No technical background assumed. Just you, your computer, and a desire to keep your passwords safe.

Take your time. There is no rush.

---

## Table of Contents

1. [What Is PassFX?](#what-is-passfx)
2. [Before You Begin](#before-you-begin)
3. [Installing Python](#installing-python)
4. [Installing PassFX](#installing-passfx)
5. [Launching PassFX](#launching-passfx)
6. [Your First Time: Creating a Vault](#your-first-time-creating-a-vault)
7. [Basic Usage Overview](#basic-usage-overview)
8. [Safety Tips for New Users](#safety-tips-for-new-users)
9. [Uninstalling PassFX](#uninstalling-passfx)
10. [Where to Go Next](#where-to-go-next)

---

## What Is PassFX?

PassFX is a **password manager** — a tool that securely stores all your passwords, PINs, credit card numbers, and other sensitive information in one place.

### What makes it different?

**It stays on your computer.** Unlike many password managers that store your data on company servers "in the cloud," PassFX keeps everything on your own machine. Your passwords never leave your computer. They are never uploaded anywhere.

**It is encrypted.** Your data is scrambled using strong encryption. Even if someone stole the files from your computer, they could not read your passwords without your master password.

**It is offline.** PassFX does not need an internet connection to work. Once installed, it runs entirely on your computer.

### Who is it for?

PassFX is for anyone who:
- Wants to stop reusing the same password everywhere
- Prefers to keep their data under their own control
- Values privacy and security
- Is willing to take responsibility for remembering one strong password

### What it does NOT do

- **No cloud sync.** Your data stays on your computer only.
- **No accounts to create.** There is no signup, no login to a website.
- **No password recovery.** If you forget your master password, there is no "reset" option. This is a security feature, not a limitation.
- **No tracking.** PassFX does not collect data about you or send anything to servers.

---

## Before You Begin

Here is what you will need:

- **A computer** running macOS, Windows, or Linux
- **An internet connection** (only needed during installation)
- **About 15-20 minutes** of your time
- **No programming knowledge** — seriously, none required

### A word of reassurance

> You will not break your computer by following this guide. Everything we do can be undone. If something goes wrong, we will explain how to fix it. Take a deep breath. You have got this.

---

## Installing Python

PassFX is built using a programming language called **Python**. Before you can run PassFX, you need to have Python installed on your computer.

### What is Python?

Python is a widely-used programming language. You do not need to learn how to program in Python — you just need it installed so that PassFX can run.

Think of it like this: if PassFX were a video, Python would be the video player. You do not need to know how the video player works to watch a video. You just need it installed.

**Python is:**
- Free and open source
- Used by millions of people worldwide
- Safe to install (it is not a virus or malware)
- Already installed on many computers

---

### Installing Python on macOS

Your Mac might already have Python installed. Let us check first.

#### Step 1: Open the Terminal

The Terminal is an application on your Mac that lets you type commands. Do not worry — we will tell you exactly what to type.

1. Press `Command + Space` to open Spotlight Search
2. Type `Terminal` and press Enter
3. A window will open with a blinking cursor

This is the Terminal. It might look intimidating, but it is just a way to talk to your computer by typing.

#### Step 2: Check if Python is already installed

In the Terminal, type this exactly and press Enter:

```
python3 --version
```

**If you see something like:**
```
Python 3.11.4
```

Congratulations! Python is already installed. The number (3.11.4 or similar) should be 3.10 or higher. You can skip ahead to [Installing PassFX](#installing-passfx).

**If you see an error like:**
```
command not found: python3
```

That is okay. It just means Python is not installed yet. Continue to the next step.

#### Step 3: Download Python

1. Open your web browser
2. Go to: **https://www.python.org/downloads/macos/**
3. Click the big yellow button that says "Download Python 3.x.x" (the numbers may vary)
4. A file will download to your computer

#### Step 4: Install Python

1. Open the downloaded file (it will be in your Downloads folder)
2. A window will appear with the Python installer
3. Click "Continue" through the screens
4. When asked, click "Install"
5. Enter your Mac password if prompted
6. Wait for the installation to complete
7. Click "Close" when finished

#### Step 5: Verify the installation

Open a **new** Terminal window (close the old one and open Terminal again), then type:

```
python3 --version
```

You should now see a version number. If you do, Python is installed correctly. ✅

---

### Installing Python on Windows

Windows does not come with Python, so you will need to install it.

#### Step 1: Download Python

1. Open your web browser
2. Go to: **https://www.python.org/downloads/windows/**
3. Click the big yellow button that says "Download Python 3.x.x"
4. A file will download to your computer

#### Step 2: Run the installer

1. Open the downloaded file
2. **Very important:** At the bottom of the first screen, there is a checkbox that says **"Add Python to PATH"** — **check this box**. This step is crucial. If you skip it, the rest of the installation will not work correctly.
3. Click "Install Now"
4. Wait for the installation to complete
5. Click "Close" when finished

#### Step 3: Open Command Prompt

The Command Prompt is Windows' version of a terminal — a place to type commands.

1. Press the Windows key on your keyboard
2. Type `cmd` and press Enter
3. A black window will appear with a blinking cursor

This is the Command Prompt.

#### Step 4: Verify the installation

In the Command Prompt, type this exactly and press Enter:

```
python --version
```

**If you see something like:**
```
Python 3.11.4
```

Python is installed correctly. ✅

**If you see an error**, try closing and reopening Command Prompt, then try again. If it still does not work, you may need to restart your computer and try once more.

---

### Installing Python on Linux

Good news: most Linux systems already have Python installed.

#### Step 1: Open a terminal

How you open a terminal depends on your Linux distribution, but common methods include:
- Pressing `Ctrl + Alt + T`
- Searching for "Terminal" in your applications menu

#### Step 2: Check if Python is installed

Type this command and press Enter:

```
python3 --version
```

**If you see a version number (3.10 or higher)**, you are all set. Skip ahead to [Installing PassFX](#installing-passfx).

**If Python is not installed**, here is how to install it:

**On Ubuntu or Debian:**
```
sudo apt update
sudo apt install python3 python3-pip
```

**On Fedora:**
```
sudo dnf install python3 python3-pip
```

You will be asked for your password. Type it (you will not see it as you type — that is normal) and press Enter.

#### Step 3: Verify the installation

```
python3 --version
```

You should see a version number. ✅

---

### Understanding what you just installed

Python is now on your computer. Here is what that means:

- You can now run programs written in Python, including PassFX
- Python takes up a small amount of space (around 100-200 MB)
- It runs quietly in the background when needed
- You do not need to do anything with it directly

---

## Installing PassFX

Now that Python is installed, you can install PassFX itself.

### What is pip?

When you installed Python, you also got a tool called **pip**. Pip is like an app store for Python programs. It downloads and installs Python software for you.

You do not need to understand how pip works. You just need to type one command.

### Installing PassFX

Open your terminal (or Command Prompt on Windows) and type:

**On macOS or Linux:**
```
pip3 install passfx
```

**On Windows:**
```
pip install passfx
```

Press Enter.

You will see some text scrolling by. This is pip downloading and installing PassFX and everything it needs to run. This may take a minute or two depending on your internet connection.

**When it is done**, you will see a message like "Successfully installed passfx" and you will be back at the blinking cursor.

### What just happened?

- Pip downloaded PassFX from a public repository (like an app store)
- It installed PassFX on your computer
- It also installed the libraries PassFX needs to run
- **Nothing was uploaded from your computer.** Installation only downloads; it does not send anything.

### Where does PassFX live?

PassFX is now installed in your Python environment. You do not need to know exactly where — you just need to know how to run it (coming next).

Your passwords and data will be stored in a folder called `.passfx` in your home directory:
- **macOS/Linux:** `/Users/yourname/.passfx/` or `/home/yourname/.passfx/`
- **Windows:** `C:\Users\yourname\.passfx\`

This folder is created the first time you run PassFX.

---

### If something went wrong

**"pip: command not found" or "pip is not recognized"**

Try using `pip3` instead of `pip`, or vice versa.

On Windows, if neither works, Python may not have been added to PATH during installation. The easiest fix is to uninstall Python, download it again, and make sure to check "Add Python to PATH" during installation.

**"Permission denied" error**

On macOS or Linux, try:
```
pip3 install --user passfx
```

This installs PassFX just for your user account, which does not require special permissions.

**Other errors**

Do not panic. Error messages can look scary, but they usually point to simple problems. Common fixes:
- Close and reopen your terminal, then try again
- Restart your computer, then try again
- Make sure you have an internet connection

If you are still stuck, you can ask for help at the PassFX GitHub page (we will give you the link at the end of this guide).

---

## Launching PassFX

You are almost there. Let us start PassFX for the first time.

### Opening the terminal

If you closed your terminal, open it again:
- **macOS:** Press `Command + Space`, type `Terminal`, press Enter
- **Windows:** Press the Windows key, type `cmd`, press Enter
- **Linux:** Press `Ctrl + Alt + T` or find Terminal in your applications

### Starting PassFX

Type this command and press Enter:

```
passfx
```

Your terminal window will transform. Instead of a blinking cursor, you will see the PassFX login screen with a stylized interface.

### What you are looking at

The login screen shows:
- The PassFX logo
- A field for entering your master password
- A cyberpunk-inspired visual theme (green text on a dark background)

If this is your first time running PassFX, you will see a message about creating a new vault.

---

## Your First Time: Creating a Vault

When you run PassFX for the first time, it needs to create a "vault" — a secure, encrypted file where all your passwords will be stored.

### What is a vault?

Think of the vault like a safe. All your passwords go inside it. The safe is locked with your master password. Without the master password, no one can open the safe — not even you.

### Creating your master password

PassFX will ask you to create a master password. This is **the most important password you will ever create** for PassFX.

**Your master password must have:**
- At least 12 characters
- At least one uppercase letter (A-Z)
- At least one lowercase letter (a-z)
- At least one number (0-9)
- At least one special character (!@#$%^&* and so on)

**Good examples:**
- `Sunset-River-42!`
- `MyDog$Buddy2015`
- `Coffee&Books#99`

**Bad examples:**
- `password123` (too common)
- `12345678901` (no letters or symbols)
- `qwertyuiop` (keyboard pattern)

### There is no password recovery

This is very important, so we are going to say it clearly:

> **If you forget your master password, your data is gone forever. There is no "forgot password" button. There is no way to reset it. There is no customer support that can help you recover it.**

This sounds scary, but it is actually a security feature. It means:
- No one can trick PassFX into giving them your password
- No hacker can reset your password and steal your data
- Your passwords are truly protected

**What you should do:**
- Choose a master password you can remember
- Consider writing it down and storing it somewhere very safe (like a locked drawer or a safe)
- Tell a trusted family member where to find it in case of emergency

### Confirming your password

After typing your master password, you will be asked to type it again. This confirms you did not make a typo.

Once both entries match and your password meets the requirements, PassFX will create your vault. This takes just a moment.

### What happens next?

You will see the PassFX main menu — called the "Command Center." This is your home base. From here, you can:
- Store passwords
- Store credit card information
- Store PINs and phone numbers
- Generate new strong passwords
- And more

---

## Basic Usage Overview

Now that your vault is created, here is a quick overview of what you can do. For detailed instructions, see the [User Guide](USER_GUIDE.md).

### The main menu

The main menu shows different categories:
- **KEY:** Passwords (for websites, apps, and accounts)
- **PIN:** Phone numbers and PINs
- **CRD:** Credit cards
- **MEM:** Secure notes
- **ENV:** Environment variables (for developers)
- **SOS:** Recovery codes (for two-factor authentication)
- **GEN:** Password generator
- **SET:** Settings
- **EXIT:** Quit PassFX

Use the arrow keys to navigate and press Enter to select.

### Adding a password

1. Navigate to KEY (Passwords) and press Enter
2. Press `A` to add a new entry
3. Fill in the label (like "Gmail"), email, and password
4. Press Enter to save

Your password is now encrypted and stored safely.

### Copying a password

1. Navigate to the entry you want
2. Press `C` to copy the password to your clipboard
3. Paste it wherever you need it

**Note:** PassFX automatically clears your clipboard after 15 seconds. This is a security feature — it prevents your password from sitting in your clipboard indefinitely.

### Locking and exiting

PassFX automatically locks after a period of inactivity (default is 5 minutes). When locked, you will need to enter your master password again.

To exit PassFX, navigate to EXIT in the menu, or press `Q`. When you exit:
- Your vault remains encrypted on disk
- Your clipboard is cleared
- Sensitive data is removed from memory

### Navigation shortcuts

| Key | What it does |
|-----|--------------|
| Arrow keys | Move through menus and lists |
| Enter | Select or confirm |
| Escape | Go back or cancel |
| Q | Quit PassFX |
| A | Add new entry |
| E | Edit selected entry |
| D | Delete selected entry |
| C | Copy to clipboard |

---

## Safety Tips for New Users

Here are some important things to keep in mind as you start using PassFX.

### Choose a strong master password

Your master password protects everything. Make it strong:
- Use at least 12 characters (longer is better)
- Mix letters, numbers, and symbols
- Avoid obvious things like your birthday or pet's name
- Consider using a passphrase: "Purple-Elephant-Runs-Fast-42!"

### Do not share your master password

This might seem obvious, but it is worth saying: your master password should be known only to you (and perhaps one trusted person for emergencies).

### Lock your computer when you step away

If you leave your computer unlocked while PassFX is open, anyone could see your passwords. Always lock your screen:
- **macOS:** Press `Control + Command + Q`
- **Windows:** Press `Windows + L`
- **Linux:** Usually `Super + L` or through your desktop menu

### Be aware of your surroundings

When typing your master password or viewing passwords, be aware of who might be watching. This is called "shoulder surfing."

### Back up your vault

Your vault files are stored at:
- **macOS/Linux:** `~/.passfx/`
- **Windows:** `C:\Users\yourname\.passfx\`

Inside this folder, you will find:
- `vault.enc` — your encrypted passwords
- `salt` — a file needed for decryption

**You need BOTH files to restore your vault.** Consider backing them up to:
- An encrypted USB drive
- A secure backup service
- Another safe location

### Be careful with screenshots

If you take a screenshot while PassFX is open, you might accidentally capture sensitive information. Be mindful of what is on screen.

### Keep PassFX updated

Occasionally, check for updates:

```
pip3 install --upgrade passfx
```

Updates may include security improvements and bug fixes.

---

## Uninstalling PassFX

If you ever need to remove PassFX, here is how.

### Removing the program

Open your terminal and type:

**On macOS or Linux:**
```
pip3 uninstall passfx
```

**On Windows:**
```
pip uninstall passfx
```

Type `y` and press Enter when asked to confirm.

### What about your passwords?

Uninstalling PassFX does **not** delete your vault. Your encrypted passwords remain on your computer at:
- **macOS/Linux:** `~/.passfx/`
- **Windows:** `C:\Users\yourname\.passfx\`

If you want to completely remove your data:
1. Navigate to that folder
2. Delete the entire `.passfx` folder

**Warning:** Once deleted, your passwords are gone forever. There is no way to recover them.

### What about Python?

You can leave Python installed — it does not hurt anything and you might need it for other programs. If you want to remove it:
- **macOS:** Python can be uninstalled from the Applications folder
- **Windows:** Use "Add or Remove Programs" in Settings
- **Linux:** Use your package manager

---

## Where to Go Next

Congratulations! You have installed PassFX and created your first vault. Here are some resources for learning more:

### In-app help

Press `?` while using PassFX to see a help screen with keyboard shortcuts and tips.

### User Guide

For detailed instructions on all features, read the [User Guide](USER_GUIDE.md).

### Main documentation

The [README](../README.md) provides a technical overview of PassFX's features and security model.

### Need help?

If you are stuck or have questions:
- Check the [User Guide](USER_GUIDE.md) for detailed instructions
- Visit the GitHub repository for community support

### You do not need to be a programmer

Everything you need to use PassFX is covered in this guide and the User Guide. You do not need to learn programming, understand code, or become a security expert.

> If you can follow instructions, you can use PassFX.

---

## Final thoughts

You have taken an important step toward better password security. By using a password manager, you can:
- Use unique, strong passwords for every account
- Stop trying to remember dozens of passwords
- Protect yourself from the risks of password reuse

PassFX is designed to be simple enough for anyone to use, while being secure enough for security professionals. You do not need to understand how the encryption works — you just need to remember your master password.

Welcome to PassFX. Your passwords are now truly yours.

---

*If you found this guide helpful, consider sharing it with someone who might benefit from better password security. The more people who protect their passwords properly, the safer we all are.*
