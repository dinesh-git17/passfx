"""Help Screen for PassFX - System Operator's Manual."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Static, TabbedContent, TabPane


# ═══════════════════════════════════════════════════════════════════════════════
# CONTENT DATA
# ═══════════════════════════════════════════════════════════════════════════════

COMMANDS_CONTENT = """\
[bold #00d4ff]> NAVIGATION[/]
  [bold #00d4ff]UP/DOWN[/]    [#94a3b8]Navigate through list items[/]
  [bold #00d4ff]ENTER[/]      [#94a3b8]Select / Confirm action[/]
  [bold #00d4ff]ESC[/]        [#94a3b8]Go back / Cancel operation[/]
  [bold #00d4ff]TAB[/]        [#94a3b8]Switch focus between panels[/]

[bold #00d4ff]> ACTIONS[/]
  [bold #00d4ff]A[/]          [#94a3b8]Add new credential entry[/]
  [bold #00d4ff]E[/]          [#94a3b8]Edit selected credential[/]
  [bold #00d4ff]D[/]          [#94a3b8]Delete selected credential[/]
  [bold #00d4ff]V[/]          [#94a3b8]View credential details[/]
  [bold #00d4ff]C[/]          [#94a3b8]Copy password to clipboard[/]

[bold #00d4ff]> GLOBAL[/]
  [bold #00d4ff]Q[/]          [#94a3b8]Quit application[/]
  [bold #00d4ff]?[/]          [#94a3b8]Open this help screen[/]
  [bold #00d4ff]CTRL+P[/]     [#94a3b8]Open command palette[/]

[bold #8b5cf6]> TERMINAL COMMANDS[/]
  [bold #8b5cf6]/key[/]       [#94a3b8]Open Passwords screen[/]
  [bold #8b5cf6]/pin[/]       [#94a3b8]Open Phones/PINs screen[/]
  [bold #8b5cf6]/crd[/]       [#94a3b8]Open Cards screen[/]
  [bold #8b5cf6]/mem[/]       [#94a3b8]Open Secure Notes screen[/]
  [bold #8b5cf6]/env[/]       [#94a3b8]Open Env Variables screen[/]
  [bold #8b5cf6]/sos[/]       [#94a3b8]Open Recovery Codes screen[/]
  [bold #8b5cf6]/gen[/]       [#94a3b8]Open Password Generator[/]
  [bold #8b5cf6]/set[/]       [#94a3b8]Open Settings screen[/]
  [bold #8b5cf6]/help[/]      [#94a3b8]Open this help screen[/]
  [bold #8b5cf6]/clear[/]     [#94a3b8]Clear terminal output[/]
  [bold #8b5cf6]/quit[/]      [#94a3b8]Exit application[/]
"""

LEGEND_CONTENT = """\
[bold #00d4ff]> PASSWORD STRENGTH[/]
  [on #ef4444]  [/] [bold #ef4444]WEAK[/]       [#94a3b8]Easily cracked - change immediately[/]
  [on #f87171]  [/] [bold #f87171]POOR[/]       [#94a3b8]Below minimum security threshold[/]
  [on #f59e0b]  [/] [bold #f59e0b]FAIR[/]       [#94a3b8]Acceptable but could be stronger[/]
  [on #60a5fa]  [/] [bold #60a5fa]GOOD[/]       [#94a3b8]Meets security recommendations[/]
  [on #22c55e]  [/] [bold #22c55e]STRONG[/]     [#94a3b8]Excellent protection level[/]

[bold #00d4ff]> STATUS INDICATORS[/]
  [#22c55e]●[/] [bold #22c55e]ENCRYPTED[/]     [#94a3b8]Vault is secured and encrypted[/]
  [#ef4444]●[/] [bold #ef4444]DECRYPTED[/]     [#94a3b8]Vault unlocked (active session)[/]
  [#f59e0b]![/] [bold #f59e0b]WARNING[/]       [#94a3b8]Security issue detected[/]

[bold #00d4ff]> VISUAL ICONS[/]
  [#60a5fa]LOCK[/]        [#94a3b8]Credential entry (secure)[/]
  [#00d4ff]|[/]           [#94a3b8]Currently selected row[/]
  [#8b5cf6]>[/]           [#94a3b8]Active menu item[/]
"""

SYSTEM_CONTENT = """\
[bold #00d4ff]> ENCRYPTION PROTOCOL[/]
  [bold #8b5cf6]CIPHER[/]       [#22c55e]AES-256-CBC[/]
                 [dim #64748b]256-bit key, CBC mode[/]

  [bold #8b5cf6]INTEGRITY[/]    [#22c55e]HMAC-SHA256[/]
                 [dim #64748b]Message authentication[/]

  [bold #8b5cf6]KEY DERIVE[/]   [#22c55e]PBKDF2-HMAC-SHA256[/]
                 [dim #64748b]480,000 iterations[/]

  [bold #8b5cf6]SALT[/]         [#22c55e]32 bytes (256-bit)[/]
                 [dim #64748b]Cryptographically secure[/]

[bold #00d4ff]> STORAGE PATHS[/]
  [bold #8b5cf6]VAULT[/]        [#f8fafc]~/.passfx/vault.enc[/]
  [bold #8b5cf6]SALT[/]         [#f8fafc]~/.passfx/salt[/]
  [bold #8b5cf6]LOGS[/]         [#f8fafc]~/.passfx/logs/[/]

[bold #00d4ff]> SECURITY FEATURES[/]
  [#22c55e]+[/] [#94a3b8]Auto-clear clipboard (30s)[/]
  [#22c55e]+[/] [#94a3b8]No password recovery (by design)[/]
  [#22c55e]+[/] [#94a3b8]Zero-knowledge architecture[/]
  [#22c55e]+[/] [#94a3b8]Memory wiping for secrets[/]
  [#22c55e]+[/] [#94a3b8]Atomic file writes[/]
"""


# ═══════════════════════════════════════════════════════════════════════════════
# HELP SCREEN
# ═══════════════════════════════════════════════════════════════════════════════


class HelpScreen(ModalScreen[None]):
    """System Operator's Manual - Help documentation modal."""

    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("q", "close", "Close"),
        Binding("question_mark", "close", "Close"),
    ]

    def compose(self) -> ComposeResult:
        """Create the help modal layout."""
        with Vertical(id="help-modal"):
            # Header - using inverted block style like other screens
            yield Static(
                " SYSTEM OPERATOR'S MANUAL ",
                id="help-header",
                classes="pane-header-block",
            )

            # Subtitle
            yield Static(
                "[#94a3b8]PassFX Security Terminal v1.0[/]",
                id="help-subtitle",
            )

            # Tabbed content
            with TabbedContent(id="help-tabs"):
                with TabPane("COMMANDS", id="tab-commands"):
                    with VerticalScroll(id="commands-scroll"):
                        yield Static(COMMANDS_CONTENT, id="commands-content")

                with TabPane("LEGEND", id="tab-legend"):
                    with VerticalScroll(id="legend-scroll"):
                        yield Static(LEGEND_CONTENT, id="legend-content")

                with TabPane("SYSTEM", id="tab-system"):
                    with VerticalScroll(id="system-scroll"):
                        yield Static(SYSTEM_CONTENT, id="system-content")

            # Footer
            with Horizontal(id="help-footer"):
                yield Static(
                    "[dim #475569]ESC[/] [dim #64748b]Close[/]",
                    id="help-footer-left",
                )
                yield Static(
                    "[dim #475569]<-/->[/] [dim #64748b]Switch tabs[/]",
                    id="help-footer-right",
                )

    def action_close(self) -> None:
        """Close the help modal."""
        self.dismiss(None)
