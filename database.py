"""Pokemon database and name management."""

import json
import os
import requests
from tkinter import messagebox
from typing import Dict, List, Optional

from constants import TOTAL_POKEMON, NAMES_CACHE_FILE, USER_AGENT, API_POKEMON_LIMIT_URL


class PokemonDatabase:
    """
    Handles Pokemon names, slugs, and variant metadata.
    Manages caching and API interactions with PokeAPI.
    """
    NAME_CACHE: Dict[int, str] = {}      # id -> display name
    SLUG_CACHE: Dict[int, str] = {}      # id -> api slug (e.g., "mr-mime")
    
    # Persistent HTTP session for API calls
    _session: Optional[requests.Session] = None

    # Tiny built-in fallback for offline first-run
    KANTO_NAMES = [
        "Bulbasaur","Ivysaur","Venusaur","Charmander","Charmeleon",
        "Charizard","Squirtle","Wartortle","Blastoise","Caterpie",
        "Metapod","Butterfree","Weedle","Kakuna","Beedrill",
        "Pidgey","Pidgeotto","Pidgeot","Rattata","Raticate",
        "Spearow","Fearow","Ekans","Arbok","Pikachu",
        "Raichu","Sandshrew","Sandslash","Nidoran♀","Nidorina",
        "Nidoqueen","Nidoran♂","Nidorino","Nidoking","Clefairy",
        "Clefable","Vulpix","Ninetales","Jigglypuff","Wigglytuff",
        "Zubat","Golbat","Oddish","Gloom","Vileplume",
        "Paras","Parasect","Venonat","Venomoth","Diglett",
        "Dugtrio","Meowth","Persian","Psyduck","Golduck",
        "Mankey","Primeape","Growlithe","Arcanine","Poliwag",
        "Poliwhirl","Poliwrath","Abra","Kadabra","Alakazam",
        "Machop","Machoke","Machamp","Bellsprout","Weepinbell",
        "Victreebel","Tentacool","Tentacruel","Geodude","Graveler",
        "Golem","Ponyta","Rapidash","Slowpoke","Slowbro",
        "Magnemite","Magneton","Farfetch'd","Doduo","Dodrio",
        "Seel","Dewgong","Grimer","Muk","Shellder",
        "Cloyster","Gastly","Haunter","Gengar","Onix",
        "Drowzee","Hypno","Krabby","Kingler","Voltorb",
        "Electrode","Exeggcute","Exeggutor","Cubone","Marowak",
        "Hitmonlee","Hitmonchan","Lickitung","Koffing","Weezing",
        "Rhyhorn","Rhydon","Chansey","Tangela","Kangaskhan",
        "Horsea","Seadra","Goldeen","Seaking","Staryu",
        "Starmie","Mr. Mime","Scyther","Jynx","Electabuzz",
        "Magmar","Pinsir","Tauros","Magikarp","Gyarados",
        "Lapras","Ditto","Eevee","Vaporeon","Jolteon",
        "Flareon","Porygon","Omanyte","Omastar","Kabuto",
        "Kabutops","Aerodactyl","Snorlax","Articuno","Zapdos",
        "Moltres","Dratini","Dragonair","Dragonite","Mewtwo",
        "Mew"
    ]

    # Variants we want rows for (extend as you like)
    REGIONAL_VARIANTS = {
        19: ["Alolan"], 20: ["Alolan"], 26: ["Alolan"], 27: ["Alolan"], 28: ["Alolan"],
        37: ["Alolan"], 38: ["Alolan"], 50: ["Alolan"], 51: ["Alolan"], 
        52: ["Alolan", "Galarian"], 53: ["Alolan"], 74: ["Alolan"], 75: ["Alolan"], 
        76: ["Alolan"], 88: ["Alolan"], 89: ["Alolan"], 103: ["Alolan"], 105: ["Alolan"],
        # Vivillon (id 666) forms tracked as variants (separate dex logic without UI changes)
        666: [
            "Meadow", "Polar", "Tundra", "Continental", "Garden", "Elegant", "Icy Snow",
            "Modern", "Marine", "Archipelago", "High Plains", "Sandstorm", "River",
            "Monsoon", "Savanna", "Sun", "Ocean", "Jungle", "Fancy", "Poké Ball"
        ]
    }

    SPECIAL_NAME_FIXES = {
        "mr-mime": "Mr. Mime",
        "mime-jr": "Mime Jr.",
        "type-null": "Type: Null",
        "tapu-koko": "Tapu Koko",
        "tapu-lele": "Tapu Lele",
        "tapu-bulu": "Tapu Bulu",
        "tapu-fini": "Tapu Fini",
        "ho-oh": "Ho-Oh",
        "porygon-z": "Porygon-Z",
        "jangmo-o": "Jangmo-o",
        "hakamo-o": "Hakamo-o",
        "kommo-o": "Kommo-o",
        "chien-pao": "Chien-Pao",
        "ting-lu": "Ting-Lu",
        "wo-chien": "Wo-Chien",
        "chi-yu": "Chi-Yu",
    }

    VARIANT_SUFFIX = {
        "Alolan": "alola",
        "Galarian": "galar",
        "Hisuian": "hisui",
        "Paldean": "paldea",
        # Vivillon patterns (PokeAPI slugs)
        "Meadow": "meadow",
        "Polar": "polar",
        "Tundra": "tundra",
        "Continental": "continental",
        "Garden": "garden",
        "Elegant": "elegant",
        "Icy Snow": "icy-snow",
        "Modern": "modern",
        "Marine": "marine",
        "Archipelago": "archipelago",
        "High Plains": "high-plains",
        "Sandstorm": "sandstorm",
        "River": "river",
        "Monsoon": "monsoon",
        "Savanna": "savanna",
        "Sun": "sun",
        "Ocean": "ocean",
        "Jungle": "jungle",
        "Fancy": "fancy",
        "Poké Ball": "poke-ball",
    }
    
    @classmethod
    def get_session(cls) -> requests.Session:
        """Get or create the HTTP session."""
        if cls._session is None:
            cls._session = requests.Session()
            cls._session.headers.update({"User-Agent": USER_AGENT})
        return cls._session

    @classmethod
    def _slug_to_display(cls, slug: str) -> str:
        """Convert API slug to display name."""
        if slug in cls.SPECIAL_NAME_FIXES:
            return cls.SPECIAL_NAME_FIXES[slug]
        return slug.replace("-", " ").title()

    @classmethod
    def _load_cache_from_disk(cls) -> None:
        """Load cached names and slugs from disk."""
        if os.path.exists(NAMES_CACHE_FILE):
            try:
                with open(NAMES_CACHE_FILE, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                names = raw.get("names", {})
                slugs = raw.get("slugs", {})
                cls.NAME_CACHE = {int(k): v for k, v in names.items()}
                cls.SLUG_CACHE = {int(k): v for k, v in slugs.items()}
            except Exception:
                cls.NAME_CACHE = {}
                cls.SLUG_CACHE = {}

    @classmethod
    def _save_cache_to_disk(cls) -> None:
        """Save cached names and slugs to disk."""
        try:
            with open(NAMES_CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "names": cls.NAME_CACHE, 
                    "slugs": cls.SLUG_CACHE
                }, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    @classmethod
    def refresh_cache(cls, show_errors: bool = True) -> None:
        """Refresh Pokemon names cache from PokeAPI."""
        try:
            session = cls.get_session()
            resp = session.get(API_POKEMON_LIMIT_URL, timeout=8)
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])
            if not results:
                raise ValueError("No results from PokéAPI")
            
            cls.NAME_CACHE = {}
            cls.SLUG_CACHE = {}
            for idx, entry in enumerate(results, start=1):
                slug = entry.get("name", "")
                cls.SLUG_CACHE[idx] = slug
                cls.NAME_CACHE[idx] = cls._slug_to_display(slug)
            
            cls._save_cache_to_disk()
        except Exception as e:
            if show_errors:
                try:
                    messagebox.showwarning(
                        "Name Download Failed",
                        f"Could not download Pokémon names from PokéAPI.\n\nReason: {e}\n\n"
                        "Using any local cache / built-in Kanto names."
                    )
                except Exception:
                    pass

    @classmethod
    def initialize_names(cls) -> None:
        """Initialize Pokemon names, loading from cache or API."""
        cls._load_cache_from_disk()
        if len(cls.NAME_CACHE) < TOTAL_POKEMON or len(cls.SLUG_CACHE) < TOTAL_POKEMON:
            cls.refresh_cache(show_errors=False)

    @classmethod
    def get_name(cls, pokemon_id: int) -> str:
        """Get Pokemon name by ID."""
        if pokemon_id in cls.NAME_CACHE:
            return cls.NAME_CACHE[pokemon_id]
        if 1 <= pokemon_id <= len(cls.KANTO_NAMES):
            return cls.KANTO_NAMES[pokemon_id - 1]
        return f"Pokemon {pokemon_id}"

    @classmethod
    def get_slug(cls, pokemon_id: int) -> Optional[str]:
        """Get Pokemon API slug by ID."""
        return cls.SLUG_CACHE.get(pokemon_id)

    @classmethod
    def get_variants(cls, pokemon_id: int) -> List[str]:
        """Get list of regional variants for a Pokemon ID."""
        return cls.REGIONAL_VARIANTS.get(pokemon_id, [])
