"""PassFX Screens - Textual UI screens."""

from passfx.screens.cards import CardsScreen
from passfx.screens.envs import EnvsScreen
from passfx.screens.generator import GeneratorScreen
from passfx.screens.help import HelpScreen
from passfx.screens.login import LoginScreen
from passfx.screens.main_menu import MainMenuScreen
from passfx.screens.notes import NotesScreen
from passfx.screens.passwords import PasswordsScreen
from passfx.screens.phones import PhonesScreen
from passfx.screens.recovery import RecoveryScreen
from passfx.screens.settings import SettingsScreen

__all__ = [
    "LoginScreen",
    "MainMenuScreen",
    "PasswordsScreen",
    "PhonesScreen",
    "CardsScreen",
    "NotesScreen",
    "EnvsScreen",
    "RecoveryScreen",
    "GeneratorScreen",
    "SettingsScreen",
    "HelpScreen",
]
