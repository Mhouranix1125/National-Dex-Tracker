"""Main Pokemon Tracker application."""

from tkinter import messagebox
from typing import List, Tuple, Dict
import hashlib
import time
import os
import platform

import customtkinter as ctk

from constants import (
    TOTAL_POKEMON, ITEMS_PER_PAGE, DEFAULT_WINDOW_SIZE, 
    HEADER_HEIGHT, CONTROL_FRAME_HEIGHT, FILTER_FRAME_HEIGHT,
    PAGINATION_FRAME_HEIGHT, CARD_HEIGHT, COLORS, APP_ICON, APP_ICON_PNG, APP_ICON_ICNS
)
from database import PokemonDatabase
from dialogs import CSVExportDialog
from managers import LazyLoadSpriteManager, DataManager
from models import Pokemon, Mode, Region, ViewFilter


class PokemonTracker:
    """Main application class with pagination and filtering."""
    
    def __init__(self, root: ctk.CTk):
        self.root = root
        self.root.title("Pokémon Home Pokédex Tracker")
        self.root.geometry(DEFAULT_WINDOW_SIZE)
        
        # Set application icon
        self._set_app_icon()
        
        # Initialize database
        PokemonDatabase.initialize_names()

        # Initialize managers and state
        self.sprite_manager = LazyLoadSpriteManager(root)
        self.pokemon_list: List[Pokemon] = []
        self.current_region = Region.KANTO
        self.current_mode = Mode.NORMAL
        self.current_page = 0
        self.total_pages = 0
        self.card_widgets: List[Tuple] = []
        self.view_filter = ViewFilter.ALL
        
        # Performance optimization flags
        self._loading = False
        self._region_switch_pending = None
        
        # Region UI state caching
        self._region_cache: Dict[str, Dict] = {}  # Cache UI state for each region/mode/filter combo
        self._cache_data_hash = None  # Hash of pokemon_list to detect data changes
        
        # Pre-create font objects to avoid repeated creation
        self._font_cache = {
            'id_font': ctk.CTkFont(size=14, weight="bold"),
            'name_font_normal': ctk.CTkFont(size=16, weight="normal"),
            'name_font_bold': ctk.CTkFont(size=16, weight="bold"),
            'checkbox_font': ctk.CTkFont(size=12)
        }
        
        # Setup application
        self._generate_pokemon_data()
        DataManager.load(self.pokemon_list)
        self._setup_ui()
        self._update_display()
    
    def _set_app_icon(self) -> None:
        """Set the application icon with platform-specific optimizations."""
        is_macos = platform.system() == 'Darwin'
        
        print(f"Setting icon on {platform.system()}...")
        
        # macOS-specific icon handling using Cocoa
        if is_macos:
            # Method 1: Use PyObjC/Cocoa to properly set dock icon
            try:
                import AppKit
                from Cocoa import NSApplication, NSImage, NSBundle
                
                # Get the shared NSApplication instance
                app = NSApplication.sharedApplication()
                
                # Create NSImage from our icon file
                icon_path = os.path.abspath(APP_ICON_ICNS)
                if os.path.exists(icon_path):
                    # Load the ICNS file into NSImage
                    ns_image = NSImage.alloc().initWithContentsOfFile_(icon_path)
                    if ns_image:
                        # Set the application icon (this sets the dock icon properly!)
                        app.setApplicationIconImage_(ns_image)
                        print(f"✅ macOS: Dock icon set using Cocoa/ICNS: {icon_path}")
                        return
                    else:
                        print(f"Failed to create NSImage from: {icon_path}")
                        
            except ImportError:
                print("PyObjC not available, falling back to tkinter methods")
            except Exception as e:
                print(f"Cocoa method failed: {e}")
            
            # Method 2: Fallback to tkinter iconphoto with high-res PNG
            try:
                if os.path.exists(APP_ICON_PNG):
                    from tkinter import PhotoImage
                    icon_img = PhotoImage(file=APP_ICON_PNG)
                    self.root.iconphoto(True, icon_img)
                    print(f"✅ macOS: Window icon set using PNG iconphoto: {APP_ICON_PNG}")
                    print("   Note: macOS dock icon requires Cocoa/PyObjC for proper display")
                    return
            except Exception as e:
                print(f"macOS PNG iconphoto failed: {e}")
        
        # Windows/Linux icon handling
        else:
            # Method 1: Try ICO file (best for Windows) with absolute path
            try:
                if os.path.exists(APP_ICON):
                    abs_icon_path = os.path.abspath(APP_ICON)
                    self.root.iconbitmap(abs_icon_path)
                    print(f"✅ {platform.system()}: Icon set using ICO file: {abs_icon_path}")
                    return
            except Exception as e:
                print(f"ICO icon failed: {e}")
            
            # Method 2: Try ICO with wm_iconbitmap (alternative Windows method)
            try:
                if os.path.exists(APP_ICON):
                    abs_icon_path = os.path.abspath(APP_ICON)
                    self.root.wm_iconbitmap(abs_icon_path)
                    print(f"✅ {platform.system()}: Icon set using wm_iconbitmap: {abs_icon_path}")
                    return
            except Exception as e:
                print(f"wm_iconbitmap failed: {e}")
            
            # Method 3: Try PNG fallback with iconphoto
            try:
                if os.path.exists(APP_ICON_PNG):
                    from tkinter import PhotoImage
                    abs_png_path = os.path.abspath(APP_ICON_PNG)
                    icon_img = PhotoImage(file=abs_png_path)
                    self.root.iconphoto(True, icon_img)
                    print(f"✅ {platform.system()}: Icon set using PNG iconphoto: {abs_png_path}")
                    return
            except Exception as e:
                print(f"PNG iconphoto failed: {e}")
            
            # Method 4: Try PNG with wm_iconphoto
            try:
                if os.path.exists(APP_ICON_PNG):
                    from tkinter import PhotoImage
                    abs_png_path = os.path.abspath(APP_ICON_PNG)
                    icon_img = PhotoImage(file=abs_png_path)
                    self.root.wm_iconphoto(True, icon_img)
                    print(f"✅ {platform.system()}: Icon set using wm_iconphoto: {abs_png_path}")
                    return
            except Exception as e:
                print(f"wm_iconphoto failed: {e}")
        
        # If all methods failed
        print(f"⚠️ Could not set application icon on {platform.system()}")
        print(f"   Files exist - ICO: {os.path.exists(APP_ICON)}, PNG: {os.path.exists(APP_ICON_PNG)}, ICNS: {os.path.exists(APP_ICON_ICNS)}")
        if is_macos:
            print(f"   macOS Note: tkinter apps have limited dock icon support. Consider using PyObjC or creating an .app bundle.")
    
    def _generate_pokemon_data(self) -> None:
        """Generate the complete Pokemon list with variants."""
        self.pokemon_list = []
        for i in range(1, TOTAL_POKEMON + 1):
            name = PokemonDatabase.get_name(i)
            self.pokemon_list.append(Pokemon(id=i, display_id=str(i), name=name))
            
            # Add regional variants
            for idx, variant in enumerate(PokemonDatabase.get_variants(i)):
                self.pokemon_list.append(Pokemon(
                    id=i,
                    display_id=f"{i}-{idx + 1}",
                    name=name,
                    is_variant=True,
                    region=variant
                ))
    
    def _setup_ui(self) -> None:
        """Setup the main UI components."""
        # Configure appearance
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Create UI components
        self._create_header()
        self._create_mode_selector()
        self._create_controls()
        self._create_region_tabs()
        self._create_filter_selector()
        self._create_pagination_controls()
        self._create_main_area()
    
    def _create_header(self) -> None:
        """Create the application header."""
        header_frame = ctk.CTkFrame(self.root, height=HEADER_HEIGHT, corner_radius=10)
        header_frame.pack(fill="x", padx=20, pady=10)
        header_frame.pack_propagate(False)
        
        self.title_label = ctk.CTkLabel(
            header_frame, 
            text="Pokémon Home Pokédex Tracker",
            font=ctk.CTkFont(size=28, weight="bold")
        )
        self.title_label.pack(pady=20)
    
    def _create_mode_selector(self) -> None:
        """Create mode selection controls (Normal/Shiny)."""
        mode_frame = ctk.CTkFrame(self.root, height=CONTROL_FRAME_HEIGHT, corner_radius=10)
        mode_frame.pack(fill="x", padx=20, pady=5)
        mode_frame.pack_propagate(False)
        
        ctk.CTkLabel(
            mode_frame, 
            text="Mode:", 
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(side="left", padx=20, pady=15)
        
        self.mode_var = ctk.StringVar(value=Mode.NORMAL.value)
        self.mode_segmented = ctk.CTkSegmentedButton(
            mode_frame,
            values=[m.value for m in Mode],
            variable=self.mode_var,
            command=self._on_mode_change
        )
        self.mode_segmented.pack(side="left", padx=10, pady=15)
    
    def _create_controls(self) -> None:
        """Create control buttons."""
        controls_frame = ctk.CTkFrame(self.root, height=CONTROL_FRAME_HEIGHT, corner_radius=10)
        controls_frame.pack(fill="x", padx=20, pady=5)
        controls_frame.pack_propagate(False)
        
        button_config = {
            "Check All (Page)": (COLORS["captured"][0], COLORS["captured"][1], self._check_all_page),
            "Uncheck All (Page)": ("red", "darkred", self._uncheck_all_page),
            "Check All (Region)": (COLORS["region_check"][0], COLORS["region_check"][1], self._check_all_region),
            "Uncheck All (Region)": (COLORS["region_uncheck"][0], COLORS["region_uncheck"][1], self._uncheck_all_region),
            "Download CSV": (COLORS["default"][0], COLORS["default"][1], self._download_csv)
        }
        
        for text, (fg, hover, command) in button_config.items():
            ctk.CTkButton(
                controls_frame, 
                text=text, 
                command=command, 
                fg_color=fg, 
                hover_color=hover, 
                width=150, 
                height=35
            ).pack(side="left", padx=8, pady=12)
        
        self.progress_label = ctk.CTkLabel(
            controls_frame, 
            text="Progress: 0/0", 
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.progress_label.pack(side="right", padx=20, pady=15)

    def _create_filter_selector(self) -> None:
        """Create filter selection controls."""
        filter_frame = ctk.CTkFrame(self.root, height=FILTER_FRAME_HEIGHT, corner_radius=10)
        filter_frame.pack(fill="x", padx=20, pady=5)
        filter_frame.pack_propagate(False)

        ctk.CTkLabel(
            filter_frame, 
            text="Filter:", 
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(side="left", padx=20, pady=12)

        self.filter_var = ctk.StringVar(value=ViewFilter.ALL.value)
        self.filter_segmented = ctk.CTkSegmentedButton(
            filter_frame,
            values=[f.value for f in ViewFilter],
            variable=self.filter_var,
            command=self._on_filter_change
        )
        self.filter_segmented.pack(side="left", padx=10, pady=10)

        ctk.CTkLabel(
            filter_frame, 
            text="(Filter uses current Mode)", 
            font=ctk.CTkFont(size=12)
        ).pack(side="left", padx=12)

    def _create_region_tabs(self) -> None:
        """Create region selection tabs."""
        tabs_frame = ctk.CTkFrame(self.root, height=FILTER_FRAME_HEIGHT, corner_radius=10)
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
    
    def _create_pagination_controls(self) -> None:
        """Create pagination controls."""
        self.pagination_frame = ctk.CTkFrame(self.root, height=PAGINATION_FRAME_HEIGHT, corner_radius=10)
        self.pagination_frame.pack(fill="x", padx=20, pady=5)
        self.pagination_frame.pack_propagate(False)
        
        self.prev_button = ctk.CTkButton(
            self.pagination_frame, 
            text="◄ Previous", 
            command=self._prev_page, 
            width=120, 
            height=30
        )
        self.prev_button.pack(side="left", padx=20, pady=10)
        
        self.page_info_label = ctk.CTkLabel(
            self.pagination_frame, 
            text="Page 1 of 1", 
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.page_info_label.pack(side="left", expand=True)
        
        self.next_button = ctk.CTkButton(
            self.pagination_frame, 
            text="Next ►", 
            command=self._next_page, 
            width=120, 
            height=30
        )
        self.next_button.pack(side="right", padx=20, pady=10)
        
        # Page jump controls
        self.jump_frame = ctk.CTkFrame(self.pagination_frame)
        self.jump_frame.pack(side="right", padx=10)
        
        ctk.CTkLabel(self.jump_frame, text="Go to page:").pack(side="left", padx=5)
        
        self.page_entry = ctk.CTkEntry(self.jump_frame, width=50)
        self.page_entry.pack(side="left", padx=5)
        self.page_entry.bind("<Return>", lambda e: self._jump_to_page())
        
        ctk.CTkButton(
            self.jump_frame, 
            text="Go", 
            command=self._jump_to_page, 
            width=50, 
            height=25
        ).pack(side="left", padx=5)
    
    def _create_main_area(self) -> None:
        """Create the main scrollable area for Pokemon cards."""
        self.main_frame = ctk.CTkFrame(self.root, corner_radius=10)
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.main_scrollable = ctk.CTkScrollableFrame(self.main_frame, corner_radius=10)
        self.main_scrollable.pack(fill="both", expand=True, padx=10, pady=10)
        self.main_scrollable.grid_columnconfigure(0, weight=1)
        self.main_scrollable.bind_all("<MouseWheel>", self._on_scroll)
        
        # Store reference to the internal canvas for scroll position control
        self._canvas = None
        for child in self.main_scrollable.winfo_children():
            if hasattr(child, 'yview'):
                self._canvas = child
                break
    
    def _on_scroll(self, event) -> None:
        """Handle scroll events to update visible sprites."""
        self._update_visible_sprites()
    
    def _reset_scroll_position(self) -> None:
        """Reset scroll position to top of the scrollable area."""
        try:
            # Method 1: Try the most common CustomTkinter approach
            if hasattr(self.main_scrollable, '_parent_canvas'):
                self.main_scrollable._parent_canvas.yview_moveto(0.0)
                return
        except:
            pass
            
        try:
            # Method 2: Try alternative canvas access
            for widget in self.main_frame.winfo_children():
                if hasattr(widget, '_parent_canvas'):
                    widget._parent_canvas.yview_moveto(0.0)
                    return
        except:
            pass
            
        try:
            # Method 3: Try finding canvas widget directly
            for widget in self.main_scrollable.winfo_children():
                if 'canvas' in str(type(widget)).lower():
                    if hasattr(widget, 'yview_moveto'):
                        widget.yview_moveto(0.0)
                        return
        except:
            pass
            
        try:
            # Method 4: Force update the scrollable frame's scroll position
            # This works by updating the scrollregion and resetting view
            self.main_scrollable.update_idletasks()
            if hasattr(self.main_scrollable, '_parent_canvas'):
                canvas = self.main_scrollable._parent_canvas
                canvas.configure(scrollregion=canvas.bbox("all"))
                canvas.yview_moveto(0.0)
        except:
            pass  # If all methods fail, continue without scroll reset
    
    # ---- UI State Caching Methods ----
    def _get_cache_key(self) -> str:
        """Generate cache key based on current region/mode/filter state."""
        return f"{self.current_region.display_name}_{self.current_mode.value}_{self.view_filter.value}"
    
    def _get_data_hash(self) -> str:
        """Generate hash of current pokemon data to detect changes."""
        data_str = ""
        for pokemon in self.pokemon_list:
            data_str += f"{pokemon.id}{pokemon.captured_normal}{pokemon.captured_shiny}"
        return hashlib.md5(data_str.encode()).hexdigest()
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached UI state exists and data hasn't changed."""
        if cache_key not in self._region_cache:
            return False
        
        current_hash = self._get_data_hash()
        cached_hash = self._region_cache[cache_key].get('data_hash')
        return current_hash == cached_hash
    
    def _save_ui_state_to_cache(self, cache_key: str) -> None:
        """Save current UI state to cache."""
        try:
            filtered_pokemon = self._get_filtered_pokemon()
            cache_data = {
                'data_hash': self._get_data_hash(),
                'total_pages': self.total_pages,
                'filtered_count': len(filtered_pokemon),
                'pokemon_ids': [p.display_id for p in filtered_pokemon],
                'timestamp': time.time()
            }
            self._region_cache[cache_key] = cache_data
        except Exception as e:
            print(f"Failed to save UI state to cache: {e}")
    
    def _should_use_cache(self) -> bool:
        """Determine if we should use cached UI state."""
        cache_key = self._get_cache_key()
        return self._is_cache_valid(cache_key) and not self._loading
    
    def _restore_from_cache_fast(self, cache_key: str) -> None:
        """Restore UI from cached state instantly."""
        try:
            cache_data = self._region_cache[cache_key]
            
            # Clear existing widgets
            for widget in self.main_scrollable.winfo_children():
                widget.destroy()
            self.card_widgets.clear()
            
            # Restore pagination state from cache
            self.total_pages = cache_data['total_pages']
            self.current_page = min(self.current_page, self.total_pages - 1)
            self.current_page = max(0, self.current_page)
            
            # Create cards for current page
            current_pokemon = self._get_current_page_pokemon()
            for row, pokemon in enumerate(current_pokemon):
                self.card_widgets.append(self._create_pokemon_card_fast(pokemon, row))
            
            # Reset scroll position
            self.root.after(10, self._reset_scroll_position)
            
            # Update UI elements
            self._update_pagination_controls()
            self._update_progress()
            
            # Load sprites with lower priority (cached sprites load instantly anyway)
            self.root.after(100, self._load_sprites_deferred)
            
        except Exception as e:
            print(f"Failed to restore from cache, falling back to regular load: {e}")
            # Fall back to regular loading
            self._loading = True
            self._show_loading_state()
            self.root.after(1, self._update_display_deferred)
    
    def _invalidate_cache(self) -> None:
        """Invalidate all cached UI states when data changes."""
        self._region_cache.clear()
    
    def _create_cards_progressively(self, pokemon_list: List[Pokemon]) -> None:
        """Create Pokemon cards progressively to avoid UI blocking."""
        self._progressive_index = 0
        self._progressive_pokemon_list = pokemon_list
        self._create_card_batch()
    
    def _create_card_batch(self) -> None:
        """Create a batch of cards (5-10 at a time) to keep UI responsive."""
        batch_size = 8  # Create 8 cards per batch
        end_index = min(self._progressive_index + batch_size, len(self._progressive_pokemon_list))
        
        # Create batch of cards
        for i in range(self._progressive_index, end_index):
            row = i
            pokemon = self._progressive_pokemon_list[i]
            self.card_widgets.append(self._create_pokemon_card_optimized(pokemon, row))
        
        self._progressive_index = end_index
        
        # Schedule next batch if more cards to create
        if self._progressive_index < len(self._progressive_pokemon_list):
            self.root.after(1, self._create_card_batch)  # Very short delay
        else:
            # All cards created, now update UI and load sprites
            self._update_pagination_controls()
            self._update_progress()
            self.root.after(50, self._load_sprites_deferred)
            
            # Save to cache
            cache_key = self._get_cache_key()
            self._save_ui_state_to_cache(cache_key)

    def _update_visible_sprites(self) -> None:
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
                    # Small buffer so near-edge rows get prioritized too
                    if (viewport_top - 100) <= y <= (viewport_bottom + 100):
                        sprite_key = self.sprite_manager.get_sprite_key(pokemon, self.current_mode)
                        visible_keys.append(sprite_key)
            except:
                pass

        self.sprite_manager.mark_visible(visible_keys)

    # ---- Filtering helpers ----
    def _region_filter(self, p: Pokemon) -> bool:
        """Check if Pokemon belongs to current region."""
        return self.current_region.start <= p.id <= self.current_region.end

    def _status_filter(self, p: Pokemon) -> bool:
        """Check if Pokemon matches current view filter."""
        if self.view_filter == ViewFilter.ALL:
            return True
        captured = p.is_captured(self.current_mode)
        if self.view_filter == ViewFilter.CAPTURED:
            return captured
        if self.view_filter == ViewFilter.MISSING:
            return not captured
        return True

    def _get_filtered_pokemon(self) -> List[Pokemon]:
        """Get Pokemon list filtered by region and status."""
        return [p for p in self.pokemon_list if self._region_filter(p) and self._status_filter(p)]
    
    def _get_current_page_pokemon(self) -> List[Pokemon]:
        """Get Pokemon for the current page."""
        filtered = self._get_filtered_pokemon()
        start_idx = self.current_page * ITEMS_PER_PAGE
        end_idx = start_idx + ITEMS_PER_PAGE
        return filtered[start_idx:end_idx]
    
    def _update_display(self) -> None:
        """Update the main display with current Pokemon - optimized with caching."""
        if self._loading:
            return
        
        # Check if we can use cached UI state for instant switching
        cache_key = self._get_cache_key()
        if self._should_use_cache():
            self._restore_from_cache_fast(cache_key)
            return
            
        self._loading = True
        self.sprite_manager.cancel_pending_loads()
        
        # Show loading state immediately
        self._show_loading_state()
        
        # Use after() to avoid blocking UI thread
        self.root.after(1, self._update_display_deferred)
    
    def _show_loading_state(self) -> None:
        """Show loading indicator during region switches."""
        # Clear existing widgets efficiently
        for widget in self.main_scrollable.winfo_children():
            widget.destroy()
        self.card_widgets.clear()
        
        # Show loading message
        loading_frame = ctk.CTkFrame(self.main_scrollable)
        loading_frame.pack(fill="both", expand=True, padx=20, pady=50)
        
        ctk.CTkLabel(
            loading_frame,
            text="🔄 Loading Pokémon...",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=20)
        
        # Update pagination immediately with placeholder
        self.page_info_label.configure(text="Loading...")
        self.prev_button.configure(state="disabled")
        self.next_button.configure(state="disabled")
    
    def _update_display_deferred(self) -> None:
        """Deferred display update that happens after loading state is shown."""
        try:
            # Clear loading state
            for widget in self.main_scrollable.winfo_children():
                widget.destroy()
            self.card_widgets.clear()
            
            # Calculate pagination
            filtered_pokemon = self._get_filtered_pokemon()
            self.total_pages = max(1, (len(filtered_pokemon) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
            self.current_page = min(self.current_page, self.total_pages - 1)
            self.current_page = max(0, self.current_page)
            
            # Create cards progressively to avoid UI blocking
            current_pokemon = self._get_current_page_pokemon()
            self._create_cards_progressively(current_pokemon)
            
            # Reset scroll position to top so user can see the new content
            self.root.after(10, self._reset_scroll_position)
            
        finally:
            self._loading = False
    
    def _load_sprites_deferred(self) -> None:
        """Load sprites after the UI is already showing - prevents blocking."""
        # Use batch loading for better performance
        pokemon_sprite_pairs = [(pokemon, sprite_label) for pokemon, sprite_label, _ in self.card_widgets]
        self.sprite_manager.batch_queue_sprites(pokemon_sprite_pairs, self.current_mode, delay_start=0)
        
        # Update visible sprites priority after a short delay
        self.root.after(150, self._update_visible_sprites)
    
    def _update_pagination_controls(self) -> None:
        """Update pagination control states."""
        self.page_info_label.configure(text=f"Page {self.current_page + 1} of {self.total_pages}")
        self.prev_button.configure(state="normal" if self.current_page > 0 else "disabled")
        self.next_button.configure(state="normal" if self.current_page < self.total_pages - 1 else "disabled")
        self.page_entry.delete(0, 'end')
    
    def _update_progress(self) -> None:
        """Update progress display."""
        # Progress shown against the current REGION (ignoring filter), as that's more intuitive
        regional = [p for p in self.pokemon_list if self._region_filter(p)]
        captured = sum(1 for p in regional if p.is_captured(self.current_mode))
        total = len(regional)
        filter_text = f" | Filter: {self.view_filter.value}"
        self.progress_label.configure(
            text=f"{self.current_mode.value} Progress: {captured}/{total} (Page {self.current_page + 1}/{self.total_pages}){filter_text}"
        )

    def _create_pokemon_card(self, pokemon: Pokemon, row: int) -> Tuple:
        """Create a Pokemon card widget."""
        is_captured = pokemon.is_captured(self.current_mode)
        if is_captured:
            card_color = COLORS["captured"]
        elif pokemon.is_variant:
            card_color = COLORS["variant"]
        else:
            card_color = None
        
        card_frame = ctk.CTkFrame(
            self.main_scrollable, 
            height=CARD_HEIGHT, 
            corner_radius=10, 
            fg_color=card_color
        )
        card_frame.grid(row=row, column=0, sticky="ew", padx=10, pady=5)
        card_frame.grid_propagate(False)
        card_frame.grid_columnconfigure(2, weight=1)
        
        # Pokemon ID
        ctk.CTkLabel(
            card_frame, 
            text=f"#{pokemon.display_id}", 
            font=ctk.CTkFont(size=14, weight="bold"), 
            width=80
        ).grid(row=0, column=0, padx=15, pady=25)
        
        # Sprite
        sprite_label = ctk.CTkLabel(
            card_frame, 
            image=self.sprite_manager.placeholder, 
            text="", 
            width=80
        )
        sprite_label.grid(row=0, column=1, padx=10, pady=13)
        self.sprite_manager.queue_sprite_load(pokemon, sprite_label, self.current_mode)
        
        # Pokemon name
        ctk.CTkLabel(
            card_frame,
            text=pokemon.get_display_name(),
            font=ctk.CTkFont(size=16, weight="bold" if pokemon.is_variant else "normal"),
            anchor="w"
        ).grid(row=0, column=2, sticky="ew", padx=15, pady=25)
        
        # Capture checkbox
        var = ctk.BooleanVar(value=is_captured)
        ctk.CTkCheckBox(
            card_frame, 
            text="Captured", 
            variable=var,
            command=lambda: self._toggle_capture(pokemon, var),
            font=ctk.CTkFont(size=12)
        ).grid(row=0, column=3, padx=15, pady=25)
        
        return (pokemon, sprite_label, card_frame)
    
    def _create_pokemon_card_fast(self, pokemon: Pokemon, row: int) -> Tuple:
        """Create a Pokemon card widget optimized for fast loading (no immediate sprites)."""
        is_captured = pokemon.is_captured(self.current_mode)
        if is_captured:
            card_color = COLORS["captured"]
        elif pokemon.is_variant:
            card_color = COLORS["variant"]
        else:
            card_color = None
        
        card_frame = ctk.CTkFrame(
            self.main_scrollable, 
            height=CARD_HEIGHT, 
            corner_radius=10, 
            fg_color=card_color
        )
        card_frame.grid(row=row, column=0, sticky="ew", padx=10, pady=5)
        card_frame.grid_propagate(False)
        card_frame.grid_columnconfigure(2, weight=1)
        
        # Pokemon ID
        ctk.CTkLabel(
            card_frame, 
            text=f"#{pokemon.display_id}", 
            font=ctk.CTkFont(size=14, weight="bold"), 
            width=80
        ).grid(row=0, column=0, padx=15, pady=25)
        
        # Sprite placeholder (no immediate loading)
        sprite_label = ctk.CTkLabel(
            card_frame, 
            image=self.sprite_manager.placeholder, 
            text="", 
            width=80
        )
        sprite_label.grid(row=0, column=1, padx=10, pady=13)
        # Note: No sprite loading here - will be done later in batch
        
        # Pokemon name
        ctk.CTkLabel(
            card_frame,
            text=pokemon.get_display_name(),
            font=ctk.CTkFont(size=16, weight="bold" if pokemon.is_variant else "normal"),
            anchor="w"
        ).grid(row=0, column=2, sticky="ew", padx=15, pady=25)
        
        # Capture checkbox
        var = ctk.BooleanVar(value=is_captured)
        ctk.CTkCheckBox(
            card_frame, 
            text="Captured", 
            variable=var,
            command=lambda: self._toggle_capture(pokemon, var),
            font=ctk.CTkFont(size=12)
        ).grid(row=0, column=3, padx=15, pady=25)
        
        return (pokemon, sprite_label, card_frame)
    
    def _create_pokemon_card_optimized(self, pokemon: Pokemon, row: int) -> Tuple:
        """Create a Pokemon card widget with maximum performance optimizations."""
        is_captured = pokemon.is_captured(self.current_mode)
        
        # Pre-determine colors without creating variables
        card_color = (COLORS["captured"] if is_captured else 
                     COLORS["variant"] if pokemon.is_variant else None)
        
        # Create frame with minimal configuration
        card_frame = ctk.CTkFrame(
            self.main_scrollable, 
            height=CARD_HEIGHT, 
            corner_radius=6,  # Slightly smaller radius for faster rendering
            fg_color=card_color
        )
        card_frame.grid(row=row, column=0, sticky="ew", padx=8, pady=3)  # Reduced padding
        card_frame.grid_propagate(False)
        card_frame.grid_columnconfigure(2, weight=1)
        
        # Pokemon ID - use cached font
        id_label = ctk.CTkLabel(
            card_frame, 
            text=f"#{pokemon.display_id}", 
            font=self._font_cache['id_font'],
            width=80
        )
        id_label.grid(row=0, column=0, padx=12, pady=20)
        
        # Sprite placeholder - minimal configuration
        sprite_label = ctk.CTkLabel(
            card_frame, 
            image=self.sprite_manager.placeholder, 
            text="", 
            width=80
        )
        sprite_label.grid(row=0, column=1, padx=8, pady=10)
        
        # Pokemon name - use cached font
        name_label = ctk.CTkLabel(
            card_frame,
            text=pokemon.get_display_name(),
            font=self._font_cache['name_font_bold'] if pokemon.is_variant else self._font_cache['name_font_normal'],
            anchor="w"
        )
        name_label.grid(row=0, column=2, sticky="ew", padx=12, pady=20)
        
        # Capture checkbox - use cached font
        var = ctk.BooleanVar(value=is_captured)
        checkbox = ctk.CTkCheckBox(
            card_frame, 
            text="Captured", 
            variable=var,
            command=lambda: self._toggle_capture(pokemon, var),
            font=self._font_cache['checkbox_font']
        )
        checkbox.grid(row=0, column=3, padx=12, pady=20)
        
        return (pokemon, sprite_label, card_frame)

    # ---- Event handlers ----
    def _toggle_capture(self, pokemon: Pokemon, var: ctk.BooleanVar) -> None:
        """Toggle Pokemon capture status."""
        pokemon.set_captured(self.current_mode, var.get())
        DataManager.save(self.pokemon_list)
        
        # Invalidate cache since data changed
        self._invalidate_cache()
        
        self._update_progress()
        self._refresh_card_colors()

    def _refresh_card_colors(self) -> None:
        """Refresh card colors based on capture status."""
        for pokemon, _, card_frame in self.card_widgets:
            is_captured = pokemon.is_captured(self.current_mode)
            if is_captured:
                color = COLORS["captured"]
            elif pokemon.is_variant:
                color = COLORS["variant"]
            else:
                color = COLORS["card_default"]
            try:
                card_frame.configure(fg_color=color)
            except:
                pass

    def _on_mode_change(self, mode_str: str) -> None:
        """Handle mode change with optimized performance."""
        self.current_mode = Mode(mode_str)
        self.title_label.configure(
            text="✨ Pokémon Home Shiny Pokédex Tracker ✨" if self.current_mode == Mode.SHINY 
            else "Pokémon Home Pokédex Tracker"
        )
        self.current_page = 0
        
        # Clear sprite cache when switching modes to avoid wrong sprite types
        self.sprite_manager.clear_cache()
        self._update_display()

    def _on_filter_change(self, filter_str: str) -> None:
        """Handle view filter change."""
        for vf in ViewFilter:
            if vf.value == filter_str:
                self.view_filter = vf
                break
        self.current_page = 0
        self._update_display()
    
    def _on_region_change(self, region_str: str) -> None:
        """Handle region change with debouncing to prevent rapid switching lag."""
        # Cancel any pending region switch
        if self._region_switch_pending:
            self.root.after_cancel(self._region_switch_pending)
        
        # Schedule the actual region switch with a small delay
        self._region_switch_pending = self.root.after(50, lambda: self._execute_region_change(region_str))
    
    def _execute_region_change(self, region_str: str) -> None:
        """Actually execute the region change."""
        self._region_switch_pending = None
        
        for region in Region:
            if region.display_name == region_str:
                self.current_region = region
                break
        
        self.current_page = 0
        if self.current_region == Region.NATIONAL:
            self.sprite_manager.clear_cache()
        
        self._update_display()
    
    def _prev_page(self) -> None:
        """Go to previous page."""
        if self.current_page > 0:
            self.current_page -= 1
            self._update_display()
    
    def _next_page(self) -> None:
        """Go to next page."""
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self._update_display()
    
    def _jump_to_page(self) -> None:
        """Jump to specific page."""
        try:
            page_num = int(self.page_entry.get()) - 1
            if 0 <= page_num < self.total_pages:
                self.current_page = page_num
                self._update_display()
            else:
                messagebox.showwarning(
                    "Invalid Page", 
                    f"Please enter a page number between 1 and {self.total_pages}"
                )
        except ValueError:
            messagebox.showwarning("Invalid Input", "Please enter a valid page number")
    
    def _check_all_page(self) -> None:
        """Mark all Pokemon on current page as captured."""
        mode_text = self.current_mode.value.lower()
        if messagebox.askyesno("Confirm", f"Mark all {mode_text} Pokémon on THIS PAGE as captured?"):
            for pokemon in self._get_current_page_pokemon():
                pokemon.set_captured(self.current_mode, True)
            DataManager.save(self.pokemon_list)
            self._invalidate_cache()
            self._update_display()

    def _uncheck_all_page(self) -> None:
        """Mark all Pokemon on current page as not captured."""
        mode_text = self.current_mode.value.lower()
        if messagebox.askyesno("Confirm", f"Mark all {mode_text} Pokémon on THIS PAGE as NOT captured?"):
            for pokemon in self._get_current_page_pokemon():
                pokemon.set_captured(self.current_mode, False)
            DataManager.save(self.pokemon_list)
            self._invalidate_cache()
            self._update_display()

    def _check_all_region(self) -> None:
        """Mark all Pokemon in current region as captured."""
        mode_text = self.current_mode.value.lower()
        region_name = self.current_region.display_name
        if messagebox.askyesno("Confirm", f"Mark ALL {mode_text} Pokémon in {region_name} as captured?"):
            for p in self.pokemon_list:
                if self._region_filter(p):
                    p.set_captured(self.current_mode, True)
            DataManager.save(self.pokemon_list)
            self._invalidate_cache()
            self._update_display()

    def _uncheck_all_region(self) -> None:
        """Mark all Pokemon in current region as not captured."""
        mode_text = self.current_mode.value.lower()
        region_name = self.current_region.display_name
        if messagebox.askyesno("Confirm", f"Mark ALL {mode_text} Pokémon in {region_name} as NOT captured?"):
            for p in self.pokemon_list:
                if self._region_filter(p):
                    p.set_captured(self.current_mode, False)
            DataManager.save(self.pokemon_list)
            self._invalidate_cache()
            self._update_display()
    
    def _download_csv(self) -> None:
        """Export Pokemon data to CSV with intuitive dialog."""
        def handle_export_choice(choice: str) -> None:
            if choice == "cancel":
                return  # User cancelled, do nothing
            
            elif choice == "region":
                # Export current region only
                selected = [p for p in self.pokemon_list if self._region_filter(p)]
                export_region = self.current_region
                
            elif choice == "national":
                # Export complete National Dex
                selected = self.pokemon_list.copy()  # All Pokemon
                export_region = Region.NATIONAL
            
            else:
                return  # Unknown choice, do nothing
            
            # Perform the export
            success = DataManager.export_csv(self.root, selected, export_region, self.current_mode)
            
            if success:
                # Show success message with details
                count = len(selected)
                scope = "National Dex" if choice == "national" else f"{export_region.display_name} region"
                mode = self.current_mode.value
                
                messagebox.showinfo(
                    "Export Successful! 🎉",
                    f"Successfully exported {count} Pokémon from {scope}\n"
                    f"Mode: {mode}\n"
                    f"Captured: {sum(1 for p in selected if p.is_captured(self.current_mode))}\n"
                    f"Missing: {sum(1 for p in selected if not p.is_captured(self.current_mode))}"
                )
        
        # Show the improved export dialog
        CSVExportDialog(
            parent=self.root,
            current_region_name=self.current_region.display_name,
            callback=handle_export_choice
        )
