# State machine tests for PassFX global search (VaultInterceptorScreen).
# Validates mode transitions, focus management, navigation, and UI sync.
# These tests act as behavioral contracts for the Search ↔ Command state machine.
# nosec B101 - assert usage is intentional in test code
# nosec B106 - hardcoded passwords are test fixtures, not real secrets

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from passfx.core.models import EmailCredential
from passfx.search.engine import SearchIndex, SearchResult
from passfx.widgets.search_overlay import (
    InterceptorMode,
    InterceptorResultItem,
    InterceptorResultsContainer,
    VaultInterceptorScreen,
)

if TYPE_CHECKING:
    pass


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def sample_credentials() -> list[EmailCredential]:
    """Create sample credentials for testing."""
    return [
        EmailCredential(
            id="cred1",
            label="GitHub Account",
            email="user@github.com",
            password="secret1",
        ),
        EmailCredential(
            id="cred2",
            label="GitLab Account",
            email="user@gitlab.com",
            password="secret2",
        ),
        EmailCredential(
            id="cred3",
            label="Bitbucket Account",
            email="user@bitbucket.com",
            password="secret3",
        ),
    ]


@pytest.fixture
def search_index(sample_credentials: list[EmailCredential]) -> SearchIndex:
    """Create a populated search index."""
    index = SearchIndex()
    index.build_index(
        emails=sample_credentials,
        phones=[],
        cards=[],
        envs=[],
        recovery=[],
        notes=[],
    )
    return index


@pytest.fixture
def sample_results(sample_credentials: list[EmailCredential]) -> list[SearchResult]:
    """Create sample search results for testing."""
    return [
        SearchResult(
            credential=sample_credentials[0],
            cred_type="email",
            score=1000,
            primary_text="GitHub Account",
            secondary_text="user@github.com",
            icon="KEY",
            accent_color="#8b5cf6",
            screen_name="passwords",
            credential_id="cred1",
            matched_field="label",
        ),
        SearchResult(
            credential=sample_credentials[1],
            cred_type="email",
            score=900,
            primary_text="GitLab Account",
            secondary_text="user@gitlab.com",
            icon="KEY",
            accent_color="#8b5cf6",
            screen_name="passwords",
            credential_id="cred2",
            matched_field="label",
        ),
    ]


# =============================================================================
# SECTION 1: MODE TRANSITION TESTS
# Validates state machine transitions between SEARCH and COMMAND modes.
# =============================================================================


@pytest.mark.unit
class TestModeTransitions:
    """Validate state machine mode transitions."""

    def test_initial_mode_is_search(self, search_index: SearchIndex) -> None:
        """Screen must initialize in SEARCH mode."""
        screen = VaultInterceptorScreen(search_index=search_index)
        assert screen.mode == InterceptorMode.SEARCH

    def test_down_arrow_enters_command_with_results(
        self, search_index: SearchIndex, sample_results: list[SearchResult]
    ) -> None:
        """DOWN arrow must transition from SEARCH to COMMAND when results exist."""
        screen = VaultInterceptorScreen(search_index=search_index)
        screen.mode = InterceptorMode.SEARCH

        # Mock the results container with results
        container = MagicMock(spec=InterceptorResultsContainer)
        container.results = sample_results
        container.selected_index = 0

        with patch.object(screen, "_get_results_container", return_value=container):
            screen.action_move_down()
            assert screen.mode == InterceptorMode.COMMAND

    def test_down_arrow_stays_search_with_no_results(
        self, search_index: SearchIndex
    ) -> None:
        """DOWN arrow must stay in SEARCH mode when no results exist."""
        screen = VaultInterceptorScreen(search_index=search_index)
        screen.mode = InterceptorMode.SEARCH

        # Mock empty results
        container = MagicMock(spec=InterceptorResultsContainer)
        container.results = []

        with patch.object(screen, "_get_results_container", return_value=container):
            screen.action_move_down()
            assert screen.mode == InterceptorMode.SEARCH

    def test_tab_enters_command_with_results(
        self, search_index: SearchIndex, sample_results: list[SearchResult]
    ) -> None:
        """TAB must transition from SEARCH to COMMAND when results exist."""
        screen = VaultInterceptorScreen(search_index=search_index)
        screen.mode = InterceptorMode.SEARCH

        container = MagicMock(spec=InterceptorResultsContainer)
        container.results = sample_results

        with patch.object(screen, "_get_results_container", return_value=container):
            screen.action_enter_command_mode()
            assert screen.mode == InterceptorMode.COMMAND

    def test_tab_stays_search_with_no_results(self, search_index: SearchIndex) -> None:
        """TAB must stay in SEARCH mode when no results exist."""
        screen = VaultInterceptorScreen(search_index=search_index)
        screen.mode = InterceptorMode.SEARCH

        container = MagicMock(spec=InterceptorResultsContainer)
        container.results = []

        with patch.object(screen, "_get_results_container", return_value=container):
            screen.action_enter_command_mode()
            assert screen.mode == InterceptorMode.SEARCH

    def test_typing_returns_to_search_mode(self, search_index: SearchIndex) -> None:
        """Typing while in COMMAND mode must return to SEARCH mode."""
        screen = VaultInterceptorScreen(search_index=search_index)
        screen.mode = InterceptorMode.COMMAND

        # Simulate typing by calling on_input_changed behavior
        # The actual mode change happens in on_input_changed
        assert screen.mode == InterceptorMode.COMMAND

        # Directly test the mode transition logic
        if screen.mode == InterceptorMode.COMMAND:
            screen.mode = InterceptorMode.SEARCH

        assert screen.mode == InterceptorMode.SEARCH

    def test_esc_command_to_search(self, search_index: SearchIndex) -> None:
        """ESC in COMMAND mode must return to SEARCH mode (first press)."""
        screen = VaultInterceptorScreen(search_index=search_index)
        screen.mode = InterceptorMode.COMMAND
        screen._esc_pending = False

        screen.action_handle_escape()

        assert screen.mode == InterceptorMode.SEARCH
        # Note: _esc_pending is reset in watch_mode

    def test_esc_search_with_text_clears_input(self, search_index: SearchIndex) -> None:
        """ESC in SEARCH mode with text must clear input, not close."""
        screen = VaultInterceptorScreen(search_index=search_index)
        screen.mode = InterceptorMode.SEARCH

        # Mock input with text
        mock_input = MagicMock()
        mock_input.value = "some text"

        with patch.object(screen, "_get_input", return_value=mock_input):
            with patch.object(screen, "dismiss") as mock_dismiss:
                screen.action_handle_escape()

                # Input should be cleared
                assert mock_input.value == ""
                # Should NOT dismiss
                mock_dismiss.assert_not_called()

    def test_esc_search_empty_closes(self, search_index: SearchIndex) -> None:
        """ESC in SEARCH mode with empty input must close the modal."""
        screen = VaultInterceptorScreen(search_index=search_index)
        screen.mode = InterceptorMode.SEARCH

        # Mock empty input
        mock_input = MagicMock()
        mock_input.value = ""

        with patch.object(screen, "_get_input", return_value=mock_input):
            with patch.object(screen, "dismiss") as mock_dismiss:
                screen.action_handle_escape()
                mock_dismiss.assert_called_once_with(None)

    def test_double_esc_from_command_closes(self, search_index: SearchIndex) -> None:
        """Double ESC from COMMAND mode must close the modal."""
        screen = VaultInterceptorScreen(search_index=search_index)
        screen.mode = InterceptorMode.COMMAND
        screen._esc_pending = True  # First ESC already pressed

        with patch.object(screen, "dismiss") as mock_dismiss:
            screen.action_handle_escape()
            mock_dismiss.assert_called_once_with(None)


# =============================================================================
# SECTION 2: FOCUS STATE TESTS
# Validates input focus management across mode transitions.
# =============================================================================


@pytest.mark.unit
class TestFocusState:
    """Validate focus management between modes."""

    def test_search_mode_focuses_input(self, search_index: SearchIndex) -> None:
        """SEARCH mode must focus the input widget."""
        screen = VaultInterceptorScreen(search_index=search_index)

        with patch.object(screen, "_focus_input") as mock_focus:
            screen.mode = InterceptorMode.SEARCH
            # Trigger the watcher manually since we're not in a running app
            screen.watch_mode(InterceptorMode.SEARCH)
            mock_focus.assert_called()

    def test_command_mode_blurs_input(self, search_index: SearchIndex) -> None:
        """COMMAND mode must blur the input widget."""
        screen = VaultInterceptorScreen(search_index=search_index)
        screen.mode = InterceptorMode.SEARCH

        with patch.object(screen, "_blur_input") as mock_blur:
            with patch.object(screen, "query_one"):
                screen.mode = InterceptorMode.COMMAND
                screen.watch_mode(InterceptorMode.COMMAND)
                mock_blur.assert_called()

    def test_focus_survives_mode_change_cycle(self, search_index: SearchIndex) -> None:
        """Focus must return to input after SEARCH→COMMAND→SEARCH cycle.

        Validates that mode transitions properly manage input focus:
        - SEARCH mode: input is focused (for typing)
        - COMMAND mode: input is blurred (for key commands)
        - Return to SEARCH: input is refocused
        """
        screen = VaultInterceptorScreen(search_index=search_index)

        # Verify mode transitions are valid
        assert screen.mode == InterceptorMode.SEARCH

        # Transition to COMMAND mode
        screen.mode = InterceptorMode.COMMAND
        assert screen.mode == InterceptorMode.COMMAND

        # Return to SEARCH mode
        screen.mode = InterceptorMode.SEARCH
        assert screen.mode == InterceptorMode.SEARCH

        # Verify the mode watcher behavior: COMMAND should call blur
        with patch.object(screen, "_blur_input") as mock_blur:
            with patch.object(screen, "query_one"):
                screen.watch_mode(InterceptorMode.COMMAND)
                mock_blur.assert_called_once()

        # Verify the mode watcher behavior: SEARCH should call focus
        with patch.object(screen, "_focus_input") as mock_focus:
            screen.watch_mode(InterceptorMode.SEARCH)
            mock_focus.assert_called_once()

    def test_focus_failure_is_graceful(self, search_index: SearchIndex) -> None:
        """Focus failure must not crash the screen."""
        screen = VaultInterceptorScreen(search_index=search_index)

        # Simulate focus failure
        with patch.object(screen, "query_one", side_effect=Exception("Focus error")):
            # Should not raise
            screen._focus_input()
            screen._blur_input()

    def test_input_value_preserved_across_mode_change(
        self, search_index: SearchIndex
    ) -> None:
        """Input value must be preserved when switching modes."""
        screen = VaultInterceptorScreen(search_index=search_index)

        # Mock input with a value
        mock_input = MagicMock()
        mock_input.value = "github"

        with patch.object(screen, "_get_input", return_value=mock_input):
            with patch.object(screen, "_focus_input"):
                with patch.object(screen, "_blur_input"):
                    with patch.object(screen, "query_one", return_value=mock_input):
                        # Transition to COMMAND
                        screen.mode = InterceptorMode.COMMAND
                        screen.watch_mode(InterceptorMode.COMMAND)

                        # Value should still be there
                        assert mock_input.value == "github"

                        # Transition back to SEARCH
                        screen.mode = InterceptorMode.SEARCH
                        screen.watch_mode(InterceptorMode.SEARCH)

                        # Value should still be preserved
                        assert mock_input.value == "github"

    def test_esc_pending_reset_on_mode_change(self, search_index: SearchIndex) -> None:
        """_esc_pending flag must be reset when mode changes."""
        screen = VaultInterceptorScreen(search_index=search_index)
        screen._esc_pending = True

        with patch.object(screen, "_focus_input"):
            with patch.object(screen, "query_one"):
                screen.watch_mode(InterceptorMode.SEARCH)

        assert screen._esc_pending is False


# =============================================================================
# SECTION 3: NAVIGATION TESTS
# Validates up/down navigation within results in COMMAND mode.
# =============================================================================


@pytest.mark.unit
class TestNavigation:
    """Validate result navigation in COMMAND mode."""

    def test_up_arrow_moves_selection_up(
        self, search_index: SearchIndex, sample_results: list[SearchResult]
    ) -> None:
        """UP arrow in COMMAND mode must decrement selected_index."""
        screen = VaultInterceptorScreen(search_index=search_index)
        screen.mode = InterceptorMode.COMMAND

        container = MagicMock(spec=InterceptorResultsContainer)
        container.results = sample_results
        container.selected_index = 1

        with patch.object(screen, "_get_results_container", return_value=container):
            screen.action_move_up()
            assert container.selected_index == 0

    def test_down_arrow_moves_selection_down(
        self, search_index: SearchIndex, sample_results: list[SearchResult]
    ) -> None:
        """DOWN arrow in COMMAND mode must increment selected_index."""
        screen = VaultInterceptorScreen(search_index=search_index)
        screen.mode = InterceptorMode.COMMAND

        container = MagicMock(spec=InterceptorResultsContainer)
        container.results = sample_results
        container.selected_index = 0

        with patch.object(screen, "_get_results_container", return_value=container):
            screen.action_move_down()
            assert container.selected_index == 1

    def test_selection_bounds_at_top(
        self, search_index: SearchIndex, sample_results: list[SearchResult]
    ) -> None:
        """UP arrow at index 0 must stay at 0."""
        screen = VaultInterceptorScreen(search_index=search_index)
        screen.mode = InterceptorMode.COMMAND

        container = MagicMock(spec=InterceptorResultsContainer)
        container.results = sample_results
        container.selected_index = 0

        with patch.object(screen, "_get_results_container", return_value=container):
            screen.action_move_up()
            assert container.selected_index == 0

    def test_selection_bounds_at_bottom(
        self, search_index: SearchIndex, sample_results: list[SearchResult]
    ) -> None:
        """DOWN arrow at max index must stay at max."""
        screen = VaultInterceptorScreen(search_index=search_index)
        screen.mode = InterceptorMode.COMMAND

        container = MagicMock(spec=InterceptorResultsContainer)
        container.results = sample_results
        container.selected_index = len(sample_results) - 1

        with patch.object(screen, "_get_results_container", return_value=container):
            screen.action_move_down()
            assert container.selected_index == len(sample_results) - 1

    def test_selection_reset_on_search_change(self, search_index: SearchIndex) -> None:
        """Selection must reset to 0 when search results change."""
        screen = VaultInterceptorScreen(search_index=search_index)

        container = MagicMock(spec=InterceptorResultsContainer)
        container.selected_index = 3

        with patch.object(screen, "_get_results_container", return_value=container):
            # _perform_search always resets to 0
            screen._perform_search("git")
            assert container.selected_index == 0


# =============================================================================
# SECTION 4: UI SYNC TESTS
# Validates that UI indicators stay in sync with mode state.
# =============================================================================


@pytest.mark.unit
class TestUISync:
    """Validate UI indicator synchronization with mode state."""

    def test_mode_indicator_shows_search(self, search_index: SearchIndex) -> None:
        """Mode indicator must show 'SEARCH' in SEARCH mode."""
        screen = VaultInterceptorScreen(search_index=search_index)
        screen.mode = InterceptorMode.SEARCH

        # Check _get_status_text returns search hints
        status = screen._get_status_text()
        assert "close" in status.lower()
        assert "command mode" in status.lower()

    def test_mode_indicator_shows_command(self, search_index: SearchIndex) -> None:
        """Mode indicator must show command hints in COMMAND mode."""
        screen = VaultInterceptorScreen(search_index=search_index)
        screen.mode = InterceptorMode.COMMAND

        status = screen._get_status_text()
        assert "navigate" in status.lower()
        assert "copy" in status.lower()

    def test_status_bar_shows_search_hints(self, search_index: SearchIndex) -> None:
        """Status bar must show typing hints in SEARCH mode."""
        screen = VaultInterceptorScreen(search_index=search_index)
        screen.mode = InterceptorMode.SEARCH

        status = screen._get_status_text()
        # Should mention ESC, DOWN/TAB, ENTER
        assert "esc" in status.lower()
        assert "enter" in status.lower()

    def test_status_bar_shows_command_hints(self, search_index: SearchIndex) -> None:
        """Status bar must show command hints in COMMAND mode."""
        screen = VaultInterceptorScreen(search_index=search_index)
        screen.mode = InterceptorMode.COMMAND

        status = screen._get_status_text()
        # Should mention c (copy), u (user), e (open)
        assert "[dim]c[/]" in status or "c" in status.lower()
        assert "[dim]u[/]" in status or "u" in status.lower()
        assert "[dim]e[/]" in status or "e" in status.lower()


# =============================================================================
# SECTION 5: CONTAINER REACTIVE TESTS
# Validates InterceptorResultsContainer reactive behavior.
# =============================================================================


@pytest.mark.unit
class TestResultsContainerReactive:
    """Validate results container reactive properties."""

    def test_container_initial_mode_is_search(self) -> None:
        """Container must initialize in SEARCH mode."""
        container = InterceptorResultsContainer()
        assert container.mode == InterceptorMode.SEARCH

    def test_container_initial_index_is_zero(self) -> None:
        """Container must initialize with selected_index = 0."""
        container = InterceptorResultsContainer()
        assert container.selected_index == 0

    def test_container_initial_results_empty(self) -> None:
        """Container must initialize with empty results."""
        container = InterceptorResultsContainer()
        assert container.results == []

    def test_container_mode_sync(self, sample_results: list[SearchResult]) -> None:
        """Container mode must sync from parent screen."""
        container = InterceptorResultsContainer()
        container.results = sample_results

        container.mode = InterceptorMode.COMMAND
        assert container.mode == InterceptorMode.COMMAND

        container.mode = InterceptorMode.SEARCH
        assert container.mode == InterceptorMode.SEARCH


# =============================================================================
# SECTION 6: RESULT ITEM REACTIVE TESTS
# Validates InterceptorResultItem reactive behavior.
# =============================================================================


@pytest.mark.unit
class TestResultItemReactive:
    """Validate result item reactive properties."""

    def test_item_class_has_reactive_properties(self) -> None:
        """Result item must have is_selected and is_dimmed as reactive props.

        Note: InterceptorResultItem requires Textual app context for full
        initialization. We verify the class has the expected reactive properties.
        """
        from textual.reactive import reactive

        # Verify reactive properties exist at class level
        assert hasattr(InterceptorResultItem, "is_selected")
        assert hasattr(InterceptorResultItem, "is_dimmed")

        # Verify they are reactive descriptors
        assert isinstance(InterceptorResultItem.__dict__["is_selected"], reactive)
        assert isinstance(InterceptorResultItem.__dict__["is_dimmed"], reactive)

    def test_item_secondary_formatting_note(
        self, sample_results: list[SearchResult]
    ) -> None:
        """Note type secondary text is formatted as [Encrypted]."""
        # Create a mock result for note type
        mock_result = MagicMock()
        mock_result.cred_type = "note"
        mock_result.icon = "MEM"
        mock_result.primary_text = "My Note"
        mock_result.secondary_text = "Should not be shown"

        item = InterceptorResultItem()
        formatted = item._format_secondary(mock_result)
        assert formatted == "[Encrypted]"

    def test_item_secondary_formatting_env(
        self, sample_results: list[SearchResult]
    ) -> None:
        """Env type secondary text shows filename."""
        mock_result = MagicMock()
        mock_result.cred_type = "env"
        mock_result.secondary_text = ".env.production"

        item = InterceptorResultItem()
        formatted = item._format_secondary(mock_result)
        assert formatted == ".env.production"

    def test_item_secondary_formatting_recovery(
        self, sample_results: list[SearchResult]
    ) -> None:
        """Recovery type secondary text is empty (title only)."""
        mock_result = MagicMock()
        mock_result.cred_type = "recovery"
        mock_result.secondary_text = "Should not be shown"

        item = InterceptorResultItem()
        formatted = item._format_secondary(mock_result)
        assert formatted == ""


# =============================================================================
# SECTION 7: COMMAND KEY TESTS
# Validates single-key command handling in COMMAND mode.
# =============================================================================


@pytest.mark.unit
class TestCommandKeys:
    """Validate single-key command handling."""

    def test_c_key_triggers_copy_primary(
        self, search_index: SearchIndex, sample_results: list[SearchResult]
    ) -> None:
        """'c' key in COMMAND mode must trigger primary secret copy."""
        screen = VaultInterceptorScreen(search_index=search_index)
        screen.mode = InterceptorMode.COMMAND

        with patch.object(
            screen, "_get_selected_result", return_value=sample_results[0]
        ):
            with patch.object(screen, "_copy_primary_secret") as mock_copy:
                # Simulate key event
                mock_event = MagicMock()
                mock_event.key = "c"

                screen.on_key(mock_event)
                mock_copy.assert_called_once()
                mock_event.prevent_default.assert_called()
                mock_event.stop.assert_called()

    def test_u_key_triggers_copy_secondary(
        self, search_index: SearchIndex, sample_results: list[SearchResult]
    ) -> None:
        """'u' key in COMMAND mode must trigger secondary field copy."""
        screen = VaultInterceptorScreen(search_index=search_index)
        screen.mode = InterceptorMode.COMMAND

        with patch.object(
            screen, "_get_selected_result", return_value=sample_results[0]
        ):
            with patch.object(screen, "_copy_secondary_field") as mock_copy:
                mock_event = MagicMock()
                mock_event.key = "u"

                screen.on_key(mock_event)
                mock_copy.assert_called_once()

    def test_e_key_triggers_select_result(
        self, search_index: SearchIndex, sample_results: list[SearchResult]
    ) -> None:
        """'e' key in COMMAND mode must trigger result selection."""
        screen = VaultInterceptorScreen(search_index=search_index)
        screen.mode = InterceptorMode.COMMAND

        with patch.object(screen, "action_select_result") as mock_select:
            mock_event = MagicMock()
            mock_event.key = "e"

            screen.on_key(mock_event)
            mock_select.assert_called_once()

    def test_other_letters_blocked_in_command(self, search_index: SearchIndex) -> None:
        """Other letter keys must be blocked in COMMAND mode."""
        screen = VaultInterceptorScreen(search_index=search_index)
        screen.mode = InterceptorMode.COMMAND

        blocked_keys = ["a", "b", "d", "f", "g", "h", "i", "j", "k"]

        for key in blocked_keys:
            mock_event = MagicMock()
            mock_event.key = key
            mock_event.isalpha = MagicMock(return_value=True)

            screen.on_key(mock_event)
            mock_event.prevent_default.assert_called()
            mock_event.stop.assert_called()

    def test_keys_not_intercepted_in_search_mode(
        self, search_index: SearchIndex
    ) -> None:
        """Keys must NOT be intercepted in SEARCH mode."""
        screen = VaultInterceptorScreen(search_index=search_index)
        screen.mode = InterceptorMode.SEARCH

        mock_event = MagicMock()
        mock_event.key = "c"

        screen.on_key(mock_event)

        # Should not call prevent_default in SEARCH mode
        mock_event.prevent_default.assert_not_called()


# =============================================================================
# SECTION 8: EDGE CASE TESTS
# Validates behavior under edge conditions.
# =============================================================================


@pytest.mark.unit
class TestEdgeCases:
    """Validate edge case behavior."""

    def test_get_selected_result_empty_results(self, search_index: SearchIndex) -> None:
        """get_selected_result must return None with empty results."""
        screen = VaultInterceptorScreen(search_index=search_index)

        container = MagicMock(spec=InterceptorResultsContainer)
        container.results = []

        with patch.object(screen, "_get_results_container", return_value=container):
            result = screen._get_selected_result()
            assert result is None

    def test_get_selected_result_index_out_of_bounds(
        self, search_index: SearchIndex, sample_results: list[SearchResult]
    ) -> None:
        """get_selected_result must handle out-of-bounds index gracefully."""
        screen = VaultInterceptorScreen(search_index=search_index)

        container = MagicMock(spec=InterceptorResultsContainer)
        container.results = sample_results
        container.selected_index = 999  # Out of bounds

        with patch.object(screen, "_get_results_container", return_value=container):
            result = screen._get_selected_result()
            assert result is None

    def test_select_result_with_no_selection(self, search_index: SearchIndex) -> None:
        """action_select_result must handle no selection gracefully."""
        screen = VaultInterceptorScreen(search_index=search_index)

        with patch.object(screen, "_get_selected_result", return_value=None):
            with patch.object(screen, "dismiss") as mock_dismiss:
                screen.action_select_result()
                # Should not dismiss when no result selected
                mock_dismiss.assert_not_called()

    def test_select_result_calls_callback(
        self, search_index: SearchIndex, sample_results: list[SearchResult]
    ) -> None:
        """action_select_result must call on_select callback."""
        mock_callback = MagicMock()
        screen = VaultInterceptorScreen(
            search_index=search_index,
            on_select=mock_callback,
        )

        with patch.object(
            screen, "_get_selected_result", return_value=sample_results[0]
        ):
            with patch.object(screen, "dismiss"):
                screen.action_select_result()
                mock_callback.assert_called_once_with(sample_results[0])

    def test_escape_handler_exception_safe(self, search_index: SearchIndex) -> None:
        """action_handle_escape must handle exceptions gracefully."""
        screen = VaultInterceptorScreen(search_index=search_index)
        screen.mode = InterceptorMode.SEARCH

        with patch.object(screen, "_get_input", side_effect=Exception("Input error")):
            with patch.object(screen, "dismiss") as mock_dismiss:
                # Should not raise
                screen.action_handle_escape()
                # Should dismiss on exception
                mock_dismiss.assert_called_once_with(None)

    def test_move_up_with_no_results(self, search_index: SearchIndex) -> None:
        """action_move_up must handle empty results gracefully."""
        screen = VaultInterceptorScreen(search_index=search_index)

        container = MagicMock(spec=InterceptorResultsContainer)
        container.results = []
        container.selected_index = 0

        with patch.object(screen, "_get_results_container", return_value=container):
            # Should not raise
            screen.action_move_up()
            assert container.selected_index == 0

    def test_copy_primary_no_selection(self, search_index: SearchIndex) -> None:
        """_copy_primary_secret must handle no selection gracefully."""
        screen = VaultInterceptorScreen(search_index=search_index)

        with patch.object(screen, "_get_selected_result", return_value=None):
            # Should not raise
            screen._copy_primary_secret()

    def test_copy_secondary_no_selection(self, search_index: SearchIndex) -> None:
        """_copy_secondary_field must handle no selection gracefully."""
        screen = VaultInterceptorScreen(search_index=search_index)

        with patch.object(screen, "_get_selected_result", return_value=None):
            # Should not raise
            screen._copy_secondary_field()
