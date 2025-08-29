# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python-based image comparison and sorting tool that displays pairs of random images for user evaluation. The main purpose is to help users curate image collections by discarding unwanted images through a minimal UI.

## Architecture

### Core Components

- **batch_sorter.py**: The main PyQt5 application that handles the image comparison interface
  - `ImageComparison` class: Main widget handling UI, image loading, and user interactions
  - `Config` enum: Configuration constants (colors, supported formats, etc.)
  - Image caching system for performance optimization
  - Undo functionality with stack-based history

### Key Features

- Displays two random images side by side with keyboard controls
- Moves discarded images to a `discarded/` subfolder (not deleted)
- Supports PNG, JPG, WEBP, JPEG formats
- Dark theme with customizable colors
- Comprehensive error logging to `error.log`
- Undo functionality (U key)

### File Operations

- Images are **moved** (not deleted) to `discarded/` subfolder
- All file operations are logged to terminal and `error.log`
- Handles duplicate filenames in discarded folder
- Validates folder paths and image availability

## Running the Application

### Windows (Recommended)
```bash
batch_sorter.bat
```
The batch file automatically:
- Creates a virtual environment if needed
- Installs dependencies (pillow, pyqt5)
- Runs the application

### Direct Python Execution
```bash
python batch_sorter.py [FOLDER_PATH]
```
- FOLDER_PATH is optional - file dialog appears if not provided or invalid
- No additional command-line flags supported

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

- All exceptions logged to `error.log` with timestamps
- Critical errors show popup dialogs
- Graceful handling of corrupted/unreadable images
- Automatic folder validation with user prompts