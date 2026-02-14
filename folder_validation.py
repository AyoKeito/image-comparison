"""Folder validation utilities for image folders."""

from pathlib import Path

from exceptions import FolderValidationError
from file_operations import FileOperationHandler


def validate_image_folder(folder_path: Path, file_handler: FileOperationHandler) -> Path:
    """Validate that folder exists, is a directory, and contains supported images."""
    if not folder_path.exists():
        raise FolderValidationError(f"Folder does not exist: {folder_path}")

    if not folder_path.is_dir():
        raise FolderValidationError(f"Path is not a directory: {folder_path}")

    image_files = file_handler.get_image_files(folder_path)
    if not image_files:
        raise FolderValidationError(f"No supported images found in folder: {folder_path}")

    return folder_path
