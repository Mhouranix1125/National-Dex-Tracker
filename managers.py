"""Managers for sprites and data persistence."""

import csv
import json
import os
import threading
import time
from collections import deque
from dataclasses import asdict
from datetime import datetime
from tkinter import filedialog, messagebox
from typing import Dict, List, Set, Tuple
from urllib.error import URLError
from urllib.request import urlopen
import io

import customtkinter as ctk
from PIL import Image

from constants import (
    SPRITE_SIZE, SPRITE_BASE_URL, DATA_FILE, MAX_CONCURRENT_LOADS, 
    SPRITE_LOAD_DELAY, API_POKEMON_URL, SPRITE_CACHE_DIR, CACHE_REFRESH_DAYS, CACHE_VERSION
)
from database import PokemonDatabase
from models import Pokemon, Mode, Region


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
        
        # Initialize disk cache
        self._init_disk_cache()
    
    @property
    def placeholder(self) -> ctk.CTkImage:
        """Get placeholder image for loading sprites."""
        if not self._placeholder:
            img = Image.new('RGB', SPRITE_SIZE, color=(128, 128, 128))
            self._placeholder = ctk.CTkImage(light_image=img, size=SPRITE_SIZE)
        return self._placeholder
    
    def _init_disk_cache(self) -> None:
        """Initialize the disk cache directory."""
        try:
            os.makedirs(SPRITE_CACHE_DIR, exist_ok=True)
            # Create cache info file if it doesn't exist
            cache_info_path = os.path.join(SPRITE_CACHE_DIR, "cache_info.json")
            if not os.path.exists(cache_info_path):
                cache_info = {
                    "version": CACHE_VERSION,
                    "created": time.time(),
                    "last_updated": time.time()
                }
                with open(cache_info_path, 'w') as f:
                    json.dump(cache_info, f)
        except Exception as e:
            print(f"Failed to initialize sprite cache: {e}")
    
    def _get_cache_path(self, sprite_key: str) -> str:
        """Get the file path for a cached sprite."""
        # Use PNG format for cached sprites
        safe_key = sprite_key.replace("/", "_").replace("\\", "_")
        return os.path.join(SPRITE_CACHE_DIR, f"{safe_key}.png")
    
    def _is_cache_valid(self, cache_path: str) -> bool:
        """Check if cached sprite exists and is not expired."""
        try:
            if not os.path.exists(cache_path):
                return False
            
            # Check if file is older than CACHE_REFRESH_DAYS
            file_time = os.path.getmtime(cache_path)
            current_time = time.time()
            days_old = (current_time - file_time) / (24 * 60 * 60)
            
            return days_old < CACHE_REFRESH_DAYS
        except:
            return False
    
    def _save_sprite_to_cache(self, sprite_key: str, image: Image.Image) -> None:
        """Save a sprite image to disk cache."""
        try:
            cache_path = self._get_cache_path(sprite_key)
            image.save(cache_path, "PNG")
        except Exception as e:
            print(f"Failed to save sprite {sprite_key} to cache: {e}")
    
    def _load_sprite_from_cache(self, sprite_key: str) -> ctk.CTkImage:
        """Load a sprite from disk cache."""
        try:
            cache_path = self._get_cache_path(sprite_key)
            if self._is_cache_valid(cache_path):
                image = Image.open(cache_path)
                image = image.resize(SPRITE_SIZE, Image.Resampling.LANCZOS)
                return ctk.CTkImage(light_image=image, size=SPRITE_SIZE)
        except Exception as e:
            print(f"Failed to load sprite {sprite_key} from cache: {e}")
        return None
    
    def get_sprite_key(self, pokemon: Pokemon, mode: Mode) -> str:
        """Generate unique key for sprite caching."""
        return f"{pokemon.display_id}_{mode.value.lower()}"
    
    def _resolve_sprite_url(self, pokemon: Pokemon, mode: Mode) -> str:
        """Resolve the correct sprite URL for a Pokemon and mode."""
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
            api_url = f"{API_POKEMON_URL}/{form_slug}"
            session = PokemonDatabase.get_session()
            resp = session.get(api_url, timeout=5)
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
        """Queue a sprite for loading."""
        sprite_key = self.get_sprite_key(pokemon, mode)
        self.sprite_labels[sprite_key] = sprite_label
        
        # Check memory cache first
        if sprite_key in self.cache:
            sprite_label.configure(image=self.cache[sprite_key])
            return
        
        # Check disk cache second
        cached_image = self._load_sprite_from_cache(sprite_key)
        if cached_image:
            self.cache[sprite_key] = cached_image
            sprite_label.configure(image=cached_image)
            return
        
        # Only queue for download if not in either cache
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
        """Mark sprites as visible for prioritization."""
        self.visible_sprites = set(sprite_keys)
        self._prioritize_visible()
    
    def _prioritize_visible(self):
        """Prioritize visible sprites in the load queue."""
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
        """Process the sprite loading queue."""
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
        """Load sprite in background thread."""
        try:
            time.sleep(SPRITE_LOAD_DELAY)
            url = self._resolve_sprite_url(pokemon, mode)
            with urlopen(url, timeout=5) as response:
                image_data = response.read()
            image = Image.open(io.BytesIO(image_data))
            image = image.resize(SPRITE_SIZE, Image.Resampling.LANCZOS)
            
            # Save to disk cache for future use
            self._save_sprite_to_cache(sprite_key, image)
            
            # Create CustomTkinter image and cache in memory
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
        """Update sprite label with loaded image."""
        try:
            if sprite_key in self.sprite_labels:
                label = self.sprite_labels[sprite_key]
                if label.winfo_exists():
                    label.configure(image=image)
        except:
            pass
    
    def clear_cache(self):
        """Clear sprite cache, keeping only visible sprites."""
        new_cache = {}
        for key in self.visible_sprites:
            if key in self.cache:
                new_cache[key] = self.cache[key]
        self.cache = new_cache
    
    def cancel_pending_loads(self):
        """Cancel all pending sprite loads."""
        self.load_queue.clear()
        self.sprite_labels.clear()
    
    def batch_queue_sprites(self, pokemon_sprite_pairs: List[Tuple], mode: Mode, delay_start: int = 0):
        """Batch queue multiple sprites with staggered loading to prevent UI blocking."""
        def queue_batch():
            for pokemon, sprite_label in pokemon_sprite_pairs:
                if sprite_label.winfo_exists():  # Check if widget still exists
                    self.queue_sprite_load(pokemon, sprite_label, mode, priority=False)
        
        # Start loading after a small delay to let UI render first
        if delay_start > 0:
            self.root.after(delay_start, queue_batch)
        else:
            queue_batch()


class DataManager:
    """Handles saving/loading Pokemon data and CSV export."""
    
    @staticmethod
    def save(pokemon_list: List[Pokemon]) -> None:
        """Save Pokemon data to JSON file."""
        try:
            data = [asdict(p) for p in pokemon_list]
            with open(DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving data: {e}")
    
    @staticmethod
    def load(pokemon_list: List[Pokemon]) -> None:
        """Load Pokemon data from JSON file."""
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
        """Export Pokemon data to CSV file."""
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
