"""Matrix Rain Side Strips for PassFX Login Screen.

Uses buffer-based rendering with light decay for smooth, lag-free animation.
"""

from __future__ import annotations

import os
import random  # nosec B311 - Used for visual effects only, not security

from rich.segment import Segment
from rich.style import Style
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.strip import Strip
from textual.timer import Timer
from textual.widget import Widget

# Character set for Matrix rain
MATRIX_CHARS = "ｱｲｳｴｵｶｷｸｹｺｻｼｽｾｿﾀﾁﾂﾃﾄﾅﾆﾇﾈﾉﾊﾋﾌﾍﾎﾏﾐﾑﾒﾓﾔﾕﾖﾗﾘﾙﾚﾛﾜﾝ0123456789"

# Pre-computed styles - subtle ambient effect
BG_COLOR = "#050505"
STYLE_BRIGHT = Style(color="#003d00", bgcolor=BG_COLOR)
STYLE_DIM = Style(color="#002400", bgcolor=BG_COLOR)
STYLE_EMPTY = Style(bgcolor=BG_COLOR)


class MatrixRainStrip(Widget):
    """Matrix rain strip using buffer-based rendering with light decay."""

    DEFAULT_CSS = """
    MatrixRainStrip {
        width: 1fr;
        height: 100%;
        background: #050505;
    }
    """

    def __init__(  # pylint: disable=too-many-positional-arguments
        self,
        update_interval: float = 0.06,
        decay_rate: float = 0.03,
        start_delay: float = 0.0,
        name: str | None = None,
        id: str | None = None,  # noqa: A002  # pylint: disable=redefined-builtin
        classes: str | None = None,
    ) -> None:
        """Initialize the Matrix rain strip."""
        super().__init__(name=name, id=id, classes=classes)
        self._update_interval = update_interval
        self._decay_rate = decay_rate
        self._start_delay = start_delay
        self._buffer: list[list[str]] = []
        self._streams: list[dict] = []
        self._timer: Timer | None = None
        self._enabled = os.environ.get("PASSFX_REDUCE_MOTION", "0") != "1"

    def on_mount(self) -> None:
        """Start animation timer, with optional delay."""
        if self._enabled:
            # Always create buffer immediately for background rendering
            self.call_after_refresh(self._init_buffer)
            if self._start_delay > 0:
                self.set_timer(self._start_delay, self._start_rain)
            else:
                self.call_after_refresh(self._start_rain)

    def _init_buffer(self) -> None:
        """Initialize buffer for background, without starting animation."""
        self._ensure_buffer()

    def _start_rain(self) -> None:
        """Initialize and start the rain effect."""
        if not self._enabled:
            return

        w, h = self.size.width, self.size.height
        if w > 0 and h > 0:
            self._ensure_buffer()
            if self._timer is None:
                self._timer = self.set_interval(self._update_interval, self._tick)
        else:
            self.call_after_refresh(self._start_rain)

    def on_resize(self) -> None:
        """Reinitialize buffer on resize."""
        if self._enabled:
            self._ensure_buffer()

    def _ensure_buffer(self) -> None:
        """Create or resize the character buffer and streams."""
        w, h = self.size.width, self.size.height
        if w <= 0 or h <= 0:
            return

        # Check if buffer needs recreation
        if (
            not self._buffer
            or len(self._buffer) != h
            or (self._buffer and len(self._buffer[0]) != w)
        ):
            self._buffer = [[" " for _ in range(w)] for _ in range(h)]
            self._streams = [
                {
                    "y": random.randint(-h, 0),
                    "length": random.randint(6, 16),
                    "char": random.choice(MATRIX_CHARS),
                }
                for _ in range(w)
            ]

    def _tick(self) -> None:
        """Advance animation by one frame."""
        if not self._enabled or not self._buffer:
            return

        w, h = self.size.width, self.size.height
        if w <= 0 or h <= 0:
            return

        # Light decay - characters randomly fade
        for y in range(h):
            for x in range(w):
                if self._buffer[y][x] != " " and random.random() < self._decay_rate:
                    self._buffer[y][x] = " "

        # Update streams - O(width) only
        for x, stream in enumerate(self._streams):
            y = stream["y"]
            if 0 <= y < h:
                self._buffer[y][x] = stream["char"]
                # Randomly change character occasionally
                if random.random() < 0.3:
                    stream["char"] = random.choice(MATRIX_CHARS)

            stream["y"] += 1

            # Reset stream when it's fully off screen
            if stream["y"] - stream["length"] > h:
                stream["y"] = random.randint(-h, 0)
                stream["length"] = random.randint(6, 16)
                stream["char"] = random.choice(MATRIX_CHARS)

        self.refresh()

    def render_line(self, y: int) -> Strip:
        """Render a single line from the buffer."""
        if not self._buffer or y >= len(self._buffer):
            # Return black background instead of transparent
            return Strip([Segment(" " * self.size.width, STYLE_EMPTY)])

        segments: list[Segment] = []
        row = self._buffer[y]

        for x, char in enumerate(row):
            if char != " ":
                # Check if this is a stream head (brighter)
                is_head = False
                if x < len(self._streams):
                    stream_y = self._streams[x]["y"]
                    if stream_y == y:
                        is_head = True

                if is_head:
                    segments.append(Segment(char, STYLE_BRIGHT))
                else:
                    segments.append(Segment(char, STYLE_DIM))
            else:
                segments.append(Segment(" ", STYLE_EMPTY))

        return Strip(segments)


class MatrixRainContainer(Horizontal):
    """Container with Matrix rain strips on the sides."""

    DEFAULT_CSS = """
    MatrixRainContainer {
        width: 100%;
        height: 100%;
        background: #050505;
    }

    MatrixRainContainer > .matrix-strip-left,
    MatrixRainContainer > .matrix-strip-right {
        width: 1fr;
        height: 100%;
    }

    MatrixRainContainer > .matrix-center {
        width: auto;
        height: 100%;
    }
    """

    def compose(self) -> ComposeResult:
        """Create the layout with rain strips on sides."""
        yield MatrixRainStrip(
            update_interval=0.06,
            decay_rate=0.08,
            classes="matrix-strip-left",
        )
        yield Vertical(classes="matrix-center")
        yield MatrixRainStrip(
            update_interval=0.06,
            decay_rate=0.08,
            classes="matrix-strip-right",
        )
