"""Application constants and configuration."""

# Application settings
TOTAL_POKEMON = 1025
SPRITE_SIZE = (64, 64)
SPRITE_BASE_URL = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon"
DATA_FILE = "pokemon_tracker_data.json"
NAMES_CACHE_FILE = "pokemon_names_cache.json"
ITEMS_PER_PAGE = 25  # Reduced from 50 for better performance
MAX_CONCURRENT_LOADS = 6
SPRITE_LOAD_DELAY = 0.0

# API configuration
API_BASE_URL = "https://pokeapi.co/api/v2"
API_POKEMON_LIMIT_URL = f"{API_BASE_URL}/pokemon?limit={TOTAL_POKEMON}"
API_POKEMON_URL = f"{API_BASE_URL}/pokemon"

# User agent for API requests
USER_AGENT = "NationalDexTracker/1.0"

# Caching configuration
SPRITE_CACHE_DIR = ".sprite_cache"
CACHE_REFRESH_DAYS = 7  # Refresh sprites weekly
CACHE_VERSION = "1.0"  # Increment to force cache rebuild

# Application assets
APP_ICON = "assets/icon.ico"  # Windows and cross-platform
APP_ICON_PNG = "assets/icon.png"  # Fallback PNG format
APP_ICON_ICNS = "assets/icon.icns"  # macOS native format

# UI Configuration
DEFAULT_WINDOW_SIZE = "1400x920"
HEADER_HEIGHT = 80
CONTROL_FRAME_HEIGHT = 60
FILTER_FRAME_HEIGHT = 50
PAGINATION_FRAME_HEIGHT = 50
CARD_HEIGHT = 90

# Colors
COLORS = {
    "captured": ("green", "darkgreen"),
    "variant": ("blue", "darkblue"),
    "region_check": ("#1f9d55", "#167a42"),
    "region_uncheck": ("#b91c1c", "#991b1b"),
    "default": ("gray", "darkgray"),
    "card_default": ("gray23", "gray23")
}
