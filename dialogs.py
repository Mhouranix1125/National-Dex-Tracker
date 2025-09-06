"""Dialog windows for the Pokemon tracker application."""

from tkinter import messagebox
from typing import Callable, List

import customtkinter as ctk

from constants import ITEMS_PER_PAGE, APP_ICON, APP_ICON_PNG, APP_ICON_ICNS
from models import Pokemon
import os
import platform


class QuickSearchDialog:
    """Dialog for quickly searching Pokemon by name or number."""
    
    def __init__(self, parent: ctk.CTk, pokemon_list: List[Pokemon], callback: Callable[[int], None]):
        """
        Initialize the quick search dialog.
        
        Args:
            parent: Parent window
            pokemon_list: List of Pokemon to search through
            callback: Function to call with page number when Pokemon is found
        """
        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title("Quick Search")
        self.dialog.geometry("400x150")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self.pokemon_list = pokemon_list
        self.callback = callback
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Setup the dialog UI elements."""
        ctk.CTkLabel(
            self.dialog, 
            text="Enter Pokémon name or number:"
        ).pack(pady=10)
        
        self.search_entry = ctk.CTkEntry(self.dialog, width=300)
        self.search_entry.pack(pady=10)
        self.search_entry.focus()
        self.search_entry.bind("<Return>", lambda e: self.search())
        
        button_frame = ctk.CTkFrame(self.dialog)
        button_frame.pack(pady=10)
        
        ctk.CTkButton(
            button_frame, 
            text="Search", 
            command=self.search
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            button_frame, 
            text="Cancel", 
            command=self.dialog.destroy
        ).pack(side="left", padx=5)
    
    def search(self) -> None:
        """Search for Pokemon and navigate to the page containing it."""
        query = self.search_entry.get().lower().strip()
        if not query:
            return
        
        for i, pokemon in enumerate(self.pokemon_list):
            if (query in pokemon.display_id.lower() or 
                query in pokemon.name.lower()):
                page = i // ITEMS_PER_PAGE
                self.callback(page)
                self.dialog.destroy()
                return
        
        messagebox.showinfo(
            "Not Found", 
            f"No Pokémon matching '{query}' was found."
        )


class CSVExportDialog:
    """Dialog for choosing CSV export options."""
    
    def __init__(self, parent: ctk.CTk, current_region_name: str, callback: Callable[[str], None]):
        """
        Initialize the CSV export dialog.
        
        Args:
            parent: Parent window
            current_region_name: Name of the current region (e.g., "Kanto", "Johto")
            callback: Function to call with export choice ("region", "national", or "cancel")
        """
        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title("Export CSV")
        self.dialog.geometry("480x380")  # Increased height from 280 to 380
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.resizable(False, False)
        
        # Set dialog icon to match main app
        self._set_dialog_icon()
        
        self.current_region_name = current_region_name
        self.callback = callback
        self.result = "cancel"  # Default to cancel
        
        self._setup_ui()
        
        # Center the dialog on the parent window
        self._center_dialog(parent)
    
    def _setup_ui(self) -> None:
        """Setup the dialog UI elements."""
        # Main container with padding
        main_frame = ctk.CTkFrame(self.dialog)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Header
        header_label = ctk.CTkLabel(
            main_frame,
            text="📊 Export Pokémon Data to CSV",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        header_label.pack(pady=(10, 20))
        
        # Description
        desc_label = ctk.CTkLabel(
            main_frame,
            text="Choose what data you'd like to export:",
            font=ctk.CTkFont(size=14)
        )
        desc_label.pack(pady=(0, 20))
        
        # Button container
        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack(fill="x", pady=(0, 20))
        
        # Current Region button
        region_btn = ctk.CTkButton(
            button_frame,
            text=f"🌍 Current Region ({self.current_region_name})",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=50,
            fg_color=("#3B82F6", "#2563EB"),
            hover_color=("#2563EB", "#1D4ED8"),
            command=self._export_region
        )
        region_btn.pack(fill="x", padx=15, pady=(15, 10))
        
        # National Dex button  
        national_btn = ctk.CTkButton(
            button_frame,
            text="🗾 Complete National Dex",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=50,
            fg_color=("#059669", "#047857"),
            hover_color=("#047857", "#065F46"),
            command=self._export_national
        )
        national_btn.pack(fill="x", padx=15, pady=10)
        
        # Cancel button - same height as export buttons for consistency
        cancel_btn = ctk.CTkButton(
            button_frame,
            text="❌ Cancel",
            font=ctk.CTkFont(size=14, weight="bold"),  # Made bold like other buttons
            height=50,  # Same height as other buttons
            fg_color=("#DC2626", "#B91C1C"),  # Changed to red for better visibility
            hover_color=("#B91C1C", "#991B1B"),
            command=self._cancel
        )
        cancel_btn.pack(fill="x", padx=15, pady=(10, 15))
        
        # Info text
        info_label = ctk.CTkLabel(
            main_frame,
            text="💡 Exported file will include Pokémon ID, Name, Region, Mode, and Capture Status",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        info_label.pack(pady=(10, 10))
        
        # Bind escape key to cancel
        self.dialog.bind("<Escape>", lambda e: self._cancel())
        self.dialog.focus()
    
    def _center_dialog(self, parent: ctk.CTk) -> None:
        """Center the dialog on the parent window."""
        self.dialog.update_idletasks()  # Ensure geometry is calculated
        
        # Get parent window position and size
        parent.update_idletasks()
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()
        
        # Get dialog size
        dialog_width = self.dialog.winfo_width()
        dialog_height = self.dialog.winfo_height()
        
        # Calculate center position
        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2
        
        self.dialog.geometry(f"+{x}+{y}")
    
    def _set_dialog_icon(self) -> None:
        """Set the dialog icon to match the main application."""
        is_macos = platform.system() == 'Darwin'
        
        if is_macos:
            # macOS-specific icon handling
            try:
                if os.path.exists(APP_ICON_ICNS):
                    self.dialog.iconbitmap(APP_ICON_ICNS)
                    return
            except Exception as e:
                print(f"macOS dialog ICNS failed: {e}")
            
            try:
                if os.path.exists(APP_ICON_PNG):
                    from tkinter import PhotoImage
                    icon_img = PhotoImage(file=APP_ICON_PNG)
                    self.dialog.iconphoto(True, icon_img)
                    return
            except Exception as e:
                print(f"macOS dialog PNG failed: {e}")
        else:
            # Windows/Linux icon handling
            try:
                if os.path.exists(APP_ICON):
                    self.dialog.iconbitmap(APP_ICON)
                    return
            except Exception as e:
                print(f"Dialog ICO failed: {e}")
            
            try:
                if os.path.exists(APP_ICON_PNG):
                    from tkinter import PhotoImage
                    icon_img = PhotoImage(file=APP_ICON_PNG)
                    self.dialog.iconphoto(True, icon_img)
                    return
            except Exception as e:
                print(f"Dialog PNG failed: {e}")
    
    def _export_region(self) -> None:
        """Export current region data."""
        self.result = "region"
        self.callback("region")
        self.dialog.destroy()
    
    def _export_national(self) -> None:
        """Export complete National Dex data."""
        self.result = "national"
        self.callback("national")
        self.dialog.destroy()
    
    def _cancel(self) -> None:
        """Cancel export."""
        self.result = "cancel"
        self.callback("cancel")
        self.dialog.destroy()
