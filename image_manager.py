"""Business logic manager for Image Comparison application."""

import random
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Protocol, Tuple

from config import AppConfig
from exceptions import FolderValidationError, InsufficientImagesError
from file_operations import FileOperationHandler
from logger import logger


@dataclass
class ImagePair:
    """Represents a pair of images for comparison."""
    image1_path: Path
    image2_path: Path
    
    def __post_init__(self):
        """Validate image paths after initialization."""
        if not self.image1_path.exists():
            raise FileNotFoundError(f"Image 1 does not exist: {self.image1_path}")
        if not self.image2_path.exists():
            raise FileNotFoundError(f"Image 2 does not exist: {self.image2_path}")


class ImageManagerObserver(Protocol):
    """Observer protocol for ImageManager events."""
    
    def on_images_updated(self, available_count: int, discarded_count: int, loop_count: int):
        """Called when image counts are updated."""
        pass
    
    def on_comparison_completed(self, remaining_images: List[Path]):
        """Called when comparison process is completed."""
        pass


class ImageSelectionStrategy(ABC):
    """Abstract strategy for selecting images."""
    
    @abstractmethod
    def select_pair(self, available_images: List[Path]) -> Tuple[Path, Path]:
        """Select a pair of images from the available list."""
        pass


class RandomImageSelection(ImageSelectionStrategy):
    """Random selection strategy."""
    
    def select_pair(self, available_images: List[Path]) -> Tuple[Path, Path]:
        """Select two random images from the list."""
        if len(available_images) < 2:
            raise InsufficientImagesError(len(available_images))
        
        selected = random.sample(available_images, 2)
        return selected[0], selected[1]


class SequentialImageSelection(ImageSelectionStrategy):
    """Sequential selection strategy (for testing)."""
    
    def __init__(self):
        self._index = 0
    
    def select_pair(self, available_images: List[Path]) -> Tuple[Path, Path]:
        """Select the next sequential pair of images."""
        if len(available_images) < 2:
            raise InsufficientImagesError(len(available_images))
        
        # Reset if we've gone past the available images
        if self._index >= len(available_images) - 1:
            self._index = 0
        
        image1 = available_images[self._index]
        image2 = available_images[self._index + 1]
        self._index += 2
        
        return image1, image2


class ImageManager:
    """Manages the core business logic for image comparison."""
    
    def __init__(self, folder_path: Path, config: AppConfig, 
                 file_handler: FileOperationHandler, 
                 selection_strategy: Optional[ImageSelectionStrategy] = None):
        self.config = config
        self.file_handler = file_handler
        self.logger = logger
        
        # Initialize folder and validate
        self.source_folder = self._validate_and_set_folder(folder_path)
        
        # Image management
        self.available_images: List[Path] = []
        self.current_pair: Optional[ImagePair] = None
        
        # Statistics
        self.discarded_count = 0
        self.loop_count = 0
        
        # Strategy for image selection
        self.selection_strategy = selection_strategy or RandomImageSelection()
        
        # Observer pattern
        self.observers: List[ImageManagerObserver] = []
        
        # Initialize available images
        self.refresh_available_images()
    
    def add_observer(self, observer: ImageManagerObserver):
        """Add an observer to receive updates."""
        self.observers.append(observer)
    
    def remove_observer(self, observer: ImageManagerObserver):
        """Remove an observer."""
        if observer in self.observers:
            self.observers.remove(observer)
    
    def _notify_images_updated(self):
        """Notify observers that image counts have been updated."""
        for observer in self.observers:
            observer.on_images_updated(
                len(self.available_images), 
                self.discarded_count, 
                self.loop_count
            )
    
    def _notify_comparison_completed(self):
        """Notify observers that comparison is completed."""
        for observer in self.observers:
            observer.on_comparison_completed(self.available_images.copy())
    
    def _validate_and_set_folder(self, folder_path: Optional[Path]) -> Path:
        """Validate and set the source folder."""
        attempts = 0
        
        while attempts < self.config.max_folder_validation_attempts:
            if folder_path and folder_path.exists() and folder_path.is_dir():
                # Check if folder contains images
                try:
                    image_files = self.file_handler.get_image_files(folder_path)
                    if image_files:
                        self.logger.info(f"Using folder: {folder_path}")
                        return folder_path
                    else:
                        self.logger.warning(f"Folder contains no images: {folder_path}")
                except Exception as e:
                    self.logger.error(f"Error accessing folder {folder_path}: {e}")
            
            # Folder is invalid, need to prompt user
            # In CLI version, this would exit with error
            # In GUI version, this would show folder selection dialog
            attempts += 1
            folder_path = None  # Force re-selection
        
        raise FolderValidationError(
            f"Failed to validate folder after {self.config.max_folder_validation_attempts} attempts"
        )
    
    def refresh_available_images(self):
        """Refresh the list of available images from the source folder."""
        try:
            all_images = self.file_handler.get_image_files(self.source_folder)
            
            # Exclude current pair if they still exist
            self.available_images = []
            for img in all_images:
                if (not self.current_pair or 
                    (img != self.current_pair.image1_path and 
                     img != self.current_pair.image2_path)):
                    self.available_images.append(img)
            
            # Shuffle for randomness
            random.shuffle(self.available_images)
            
            self.logger.debug(f"Refreshed: {len(self.available_images)} available images")
            self._notify_images_updated()
            
        except Exception as e:
            self.logger.error(f"Failed to refresh available images: {e}")
            raise
    
    def get_next_pair(self) -> Optional[ImagePair]:
        """
        Get the next pair of images for comparison.
        
        Returns:
            ImagePair if available, None if comparison is complete
        """
        # Check if we need to refresh the available images
        if len(self.available_images) < 2:
            self.refresh_available_images()
            self.loop_count += 1
        
        # Check for completion conditions
        total_images = len(self.file_handler.get_image_files(self.source_folder))
        
        if total_images < 2:
            self.logger.info("Comparison completed: less than 2 images remaining")
            self._notify_comparison_completed()
            return None
        
        if total_images == 2:
            # Special case: exactly 2 images left
            all_images = self.file_handler.get_image_files(self.source_folder)
            self.current_pair = ImagePair(all_images[0], all_images[1])
            self.logger.info("Final pair: exactly 2 images remaining")
            self._notify_comparison_completed()
            return self.current_pair
        
        # Get next pair using strategy
        try:
            image1, image2 = self.selection_strategy.select_pair(self.available_images)
            
            # Remove selected images from available list
            self.available_images.remove(image1)
            self.available_images.remove(image2)
            
            self.current_pair = ImagePair(image1, image2)
            self.logger.debug(f"Selected pair: {image1.name}, {image2.name}")
            
            return self.current_pair
            
        except InsufficientImagesError:
            self.logger.warning("Insufficient images for next pair")
            return None
    
    def discard_current_images(self, discard_left: bool = False, discard_right: bool = False, 
                             discard_both: bool = False) -> List[Path]:
        """
        Mark current images for discard based on user choice.
        
        Args:
            discard_left: Discard the left image
            discard_right: Discard the right image  
            discard_both: Discard both images
            
        Returns:
            List of image paths to be discarded
        """
        if not self.current_pair:
            self.logger.warning("No current pair to discard")
            return []
        
        to_discard = []
        
        if discard_both:
            to_discard = [self.current_pair.image1_path, self.current_pair.image2_path]
        elif discard_left:
            to_discard = [self.current_pair.image1_path]
        elif discard_right:
            to_discard = [self.current_pair.image2_path]
        
        if to_discard:
            self.discarded_count += len(to_discard)
            self.logger.debug(f"Marked for discard: {[img.name for img in to_discard]}")
            self._notify_images_updated()
        
        return to_discard
    
    def get_statistics(self) -> dict:
        """Get current statistics."""
        total_images = len(self.file_handler.get_image_files(self.source_folder))
        
        return {
            "total_images": total_images,
            "available_images": len(self.available_images),
            "discarded_count": self.discarded_count,
            "loop_count": self.loop_count,
            "current_pair": self.current_pair,
            "completion_ratio": (self.discarded_count / max(1, total_images + self.discarded_count))
        }
    
    def is_comparison_complete(self) -> bool:
        """Check if the comparison process is complete."""
        total_images = len(self.file_handler.get_image_files(self.source_folder))
        return total_images < 2
    
    def get_remaining_images(self) -> List[Path]:
        """Get list of all remaining images in the source folder."""
        return self.file_handler.get_image_files(self.source_folder)
    
    def reset_statistics(self):
        """Reset counters (useful for testing)."""
        self.discarded_count = 0
        self.loop_count = 0
        self._notify_images_updated()