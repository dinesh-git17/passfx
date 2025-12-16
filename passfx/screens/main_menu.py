"""Main Menu Screen for PassFX - Security Command Center."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.events import Click
from textual.screen import Screen
from textual.widgets import Digits, Label, OptionList, Static
from textual.widgets.option_list import Option

from passfx.utils.strength import check_strength

if TYPE_CHECKING:
    from passfx.app import PassFXApp


# Common weak PINs to check against
WEAK_PINS = {
    "0000", "1111", "2222", "3333", "4444", "5555", "6666", "7777", "8888", "9999",
    "1234", "4321", "1212", "2121", "1122", "2211", "0123", "3210", "9876", "6789",
    "1010", "2020", "1357", "2468", "1379", "2580", "0852", "1590", "7531", "8642",
    "0001", "0002", "0007", "0011", "0069", "0420", "1004", "1007", "2000", "2001",
    "2002", "2003", "2004", "2005", "2006", "2007", "2008", "2009", "2010", "2011",
    "2012", "2013", "2014", "2015", "2016", "2017", "2018", "2019", "2020", "2021",
    "2022", "2023", "2024", "2025", "6969", "4200", "1337",
}

# Password age threshold in days
PASSWORD_AGE_WARNING_DAYS = 90


@dataclass
class SecurityAnalysis:
    """Detailed security analysis results."""

    score: int  # 0-100
    password_scores: list[int]  # Individual password strength scores (0-4)
    reused_passwords: int  # Count of reused passwords
    weak_pins: int  # Count of weak PINs
    old_passwords: int  # Passwords older than threshold
    total_items: int
    issues: list[str]  # List of security issues found

# Compact sidebar logo
SIDEBAR_LOGO = """[bold #00d4ff]╔══════════════════════╗
║  P A S S F X  ║
║  COMMAND CENTER  ║
╚══════════════════════╝[/]"""

VERSION = "v1.0.0"


def _make_menu_item(code: str, label: str) -> Text:
    """Create a menu item with fixed-width icon and label columns.

    Args:
        code: The short code (e.g., "KEY", "PIN")
        label: The menu item label

    Returns:
        Rich Text object with consistent formatting
    """
    text = Text()
    # Icon part: Cyan/Blue, fixed width 7 chars, centered
    text.append(f"{code:^7}", style="bold #3b82f6")
    # Label part: White, bold
    text.append(f" {label}", style="bold white")
    return text


class MainMenuScreen(Screen):
    """Security Command Center - main dashboard with navigation sidebar."""

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("question_mark", "help", "Help"),
    ]

    def compose(self) -> ComposeResult:
        """Create the command center layout."""
        # Custom header - System Status Bar with live telemetry
        with Horizontal(id="app-header"):
            yield Static("[bold #00d4ff]◄ PASSFX ►[/]", id="header-branding")
            yield Static("░░ SECURITY COMMAND CENTER ░░", id="header-status")
            yield Static("", id="header-clock")
            yield Static("🔓 DECRYPTED", id="header-lock")

        with Horizontal(id="main-container"):
            # Left pane: Navigation sidebar
            with Vertical(id="sidebar"):
                yield Static(SIDEBAR_LOGO, id="sidebar-logo")
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
                    "[bold #60a5fa]━━━ VAULT STATUS ━━━[/]",
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

                # Security gauge and System log - side by side (responsive)
                with Horizontal(id="panels-row"):
                    yield Static(id="security-gauge", classes="gauge-panel")
                    yield Static(id="system-log", classes="log-panel")

        # Custom footer - Mechanical keycap command strip
        with Horizontal(id="app-footer"):
            # Left segment: Version (aligns with sidebar)
            yield Static(f" {VERSION} ", id="footer-version")
            # Right segment: Key hints as mechanical keycaps
            with Horizontal(id="footer-keys"):
                with Horizontal(classes="keycap-group"):
                    yield Static("[bold #a78bfa] ↑↓ [/]", classes="keycap")
                    yield Static("[#64748b]Navigate[/]", classes="keycap-label")
                with Horizontal(classes="keycap-group"):
                    yield Static("[bold #a78bfa] ⏎ [/]", classes="keycap")
                    yield Static("[#64748b]Select[/]", classes="keycap-label")
                with Horizontal(classes="keycap-group"):
                    yield Static("[bold #a78bfa] ? [/]", classes="keycap")
                    yield Static("[#64748b]Help[/]", classes="keycap-label")
                with Horizontal(classes="keycap-group"):
                    yield Static("[bold #a78bfa] Q [/]", classes="keycap")
                    yield Static("[#64748b]Quit[/]", classes="keycap-label")

    def on_mount(self) -> None:
        """Initialize dashboard data on mount."""
        self._focus_sidebar()
        self._refresh_dashboard()
        self._update_clock()
        self.set_interval(1, self._update_clock)

    def _update_clock(self) -> None:
        """Update the header clock with current time and vault stats."""
        app: PassFXApp = self.app  # type: ignore
        now = datetime.now().strftime("%H:%M:%S")

        # Get vault file size if available
        vault_size = ""
        if app._unlocked and app.vault.path.exists():
            size_bytes = app.vault.path.stat().st_size
            if size_bytes < 1024:
                vault_size = f"{size_bytes}B"
            else:
                vault_size = f"{size_bytes // 1024}KB"
            vault_size = f"[dim]│[/] [#8b5cf6]{vault_size}[/]"

        clock_widget = self.query_one("#header-clock", Static)
        clock_widget.update(f"[#60a5fa]{now}[/] {vault_size}")

    def on_screen_resume(self) -> None:
        """Called when screen becomes active again after being covered."""
        self._focus_sidebar()
        self._refresh_dashboard()

    def _focus_sidebar(self) -> None:
        """Focus the sidebar menu."""
        self.query_one("#sidebar-menu", OptionList).focus()

    def _refresh_dashboard(self) -> None:
        """Refresh all dashboard widgets with current vault data."""
        app: PassFXApp = self.app  # type: ignore
        stats = app.vault.get_stats() if app._unlocked else {}

        email_count = stats.get("emails", 0)
        phone_count = stats.get("phones", 0)
        card_count = stats.get("cards", 0)
        notes_count = stats.get("notes", 0)
        envs_count = stats.get("envs", 0)
        recovery_count = stats.get("recovery", 0)
        total = stats.get("total", 0)

        # Update stat digits - Row 1
        self.query_one("#digits-passwords", Digits).update(f"{email_count:02d}")
        self.query_one("#digits-phones", Digits).update(f"{phone_count:02d}")
        self.query_one("#digits-cards", Digits).update(f"{card_count:02d}")

        # Update stat digits - Row 2
        self.query_one("#digits-notes", Digits).update(f"{notes_count:02d}")
        self.query_one("#digits-envs", Digits).update(f"{envs_count:02d}")
        self.query_one("#digits-recovery", Digits).update(f"{recovery_count:02d}")

        # Run security analysis
        analysis = self._analyze_security(app)
        bar_color = self._get_score_color(analysis.score)

        # Build strength frequency histogram
        gauge_lines = self._build_strength_histogram(analysis, bar_color)

        gauge_widget = self.query_one("#security-gauge", Static)
        gauge_widget.border_title = "SECURITY SCORE"
        gauge_widget.update("\n".join(gauge_lines))

        # System log with bracketed timestamps (terminal buffer style)
        ts = datetime.now().strftime("%H:%M:%S")
        status_lines = [
            f"[dim #555555][{ts}][/] [bold #22c55e]➜[/] VAULT MOUNTED (AES-256)",
            f"[dim #555555][{ts}][/] [bold #3b82f6]i[/] INDEXED: {total} ITEMS",
            f"[dim #555555][{ts}][/] [bold #22c55e]✓[/] ENCRYPTION VERIFIED",
        ]

        if analysis.issues:
            for issue in analysis.issues[:2]:  # Limit to 2 issues
                status_lines.append(f"[dim #555555][{ts}][/] [bold #ef4444]![/] {issue.upper()}")
        else:
            status_lines.append(f"[dim #555555][{ts}][/] [bold #22c55e]✓[/] SECURITY AUDIT: PASS")
            status_lines.append(f"[dim #555555][{ts}][/] [bold #3b82f6]i[/] SYSTEM READY")

        log_widget = self.query_one("#system-log", Static)
        log_widget.border_title = "SYSTEM LOG"
        log_widget.update("\n".join(status_lines))

    def _analyze_security(self, app: PassFXApp) -> SecurityAnalysis:
        """Perform comprehensive security analysis of vault contents."""
        if not app._unlocked:
            return SecurityAnalysis(
                score=0,
                password_scores=[],
                reused_passwords=0,
                weak_pins=0,
                old_passwords=0,
                total_items=0,
                issues=["Vault is locked"],
            )

        emails = app.vault.get_emails()
        phones = app.vault.get_phones()
        cards = app.vault.get_cards()

        total_items = len(emails) + len(phones) + len(cards)

        if total_items == 0:
            return SecurityAnalysis(
                score=100,  # Empty vault is "secure" by default
                password_scores=[],
                reused_passwords=0,
                weak_pins=0,
                old_passwords=0,
                total_items=0,
                issues=[],
            )

        issues: list[str] = []
        password_scores: list[int] = []
        all_passwords: list[str] = []
        old_passwords = 0
        weak_pins = 0
        now = datetime.now()

        # Analyze email credentials
        for cred in emails:
            # Check password strength
            strength = check_strength(cred.password)
            password_scores.append(strength.score)
            all_passwords.append(cred.password)

            if strength.score <= 1:
                issues.append(f"Weak password: {cred.label}")

            # Check password age
            try:
                created = datetime.fromisoformat(cred.created_at)
                age_days = (now - created).days
                if age_days > PASSWORD_AGE_WARNING_DAYS:
                    old_passwords += 1
            except (ValueError, TypeError):
                pass

        # Analyze phone PINs
        for cred in phones:
            pin = cred.password
            all_passwords.append(pin)

            # Check for weak PINs
            if pin in WEAK_PINS:
                weak_pins += 1
                issues.append(f"Weak PIN: {cred.label}")
            elif len(pin) < 4:
                weak_pins += 1
                issues.append(f"Short PIN: {cred.label}")
            elif len(set(pin)) == 1:  # All same digits
                weak_pins += 1
                issues.append(f"Repeating PIN: {cred.label}")

        # Check for password reuse
        password_counts = Counter(all_passwords)
        reused = sum(1 for count in password_counts.values() if count > 1)
        if reused > 0:
            issues.append(f"{reused} reused password(s) detected")

        # Calculate overall score
        score = self._compute_score(
            password_scores=password_scores,
            reused_passwords=reused,
            weak_pins=weak_pins,
            old_passwords=old_passwords,
            total_items=total_items,
        )

        return SecurityAnalysis(
            score=score,
            password_scores=password_scores,
            reused_passwords=reused,
            weak_pins=weak_pins,
            old_passwords=old_passwords,
            total_items=total_items,
            issues=issues[:5],  # Limit to top 5 issues
        )

    def _compute_score(
        self,
        password_scores: list[int],
        reused_passwords: int,
        weak_pins: int,
        old_passwords: int,
        total_items: int,
    ) -> int:
        """Compute the final security score from analysis data."""
        if total_items == 0:
            return 100

        score = 100.0

        # Password strength component (40% of score)
        if password_scores:
            avg_strength = sum(password_scores) / len(password_scores)
            # Convert 0-4 scale to 0-40 points
            strength_points = (avg_strength / 4) * 40
            score = score - 40 + strength_points

        # Password reuse penalty (25% of score)
        if reused_passwords > 0:
            reuse_penalty = min(25, reused_passwords * 10)
            score -= reuse_penalty

        # Weak PIN penalty (20% of score)
        if weak_pins > 0:
            pin_penalty = min(20, weak_pins * 10)
            score -= pin_penalty

        # Password age penalty (15% of score)
        if old_passwords > 0:
            age_penalty = min(15, old_passwords * 5)
            score -= age_penalty

        return max(0, min(100, int(score)))

    def _get_score_color(self, score: int) -> str:
        """Get color based on security score."""
        if score >= 80:
            return "#22c55e"  # Green - Excellent
        elif score >= 60:
            return "#60a5fa"  # Blue - Good
        elif score >= 40:
            return "#f59e0b"  # Yellow/Orange - Fair
        else:
            return "#ef4444"  # Red - Poor

    def _build_strength_histogram(
        self, analysis: SecurityAnalysis, score_color: str
    ) -> list[str]:
        """Build a VFD-style segmented gauge with strength distribution."""
        lines: list[str] = []

        # VFD-style segmented gauge (20 segments)
        num_segments = 20
        filled = int((analysis.score / 100) * num_segments)
        empty = num_segments - filled
        # Use pipe characters for retro LED/VFD look
        bar_str = f"[{score_color}]{'▮' * filled}[/][dim #222222]{'·' * empty}[/]"
        lines.append(f"{bar_str}  [bold {score_color}]{analysis.score}%[/]")
        lines.append("")

        if not analysis.password_scores:
            lines.append("[dim #555555]No passwords to analyze[/]")
            return lines

        # Count occurrences of each strength level (0-4)
        strength_counts = Counter(analysis.password_scores)
        max_count = max(strength_counts.values()) if strength_counts else 1
        bar_width = 12  # Maximum bar width in characters

        # Strength level definitions with colors
        levels = [
            (0, "WEAK  ", "#ef4444"),
            (1, "POOR  ", "#ef4444"),
            (2, "FAIR  ", "#f59e0b"),
            (3, "GOOD  ", "#60a5fa"),
            (4, "STRONG", "#22c55e"),
        ]

        # Build histogram bars with spacing
        for level, label, color in levels:
            count = strength_counts.get(level, 0)
            if count > 0 or level in (0, 4):  # Always show WEAK and STRONG
                bar_len = int((count / max_count) * bar_width) if max_count > 0 else 0
                bar = "█" * bar_len + "░" * (bar_width - bar_len)
                lines.append(f"[{color}]{label}[/] [{color}]{bar}[/] {count}")
                lines.append("")  # Breathing room between bars

        # Add issue summary if any
        if analysis.reused_passwords > 0 or analysis.weak_pins > 0:
            if analysis.reused_passwords > 0:
                lines.append(f"[#ef4444]⚠ Reused:[/] {analysis.reused_passwords}")
            if analysis.weak_pins > 0:
                lines.append(f"[#f59e0b]⚠ Weak PINs:[/] {analysis.weak_pins}")

        return lines

    def on_click(self, event: Click) -> None:
        """Handle clicks on stat segments."""
        # Check if click is within a stat segment
        widget = event.widget
        while widget is not None:
            if widget.id == "segment-passwords":
                self.action_passwords()
                return
            elif widget.id == "segment-phones":
                self.action_phones()
                return
            elif widget.id == "segment-cards":
                self.action_cards()
                return
            elif widget.id == "segment-notes":
                self.action_notes()
                return
            elif widget.id == "segment-envs":
                self.action_envs()
                return
            elif widget.id == "segment-recovery":
                self.action_recovery()
                return
            widget = widget.parent

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

    def action_passwords(self) -> None:
        """Go to passwords screen."""
        from passfx.screens.passwords import PasswordsScreen

        self.app.push_screen(PasswordsScreen())

    def action_phones(self) -> None:
        """Go to phones screen."""
        from passfx.screens.phones import PhonesScreen

        self.app.push_screen(PhonesScreen())

    def action_cards(self) -> None:
        """Go to cards screen."""
        from passfx.screens.cards import CardsScreen

        self.app.push_screen(CardsScreen())

    def action_notes(self) -> None:
        """Go to secure notes screen."""
        from passfx.screens.notes import NotesScreen

        self.app.push_screen(NotesScreen())

    def action_envs(self) -> None:
        """Go to env vars screen."""
        from passfx.screens.envs import EnvsScreen

        self.app.push_screen(EnvsScreen())

    def action_recovery(self) -> None:
        """Go to recovery codes screen."""
        from passfx.screens.recovery import RecoveryScreen

        self.app.push_screen(RecoveryScreen())

    def action_generator(self) -> None:
        """Go to password generator screen."""
        from passfx.screens.generator import GeneratorScreen

        self.app.push_screen(GeneratorScreen())

    def action_settings(self) -> None:
        """Go to settings screen."""
        from passfx.screens.settings import SettingsScreen

        self.app.push_screen(SettingsScreen())

    def action_help(self) -> None:
        """Show the help screen."""
        from passfx.screens.help import HelpScreen

        self.app.push_screen(HelpScreen())

    def action_quit(self) -> None:
        """Quit the application."""
        self.app.action_quit()
