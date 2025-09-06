# 🌍 Planet Earth Pokeball Icon Guide

## Icon Design
The National Dex Tracker features a custom **planet earth-shaped pokeball icon** that perfectly represents the global nature of tracking a National Pokédex.

## Design Elements
- **🌍 Earth Colors**: Blue top (oceans), green bottom (continents)
- **⚪ Pokeball Features**: Black middle band, white center button
- **🗺️ Continents**: Small green landmasses representing earth
- **🎨 Vibrant Colors**: High contrast for visibility at all sizes

## Cross-Platform Support

### macOS 🍎
- **Format**: `.icns` (native macOS format)
- **Method**: PyObjC/Cocoa `NSApplication.setApplicationIconImage_()`
- **Display**: Appears in Dock and Cmd+Tab switcher
- **Quality**: High-resolution with Retina support

### Windows 🪟
- **Format**: `.ico` (multi-size Windows format)
- **Method**: tkinter `iconbitmap()` 
- **Display**: Window title bar, taskbar, Alt+Tab switcher
- **Quality**: 7 different icon sizes (16px to 256px)

### Linux 🐧
- **Format**: `.png` fallback via `iconphoto()`
- **Method**: tkinter `iconphoto()` with PNG
- **Display**: Depends on window manager
- **Quality**: 64x64 PNG with transparency

## File Structure
```
assets/
├── icon.icns          # macOS native (152KB, multiple resolutions)
├── icon.ico           # Windows native (25KB, 7 sizes) 
├── icon.png           # Cross-platform (4KB, 64x64)
├── icon_large.png     # Testing/preview (3KB, 256x256)
└── AppIcon.iconset/   # macOS iconset source (11 files)
    ├── icon_16x16.png
    ├── icon_16x16@2x.png
    ├── icon_32x32.png
    ├── icon_64x64@2x.png
    ├── icon_128x128.png
    ├── icon_128x128@2x.png
    ├── icon_256x256.png
    ├── icon_256x256@2x.png
    ├── icon_512x512.png
    ├── icon_1024x1024.png
    └── icon_8x8@2x.png
```

## Implementation Details

### Automatic Platform Detection
The app automatically detects the operating system and uses the best icon method:

```python
if platform.system() == 'Darwin':
    # macOS: Use Cocoa for proper dock icon
    app.setApplicationIconImage_(ns_image)
else:
    # Windows/Linux: Use tkinter methods
    root.iconbitmap('assets/icon.ico')
```

### Fallback Chain
Each platform has multiple fallback methods to ensure the icon always loads:

1. **Primary Method**: Platform-native format
2. **Secondary Method**: Cross-platform PNG
3. **Graceful Degradation**: App continues if icon fails

### Dependencies
- **macOS**: Requires `pyobjc-framework-Cocoa` (automatically installed)
- **Windows**: No additional dependencies needed
- **Linux**: Uses standard PIL/tkinter

## Testing
The icon has been tested and confirmed working on:
- ✅ **macOS 15.5** (Sequoia) - Dock icon via Cocoa
- ✅ **Windows** - ICO format with multi-size support
- ✅ **Linux** - PNG fallback method

## Troubleshooting

### macOS
- Icon appears in **Dock** and **Cmd+Tab**, not window title
- Requires PyObjC for proper dock icon display
- If dock icon doesn't appear, check Console.app for errors

### Windows  
- Icon appears in **window title**, **taskbar**, and **Alt+Tab**
- Uses native ICO format for best compatibility
- Should work on Windows 7, 10, 11

### Linux
- Icon display depends on window manager (GNOME, KDE, etc.)
- Uses PNG format via iconphoto()
- May require additional desktop integration packages
