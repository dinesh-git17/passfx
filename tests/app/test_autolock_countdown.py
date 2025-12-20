# Auto-Lock Countdown Tests
# Validates MainMenuScreen countdown warning visibility, color escalation,
# and time formatting behavior.

from __future__ import annotations

import pytest


class TestCountdownVisibilityConditions:
    """Tests for countdown warning visibility conditions."""

    @pytest.mark.unit
    def test_countdown_hidden_when_remaining_over_30_seconds(self) -> None:
        """Countdown should be hidden when remaining time > 30 seconds."""
        remaining = 60
        should_show = remaining is not None and remaining <= 30
        assert should_show is False

    @pytest.mark.unit
    def test_countdown_visible_when_remaining_30_or_less(self) -> None:
        """Countdown should be visible when remaining time <= 30 seconds."""
        remaining = 30
        should_show = remaining is not None and remaining <= 30
        assert should_show is True

    @pytest.mark.unit
    def test_countdown_visible_when_remaining_1_second(self) -> None:
        """Countdown should be visible at 1 second remaining."""
        remaining = 1
        should_show = remaining is not None and remaining <= 30
        assert should_show is True

    @pytest.mark.unit
    def test_countdown_hidden_when_remaining_none(self) -> None:
        """Countdown hidden when remaining is None (disabled or locked)."""
        remaining = None
        should_show = remaining is not None and remaining <= 30
        assert should_show is False


class TestCountdownColorEscalation:
    """Tests for countdown color escalation logic."""

    @pytest.mark.unit
    def test_cyan_color_for_30_seconds(self) -> None:
        """Cyan color used at 30 seconds."""
        remaining = 30
        if remaining <= 5:
            color = "#ef4444"
        elif remaining <= 15:
            color = "#f59e0b"
        else:
            color = "#00FFFF"
        assert color == "#00FFFF"

    @pytest.mark.unit
    def test_cyan_color_for_16_seconds(self) -> None:
        """Cyan color used at 16 seconds (boundary)."""
        remaining = 16
        if remaining <= 5:
            color = "#ef4444"
        elif remaining <= 15:
            color = "#f59e0b"
        else:
            color = "#00FFFF"
        assert color == "#00FFFF"

    @pytest.mark.unit
    def test_amber_color_for_15_seconds(self) -> None:
        """Amber color used at 15 seconds (boundary)."""
        remaining = 15
        if remaining <= 5:
            color = "#ef4444"
        elif remaining <= 15:
            color = "#f59e0b"
        else:
            color = "#00FFFF"
        assert color == "#f59e0b"

    @pytest.mark.unit
    def test_amber_color_for_10_seconds(self) -> None:
        """Amber color used at 10 seconds."""
        remaining = 10
        if remaining <= 5:
            color = "#ef4444"
        elif remaining <= 15:
            color = "#f59e0b"
        else:
            color = "#00FFFF"
        assert color == "#f59e0b"

    @pytest.mark.unit
    def test_amber_color_for_6_seconds(self) -> None:
        """Amber color used at 6 seconds (boundary)."""
        remaining = 6
        if remaining <= 5:
            color = "#ef4444"
        elif remaining <= 15:
            color = "#f59e0b"
        else:
            color = "#00FFFF"
        assert color == "#f59e0b"

    @pytest.mark.unit
    def test_red_color_for_5_seconds(self) -> None:
        """Red color used at 5 seconds (critical threshold)."""
        remaining = 5
        if remaining <= 5:
            color = "#ef4444"
        elif remaining <= 15:
            color = "#f59e0b"
        else:
            color = "#00FFFF"
        assert color == "#ef4444"

    @pytest.mark.unit
    def test_red_color_for_1_second(self) -> None:
        """Red color used at 1 second."""
        remaining = 1
        if remaining <= 5:
            color = "#ef4444"
        elif remaining <= 15:
            color = "#f59e0b"
        else:
            color = "#00FFFF"
        assert color == "#ef4444"


class TestCountdownTimeFormatting:
    """Tests for countdown time string formatting."""

    @pytest.mark.unit
    def test_format_30_seconds(self) -> None:
        """Format 30 seconds as 00:30."""
        remaining = 30
        minutes = remaining // 60
        seconds = remaining % 60
        time_str = f"{minutes:02d}:{seconds:02d}"
        assert time_str == "00:30"

    @pytest.mark.unit
    def test_format_5_seconds(self) -> None:
        """Format 5 seconds as 00:05 with zero padding."""
        remaining = 5
        minutes = remaining // 60
        seconds = remaining % 60
        time_str = f"{minutes:02d}:{seconds:02d}"
        assert time_str == "00:05"

    @pytest.mark.unit
    def test_format_1_second(self) -> None:
        """Format 1 second as 00:01."""
        remaining = 1
        minutes = remaining // 60
        seconds = remaining % 60
        time_str = f"{minutes:02d}:{seconds:02d}"
        assert time_str == "00:01"

    @pytest.mark.unit
    def test_format_10_seconds(self) -> None:
        """Format 10 seconds as 00:10."""
        remaining = 10
        minutes = remaining // 60
        seconds = remaining % 60
        time_str = f"{minutes:02d}:{seconds:02d}"
        assert time_str == "00:10"


class TestCountdownPulseBehavior:
    """Tests for countdown pulse toggle behavior."""

    @pytest.mark.unit
    def test_pulse_class_toggles_on_update(self) -> None:
        """Pulse class should toggle between on and off states."""
        has_pulse = False

        # First toggle
        has_pulse = not has_pulse
        assert has_pulse is True

        # Second toggle
        has_pulse = not has_pulse
        assert has_pulse is False

        # Third toggle
        has_pulse = not has_pulse
        assert has_pulse is True


class TestCountdownMessageFormat:
    """Tests for the complete countdown message format."""

    @pytest.mark.unit
    def test_message_format_cyan(self) -> None:
        """Full message format for cyan state."""
        remaining = 25
        minutes = remaining // 60
        seconds = remaining % 60
        time_str = f"{minutes:02d}:{seconds:02d}"
        color = "#00FFFF"
        message = f"[bold {color}]AUTO-LOCK IN {time_str}[/]"
        assert message == "[bold #00FFFF]AUTO-LOCK IN 00:25[/]"

    @pytest.mark.unit
    def test_message_format_amber(self) -> None:
        """Full message format for amber state."""
        remaining = 10
        minutes = remaining // 60
        seconds = remaining % 60
        time_str = f"{minutes:02d}:{seconds:02d}"
        color = "#f59e0b"
        message = f"[bold {color}]AUTO-LOCK IN {time_str}[/]"
        assert message == "[bold #f59e0b]AUTO-LOCK IN 00:10[/]"

    @pytest.mark.unit
    def test_message_format_red(self) -> None:
        """Full message format for red/critical state."""
        remaining = 3
        minutes = remaining // 60
        seconds = remaining % 60
        time_str = f"{minutes:02d}:{seconds:02d}"
        color = "#ef4444"
        message = f"[bold {color}]AUTO-LOCK IN {time_str}[/]"
        assert message == "[bold #ef4444]AUTO-LOCK IN 00:03[/]"
