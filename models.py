"""Data models and enums for the Pokemon tracker."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Mode(Enum):
    """Pokemon capture mode - normal or shiny."""
    NORMAL = "Normal"
    SHINY = "Shiny"


class Region(Enum):
    """Pokemon regions with their ID ranges."""
    NATIONAL = ("National", 1, 1025)
    KANTO = ("Kanto", 1, 151)
    JOHTO = ("Johto", 152, 251)
    HOENN = ("Hoenn", 252, 386)
    SINNOH = ("Sinnoh", 387, 493)
    UNOVA = ("Unova", 494, 649)
    KALOS = ("Kalos", 650, 721)
    ALOLA = ("Alola", 722, 809)
    GALAR = ("Galar", 810, 905)
    PALDEA = ("Paldea", 906, 1025)
    
    def __init__(self, display_name: str, start: int, end: int):
        self.display_name = display_name
        self.start = start
        self.end = end


class ViewFilter(Enum):
    """View filter for captured/missing Pokemon."""
    ALL = "All"
    CAPTURED = "Captured"
    MISSING = "Missing"


@dataclass
class Pokemon:
    """Pokemon data model."""
    id: int                # base dex number (1..1025)
    display_id: str        # "52" for base, "52-1" for first variant
    name: str
    captured_normal: bool = False
    captured_shiny: bool = False
    is_variant: bool = False
    region: Optional[str] = None  # "Alolan", "Galarian", etc.
    
    def is_captured(self, mode: Mode) -> bool:
        """Check if Pokemon is captured in the given mode."""
        return self.captured_shiny if mode == Mode.SHINY else self.captured_normal
    
    def set_captured(self, mode: Mode, value: bool) -> None:
        """Set Pokemon capture status for the given mode."""
        if mode == Mode.SHINY:
            self.captured_shiny = value
        else:
            self.captured_normal = value
    
    def get_display_name(self) -> str:
        """Get the display name with regional variant if applicable."""
        if self.is_variant and self.region:
            return f"{self.name} ({self.region})"
        return self.name
