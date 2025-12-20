"""Main Menu Screen for PassFX - Security Command Center."""

# pylint: disable=duplicate-code

from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import TYPE_CHECKING

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.dom import DOMNode
from textual.events import Click
from textual.screen import Screen
from textual.widgets import Digits, Input, Label, OptionList, Static
from textual.widgets.option_list import Option

from passfx.utils.strength import VaultHealthResult, analyze_vault
from passfx.widgets.terminal import SystemTerminal

if TYPE_CHECKING:
    from passfx.app import PassFXApp

# Compact ASCII Logo - 3 lines
HEADER_LOGO = """[bold #00FFFF]█▀█ ▄▀█ █▀ █▀ █▀▀ ▀▄▀
█▀▀ █▀█ ▄█ ▄█ █▀  █ █[/]"""

VERSION = "v1.0.0"


class SecurityScore(Static):
    """Widget displaying vault health analysis with score and statistics.

    Renders everything as formatted text for precise layout control.
    """

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]
        self._health: VaultHealthResult | None = None

    def update_health(self, health: VaultHealthResult) -> None:
        """Update the widget with new health data and tooltip."""
        self._health = health
        self._render_display()
        self._update_tooltip(health)

    def _update_tooltip(self, health: VaultHealthResult) -> None:
        """Update tooltip with health explanation."""
        if health.overall_score >= 100:
            self.tooltip = "All credentials meet strength requirements"
        elif health.overall_score >= 80:
            issues = []
            if health.weak_count > 0:
                issues.append(f"{health.weak_count} weak")
            if health.reuse_count > 0:
                issues.append(f"{health.reuse_count} reused")
            if health.old_count > 0:
                issues.append(f"{health.old_count} old")
            self.tooltip = f"Minor issues: {', '.join(issues)}" if issues else "Good"
        else:
            self.tooltip = "Review weak or reused credentials"

    def _render_display(self) -> None:
        """Render the complete health display."""
        if self._health is None:
            self.update("[dim]No data[/]")
            return

        health = self._health
        lines: list[str] = []

        # Score bar
        score_color = self._get_score_color(health.overall_score)
        num_segments = 20
        filled = int((health.overall_score / 100) * num_segments)
        empty = num_segments - filled
        bar_str = f"[{score_color}]{'█' * filled}[/][#333333]{'░' * empty}[/]"
        lines.append(f"{bar_str}  [bold {score_color}]{health.overall_score}%[/]")
        lines.append("")  # Breathing room

        # Stats row - values and labels combined
        reuse_color = "#ef4444" if health.reuse_count > 0 else "#22c55e"
        old_color = "#f59e0b" if health.old_count > 0 else "#22c55e"
        weak_color = "#ef4444" if health.weak_count > 0 else "#22c55e"

        lines.append(
            f"[bold {reuse_color}]{health.reuse_count:^12}[/]"
            f"[bold {old_color}]{health.old_count:^12}[/]"
            f"[bold {weak_color}]{health.weak_count:^12}[/]"
        )
        lines.append(f"[#64748b]{'REUSED':^12}{'OLD (90d)':^12}{'WEAK':^12}[/]")
        lines.append("")  # Breathing room

        # Histogram
        lines.extend(self._build_histogram(health))

        self.update("\n".join(lines))

    def _get_score_color(self, score: int) -> str:
        """Get color based on security score - Operator theme palette."""
        if score >= 80:
            return "#00FFFF"  # Cyan - excellent
        if score >= 60:
            return "#22c55e"  # Green - good
        if score >= 40:
            return "#f59e0b"  # Amber - needs attention
        return "#ef4444"  # Red - critical

    def _build_histogram(self, health: VaultHealthResult) -> list[str]:
        """Build strength distribution histogram."""
        lines: list[str] = []

        if not health.password_scores:
            lines.append("[dim #555555]No passwords to analyze[/]")
            return lines

        strength_counts = Counter(health.password_scores)
        max_count = max(strength_counts.values()) if strength_counts else 1
        bar_width = 12

        levels = [
            (0, "WEAK  ", "#ef4444"),
            (1, "POOR  ", "#ef4444"),
            (2, "FAIR  ", "#f59e0b"),
            (3, "GOOD  ", "#00FFFF"),
            (4, "STRONG", "#22c55e"),
        ]

        for level, label, color in levels:
            count = strength_counts.get(level, 0)
            if count > 0 or level in (0, 4):
                bar_len = int((count / max_count) * bar_width) if max_count > 0 else 0
                progress_bar = "█" * bar_len + "░" * (bar_width - bar_len)
                lines.append(f"[{color}]{label}[/] [{color}]{progress_bar}[/] {count}")

        return lines


def _make_menu_item(code: str, label: str) -> Text:
    """Create a menu item with Operator theme [ ] prefix decorators.

    Args:
        code: The short code (e.g., "KEY", "PIN")
        label: The menu item label

    Returns:
        Rich Text object with [ CODE ] prefix decoration
    """
    text = Text()
    # Operator theme: [ ] prefix with cyan accent
    text.append("[", style="bold #00FFFF")
    text.append(f"{code:^5}", style="bold #00FFFF")
    text.append("]", style="bold #00FFFF")
    text.append(f" {label}", style="white")
    return text


class MainMenuScreen(Screen):
    """Security Command Center - main dashboard with navigation sidebar."""

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("question_mark", "help", "Help"),
        Binding("escape", "focus_sidebar", "Back to Menu", show=False),
        Binding("slash", "focus_terminal", "Terminal", show=False),
    ]

    def compose(self) -> ComposeResult:  # pylint: disable=too-many-statements
        """Create the command center layout."""
        # Command Bar - Operator theme header with ASCII logo
        with Horizontal(id="app-header"):
            yield Static(HEADER_LOGO, id="header-branding")
            yield Static("", id="header-countdown")
            with Horizontal(id="header-right"):
                yield Static("", id="header-clock")
                yield Static("[dim]│[/] [#22c55e]DECRYPTED[/]", id="header-lock")

        with Horizontal(id="main-container"):
            # Left pane: Navigation sidebar
            with Vertical(id="sidebar") as sidebar:
                sidebar.border_title = "COMMAND CENTRE"
                yield OptionList(
                    Option(_make_menu_item("KEY", "Passwords"), id="passwords"),
                    Option(_make_menu_item("PIN", "Phones"), id="phones"),
                    Option(_make_menu_item("CRD", "Cards"), id="cards"),
                    Option(_make_menu_item("MEM", "Notes"), id="notes"),
                    Option(_make_menu_item("ENV", "Env Vars"), id="envs"),
                    Option(_make_menu_item("SOS", "Recovery"), id="recovery"),
                    Option(_make_menu_item("GEN", "Generator"), id="generator"),
                    Option(_make_menu_item("SET", "Settings"), id="settings"),
                    Option(_make_menu_item("?", "Help"), id="help"),
                    Option(_make_menu_item("EXIT", "Quit"), id="exit"),
                    id="sidebar-menu",
                )

            # Right pane: Dashboard view (scrollable for smaller screens)
            with VerticalScroll(id="dashboard-view"):
                yield Static(
                    "[bold #00FFFF][ VAULT STATUS ][/]",
                    id="dashboard-title",
                )

                # Stats HUD strip - Row 1: Primary Credentials
                with Horizontal(id="stats-strip"):
                    # Segment 1: Passwords
                    with Vertical(id="segment-passwords", classes="stat-segment"):
                        yield Label("PASSWORDS", classes="stat-label")
                        yield Digits("00", id="digits-passwords", classes="stat-value")

                    # Segment 2: PINs
                    with Vertical(id="segment-phones", classes="stat-segment"):
                        yield Label("PINS", classes="stat-label")
                        yield Digits("00", id="digits-phones", classes="stat-value")

                    # Segment 3: Cards
                    with Vertical(id="segment-cards", classes="stat-segment"):
                        yield Label("CARDS", classes="stat-label")
                        yield Digits("00", id="digits-cards", classes="stat-value")

                # Stats HUD strip - Row 2: Extended Vault
                with Horizontal(id="stats-strip-2"):
                    # Segment 4: Notes
                    with Vertical(id="segment-notes", classes="stat-segment"):
                        yield Label("NOTES", classes="stat-label")
                        yield Digits("00", id="digits-notes", classes="stat-value")

                    # Segment 5: Env Vars
                    with Vertical(id="segment-envs", classes="stat-segment"):
                        yield Label("ENV VARS", classes="stat-label")
                        yield Digits("00", id="digits-envs", classes="stat-value")

                    # Segment 6: Recovery
                    with Vertical(id="segment-recovery", classes="stat-segment"):
                        yield Label("RECOVERY", classes="stat-label")
                        yield Digits("00", id="digits-recovery", classes="stat-value")

                # Security gauge and System terminal - side by side (responsive)
                with Horizontal(id="panels-row"):
                    yield SecurityScore(id="security-gauge", classes="gauge-panel")
                    yield SystemTerminal(id="system-terminal", classes="log-panel")

        # Custom footer - Mechanical keycap command strip
        with Horizontal(id="app-footer"):
            # Left segment: Version (aligns with sidebar)
            yield Static(f" {VERSION} ", id="footer-version")
            # Right segment: Key hints as mechanical keycaps
            with Horizontal(id="footer-keys"):
                with Horizontal(classes="keycap-group"):
                    yield Static("[bold #00FFFF] ↑↓ [/]", classes="keycap")
                    yield Static("[#666666]Navigate[/]", classes="keycap-label")
                with Horizontal(classes="keycap-group"):
                    yield Static("[bold #00FFFF] ENTER [/]", classes="keycap")
                    yield Static("[#666666]Select[/]", classes="keycap-label")
                with Horizontal(classes="keycap-group"):
                    yield Static("[bold #00FFFF] / [/]", classes="keycap")
                    yield Static("[#666666]Terminal[/]", classes="keycap-label")
                with Horizontal(classes="keycap-group"):
                    yield Static("[bold #00FFFF] ESC [/]", classes="keycap")
                    yield Static("[#666666]Back[/]", classes="keycap-label")
                with Horizontal(classes="keycap-group"):
                    yield Static("[bold #00FFFF] ? [/]", classes="keycap")
                    yield Static("[#666666]Help[/]", classes="keycap-label")
                with Horizontal(classes="keycap-group"):
                    yield Static("[bold #00FFFF] Q [/]", classes="keycap")
                    yield Static("[#666666]Quit[/]", classes="keycap-label")

    def on_mount(self) -> None:
        """Initialize dashboard data on mount."""
        self._focus_sidebar()
        self._log_startup_sequence()
        self._refresh_dashboard()
        self._update_clock()
        self.set_interval(1, self._update_clock)
        # Start subtle pulse on DECRYPTED status indicator
        self.set_interval(3.0, self._pulse_status)
        # Initialize countdown with placeholder to reserve space (hidden via opacity)
        countdown = self.query_one("#header-countdown", Static)
        countdown.update("AUTO-LOCK IN 00:00")

    def _log_startup_sequence(self) -> None:
        """Log welcome message and tips to the terminal."""
        terminal = self.query_one("#system-terminal", SystemTerminal)
        terminal.border_title = "SYSTEM TERMINAL"

        # Welcome and explanation
        terminal.log_raw("[bold #8b5cf6]Quick Navigation Terminal[/]")
        terminal.log_raw("[dim]Navigate PassFX using commands[/]")
        terminal.log_raw("")
        terminal.log_raw("[#666666]Commands:[/]")
        terminal.log_raw("  [#00FFFF]/key[/]  [dim]→ Passwords[/]")
        terminal.log_raw("  [#00FFFF]/gen[/]  [dim]→ Generator[/]")
        terminal.log_raw("  [#00FFFF]/help[/] [dim]→ All commands[/]")
        terminal.log_raw("")
        terminal.log_raw("[dim]Press[/] [#8b5cf6]/[/] [dim]to focus terminal[/]")
        terminal.log_raw("[dim]Press[/] [#8b5cf6]ESC[/] [dim]to return to menu[/]")

    def _update_clock(self) -> None:
        """Update the header clock with current time and vault stats.

        Applies a micro tick-glow effect to indicate time refresh.
        """
        app: PassFXApp = self.app  # type: ignore
        now = datetime.now().strftime("%H:%M:%S")

        # Get vault file size if available
        vault_size = ""
        if (
            app._unlocked and app.vault.path.exists()
        ):  # pylint: disable=protected-access
            size_bytes = app.vault.path.stat().st_size
            if size_bytes < 1024:
                vault_size = f"{size_bytes}B"
            else:
                vault_size = f"{size_bytes // 1024}KB"
            vault_size = f"[dim]│[/] [#8b5cf6]{vault_size}[/]"

        clock_widget = self.query_one("#header-clock", Static)
        clock_widget.update(f"[#00FFFF]{now}[/] {vault_size}")
        # Micro tick glow - brief brightness shift
        clock_widget.add_class("tick-glow")
        self.set_timer(0.15, lambda: clock_widget.remove_class("tick-glow"))

        # Update auto-lock countdown warning
        self._update_countdown()

    def _pulse_status(self) -> None:
        """Subtle pulse on DECRYPTED status indicator.

        Creates a slow heartbeat effect indicating active encryption monitoring.
        """
        app: PassFXApp = self.app  # type: ignore
        if not app._unlocked:  # pylint: disable=protected-access
            return

        lock_widget = self.query_one("#header-lock", Static)
        # Subtle brightness pulse - toggle intensity briefly
        lock_widget.update("[dim]│[/] [bold #00ff41]DECRYPTED[/]")
        self.set_timer(0.5, self._reset_status)

    def _reset_status(self) -> None:
        """Reset DECRYPTED status to normal intensity."""
        lock_widget = self.query_one("#header-lock", Static)
        lock_widget.update("[dim]│[/] [#22c55e]DECRYPTED[/]")

    def _update_countdown(self) -> None:
        """Update auto-lock countdown warning.

        Shows warning only in final 30 seconds before auto-lock.
        Color escalation: cyan (30-16s) -> amber (15-6s) -> red (<=5s).
        Uses opacity to show/hide while reserving layout space.
        """
        app: PassFXApp = self.app  # type: ignore[assignment]
        countdown_widget = self.query_one("#header-countdown", Static)

        # Hide if vault locked
        if not app._unlocked:  # pylint: disable=protected-access
            countdown_widget.remove_class("countdown-active", "countdown-pulse")
            return

        remaining = app.vault.get_remaining_lock_time()

        # Hide if auto-lock disabled or not in warning window
        if remaining is None or remaining > 30:
            countdown_widget.remove_class("countdown-active", "countdown-pulse")
            return

        # Format MM:SS
        minutes = remaining // 60
        seconds = remaining % 60
        time_str = f"{minutes:02d}:{seconds:02d}"

        # Color escalation
        if remaining <= 5:
            color = "#ef4444"  # Red - critical
        elif remaining <= 15:
            color = "#f59e0b"  # Amber - warning
        else:
            color = "#00FFFF"  # Cyan - notice

        countdown_widget.update(f"[bold {color}]AUTO-LOCK IN {time_str}[/]")
        countdown_widget.add_class("countdown-active")

        # Toggle pulse effect
        if countdown_widget.has_class("countdown-pulse"):
            countdown_widget.remove_class("countdown-pulse")
        else:
            countdown_widget.add_class("countdown-pulse")

    def on_screen_resume(self) -> None:
        """Called when screen becomes active again after being covered."""
        self._focus_sidebar()
        self._refresh_dashboard()

    def _focus_sidebar(self) -> None:
        """Focus the sidebar menu."""
        self.query_one("#sidebar-menu", OptionList).focus()

    def action_focus_sidebar(self) -> None:
        """Action to return focus to the sidebar menu (triggered by ESC)."""
        self._focus_sidebar()

    def action_focus_terminal(self) -> None:
        """Action to focus the terminal input (triggered by /)."""
        terminal = self.query_one("#system-terminal", SystemTerminal)
        terminal.focus_input()

    def _refresh_dashboard(self) -> None:
        """Refresh dashboard stat widgets with current vault data.

        Note: This only updates the stat digits and security gauge.
        Terminal logs are handled separately in _log_startup_sequence.
        """
        app: PassFXApp = self.app  # type: ignore
        stats = (
            app.vault.get_stats() if app._unlocked else {}
        )  # pylint: disable=protected-access

        email_count = stats.get("emails", 0)
        phone_count = stats.get("phones", 0)
        card_count = stats.get("cards", 0)
        notes_count = stats.get("notes", 0)
        envs_count = stats.get("envs", 0)
        recovery_count = stats.get("recovery", 0)

        # Update stat digits - Row 1
        self.query_one("#digits-passwords", Digits).update(f"{email_count:02d}")
        self.query_one("#digits-phones", Digits).update(f"{phone_count:02d}")
        self.query_one("#digits-cards", Digits).update(f"{card_count:02d}")

        # Update stat digits - Row 2
        self.query_one("#digits-notes", Digits).update(f"{notes_count:02d}")
        self.query_one("#digits-envs", Digits).update(f"{envs_count:02d}")
        self.query_one("#digits-recovery", Digits).update(f"{recovery_count:02d}")

        # Run security analysis using the new analyze_vault function
        credentials: list = []
        if app._unlocked:  # pylint: disable=protected-access
            credentials.extend(app.vault.get_emails())
            credentials.extend(app.vault.get_phones())

        health = analyze_vault(credentials)

        # Update the SecurityScore widget
        gauge_widget = self.query_one("#security-gauge", SecurityScore)
        gauge_widget.border_title = "VAULT HEALTH"
        gauge_widget.update_health(health)

    def on_click(self, event: Click) -> None:
        """Handle clicks on stat segments."""
        # Check if click is within a stat segment
        node: DOMNode | None = event.widget
        while node is not None:
            if node.id == "segment-passwords":
                self.action_passwords()
                return
            if node.id == "segment-phones":
                self.action_phones()
                return
            if node.id == "segment-cards":
                self.action_cards()
                return
            if node.id == "segment-notes":
                self.action_notes()
                return
            if node.id == "segment-envs":
                self.action_envs()
                return
            if node.id == "segment-recovery":
                self.action_recovery()
                return
            node = node.parent

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Handle menu selection."""
        option_id = event.option.id

        if option_id == "passwords":
            self.action_passwords()
        elif option_id == "phones":
            self.action_phones()
        elif option_id == "cards":
            self.action_cards()
        elif option_id == "notes":
            self.action_notes()
        elif option_id == "envs":
            self.action_envs()
        elif option_id == "recovery":
            self.action_recovery()
        elif option_id == "generator":
            self.action_generator()
        elif option_id == "settings":
            self.action_settings()
        elif option_id == "help":
            self.action_help()
        elif option_id == "exit":
            self.action_quit()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle terminal command input submission."""
        if event.input.id != "terminal-input":
            return

        terminal = self.query_one("#system-terminal", SystemTerminal)
        raw_command = event.value.strip()

        # Clear input and keep focus
        terminal.clear_input()
        terminal.focus_input()

        if not raw_command:
            return

        # Echo the command to the log
        terminal.write_log(f"[bold #8b5cf6]>[/] {raw_command}")

        # Normalize command: remove leading slash, uppercase for matching
        command = raw_command.lstrip("/").upper()

        # Command mapping
        commands = {
            "KEY": self.action_passwords,
            "PASSWORDS": self.action_passwords,
            "PIN": self.action_phones,
            "PHONES": self.action_phones,
            "CRD": self.action_cards,
            "CARDS": self.action_cards,
            "MEM": self.action_notes,
            "NOTES": self.action_notes,
            "ENV": self.action_envs,
            "ENVS": self.action_envs,
            "SOS": self.action_recovery,
            "RECOVERY": self.action_recovery,
            "GEN": self.action_generator,
            "GENERATOR": self.action_generator,
            "SET": self.action_settings,
            "SETTINGS": self.action_settings,
            "HELP": self.action_help,
            "?": self.action_help,
            "QUIT": self.action_quit,
            "EXIT": self.action_quit,
            "Q": self.action_quit,
        }

        # Special commands
        if command in ("CLEAR", "CLS"):
            terminal.clear_log()
            self._log_startup_sequence()
            return

        # Execute navigation command
        if command in commands:
            terminal.write_log("[bold #8b5cf6]⟩[/] Executing navigation protocol...")
            commands[command]()
        else:
            terminal.write_log(
                "[bold #ef4444]✗[/] Command not recognized. Try [bold]/help[/]"
            )

    def action_passwords(self) -> None:
        """Go to passwords screen."""
        # pylint: disable=import-outside-toplevel
        from passfx.screens.passwords import PasswordsScreen

        self.app.push_screen(PasswordsScreen())

    def action_phones(self) -> None:
        """Go to phones screen."""
        # pylint: disable=import-outside-toplevel
        from passfx.screens.phones import PhonesScreen

        self.app.push_screen(PhonesScreen())

    def action_cards(self) -> None:
        """Go to cards screen."""
        # pylint: disable=import-outside-toplevel
        from passfx.screens.cards import CardsScreen

        self.app.push_screen(CardsScreen())

    def action_notes(self) -> None:
        """Go to secure notes screen."""
        # pylint: disable=import-outside-toplevel
        from passfx.screens.notes import NotesScreen

        self.app.push_screen(NotesScreen())

    def action_envs(self) -> None:
        """Go to env vars screen."""
        # pylint: disable=import-outside-toplevel
        from passfx.screens.envs import EnvsScreen

        self.app.push_screen(EnvsScreen())

    def action_recovery(self) -> None:
        """Go to recovery codes screen."""
        # pylint: disable=import-outside-toplevel
        from passfx.screens.recovery import RecoveryScreen

        self.app.push_screen(RecoveryScreen())

    def action_generator(self) -> None:
        """Go to password generator screen."""
        # pylint: disable=import-outside-toplevel
        from passfx.screens.generator import GeneratorScreen

        self.app.push_screen(GeneratorScreen())

    def action_settings(self) -> None:
        """Go to settings screen."""
        # pylint: disable=import-outside-toplevel
        from passfx.screens.settings import SettingsScreen

        self.app.push_screen(SettingsScreen())

    def action_help(self) -> None:
        """Show the help screen."""
        # pylint: disable=import-outside-toplevel
        from passfx.screens.help import HelpScreen

        self.app.push_screen(HelpScreen())

    def action_quit(self) -> None:
        """Quit the application."""
        self.app.exit()
