"""PassFX Custom Widgets."""

from passfx.widgets.id_card_modal import (
    IDCardButton,
    IDCardColors,
    IDCardConfig,
    IDCardField,
    IDCardModal,
)
from passfx.widgets.keycap_footer import KeycapFooter, KeycapHint
from passfx.widgets.matrix_rain import MatrixRainContainer, MatrixRainStrip
from passfx.widgets.search_overlay import SearchOverlay
from passfx.widgets.terminal import SystemTerminal

__all__ = [
    "SystemTerminal",
    "IDCardModal",
    "IDCardConfig",
    "IDCardColors",
    "IDCardField",
    "IDCardButton",
    "MatrixRainContainer",
    "MatrixRainStrip",
    "KeycapFooter",
    "KeycapHint",
    "SearchOverlay",
]
