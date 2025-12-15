"""Main Menu Screen for PassFX - Security Command Center."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, OptionList, Static
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


class MainMenuScreen(Screen):
    """Security Command Center - main dashboard with navigation sidebar."""

    BINDINGS = [
        Binding("1", "passwords", "Passwords", show=False),
        Binding("2", "phones", "Phones", show=False),
        Binding("3", "cards", "Cards", show=False),
        Binding("4", "generator", "Generator", show=False),
        Binding("5", "settings", "Settings", show=False),
        Binding("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        """Create the command center layout."""
        yield Header()

        with Horizontal(id="main-container"):
            # Left pane: Navigation sidebar
            with Vertical(id="sidebar"):
                yield Static(SIDEBAR_LOGO, id="sidebar-logo")
                yield OptionList(
                    Option("[ KEY ]  Passwords", id="passwords"),
                    Option("[ PIN ]  Phones", id="phones"),
                    Option("[ CRD ]  Cards", id="cards"),
                    Option("[ GEN ]  Generator", id="generator"),
                    Option("[ SET ]  Settings", id="settings"),
                    Option("[ EXIT ] Quit", id="exit"),
                    id="sidebar-menu",
                )
                yield Static(f"[dim]{VERSION}[/]", id="sidebar-version")

            # Right pane: Dashboard view
            with Vertical(id="dashboard-view"):
                yield Static(
                    "[bold #60a5fa]━━━ VAULT STATUS ━━━[/]",
                    id="dashboard-title",
                )

                # Stats row - clickable cards
                with Horizontal(id="stats-row"):
                    yield Button("PASSWORDS\n0", id="stat-passwords", classes="stat-card")
                    yield Button("PINS\n0", id="stat-phones", classes="stat-card")
                    yield Button("CARDS\n0", id="stat-cards", classes="stat-card")

                # Security gauge
                yield Static(id="security-gauge", classes="gauge-panel")

                # System log
                yield Static(id="system-log", classes="log-panel")

        yield Footer()

    def on_mount(self) -> None:
        """Initialize dashboard data on mount."""
        self._focus_sidebar()
        self._refresh_dashboard()

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
        total = stats.get("total", 0)

        # Update stat cards (Buttons)
        self.query_one("#stat-passwords", Button).label = f"PASSWORDS\n{email_count}"
        self.query_one("#stat-phones", Button).label = f"PINS\n{phone_count}"
        self.query_one("#stat-cards", Button).label = f"CARDS\n{card_count}"

        # Run security analysis
        analysis = self._analyze_security(app)
        bar_filled = int(analysis.score / 10)
        bar_empty = 10 - bar_filled
        bar_color = self._get_score_color(analysis.score)

        # Build security gauge with breakdown
        gauge_lines = [
            f"[bold #60a5fa]━━━ SECURITY SCORE ━━━[/]\n",
            f"  [{bar_color}]{'█' * bar_filled}[/][dim]{'░' * bar_empty}[/]  "
            f"[bold {bar_color}]{analysis.score}%[/]\n",
        ]

        # Add breakdown if there are items
        if total > 0:
            if analysis.password_scores:
                avg = sum(analysis.password_scores) / len(analysis.password_scores)
                strength_label = ["Very Weak", "Weak", "Fair", "Good", "Strong"][min(4, int(avg))]
                gauge_lines.append(f"  [dim]Avg Strength:[/] {strength_label}")
            if analysis.reused_passwords > 0:
                gauge_lines.append(f"  [#ef4444]Reused:[/] {analysis.reused_passwords}")
            if analysis.weak_pins > 0:
                gauge_lines.append(f"  [#f59e0b]Weak PINs:[/] {analysis.weak_pins}")
            if analysis.old_passwords > 0:
                gauge_lines.append(f"  [#f59e0b]Stale (>90d):[/] {analysis.old_passwords}")

        self.query_one("#security-gauge", Static).update("\n".join(gauge_lines))

        # System log with issues
        status_lines = [
            "[bold #60a5fa]━━━ SYSTEM STATUS ━━━[/]\n",
            f"  [#22c55e]●[/] Vault Decrypted",
            f"  [#22c55e]●[/] Session Active",
            f"  [dim]●[/] Entries: {total}",
        ]

        if analysis.issues:
            status_lines.append("\n[bold #f59e0b]━━━ ISSUES ━━━[/]\n")
            for issue in analysis.issues:
                status_lines.append(f"  [#ef4444]![/] {issue}")
        else:
            status_lines.append("\n  [#22c55e]✓[/] No security issues")

        self.query_one("#system-log", Static).update("\n".join(status_lines))

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

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle stat card button clicks."""
        button_id = event.button.id

        if button_id == "stat-passwords":
            self.action_passwords()
        elif button_id == "stat-phones":
            self.action_phones()
        elif button_id == "stat-cards":
            self.action_cards()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Handle menu selection."""
        option_id = event.option.id

        if option_id == "passwords":
            self.action_passwords()
        elif option_id == "phones":
            self.action_phones()
        elif option_id == "cards":
            self.action_cards()
        elif option_id == "generator":
            self.action_generator()
        elif option_id == "settings":
            self.action_settings()
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

    def action_generator(self) -> None:
        """Go to password generator screen."""
        from passfx.screens.generator import GeneratorScreen

        self.app.push_screen(GeneratorScreen())

    def action_settings(self) -> None:
        """Go to settings screen."""
        from passfx.screens.settings import SettingsScreen

        self.app.push_screen(SettingsScreen())

    def action_quit(self) -> None:
        """Quit the application."""
        self.app.action_quit()
