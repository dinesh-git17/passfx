# Search Routing Tests
# Validates PassFXApp search overlay activation, index building, and result routing.
# Tests focus on isolated unit behavior, not full UI rendering.

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    from collections.abc import Generator


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_vault() -> MagicMock:
    """Create a mock Vault for testing without filesystem."""
    mock = MagicMock()
    mock.is_locked = False
    mock.get_emails.return_value = []
    mock.get_phones.return_value = []
    mock.get_cards.return_value = []
    mock.get_envs.return_value = []
    mock.get_recovery_entries.return_value = []
    mock.get_notes.return_value = []
    return mock


@pytest.fixture
def isolated_app(mock_vault: MagicMock) -> Generator[MagicMock, None, None]:
    """Create an isolated PassFXApp instance for testing.

    Uses mocking to prevent actual UI rendering or filesystem access.
    """
    with patch("passfx.app.Vault", return_value=mock_vault):
        from passfx.app import PassFXApp

        app = PassFXApp()
        # Mock UI methods to avoid TUI rendering
        app.push_screen = MagicMock()  # type: ignore[method-assign]  # type: ignore[method-assign]
        app.pop_screen = MagicMock()  # type: ignore[method-assign]
        app.notify = MagicMock()  # type: ignore[method-assign]
        yield app  # type: ignore[misc]


# ---------------------------------------------------------------------------
# action_toggle_search() Tests
# ---------------------------------------------------------------------------


class TestActionToggleSearch:
    """Tests for PassFXApp.action_toggle_search() method.

    Validates the search overlay activation guards and behavior.
    """

    @pytest.mark.unit
    def test_does_nothing_when_unlocked_is_false(self) -> None:
        """Verify action_toggle_search does nothing when vault is locked.

        Security invariant: Search is disabled when vault is locked to prevent
        any credential data exposure.
        """
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            app = PassFXApp()
            app._unlocked = False  # Vault is locked
            app.push_screen = MagicMock()  # type: ignore[method-assign]

            app.action_toggle_search()

            # push_screen should not be called when locked
            app.push_screen.assert_not_called()

    @pytest.mark.unit
    def test_does_nothing_on_login_screen(self) -> None:
        """Verify action_toggle_search does nothing when on LoginScreen.

        Guard: Search should not activate on authentication screen.
        """
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            # Create mock screen with LoginScreen class name
            mock_screen = MagicMock()
            mock_screen.__class__.__name__ = "LoginScreen"

            with patch.object(
                PassFXApp,
                "screen",
                new_callable=lambda: property(lambda self: mock_screen),
            ):
                app = PassFXApp()
                app._unlocked = True  # Unlocked
                app.push_screen = MagicMock()  # type: ignore[method-assign]

                app.action_toggle_search()

                app.push_screen.assert_not_called()

    @pytest.mark.unit
    def test_does_nothing_on_vault_interceptor_screen(self) -> None:
        """Verify action_toggle_search does nothing on VaultInterceptorScreen.

        Guard: Prevents nested search overlay activation.
        """
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            # Create mock screen with VaultInterceptorScreen class name
            mock_screen = MagicMock()
            mock_screen.__class__.__name__ = "VaultInterceptorScreen"

            with patch.object(
                PassFXApp,
                "screen",
                new_callable=lambda: property(lambda self: mock_screen),
            ):
                app = PassFXApp()
                app._unlocked = True
                app.push_screen = MagicMock()  # type: ignore[method-assign]

                app.action_toggle_search()

                app.push_screen.assert_not_called()

    @pytest.mark.unit
    def test_calls_build_search_index_when_guards_pass(self) -> None:
        """Verify _build_search_index is called when all guards pass."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault.is_locked = False
            mock_vault.get_emails.return_value = []
            mock_vault.get_phones.return_value = []
            mock_vault.get_cards.return_value = []
            mock_vault.get_envs.return_value = []
            mock_vault.get_recovery_entries.return_value = []
            mock_vault.get_notes.return_value = []
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            # Create mock screen (not LoginScreen or VaultInterceptorScreen)
            mock_screen = MagicMock()
            mock_screen.__class__.__name__ = "MainMenuScreen"

            with patch.object(
                PassFXApp,
                "screen",
                new_callable=lambda: property(lambda self: mock_screen),
            ):
                app = PassFXApp()
                app._unlocked = True
                app.push_screen = MagicMock()  # type: ignore[method-assign]
                app._build_search_index = MagicMock()  # type: ignore[method-assign]

                app.action_toggle_search()

                app._build_search_index.assert_called_once()

    @pytest.mark.unit
    def test_pushes_vault_interceptor_screen(self) -> None:
        """Verify VaultInterceptorScreen is pushed when search is activated."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault.is_locked = False
            mock_vault.get_emails.return_value = []
            mock_vault.get_phones.return_value = []
            mock_vault.get_cards.return_value = []
            mock_vault.get_envs.return_value = []
            mock_vault.get_recovery_entries.return_value = []
            mock_vault.get_notes.return_value = []
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp
            from passfx.widgets.search_overlay import VaultInterceptorScreen

            mock_screen = MagicMock()
            mock_screen.__class__.__name__ = "MainMenuScreen"

            with patch.object(
                PassFXApp,
                "screen",
                new_callable=lambda: property(lambda self: mock_screen),
            ):
                app = PassFXApp()
                app._unlocked = True
                app.push_screen = MagicMock()  # type: ignore[method-assign]

                app.action_toggle_search()

                app.push_screen.assert_called_once()
                call_args = app.push_screen.call_args

                # First positional argument should be VaultInterceptorScreen
                pushed_screen = call_args[0][0]
                assert isinstance(pushed_screen, VaultInterceptorScreen)

    @pytest.mark.unit
    def test_sets_callback_to_handle_search_result(self) -> None:
        """Verify callback is set to _handle_search_result."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault.is_locked = False
            mock_vault.get_emails.return_value = []
            mock_vault.get_phones.return_value = []
            mock_vault.get_cards.return_value = []
            mock_vault.get_envs.return_value = []
            mock_vault.get_recovery_entries.return_value = []
            mock_vault.get_notes.return_value = []
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            mock_screen = MagicMock()
            mock_screen.__class__.__name__ = "PasswordsScreen"

            with patch.object(
                PassFXApp,
                "screen",
                new_callable=lambda: property(lambda self: mock_screen),
            ):
                app = PassFXApp()
                app._unlocked = True
                app.push_screen = MagicMock()  # type: ignore[method-assign]

                app.action_toggle_search()

                call_kwargs = app.push_screen.call_args[1]
                assert "callback" in call_kwargs
                assert call_kwargs["callback"] == app._handle_search_result

    @pytest.mark.unit
    def test_passes_search_index_to_interceptor(self) -> None:
        """Verify the built search index is passed to VaultInterceptorScreen."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault.is_locked = False
            mock_vault.get_emails.return_value = []
            mock_vault.get_phones.return_value = []
            mock_vault.get_cards.return_value = []
            mock_vault.get_envs.return_value = []
            mock_vault.get_recovery_entries.return_value = []
            mock_vault.get_notes.return_value = []
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp
            from passfx.search.engine import SearchIndex

            mock_screen = MagicMock()
            mock_screen.__class__.__name__ = "CardsScreen"

            with patch.object(
                PassFXApp,
                "screen",
                new_callable=lambda: property(lambda self: mock_screen),
            ):
                app = PassFXApp()
                app._unlocked = True
                app.push_screen = MagicMock()  # type: ignore[method-assign]

                app.action_toggle_search()

                # Verify search index was built and stored
                assert app._search_index is not None
                assert isinstance(app._search_index, SearchIndex)

    @pytest.mark.unit
    def test_search_works_from_various_screens(self) -> None:
        """Verify search can be activated from various non-guarded screens."""
        screen_names = [
            "MainMenuScreen",
            "PasswordsScreen",
            "PhonesScreen",
            "CardsScreen",
            "EnvsScreen",
            "RecoveryScreen",
            "NotesScreen",
            "GeneratorScreen",
            "SettingsScreen",
        ]

        for screen_name in screen_names:
            with patch("passfx.app.Vault") as mock_vault_class:
                mock_vault = MagicMock()
                mock_vault.is_locked = False
                mock_vault.get_emails.return_value = []
                mock_vault.get_phones.return_value = []
                mock_vault.get_cards.return_value = []
                mock_vault.get_envs.return_value = []
                mock_vault.get_recovery_entries.return_value = []
                mock_vault.get_notes.return_value = []
                mock_vault_class.return_value = mock_vault

                from passfx.app import PassFXApp

                mock_screen = MagicMock()
                mock_screen.__class__.__name__ = screen_name

                with patch.object(
                    PassFXApp,
                    "screen",
                    new_callable=lambda: property(lambda self: mock_screen),
                ):
                    app = PassFXApp()
                    app._unlocked = True
                    app.push_screen = MagicMock()  # type: ignore[method-assign]

                    app.action_toggle_search()

                    app.push_screen.assert_called_once()


# ---------------------------------------------------------------------------
# _build_search_index() Tests
# ---------------------------------------------------------------------------


class TestBuildSearchIndex:
    """Tests for PassFXApp._build_search_index() method.

    Validates index building behavior and state management.
    """

    @pytest.mark.unit
    def test_sets_search_index_none_when_unlocked_false(self) -> None:
        """Verify _search_index is set to None when _unlocked is False."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            app = PassFXApp()
            app._unlocked = False
            app._search_index = MagicMock()  # Pre-set to non-None

            app._build_search_index()

            assert app._search_index is None

    @pytest.mark.unit
    def test_sets_search_index_none_when_vault_is_locked(self) -> None:
        """Verify _search_index is set to None when vault.is_locked is True."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault.is_locked = True  # Vault reports locked
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            app = PassFXApp()
            app._unlocked = True  # App says unlocked
            app._search_index = MagicMock()

            app._build_search_index()

            # Even with _unlocked=True, vault.is_locked=True should null index
            assert app._search_index is None

    @pytest.mark.unit
    def test_creates_search_index_when_unlocked_and_vault_unlocked(self) -> None:
        """Verify SearchIndex is created when both conditions pass."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault.is_locked = False
            mock_vault.get_emails.return_value = []
            mock_vault.get_phones.return_value = []
            mock_vault.get_cards.return_value = []
            mock_vault.get_envs.return_value = []
            mock_vault.get_recovery_entries.return_value = []
            mock_vault.get_notes.return_value = []
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp
            from passfx.search.engine import SearchIndex

            app = PassFXApp()
            app._unlocked = True
            app._search_index = None

            app._build_search_index()

            assert app._search_index is not None
            assert isinstance(app._search_index, SearchIndex)

    @pytest.mark.unit
    def test_calls_build_index_with_correct_credential_lists(self) -> None:
        """Verify index.build_index is called with correct vault data."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault.is_locked = False

            # Set up mock return values
            mock_emails = [MagicMock()]
            mock_phones = [MagicMock()]
            mock_cards = [MagicMock()]
            mock_envs = [MagicMock()]
            mock_recovery = [MagicMock()]
            mock_notes = [MagicMock()]

            mock_vault.get_emails.return_value = mock_emails
            mock_vault.get_phones.return_value = mock_phones
            mock_vault.get_cards.return_value = mock_cards
            mock_vault.get_envs.return_value = mock_envs
            mock_vault.get_recovery_entries.return_value = mock_recovery
            mock_vault.get_notes.return_value = mock_notes
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            with patch("passfx.app.SearchIndex") as mock_index_class:
                mock_index = MagicMock()
                mock_index_class.return_value = mock_index

                app = PassFXApp()
                app._unlocked = True

                app._build_search_index()

                # Verify build_index was called with all credential types
                mock_index.build_index.assert_called_once_with(
                    emails=mock_emails,
                    phones=mock_phones,
                    cards=mock_cards,
                    envs=mock_envs,
                    recovery=mock_recovery,
                    notes=mock_notes,
                )

    @pytest.mark.unit
    def test_stores_resulting_index_in_app_search_index(self) -> None:
        """Verify the resulting index is stored in app._search_index."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault.is_locked = False
            mock_vault.get_emails.return_value = []
            mock_vault.get_phones.return_value = []
            mock_vault.get_cards.return_value = []
            mock_vault.get_envs.return_value = []
            mock_vault.get_recovery_entries.return_value = []
            mock_vault.get_notes.return_value = []
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            with patch("passfx.app.SearchIndex") as mock_index_class:
                mock_index = MagicMock()
                mock_index_class.return_value = mock_index

                app = PassFXApp()
                app._unlocked = True

                app._build_search_index()

                assert app._search_index is mock_index

    @pytest.mark.unit
    def test_vault_getters_called_once_each(self) -> None:
        """Verify each vault getter is called exactly once."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault.is_locked = False
            mock_vault.get_emails.return_value = []
            mock_vault.get_phones.return_value = []
            mock_vault.get_cards.return_value = []
            mock_vault.get_envs.return_value = []
            mock_vault.get_recovery_entries.return_value = []
            mock_vault.get_notes.return_value = []
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            app = PassFXApp()
            app._unlocked = True

            app._build_search_index()

            mock_vault.get_emails.assert_called_once()
            mock_vault.get_phones.assert_called_once()
            mock_vault.get_cards.assert_called_once()
            mock_vault.get_envs.assert_called_once()
            mock_vault.get_recovery_entries.assert_called_once()
            mock_vault.get_notes.assert_called_once()

    @pytest.mark.unit
    def test_rebuilds_index_on_subsequent_calls(self) -> None:
        """Verify index is rebuilt on each call (no caching)."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault.is_locked = False
            mock_vault.get_emails.return_value = []
            mock_vault.get_phones.return_value = []
            mock_vault.get_cards.return_value = []
            mock_vault.get_envs.return_value = []
            mock_vault.get_recovery_entries.return_value = []
            mock_vault.get_notes.return_value = []
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp
            from passfx.search.engine import SearchIndex

            app = PassFXApp()
            app._unlocked = True

            # First build
            app._build_search_index()
            first_index = app._search_index

            # Second build
            app._build_search_index()
            second_index = app._search_index

            # Should be different instances
            assert first_index is not second_index
            assert isinstance(first_index, SearchIndex)
            assert isinstance(second_index, SearchIndex)


# ---------------------------------------------------------------------------
# _handle_search_result() Tests
# ---------------------------------------------------------------------------


class TestHandleSearchResult:
    """Tests for PassFXApp._handle_search_result() method.

    Validates search result handling and navigation routing.
    """

    @pytest.mark.unit
    def test_does_nothing_when_result_is_none(self) -> None:
        """Verify no navigation occurs when result is None."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            app = PassFXApp()
            app._navigate_to_result = MagicMock()  # type: ignore[method-assign]

            app._handle_search_result(None)

            app._navigate_to_result.assert_not_called()

    @pytest.mark.unit
    def test_calls_navigate_to_result_when_result_provided(self) -> None:
        """Verify _navigate_to_result is called when result is not None."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp
            from passfx.search.engine import SearchResult

            app = PassFXApp()
            app._navigate_to_result = MagicMock()  # type: ignore[method-assign]

            # Create a mock SearchResult
            mock_result = MagicMock(spec=SearchResult)
            mock_result.screen_name = "passwords"
            mock_result.credential_id = "test-id-123"

            app._handle_search_result(mock_result)

            app._navigate_to_result.assert_called_once_with(mock_result)

    @pytest.mark.unit
    def test_passes_exact_result_to_navigate(self) -> None:
        """Verify the exact result object is passed to _navigate_to_result."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp
            from passfx.search.engine import SearchResult

            app = PassFXApp()
            app._navigate_to_result = MagicMock()  # type: ignore[method-assign]

            mock_result = MagicMock(spec=SearchResult)

            app._handle_search_result(mock_result)

            call_args = app._navigate_to_result.call_args[0]
            assert call_args[0] is mock_result


# ---------------------------------------------------------------------------
# _navigate_to_result() Tests
# ---------------------------------------------------------------------------


class TestNavigateToResult:
    """Tests for PassFXApp._navigate_to_result() method.

    Validates screen routing for each credential type.
    """

    @pytest.mark.unit
    def test_navigates_to_passwords_screen(self) -> None:
        """Verify passwords screen is pushed with correct pending_select_id."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp
            from passfx.screens.passwords import PasswordsScreen
            from passfx.search.engine import SearchResult

            app = PassFXApp()
            app.push_screen = MagicMock()  # type: ignore[method-assign]

            mock_result = MagicMock(spec=SearchResult)
            mock_result.screen_name = "passwords"
            mock_result.credential_id = "pwd-123"

            app._navigate_to_result(mock_result)

            app.push_screen.assert_called_once()
            pushed_screen = app.push_screen.call_args[0][0]
            assert isinstance(pushed_screen, PasswordsScreen)
            assert pushed_screen._pending_select_id == "pwd-123"

    @pytest.mark.unit
    def test_navigates_to_phones_screen(self) -> None:
        """Verify phones screen is pushed with correct pending_select_id."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp
            from passfx.screens.phones import PhonesScreen
            from passfx.search.engine import SearchResult

            app = PassFXApp()
            app.push_screen = MagicMock()  # type: ignore[method-assign]

            mock_result = MagicMock(spec=SearchResult)
            mock_result.screen_name = "phones"
            mock_result.credential_id = "phone-456"

            app._navigate_to_result(mock_result)

            app.push_screen.assert_called_once()
            pushed_screen = app.push_screen.call_args[0][0]
            assert isinstance(pushed_screen, PhonesScreen)
            assert pushed_screen._pending_select_id == "phone-456"

    @pytest.mark.unit
    def test_navigates_to_cards_screen(self) -> None:
        """Verify cards screen is pushed with correct pending_select_id."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp
            from passfx.screens.cards import CardsScreen
            from passfx.search.engine import SearchResult

            app = PassFXApp()
            app.push_screen = MagicMock()  # type: ignore[method-assign]

            mock_result = MagicMock(spec=SearchResult)
            mock_result.screen_name = "cards"
            mock_result.credential_id = "card-789"

            app._navigate_to_result(mock_result)

            app.push_screen.assert_called_once()
            pushed_screen = app.push_screen.call_args[0][0]
            assert isinstance(pushed_screen, CardsScreen)
            assert pushed_screen._pending_select_id == "card-789"

    @pytest.mark.unit
    def test_navigates_to_envs_screen(self) -> None:
        """Verify envs screen is pushed with correct pending_select_id."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp
            from passfx.screens.envs import EnvsScreen
            from passfx.search.engine import SearchResult

            app = PassFXApp()
            app.push_screen = MagicMock()  # type: ignore[method-assign]

            mock_result = MagicMock(spec=SearchResult)
            mock_result.screen_name = "envs"
            mock_result.credential_id = "env-abc"

            app._navigate_to_result(mock_result)

            app.push_screen.assert_called_once()
            pushed_screen = app.push_screen.call_args[0][0]
            assert isinstance(pushed_screen, EnvsScreen)
            assert pushed_screen._pending_select_id == "env-abc"

    @pytest.mark.unit
    def test_navigates_to_recovery_screen(self) -> None:
        """Verify recovery screen is pushed with correct pending_select_id."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp
            from passfx.screens.recovery import RecoveryScreen
            from passfx.search.engine import SearchResult

            app = PassFXApp()
            app.push_screen = MagicMock()  # type: ignore[method-assign]

            mock_result = MagicMock(spec=SearchResult)
            mock_result.screen_name = "recovery"
            mock_result.credential_id = "recovery-def"

            app._navigate_to_result(mock_result)

            app.push_screen.assert_called_once()
            pushed_screen = app.push_screen.call_args[0][0]
            assert isinstance(pushed_screen, RecoveryScreen)
            assert pushed_screen._pending_select_id == "recovery-def"

    @pytest.mark.unit
    def test_navigates_to_notes_screen(self) -> None:
        """Verify notes screen is pushed with correct pending_select_id."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp
            from passfx.screens.notes import NotesScreen
            from passfx.search.engine import SearchResult

            app = PassFXApp()
            app.push_screen = MagicMock()  # type: ignore[method-assign]

            mock_result = MagicMock(spec=SearchResult)
            mock_result.screen_name = "notes"
            mock_result.credential_id = "note-xyz"

            app._navigate_to_result(mock_result)

            app.push_screen.assert_called_once()
            pushed_screen = app.push_screen.call_args[0][0]
            assert isinstance(pushed_screen, NotesScreen)
            assert pushed_screen._pending_select_id == "note-xyz"

    @pytest.mark.unit
    def test_push_screen_called_with_screen_instance(self) -> None:
        """Verify push_screen is called with screen instance, not name."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp
            from passfx.search.engine import SearchResult

            app = PassFXApp()
            app.push_screen = MagicMock()  # type: ignore[method-assign]

            mock_result = MagicMock(spec=SearchResult)
            mock_result.screen_name = "passwords"
            mock_result.credential_id = "test-id"

            app._navigate_to_result(mock_result)

            # Verify argument is an object, not a string
            pushed = app.push_screen.call_args[0][0]
            assert not isinstance(pushed, str)

    @pytest.mark.unit
    def test_pending_select_id_set_before_push(self) -> None:
        """Verify _pending_select_id is set before push_screen is called.

        This is critical: the screen needs the ID before mounting.
        """
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp
            from passfx.search.engine import SearchResult

            pending_id_at_push_time = None

            def capture_push(screen: object) -> None:
                nonlocal pending_id_at_push_time
                pending_id_at_push_time = getattr(screen, "_pending_select_id", None)

            app = PassFXApp()
            app.push_screen = capture_push  # type: ignore[method-assign, assignment]

            mock_result = MagicMock(spec=SearchResult)
            mock_result.screen_name = "passwords"
            mock_result.credential_id = "captured-id"

            app._navigate_to_result(mock_result)

            assert pending_id_at_push_time == "captured-id"

    @pytest.mark.unit
    def test_unknown_screen_name_no_navigation(self) -> None:
        """Verify unknown screen_name does not cause navigation or error."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp
            from passfx.search.engine import SearchResult

            app = PassFXApp()
            app.push_screen = MagicMock()  # type: ignore[method-assign]

            mock_result = MagicMock(spec=SearchResult)
            mock_result.screen_name = "unknown_screen"
            mock_result.credential_id = "some-id"

            # Should not raise and should not push
            app._navigate_to_result(mock_result)

            app.push_screen.assert_not_called()

    @pytest.mark.unit
    def test_each_screen_type_creates_new_instance(self) -> None:
        """Verify each navigation creates a fresh screen instance."""
        screen_types = [
            ("passwords", "passfx.screens.passwords.PasswordsScreen"),
            ("phones", "passfx.screens.phones.PhonesScreen"),
            ("cards", "passfx.screens.cards.CardsScreen"),
            ("envs", "passfx.screens.envs.EnvsScreen"),
            ("recovery", "passfx.screens.recovery.RecoveryScreen"),
            ("notes", "passfx.screens.notes.NotesScreen"),
        ]

        for screen_name, _ in screen_types:
            with patch("passfx.app.Vault") as mock_vault_class:
                mock_vault = MagicMock()
                mock_vault_class.return_value = mock_vault

                from passfx.app import PassFXApp
                from passfx.search.engine import SearchResult

                app = PassFXApp()
                app.push_screen = MagicMock()  # type: ignore[method-assign]

                mock_result = MagicMock(spec=SearchResult)
                mock_result.screen_name = screen_name
                mock_result.credential_id = f"{screen_name}-id-1"

                # First navigation
                app._navigate_to_result(mock_result)
                first_screen = app.push_screen.call_args[0][0]

                app.push_screen.reset_mock()

                mock_result.credential_id = f"{screen_name}-id-2"

                # Second navigation
                app._navigate_to_result(mock_result)
                second_screen = app.push_screen.call_args[0][0]

                # Should be different instances
                assert first_screen is not second_screen

    @pytest.mark.unit
    def test_credential_id_preserved_exactly(self) -> None:
        """Verify credential_id is preserved without modification."""
        special_ids = [
            "simple-id",
            "id-with-numbers-123",
            "id_with_underscores",
            "CamelCaseId",
            "a" * 100,  # Long ID
            "",  # Empty ID
        ]

        for cred_id in special_ids:
            with patch("passfx.app.Vault") as mock_vault_class:
                mock_vault = MagicMock()
                mock_vault_class.return_value = mock_vault

                from passfx.app import PassFXApp
                from passfx.search.engine import SearchResult

                app = PassFXApp()
                app.push_screen = MagicMock()  # type: ignore[method-assign]

                mock_result = MagicMock(spec=SearchResult)
                mock_result.screen_name = "passwords"
                mock_result.credential_id = cred_id

                app._navigate_to_result(mock_result)

                pushed_screen = app.push_screen.call_args[0][0]
                assert pushed_screen._pending_select_id == cred_id


# ---------------------------------------------------------------------------
# Integration Tests
# ---------------------------------------------------------------------------


class TestSearchRoutingIntegration:
    """Integration tests for the complete search routing flow.

    Tests the full flow from toggle_search through navigation.
    """

    @pytest.mark.unit
    def test_full_search_to_navigation_flow(self) -> None:
        """Verify complete flow from search activation to screen navigation."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault.is_locked = False
            mock_vault.get_emails.return_value = []
            mock_vault.get_phones.return_value = []
            mock_vault.get_cards.return_value = []
            mock_vault.get_envs.return_value = []
            mock_vault.get_recovery_entries.return_value = []
            mock_vault.get_notes.return_value = []
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp
            from passfx.screens.passwords import PasswordsScreen
            from passfx.search.engine import SearchResult

            mock_screen = MagicMock()
            mock_screen.__class__.__name__ = "MainMenuScreen"

            with patch.object(
                PassFXApp,
                "screen",
                new_callable=lambda: property(lambda self: mock_screen),
            ):
                app = PassFXApp()
                app._unlocked = True
                app.push_screen = MagicMock()  # type: ignore[method-assign]

                # Step 1: Activate search
                app.action_toggle_search()

                # Verify interceptor was pushed
                assert app.push_screen.call_count == 1

                # Reset for navigation test
                app.push_screen.reset_mock()

                # Step 2: Simulate user selecting a result
                mock_result = MagicMock(spec=SearchResult)
                mock_result.screen_name = "passwords"
                mock_result.credential_id = "selected-id"

                app._handle_search_result(mock_result)

                # Verify password screen was pushed
                app.push_screen.assert_called_once()
                pushed = app.push_screen.call_args[0][0]
                assert isinstance(pushed, PasswordsScreen)
                assert pushed._pending_select_id == "selected-id"

    @pytest.mark.unit
    def test_search_index_rebuilt_on_each_toggle(self) -> None:
        """Verify search index is rebuilt each time search is toggled."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault.is_locked = False
            mock_vault.get_emails.return_value = []
            mock_vault.get_phones.return_value = []
            mock_vault.get_cards.return_value = []
            mock_vault.get_envs.return_value = []
            mock_vault.get_recovery_entries.return_value = []
            mock_vault.get_notes.return_value = []
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            mock_screen = MagicMock()
            mock_screen.__class__.__name__ = "MainMenuScreen"

            with patch.object(
                PassFXApp,
                "screen",
                new_callable=lambda: property(lambda self: mock_screen),
            ):
                app = PassFXApp()
                app._unlocked = True
                app.push_screen = MagicMock()  # type: ignore[method-assign]

                # First toggle
                app.action_toggle_search()
                first_index = app._search_index

                # Second toggle
                app.action_toggle_search()
                second_index = app._search_index

                # Indexes should be different instances
                assert first_index is not second_index

    @pytest.mark.unit
    def test_null_result_does_not_crash(self) -> None:
        """Verify None result is handled gracefully throughout the flow."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            app = PassFXApp()
            app.push_screen = MagicMock()  # type: ignore[method-assign]

            # Should not raise
            app._handle_search_result(None)

            app.push_screen.assert_not_called()


# ---------------------------------------------------------------------------
# Edge Case Tests
# ---------------------------------------------------------------------------


class TestSearchRoutingEdgeCases:
    """Edge case tests for search routing robustness."""

    @pytest.mark.unit
    def test_empty_credential_id(self) -> None:
        """Verify empty credential_id is handled correctly."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp
            from passfx.search.engine import SearchResult

            app = PassFXApp()
            app.push_screen = MagicMock()  # type: ignore[method-assign]

            mock_result = MagicMock(spec=SearchResult)
            mock_result.screen_name = "passwords"
            mock_result.credential_id = ""

            app._navigate_to_result(mock_result)

            pushed = app.push_screen.call_args[0][0]
            assert pushed._pending_select_id == ""

    @pytest.mark.unit
    def test_screen_name_case_sensitivity(self) -> None:
        """Verify screen_name matching is case-sensitive."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp
            from passfx.search.engine import SearchResult

            app = PassFXApp()
            app.push_screen = MagicMock()  # type: ignore[method-assign]

            # Incorrect case should not navigate
            mock_result = MagicMock(spec=SearchResult)
            mock_result.screen_name = "Passwords"  # Wrong case
            mock_result.credential_id = "test-id"

            app._navigate_to_result(mock_result)

            app.push_screen.assert_not_called()

    @pytest.mark.unit
    def test_guards_checked_before_index_build(self) -> None:
        """Verify guards are checked before _build_search_index is called."""
        with patch("passfx.app.Vault") as mock_vault_class:
            mock_vault = MagicMock()
            mock_vault_class.return_value = mock_vault

            from passfx.app import PassFXApp

            mock_screen = MagicMock()
            mock_screen.__class__.__name__ = "LoginScreen"

            with patch.object(
                PassFXApp,
                "screen",
                new_callable=lambda: property(lambda self: mock_screen),
            ):
                app = PassFXApp()
                app._unlocked = True
                app._build_search_index = MagicMock()  # type: ignore[method-assign]
                app.push_screen = MagicMock()  # type: ignore[method-assign]

                app.action_toggle_search()

                # Build should not be called due to LoginScreen guard
                app._build_search_index.assert_not_called()

    @pytest.mark.unit
    def test_ctrl_k_binding_exists(self) -> None:
        """Verify Ctrl+K is bound to toggle_search action."""
        from textual.binding import Binding

        from passfx.app import PassFXApp

        binding_keys = [
            b.key if isinstance(b, Binding) else b[0] for b in PassFXApp.BINDINGS
        ]
        binding_actions = [
            b.action if isinstance(b, Binding) else b[1] for b in PassFXApp.BINDINGS
        ]

        assert "ctrl+k" in binding_keys
        assert "toggle_search" in binding_actions
