# Pokémon Home Pokédex Tracker

> A fast, keyboard-friendly National & Regional Pokédex tracker built with **Python + CustomTkinter**.  
> Mark captures (Normal/Shiny), filter by region, quick-search by name/ID, and export progress to CSV — all in a clean desktop UI.

<p align="center">
  <a href="#-features">Features</a> •
  <a href="#-installation">Installation</a> •
  <a href="#-usage">Usage</a> •
  <a href="#-keyboard-shortcuts">Shortcuts</a> •
  <a href="#-troubleshooting">Troubleshooting</a> •
  <a href="#-project-structure">Structure</a> •
  <a href="#-roadmap">Roadmap</a> •
  <a href="#-contributing">Contributing</a> •
  <a href="#-license">License</a>
</p>

---

## ✨ Features

- **National & Regional Dex**: Kanto → Paldea + National view.
- **Normal / Shiny modes**: Track both with one toggle.
- **Quick Search**: Jump to any Pokémon with `Ctrl + F` (by name or #).
- **One‑click capture**: Per-entry checkbox with persistent save file (JSON).
- **Filter views**: All / Captured / Missing — per mode.
- **CSV export**: Export the current region or current page.
- **Lazy sprite loading**: Fetches only what’s in view; caches images.
- **Offline‑friendly names**: Built‑in fallback names for Kanto; on‑demand refresh from PokéAPI (`Ctrl/⌘ + R`).
- **Smooth scrolling**: Mouse & trackpad scroll on hover (Windows/macOS/Linux).
- **Dark UI**: Modern CustomTkinter layout with sane defaults.

> Designed to be **simple to run** (just Python) and **easy to modify**.

---

## 🧰 Installation

### Requirements
- **Python 3.10+**
- OS: Windows 10/11, macOS 12+, or modern Linux

### 1) Clone
```bash
git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>
```

### 2) Create a virtual environment (recommended)
Using a virtual environment ensures clean dependency management for the modular project structure.

```bash
# Windows (PowerShell)
py -m venv .venv
. .venv/Scripts/Activate.ps1

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

### 3) Install dependencies
The project includes a `requirements.txt` file with the following dependencies:

```txt
customtkinter>=5.2.2
pillow>=11.3.0
requests>=2.32.0
```

Then:
```bash
pip install -r requirements.txt
```

> Linux users may need Tk packages: e.g., `sudo apt install python3-tk`

---

## ▶️ Usage

Run the app:

```bash
# Windows
py main.py

# macOS / Linux
python3 main.py
```

**Basics**
- Select a **Region** tab or choose **National**.
- Toggle **Normal/Shiny** to switch mode.
- Use **checkboxes** to mark captured.
- Use the **Filter** (All / Captured / Missing) to focus your list.
- Click **Download CSV** and choose to export the current region or the current page.

**Names & Sprites**
- Names come from local cache and PokéAPI (on demand).
- Sprites are loaded lazily and cached in memory during the session.

**Save file**
- Capture state is persisted to a JSON file alongside the script by default.

**Legacy Support**  
- The original single-file `pokemon_tracker.py` remains available for backward compatibility.
- Both versions use the same data files, so you can switch between them seamlessly.

---

## ⌨️ Keyboard Shortcuts

- **Search**: `Ctrl + F`  
  Search by **name** (case‑insensitive) or **#ID**; jumps to the entry.  
  macOS note: use the Control key (not Command).
- **Refresh names**: `Ctrl + R`  
  Pull the latest names/slugs from PokéAPI and cache them for next run.  
  macOS note: use the Control key (not Command).

---

## 🐛 Troubleshooting

### “main thread is not in main loop”
- Cause: Tkinter UI updates were called before the main loop started.
- Fix: Ensure initial rendering happens via `root.after(...)` and always call `root.mainloop()` after creating the window.

### “Sprites won’t load / stall in early Kanto”
- Check your network; sprites/artwork are fetched on demand.
- Keep concurrent loads low (e.g., 4–6) and update image widgets via `root.after(...)` to avoid thread‑UI conflicts.
- Prioritize visible items only; defer offscreen work.

### "Trackpad scrolling doesn't work"
- The app currently binds `<MouseWheel>`; on some Linux setups you may need `<Button-4/5>`.
- If needed, add additional bindings in `main_app.py` where the scroll handler is attached in the `_create_main_area()` method.

### “Checkbox isn’t visible on dark cards”
- Ensure checkbox text/fg colors contrast against the card background.

---

## 🗂 Project Structure

> **🎉 Recently Refactored!** This project was successfully refactored from a single 956-line file into a clean, modular architecture following modern Python best practices.

**Current modular structure**:
```
main.py                    # Main entry point with keyboard shortcuts
main_app.py               # PokemonTracker main application class
models.py                 # Pokemon dataclass, enums (Mode, Region, ViewFilter)
database.py               # Names/slugs cache, PokéAPI interactions, fallbacks
managers.py               # LazyLoadSpriteManager and DataManager
dialogs.py                # Quick search dialog
constants.py              # Application constants and configuration
requirements.txt          # Dependencies
pokemon_tracker.py        # Legacy single-file version (still functional)
pokemon_names_cache.json  # Cached Pokemon names from PokéAPI
pokemon_tracker_data.json # Saved capture progress
```

### Module Responsibilities

- **`main.py`**: Entry point with keyboard shortcuts and app initialization
- **`main_app.py`**: Main application UI logic, event handlers, and display management
- **`models.py`**: Data models (Pokemon, Mode, Region, ViewFilter enums)
- **`database.py`**: Pokemon name/slug management and PokéAPI integration
- **`managers.py`**: Sprite loading/caching and data persistence
- **`dialogs.py`**: UI dialogs (quick search)
- **`constants.py`**: Centralized configuration and constants

### Refactoring Benefits

✅ **Maintainability** - Easy to locate and modify specific functionality  
✅ **Testability** - Individual components can be unit tested  
✅ **Reusability** - Components can be imported into other projects  
✅ **Scalability** - Simple to extend without cluttering existing code  
✅ **Collaboration** - Multiple developers can work on different modules  
✅ **Debugging** - Easier to isolate and fix issues

---

## 🧭 Roadmap

**Completed ✅**
- ✅ Quick search (name/#) and on‑demand name refresh  
- ✅ Normal/Shiny capture tracking  
- ✅ CSV export
- ✅ **Modular architecture** - Refactored from single 956-line file into clean, maintainable modules
- ✅ **Modern Python structure** - Proper separation of concerns, type hints, and documentation

**Planned 🚀**
- [ ] Improved regional‑form artwork resolution (`-alola`, `-galar`, `-hisui`) with caching
- [ ] Bulk import/export of capture state
- [ ] Theme switcher (dark/light)
- [ ] Configurable data path (e.g., `~/.pokedext/`)
- [ ] Unit tests for models/data/sprites
- [ ] Package for easier distribution (PyPI/executable)

---

## 🙌 Contributing

PRs welcome!  
If you’re fixing a UI/perf issue, a short screen capture or clear repro steps help a ton.

1. Fork the repo & create a branch
2. Make your change with clear commits
3. Open a PR with context (what/why + screenshots if visual)

---

## 📜 License

This project is licensed under the **MIT License**.  
See [LICENSE](./LICENSE) for details.

---

## 💬 Acknowledgments

- **PokéAPI** for names, slugs, and artwork endpoints  
- **CustomTkinter** for a modern Tk UI  
- **Pillow** for image handling

---

## 📸 Screenshots

> Add screenshots/GIFs to `./assets` and link them here.

| National view | Search dialog | CSV export |
|---|---|---|
| ![s1](./assets/screenshot-1.png) | ![s2](./assets/screenshot-2.png) | ![s3](./assets/screenshot-3.png) |

---

> ⭐ If this project helps you track your Pokédex faster, consider starring the repo!
