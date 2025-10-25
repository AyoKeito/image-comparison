# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python-based image comparison and sorting tool that displays pairs of random images for user evaluation. The main purpose is to help users curate image collections by discarding unwanted images through a minimal UI.

The project has been completely refactored from a monolithic architecture to a modular, maintainable design following SOLID principles.

## Architecture

### Refactored Modular Architecture (v2.0)

**Core Modules:**
- **`main.py`**: New entry point with proper argument parsing
- **`application.py`**: Main application class with dependency injection
- **`config.py`**: Configuration management with JSON persistence  
- **`exceptions.py`**: Custom exception hierarchy for structured error handling
- **`logger.py`**: Centralized logging system with file and console output

**Business Logic:**
- **`image_manager.py`**: Core business logic with observer pattern
  - `ImageManager` class: Manages image pairs and statistics
  - `ImagePair` dataclass: Type-safe image pair representation
  - Observer pattern for UI updates
  - Strategy pattern for image selection (random/sequential)

**File Operations:**
- **`file_operations.py`**: Atomic file operations with conflict resolution
  - Handles move/restore operations safely
  - Automatic filename conflict resolution with counters
  - Comprehensive error handling

**Image Processing:**
- **`image_processor.py`**: Image processing with LRU caching
  - Efficient memory management with configurable cache size
  - Proper aspect ratio preservation
  - PIL to QImage conversion

**Command System:**
- **`commands.py`**: Command pattern for robust undo functionality
  - `DiscardImageCommand`: Single image discard with undo
  - `DiscardMultipleImagesCommand`: Batch operations
  - `CommandManager`: History management with size limits

**User Interface:**
- **`ui_widget.py`**: Clean UI widget with separation of concerns
  - Observer pattern for automatic updates
  - Proper error dialog handling
  - Keyboard input management

### Legacy Architecture (batch_sorter.py)

- **batch_sorter.py**: Original monolithic implementation (400+ lines)
- Still functional for backward compatibility
- Contains all original bugs that were fixed in the refactored version

## Running the Application

### Windows (Recommended)
```bash
batch_sorter.bat
```
The batch file automatically:
- Creates virtual environment if needed
- Installs dependencies (pillow, pyqt5)
- **Now runs the refactored version (`main.py`)**

### Direct Execution
```bash
# Refactored version (recommended)
python main.py [FOLDER_PATH]

# Legacy version  
python batch_sorter.py [FOLDER_PATH]
```

## Configuration

The refactored version uses `config.json` for persistent configuration:
```json
{
  "divider_color": "#404040",
  "padding": 40,
  "supported_extensions": [".png", ".jpg", ".webp", ".jpeg"],
  "background_color": "#202020", 
  "text_color": "white",
  "max_cache_size": 100,
  "max_filename_conflicts": 1000,
  "window_fullscreen": true
}
```

## Key Improvements in v2.0

**Architecture:**
- Separation of concerns - each class has single responsibility
- Dependency injection for loose coupling
- Observer pattern for UI updates  
- Command pattern for robust undo
- Strategy pattern for extensibility

**Error Handling:**
- Custom exception hierarchy with context
- Structured error messages with original cause tracking
- Graceful degradation for non-critical failures

**Performance:**
- LRU cache with configurable size limits
- Atomic file operations prevent race conditions
- Efficient window resize without disk I/O

**Maintainability:**
- Type hints throughout codebase
- Comprehensive logging with different levels
- Configuration management with persistence
- Modular design for easy testing

## Dependencies

- **pillow**: Image processing and format support
- **pyqt5**: GUI framework for the interface

Dependencies are automatically managed by `batch_sorter.bat` in a local `venv/` directory.

## Controls

- **A/Left Arrow**: Discard left image
- **D/Right Arrow**: Discard right image  
- **W/Up Arrow**: Keep both images (skip)
- **S/Down Arrow**: Discard both images
- **U**: Undo last discard action

## Error Handling

**Refactored Version:**
- Structured exception hierarchy with context
- Comprehensive logging to `error.log` with detailed tracebacks
- User-friendly error dialogs with actionable information
- Automatic recovery from non-critical failures

**Legacy Version:**
- Basic error logging to `error.log`
- Critical error popups
- Limited error recovery

## Development

**Testing the refactored modules:**
```bash
# Test core imports
./venv/Scripts/python.exe -c "import config, exceptions, logger"

# Test business logic  
./venv/Scripts/python.exe -c "import image_manager, file_operations"

# Test UI components
./venv/Scripts/python.exe -c "import ui_widget, application"
```

**Key files for development:**
- Modify `config.py` for new configuration options
- Extend `exceptions.py` for new error types
- Add new commands in `commands.py` for additional features
- Implement new selection strategies in `image_manager.py`