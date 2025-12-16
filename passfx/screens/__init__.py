"""PassFX Screens - Textual UI screens."""

from passfx.screens.cards import CardsScreen
from passfx.screens.generator import GeneratorScreen
from passfx.screens.login import LoginScreen
from passfx.screens.main_menu import MainMenuScreen
from passfx.screens.passwords import PasswordsScreen
from passfx.screens.phones import PhonesScreen
from passfx.screens.settings import SettingsScreen

__all__ = [
    "LoginScreen",
    "MainMenuScreen",
    "PasswordsScreen",
    "PhonesScreen",
    "CardsScreen",
    "GeneratorScreen",
    "SettingsScreen",
]
