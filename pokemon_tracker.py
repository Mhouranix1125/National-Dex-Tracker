import customtkinter as ctk
from tkinter import messagebox, filedialog
import json
import csv
from datetime import datetime
import os
from urllib.request import urlopen
from urllib.error import URLError
from PIL import Image
import io
import threading
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass, asdict
from enum import Enum
from collections import deque
import time

# NEW
import requests

# Persistent HTTP session for API calls
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "NationalDexTracker/1.0"})

# ---------- Appearance ----------
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ---------- Constants ----------
TOTAL_POKEMON = 1025
SPRITE_SIZE = (64, 64)
SPRITE_BASE_URL = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon"
DATA_FILE = "pokemon_tracker_data.json"
NAMES_CACHE_FILE = "pokemon_names_cache.json"
ITEMS_PER_PAGE = 50
MAX_CONCURRENT_LOADS = 6
SPRITE_LOAD_DELAY = 0.0

class Mode(Enum):
    NORMAL = "Normal"
    SHINY = "Shiny"

class Region(Enum):
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

# NEW: view filter for captured/missing
class ViewFilter(Enum):
    ALL = "All"
    CAPTURED = "Captured"
    MISSING = "Missing"

@dataclass
class Pokemon:
    id: int                # base dex number (1..1025)
    display_id: str        # "52" for base, "52-1" for first variant
    name: str
    captured_normal: bool = False
    captured_shiny: bool = False
    is_variant: bool = False
    region: Optional[str] = None  # "Alolan", "Galarian", etc.
    
    def is_captured(self, mode: Mode) -> bool:
        return self.captured_shiny if mode == Mode.SHINY else self.captured_normal
    
    def set_captured(self, mode: Mode, value: bool):
        if mode == Mode.SHINY:
            self.captured_shiny = value
        else:
            self.captured_normal = value
    
    def get_display_name(self) -> str:
        if self.is_variant and self.region:
            return f"{self.name} ({self.region})"
        return self.name

class PokemonDatabase:
    """
    Names + slugs + variant metadata.
    """
    NAME_CACHE: Dict[int, str] = {}      # id -> display name
    SLUG_CACHE: Dict[int, str] = {}      # id -> api slug (e.g., "mr-mime")

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
    def _slug_to_display(cls, slug: str) -> str:
        if slug in cls.SPECIAL_NAME_FIXES:
            return cls.SPECIAL_NAME_FIXES[slug]
        return slug.replace("-", " ").title()

    @classmethod
    def _load_cache_from_disk(cls):
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
    def _save_cache_to_disk(cls):
        try:
            with open(NAMES_CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump({"names": cls.NAME_CACHE, "slugs": cls.SLUG_CACHE}, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    @classmethod
    def refresh_cache(cls, show_errors: bool = True):
        try:
            url = f"https://pokeapi.co/api/v2/pokemon?limit={TOTAL_POKEMON}"
            resp = SESSION.get(url, timeout=8)
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
    def initialize_names(cls):
        cls._load_cache_from_disk()
        if len(cls.NAME_CACHE) < TOTAL_POKEMON or len(cls.SLUG_CACHE) < TOTAL_POKEMON:
            cls.refresh_cache(show_errors=False)

    @classmethod
    def get_name(cls, pokemon_id: int) -> str:
        if pokemon_id in cls.NAME_CACHE:
            return cls.NAME_CACHE[pokemon_id]
        if 1 <= pokemon_id <= len(cls.KANTO_NAMES):
            return cls.KANTO_NAMES[pokemon_id - 1]
        return f"Pokemon {pokemon_id}"

    @classmethod
    def get_slug(cls, pokemon_id: int) -> Optional[str]:
        return cls.SLUG_CACHE.get(pokemon_id)

    @classmethod
    def get_variants(cls, pokemon_id: int) -> List[str]:
        return cls.REGIONAL_VARIANTS.get(pokemon_id, [])

class LazyLoadSpriteManager:
    """Loads sprites with queueing and supports regional form sprites via PokéAPI."""
    
    def __init__(self, root: ctk.CTk):
        self.root = root
        self.cache: Dict[str, ctk.CTkImage] = {}
        self.loading: Set[str] = set()
        self.load_queue: deque = deque()
        self.active_loads = 0
        self._placeholder = None
        self.visible_sprites: Set[str] = set()
        self.sprite_labels: Dict[str, ctk.CTkLabel] = {}
        self._processing = False
        self.sprite_url_cache: Dict[str, str] = {}
    
    @property
    def placeholder(self) -> ctk.CTkImage:
        if not self._placeholder:
            img = Image.new('RGB', SPRITE_SIZE, color=(128, 128, 128))
            self._placeholder = ctk.CTkImage(light_image=img, size=SPRITE_SIZE)
        return self._placeholder
    
    def get_sprite_key(self, pokemon: Pokemon, mode: Mode) -> str:
        return f"{pokemon.display_id}_{mode.value.lower()}"
    
    def _resolve_sprite_url(self, pokemon: Pokemon, mode: Mode) -> str:
        key = self.get_sprite_key(pokemon, mode)
        if key in self.sprite_url_cache:
            return self.sprite_url_cache[key]

        if not pokemon.is_variant:
            url = f"{SPRITE_BASE_URL}/shiny/{pokemon.id}.png" if mode == Mode.SHINY else f"{SPRITE_BASE_URL}/{pokemon.id}.png"
            self.sprite_url_cache[key] = url
            return url

        base_slug = PokemonDatabase.get_slug(pokemon.id)
        if not base_slug:
            url = f"{SPRITE_BASE_URL}/shiny/{pokemon.id}.png" if mode == Mode.SHINY else f"{SPRITE_BASE_URL}/{pokemon.id}.png"
            self.sprite_url_cache[key] = url
            return url

        suffix = PokemonDatabase.VARIANT_SUFFIX.get(pokemon.region or "", "").strip()
        if not suffix:
            url = f"{SPRITE_BASE_URL}/shiny/{pokemon.id}.png" if mode == Mode.SHINY else f"{SPRITE_BASE_URL}/{pokemon.id}.png"
            self.sprite_url_cache[key] = url
            return url

        form_slug = f"{base_slug}-{suffix}"
        try:
            api_url = f"https://pokeapi.co/api/v2/pokemon/{form_slug}"
            resp = SESSION.get(api_url, timeout=5)
            resp.raise_for_status()
            j = resp.json()
            sprites = j.get("sprites", {}) or {}
            url = sprites.get("front_shiny" if mode == Mode.SHINY else "front_default")
            if not url:
                url = f"{SPRITE_BASE_URL}/shiny/{pokemon.id}.png" if mode == Mode.SHINY else f"{SPRITE_BASE_URL}/{pokemon.id}.png"
        except Exception:
            url = f"{SPRITE_BASE_URL}/shiny/{pokemon.id}.png" if mode == Mode.SHINY else f"{SPRITE_BASE_URL}/{pokemon.id}.png"

        self.sprite_url_cache[key] = url
        return url
    
    def queue_sprite_load(self, pokemon: Pokemon, sprite_label: ctk.CTkLabel, mode: Mode, priority: bool = False):
        sprite_key = self.get_sprite_key(pokemon, mode)
        self.sprite_labels[sprite_key] = sprite_label
        
        if sprite_key in self.cache:
            sprite_label.configure(image=self.cache[sprite_key])
            return
        
        if sprite_key in self.loading or any(item[0] == sprite_key for item in self.load_queue):
            return
        
        load_item = (sprite_key, pokemon, mode)
        if priority:
            self.load_queue.appendleft(load_item)
        else:
            self.load_queue.append(load_item)
        
        if not self._processing:
            self._process_queue()
    
    def mark_visible(self, sprite_keys: List[str]):
        self.visible_sprites = set(sprite_keys)
        self._prioritize_visible()
    
    def _prioritize_visible(self):
        if not self.load_queue:
            return
        visible_items, other_items = [], []
        for item in self.load_queue:
            if item[0] in self.visible_sprites:
                visible_items.append(item)
            else:
                other_items.append(item)
        self.load_queue = deque(visible_items + other_items)
    
    def _process_queue(self):
        if not self.load_queue or self.active_loads >= MAX_CONCURRENT_LOADS:
            return
        self._processing = True
        while self.load_queue and self.active_loads < MAX_CONCURRENT_LOADS:
            sprite_key, pokemon, mode = self.load_queue.popleft()
            if sprite_key not in self.loading:
                self.loading.add(sprite_key)
                self.active_loads += 1
                thread = threading.Thread(
                    target=self._load_sprite_thread,
                    args=(sprite_key, pokemon, mode),
                    daemon=True
                )
                thread.start()
        if self.load_queue:
            self.root.after(100, self._process_queue)
        else:
            self._processing = False
    
    def _load_sprite_thread(self, sprite_key: str, pokemon: Pokemon, mode: Mode):
        try:
            time.sleep(SPRITE_LOAD_DELAY)
            url = self._resolve_sprite_url(pokemon, mode)
            with urlopen(url, timeout=5) as response:
                image_data = response.read()
            image = Image.open(io.BytesIO(image_data))
            image = image.resize(SPRITE_SIZE, Image.Resampling.LANCZOS)
            ctk_image = ctk.CTkImage(light_image=image, size=SPRITE_SIZE)
            self.cache[sprite_key] = ctk_image
            if sprite_key in self.sprite_labels:
                self.root.after(0, lambda: self._update_label(sprite_key, ctk_image))
        except Exception as e:
            print(f"Failed to load sprite {sprite_key}: {e}")
        finally:
            self.loading.discard(sprite_key)
            self.active_loads -= 1
            self.root.after(50, self._process_queue)
    
    def _update_label(self, sprite_key: str, image: ctk.CTkImage):
        try:
            if sprite_key in self.sprite_labels:
                label = self.sprite_labels[sprite_key]
                if label.winfo_exists():
                    label.configure(image=image)
        except:
            pass
    
    def clear_cache(self):
        new_cache = {}
        for key in self.visible_sprites:
            if key in self.cache:
                new_cache[key] = self.cache[key]
        self.cache = new_cache
    
    def cancel_pending_loads(self):
        self.load_queue.clear()
        self.sprite_labels.clear()

class DataManager:
    """Saving/loading and CSV export."""
    @staticmethod
    def save(pokemon_list: List[Pokemon]):
        try:
            data = [asdict(p) for p in pokemon_list]
            with open(DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving data: {e}")
    
    @staticmethod
    def load(pokemon_list: List[Pokemon]):
        try:
            if not os.path.exists(DATA_FILE):
                return
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                saved_data = json.load(f)
            saved_dict = {p['display_id']: p for p in saved_data}
            for pokemon in pokemon_list:
                if pokemon.display_id in saved_dict:
                    saved = saved_dict[pokemon.display_id]
                    pokemon.captured_normal = saved.get('captured_normal', saved.get('captured', False))
                    pokemon.captured_shiny = saved.get('captured_shiny', False)
        except Exception as e:
            print(f"Error loading saved data: {e}")
    
    @staticmethod
    def export_csv(parent, pokemon_list: List[Pokemon], region: Region, mode: Mode) -> bool:
        timestamp = datetime.now().strftime('%Y-%m-%d')
        default_name = f"pokemon_{mode.value.lower()}_{region.display_name.lower()}_{timestamp}.csv"
        filepath = filedialog.asksaveasfilename(
            parent=parent,
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile=default_name,
            title="Save Pokédex CSV"
        )
        if not filepath:
            messagebox.showinfo("Export Canceled", "CSV export was canceled.")
            return False
        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['Dex Number', 'Pokemon Name', 'Region', 'Mode', 'Captured'])
                for pokemon in pokemon_list:
                    captured = 'Yes' if pokemon.is_captured(mode) else 'No'
                    region_text = pokemon.region if pokemon.is_variant else ""
                    writer.writerow([pokemon.display_id, pokemon.name, region_text, mode.value, captured])
            messagebox.showinfo("Success", f"CSV saved as:\n{filepath}")
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save CSV:\n{e}")
            return False

class PokemonTracker:
    """Main application class with pagination + filtering."""
    def __init__(self, root: ctk.CTk):
        self.root = root
        self.root.title("Pokémon Home Pokédex Tracker")
        self.root.geometry("1400x920")
        
        PokemonDatabase.initialize_names()

        self.sprite_manager = LazyLoadSpriteManager(root)
        self.pokemon_list: List[Pokemon] = []
        self.current_region = Region.KANTO
        self.current_mode = Mode.NORMAL
        self.current_page = 0
        self.total_pages = 0
        self.card_widgets: List[Tuple] = []
        # NEW: view filter
        self.view_filter = ViewFilter.ALL
        
        self._generate_pokemon_data()
        DataManager.load(self.pokemon_list)
        self._setup_ui()
        self._update_display()
    
    def _generate_pokemon_data(self):
        self.pokemon_list = []
        for i in range(1, TOTAL_POKEMON + 1):
            name = PokemonDatabase.get_name(i)
            self.pokemon_list.append(Pokemon(id=i, display_id=str(i), name=name))
            for idx, variant in enumerate(PokemonDatabase.get_variants(i)):
                self.pokemon_list.append(Pokemon(
                    id=i,
                    display_id=f"{i}-{idx + 1}",
                    name=name,
                    is_variant=True,
                    region=variant
                ))
    
    def _setup_ui(self):
        self._create_header()
        self._create_mode_selector()
        self._create_controls()
        self._create_region_tabs()
        # NEW: filter selector row
        self._create_filter_selector()
        self._create_pagination_controls()
        self._create_main_area()
    
    def _create_header(self):
        header_frame = ctk.CTkFrame(self.root, height=80, corner_radius=10)
        header_frame.pack(fill="x", padx=20, pady=10)
        header_frame.pack_propagate(False)
        
        self.title_label = ctk.CTkLabel(
            header_frame, 
            text="Pokémon Home Pokédex Tracker",
            font=ctk.CTkFont(size=28, weight="bold")
        )
        self.title_label.pack(pady=20)
    
    def _create_mode_selector(self):
        mode_frame = ctk.CTkFrame(self.root, height=60, corner_radius=10)
        mode_frame.pack(fill="x", padx=20, pady=5)
        mode_frame.pack_propagate(False)
        
        ctk.CTkLabel(mode_frame, text="Mode:", font=ctk.CTkFont(size=16, weight="bold")).pack(side="left", padx=20, pady=15)
        self.mode_var = ctk.StringVar(value=Mode.NORMAL.value)
        self.mode_segmented = ctk.CTkSegmentedButton(
            mode_frame,
            values=[m.value for m in Mode],
            variable=self.mode_var,
            command=self._on_mode_change
        )
        self.mode_segmented.pack(side="left", padx=10, pady=15)
    
    def _create_controls(self):
        controls_frame = ctk.CTkFrame(self.root, height=60, corner_radius=10)
        controls_frame.pack(fill="x", padx=20, pady=5)
        controls_frame.pack_propagate(False)
        
        button_config = {
            "Check All (Page)": ("green", "darkgreen", self._check_all_page),
            "Uncheck All (Page)": ("red", "darkred", self._uncheck_all_page),
            # NEW: region-wide actions
            "Check All (Region)": ("#1f9d55", "#167a42", self._check_all_region),
            "Uncheck All (Region)": ("#b91c1c", "#991b1b", self._uncheck_all_region),
            "Download CSV": ("gray", "darkgray", self._download_csv)
        }
        
        for text, (fg, hover, command) in button_config.items():
            ctk.CTkButton(controls_frame, text=text, command=command, fg_color=fg, hover_color=hover, width=150, height=35)\
                .pack(side="left", padx=8, pady=12)
        
        self.progress_label = ctk.CTkLabel(controls_frame, text="Progress: 0/0", font=ctk.CTkFont(size=14, weight="bold"))
        self.progress_label.pack(side="right", padx=20, pady=15)

    # NEW: Filter selector
    def _create_filter_selector(self):
        filter_frame = ctk.CTkFrame(self.root, height=50, corner_radius=10)
        filter_frame.pack(fill="x", padx=20, pady=5)
        filter_frame.pack_propagate(False)

        ctk.CTkLabel(filter_frame, text="Filter:", font=ctk.CTkFont(size=16, weight="bold"))\
            .pack(side="left", padx=20, pady=12)

        self.filter_var = ctk.StringVar(value=ViewFilter.ALL.value)
        self.filter_segmented = ctk.CTkSegmentedButton(
            filter_frame,
            values=[f.value for f in ViewFilter],
            variable=self.filter_var,
            command=self._on_filter_change
        )
        self.filter_segmented.pack(side="left", padx=10, pady=10)

        # Small hint about mode coupling
        ctk.CTkLabel(filter_frame, text="(Filter uses current Mode)", font=ctk.CTkFont(size=12))\
            .pack(side="left", padx=12)

    def _create_region_tabs(self):
        tabs_frame = ctk.CTkFrame(self.root, height=50, corner_radius=10)
        tabs_frame.pack(fill="x", padx=20, pady=5)
        tabs_frame.pack_propagate(False)
        
        regions = [r.display_name for r in Region]
        self.region_var = ctk.StringVar(value=Region.KANTO.display_name)
        self.region_segmented = ctk.CTkSegmentedButton(
            tabs_frame,
            values=regions,
            variable=self.region_var,
            command=self._on_region_change
        )
        self.region_segmented.pack(padx=20, pady=10)
    
    def _create_pagination_controls(self):
        self.pagination_frame = ctk.CTkFrame(self.root, height=50, corner_radius=10)
        self.pagination_frame.pack(fill="x", padx=20, pady=5)
        self.pagination_frame.pack_propagate(False)
        
        self.prev_button = ctk.CTkButton(self.pagination_frame, text="◄ Previous", command=self._prev_page, width=120, height=30)
        self.prev_button.pack(side="left", padx=20, pady=10)
        
        self.page_info_label = ctk.CTkLabel(self.pagination_frame, text="Page 1 of 1", font=ctk.CTkFont(size=14, weight="bold"))
        self.page_info_label.pack(side="left", expand=True)
        
        self.next_button = ctk.CTkButton(self.pagination_frame, text="Next ►", command=self._next_page, width=120, height=30)
        self.next_button.pack(side="right", padx=20, pady=10)
        
        self.jump_frame = ctk.CTkFrame(self.pagination_frame)
        self.jump_frame.pack(side="right", padx=10)
        ctk.CTkLabel(self.jump_frame, text="Go to page:").pack(side="left", padx=5)
        self.page_entry = ctk.CTkEntry(self.jump_frame, width=50)
        self.page_entry.pack(side="left", padx=5)
        self.page_entry.bind("<Return>", lambda e: self._jump_to_page())
        ctk.CTkButton(self.jump_frame, text="Go", command=self._jump_to_page, width=50, height=25)\
            .pack(side="left", padx=5)
    
    def _create_main_area(self):
        self.main_frame = ctk.CTkFrame(self.root, corner_radius=10)
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=10)
        self.main_scrollable = ctk.CTkScrollableFrame(self.main_frame, corner_radius=10)
        self.main_scrollable.pack(fill="both", expand=True, padx=10, pady=10)
        self.main_scrollable.grid_columnconfigure(0, weight=1)
        self.main_scrollable.bind_all("<MouseWheel>", self._on_scroll)
    
    def _on_scroll(self, event):
        self._update_visible_sprites()

    def _update_visible_sprites(self):
        """Prioritize loading sprites that are actually in view."""
        if not self.card_widgets:
            return

        visible_keys = []
        try:
            viewport_top = self.main_scrollable.winfo_rooty()
            viewport_bottom = viewport_top + self.main_scrollable.winfo_height()
        except:
            return

        for pokemon, sprite_label, _ in self.card_widgets:
            try:
                if sprite_label.winfo_exists():
                    y = sprite_label.winfo_rooty()
                    # small buffer so near-edge rows get prioritized too
                    if (viewport_top - 100) <= y <= (viewport_bottom + 100):
                        sprite_key = self.sprite_manager.get_sprite_key(pokemon, self.current_mode)
                        visible_keys.append(sprite_key)
            except:
                pass

        self.sprite_manager.mark_visible(visible_keys)

    # ---- Filtering helpers ----
    def _region_filter(self, p: Pokemon) -> bool:
        return self.current_region.start <= p.id <= self.current_region.end

    def _status_filter(self, p: Pokemon) -> bool:
        if self.view_filter == ViewFilter.ALL:
            return True
        captured = p.is_captured(self.current_mode)
        if self.view_filter == ViewFilter.CAPTURED:
            return captured
        if self.view_filter == ViewFilter.MISSING:
            return not captured
        return True

    def _get_filtered_pokemon(self) -> List[Pokemon]:
        return [p for p in self.pokemon_list if self._region_filter(p) and self._status_filter(p)]
    
    def _get_current_page_pokemon(self) -> List[Pokemon]:
        filtered = self._get_filtered_pokemon()
        start_idx = self.current_page * ITEMS_PER_PAGE
        end_idx = start_idx + ITEMS_PER_PAGE
        return filtered[start_idx:end_idx]
    
    def _update_display(self):
        self.sprite_manager.cancel_pending_loads()
        for widget in self.main_scrollable.winfo_children():
            widget.destroy()
        self.card_widgets.clear()
        
        filtered_pokemon = self._get_filtered_pokemon()
        self.total_pages = max(1, (len(filtered_pokemon) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
        self.current_page = min(self.current_page, self.total_pages - 1)
        self.current_page = max(0, self.current_page)
        
        for row, pokemon in enumerate(self._get_current_page_pokemon()):
            self.card_widgets.append(self._create_pokemon_card(pokemon, row))
        
        self._update_pagination_controls()
        self._update_progress()
        self.root.after(100, self._update_visible_sprites)
    
    def _update_pagination_controls(self):
        self.page_info_label.configure(text=f"Page {self.current_page + 1} of {self.total_pages}")
        self.prev_button.configure(state="normal" if self.current_page > 0 else "disabled")
        self.next_button.configure(state="normal" if self.current_page < self.total_pages - 1 else "disabled")
        self.page_entry.delete(0, 'end')
    
    def _update_progress(self):
        # Progress shown against the current REGION (ignoring filter), as that’s more intuitive
        regional = [p for p in self.pokemon_list if self._region_filter(p)]
        captured = sum(1 for p in regional if p.is_captured(self.current_mode))
        total = len(regional)
        filter_text = f" | Filter: {self.view_filter.value}"
        self.progress_label.configure(
            text=f"{self.current_mode.value} Progress: {captured}/{total} (Page {self.current_page + 1}/{self.total_pages}){filter_text}"
        )

    def _create_pokemon_card(self, pokemon: Pokemon, row: int) -> Tuple:
        is_captured = pokemon.is_captured(self.current_mode)
        if is_captured:
            card_color = ("green", "darkgreen")
        elif pokemon.is_variant:
            card_color = ("blue", "darkblue")
        else:
            card_color = None
        
        card_frame = ctk.CTkFrame(self.main_scrollable, height=90, corner_radius=10, fg_color=card_color)
        card_frame.grid(row=row, column=0, sticky="ew", padx=10, pady=5)
        card_frame.grid_propagate(False)
        card_frame.grid_columnconfigure(2, weight=1)
        
        ctk.CTkLabel(card_frame, text=f"#{pokemon.display_id}", font=ctk.CTkFont(size=14, weight="bold"), width=80)\
            .grid(row=0, column=0, padx=15, pady=25)
        
        sprite_label = ctk.CTkLabel(card_frame, image=self.sprite_manager.placeholder, text="", width=80)
        sprite_label.grid(row=0, column=1, padx=10, pady=13)
        self.sprite_manager.queue_sprite_load(pokemon, sprite_label, self.current_mode)
        
        ctk.CTkLabel(
            card_frame,
            text=pokemon.get_display_name(),
            font=ctk.CTkFont(size=16, weight="bold" if pokemon.is_variant else "normal"),
            anchor="w"
        ).grid(row=0, column=2, sticky="ew", padx=15, pady=25)
        
        var = ctk.BooleanVar(value=is_captured)
        ctk.CTkCheckBox(card_frame, text="Captured", variable=var,
                        command=lambda: self._toggle_capture(pokemon, var),
                        font=ctk.CTkFont(size=12))\
            .grid(row=0, column=3, padx=15, pady=25)
        
        return (pokemon, sprite_label, card_frame)

    # ---- Actions ----
    def _toggle_capture(self, pokemon: Pokemon, var: ctk.BooleanVar):
        pokemon.set_captured(self.current_mode, var.get())
        DataManager.save(self.pokemon_list)
        self._update_progress()
        self._refresh_card_colors()

    def _refresh_card_colors(self):
        for pokemon, _, card_frame in self.card_widgets:
            is_captured = pokemon.is_captured(self.current_mode)
            if is_captured:
                color = ("green", "darkgreen")
            elif pokemon.is_variant:
                color = ("blue", "darkblue")
            else:
                color = ("gray23", "gray23")
            try:
                card_frame.configure(fg_color=color)
            except:
                pass

    def _on_mode_change(self, mode_str: str):
        self.current_mode = Mode(mode_str)
        self.title_label.configure(
            text="✨ Pokémon Home Shiny Pokédex Tracker ✨" if self.current_mode == Mode.SHINY else "Pokémon Home Pokédex Tracker"
        )
        self.current_page = 0
        self._update_display()

    def _on_filter_change(self, filter_str: str):
        # Update filter and rebuild current view
        for vf in ViewFilter:
            if vf.value == filter_str:
                self.view_filter = vf
                break
        self.current_page = 0
        self._update_display()
    
    def _on_region_change(self, region_str: str):
        for region in Region:
            if region.display_name == region_str:
                self.current_region = region
                break
        self.current_page = 0
        if self.current_region == Region.NATIONAL:
            self.sprite_manager.clear_cache()
        self._update_display()
    
    def _prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self._update_display()
    
    def _next_page(self):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self._update_display()
    
    def _jump_to_page(self):
        try:
            page_num = int(self.page_entry.get()) - 1
            if 0 <= page_num < self.total_pages:
                self.current_page = page_num
                self._update_display()
            else:
                messagebox.showwarning("Invalid Page", f"Please enter a page number between 1 and {self.total_pages}")
        except ValueError:
            messagebox.showwarning("Invalid Input", "Please enter a valid page number")
    
    def _check_all_page(self):
        mode_text = self.current_mode.value.lower()
        if messagebox.askyesno("Confirm", f"Mark all {mode_text} Pokémon on THIS PAGE as captured?"):
            for pokemon in self._get_current_page_pokemon():
                pokemon.set_captured(self.current_mode, True)
            DataManager.save(self.pokemon_list)
            self._update_display()

    def _uncheck_all_page(self):
        mode_text = self.current_mode.value.lower()
        if messagebox.askyesno("Confirm", f"Mark all {mode_text} Pokémon on THIS PAGE as NOT captured?"):
            for pokemon in self._get_current_page_pokemon():
                pokemon.set_captured(self.current_mode, False)
            DataManager.save(self.pokemon_list)
            self._update_display()

    # NEW: region-wide actions (your “check all total”)
    def _check_all_region(self):
        mode_text = self.current_mode.value.lower()
        region_name = self.current_region.display_name
        if messagebox.askyesno("Confirm", f"Mark ALL {mode_text} Pokémon in {region_name} as captured?"):
            for p in self.pokemon_list:
                if self._region_filter(p):
                    p.set_captured(self.current_mode, True)
            DataManager.save(self.pokemon_list)
            self._update_display()

    def _uncheck_all_region(self):
        mode_text = self.current_mode.value.lower()
        region_name = self.current_region.display_name
        if messagebox.askyesno("Confirm", f"Mark ALL {mode_text} Pokémon in {region_name} as NOT captured?"):
            for p in self.pokemon_list:
                if self._region_filter(p):
                    p.set_captured(self.current_mode, False)
            DataManager.save(self.pokemon_list)
            self._update_display()
    
    def _download_csv(self):
        result = messagebox.askquestion(
            "Export Scope",
            "Export all Pokémon in this region?\n\nYes = All in region\nNo = Current page only",
            icon='question'
        )
        if result == 'yes':
            selected = [p for p in self.pokemon_list if self._region_filter(p)]
        else:
            selected = self._get_current_page_pokemon()
        DataManager.export_csv(self.root, selected, self.current_region, self.current_mode)

class QuickSearchDialog:
    def __init__(self, parent, pokemon_list: List[Pokemon], callback):
        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title("Quick Search")
        self.dialog.geometry("400x150")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self.pokemon_list = pokemon_list
        self.callback = callback
        
        ctk.CTkLabel(self.dialog, text="Enter Pokémon name or number:").pack(pady=10)
        self.search_entry = ctk.CTkEntry(self.dialog, width=300)
        self.search_entry.pack(pady=10)
        self.search_entry.focus()
        self.search_entry.bind("<Return>", lambda e: self.search())
        
        button_frame = ctk.CTkFrame(self.dialog)
        button_frame.pack(pady=10)
        ctk.CTkButton(button_frame, text="Search", command=self.search).pack(side="left", padx=5)
        ctk.CTkButton(button_frame, text="Cancel", command=self.dialog.destroy).pack(side="left", padx=5)
    
    def search(self):
        query = self.search_entry.get().lower().strip()
        if not query:
            return
        for i, pokemon in enumerate(self.pokemon_list):
            if (query in pokemon.display_id.lower() or query in pokemon.name.lower()):
                page = i // ITEMS_PER_PAGE
                self.callback(page)
                self.dialog.destroy()
                return
        messagebox.showinfo("Not Found", f"No Pokémon matching '{query}' was found.")

def main():
    root = ctk.CTk()

    def refresh_names():
        if not messagebox.askyesno("Refresh Names", "Re-download all Pokémon names from PokéAPI?"):
            return
        def _do_refresh():
            try:
                PokemonDatabase.refresh_cache()
                try:
                    root.after(0, lambda: messagebox.showinfo("Success", "Names refreshed! Please restart the app for a full rebuild."))
                except Exception:
                    pass
            except Exception as e:
                try:
                    root.after(0, lambda: messagebox.showwarning("Refresh Failed", f"Could not refresh names.\n\n{e}"))
                except Exception:
                    pass
        threading.Thread(target=_do_refresh, daemon=True).start()

    def open_search():
        if hasattr(app, 'pokemon_list'):
            def go_to_page(page):
                app.current_page = page
                app._update_display()
            QuickSearchDialog(root, app.pokemon_list, go_to_page)

    root.bind('<Control-f>', lambda e: open_search())
    root.bind('<Control-r>', lambda e: refresh_names())
    
    app = PokemonTracker(root)
    app.title_label.configure(text="Pokémon Home Pokédex Tracker (Ctrl+F: Search, Ctrl+R: Refresh Names)")
    root.mainloop()

if __name__ == "__main__":
    main()
