"""File operations handler for Image Comparison application."""

import os
import shutil
from pathlib import Path
from typing import Tuple

from config import AppConfig
from exceptions import FileOperationError
from logger import logger


class FileOperationHandler:
    """Handles all file operations including moving, restoring, and conflict resolution."""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.logger = logger
    
    def move_to_discarded(self, image_path: Path, source_folder: Path) -> Tuple[Path, Path]:
        """
        Move an image to the discarded folder.
        
        Args:
            image_path: Path to the image file (can be absolute or relative)
            source_folder: Source folder containing the image
            
        Returns:
            Tuple of (target_path, original_source_path)
            
        Raises:
            FileOperationError: If the move operation fails
        """
        try:
            # Create discarded folder if it doesn't exist
            discarded_folder = source_folder / self.config.discarded_folder_name
            discarded_folder.mkdir(exist_ok=True)
            
            # Handle both absolute and relative paths
            if image_path.is_absolute():
                source_path = image_path
                base_name = image_path.name
            else:
                source_path = source_folder / image_path
                base_name = image_path.name
            
            # Ensure source file exists
            if not source_path.exists():
                raise FileOperationError(
                    "move", str(source_path), str(discarded_folder),
                    f"Source file does not exist: {source_path}"
                )
            
            # Handle filename conflicts by adding a counter
            target_path = discarded_folder / base_name
            target_path = self._resolve_filename_conflict(target_path)
            
            # Perform atomic move operation
            shutil.move(str(source_path), str(target_path))
            
            self.logger.debug(f"Moved {source_path} to {target_path}")
            return target_path, source_path
            
        except OSError as e:
            raise FileOperationError(
                "move", str(source_path), str(target_path),
                original_error=e
            )
    
    def restore_from_discarded(self, target_path: Path, original_source_path: Path):
        """
        Restore an image from the discarded folder.
        
        Args:
            target_path: Current path of the file in discarded folder
            original_source_path: Original path where file should be restored
            
        Raises:
            FileOperationError: If the restore operation fails
        """
        try:
            if not target_path.exists():
                raise FileOperationError(
                    "restore", str(target_path), str(original_source_path),
                    f"Discarded file does not exist: {target_path}"
                )
            
            # Check if destination already exists
            if original_source_path.exists():
                raise FileOperationError(
                    "restore", str(target_path), str(original_source_path),
                    f"Cannot restore: destination already exists: {original_source_path}"
                )
            
            # Perform atomic move operation
            shutil.move(str(target_path), str(original_source_path))
            
            self.logger.debug(f"Restored {target_path} to {original_source_path}")
            
        except OSError as e:
            raise FileOperationError(
                "restore", str(target_path), str(original_source_path),
                original_error=e
            )
    
    def _resolve_filename_conflict(self, target_path: Path) -> Path:
        """
        Resolve filename conflicts by adding a counter.
        
        Args:
            target_path: Desired target path
            
        Returns:
            Path with conflict resolved
            
        Raises:
            FileOperationError: If too many conflicts exist
        """
        if not target_path.exists():
            return target_path
        
        counter = 1
        stem = target_path.stem
        suffix = target_path.suffix
        parent = target_path.parent
        
        while counter <= self.config.max_filename_conflicts:
            new_path = parent / f"{stem}_{counter}{suffix}"
            if not new_path.exists():
                return new_path
            counter += 1
        
        raise FileOperationError(
            "resolve_conflict", str(target_path),
            message=f"Too many filename conflicts for {target_path.name}"
        )
    
    def get_image_files(self, folder_path: Path) -> list[Path]:
        """
        Get list of supported image files from a folder.
        
        Args:
            folder_path: Path to the folder to scan
            
        Returns:
            List of image file paths
            
        Raises:
            FileOperationError: If folder cannot be accessed
        """
        try:
            if not folder_path.exists() or not folder_path.is_dir():
                raise FileOperationError(
                    "list_files", str(folder_path),
                    message=f"Invalid folder path: {folder_path}"
                )
            
            supported_exts = self.config.get_normalized_extensions()
            
            image_files = []
            for file_path in folder_path.iterdir():
                if (file_path.is_file() and 
                    any(file_path.name.lower().endswith(ext) for ext in supported_exts)):
                    image_files.append(file_path)
            
            self.logger.debug(f"Found {len(image_files)} image files in {folder_path}")
            return image_files
            
        except OSError as e:
            raise FileOperationError(
                "list_files", str(folder_path),
                original_error=e
            )