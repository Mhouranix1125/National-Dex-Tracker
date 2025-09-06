"""
Pokemon Home Pokedex Tracker
Main entry point for the application.
"""

import threading
from tkinter import messagebox

import customtkinter as ctk

from database import PokemonDatabase
from dialogs import QuickSearchDialog
from main_app import PokemonTracker


def main():
    """Main entry point for the Pokemon Tracker application."""
    root = ctk.CTk()

    def refresh_names():
        """Refresh Pokemon names from PokéAPI."""
        if not messagebox.askyesno("Refresh Names", "Re-download all Pokémon names from PokéAPI?"):
            return
        
        def _do_refresh():
            try:
                PokemonDatabase.refresh_cache()
                try:
                    root.after(0, lambda: messagebox.showinfo(
                        "Success", 
                        "Names refreshed! Please restart the app for a full rebuild."
                    ))
                except Exception:
                    pass
            except Exception as e:
                try:
                    root.after(0, lambda: messagebox.showwarning(
                        "Refresh Failed", 
                        f"Could not refresh names.\n\n{e}"
                    ))
                except Exception:
                    pass
        
        threading.Thread(target=_do_refresh, daemon=True).start()

    def open_search():
        """Open the quick search dialog."""
        if hasattr(app, 'pokemon_list'):
            def go_to_page(page):
                app.current_page = page
                app._update_display()
            QuickSearchDialog(root, app.pokemon_list, go_to_page)

    # Bind keyboard shortcuts
    root.bind('<Control-f>', lambda e: open_search())
    root.bind('<Control-r>', lambda e: refresh_names())
    
    # Create and start the application
    app = PokemonTracker(root)
    app.title_label.configure(
        text="Pokémon Home Pokédex Tracker (Ctrl+F: Search, Ctrl+R: Refresh Names)"
    )
    
    root.mainloop()


if __name__ == "__main__":
    main()
