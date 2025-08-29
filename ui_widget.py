"""Refactored UI widget for Image Comparison application."""

from pathlib import Path
from typing import Optional, Tuple

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import (QApplication, QHBoxLayout, QLabel, QMessageBox, 
                           QVBoxLayout, QWidget, QFileDialog)
from PIL import Image

from commands import CommandManager, DiscardImageCommand, DiscardMultipleImagesCommand
from config import AppConfig
from exceptions import ImageLoadError, FileOperationError, FolderValidationError
from file_operations import FileOperationHandler
from image_manager import ImageManager, ImageManagerObserver, ImagePair
from image_processor import ImageProcessor
from logger import logger


class ImageComparisonWidget(QWidget):
    """Main UI widget for image comparison with clean separation of concerns."""
    
    def __init__(self, image_manager: ImageManager, image_processor: ImageProcessor,
                 file_handler: FileOperationHandler, command_manager: CommandManager,
                 config: AppConfig):
        super().__init__()
        
        # Dependencies
        self.image_manager = image_manager
        self.image_processor = image_processor
        self.file_handler = file_handler
        self.command_manager = command_manager
        self.config = config
        self.logger = logger
        
        # Register as observer
        self.image_manager.add_observer(self)
        
        # UI Components
        self.image_labels = [QLabel(self) for _ in range(2)]
        self.info_labels = [QLabel(self) for _ in range(2)]
        self.current_pair: Optional[ImagePair] = None
        
        # Initialize UI
        self._setup_ui()
        self._apply_theme()
        self._set_window_geometry()
        
        # Load first pair
        self._load_next_pair()
    
    def _setup_ui(self):
        """Initialize the user interface."""
        # Configure image labels
        for label in self.image_labels:
            label.setAlignment(Qt.AlignCenter)
            label.setMinimumSize(400, 300)
        
        # Configure info labels
        for label in self.info_labels:
            label.setAlignment(Qt.AlignCenter)
            label.setWordWrap(True)
            label.setMaximumHeight(60)
        
        # Create layouts
        main_layout = QVBoxLayout()
        image_layout = QHBoxLayout()
        info_layout = QHBoxLayout()
        
        # Add image labels to horizontal layout
        for label in self.image_labels:
            image_layout.addWidget(label, 1)
        
        # Add info labels to horizontal layout
        for label in self.info_labels:
            info_layout.addWidget(label, 1)
        
        main_layout.addLayout(image_layout)
        main_layout.addLayout(info_layout)
        self.setLayout(main_layout)
        
        # Set window properties
        self.setWindowTitle('Image Comparison')
        self.setFocusPolicy(Qt.StrongFocus)
    
    def _apply_theme(self):
        """Apply the dark theme to the widget."""
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {self.config.background_color};
                color: {self.config.text_color};
            }}
            QLabel {{
                border: 1px solid #555;
                margin: 2px;
            }}
        """)
    
    def _set_window_geometry(self):
        """Set window size and position."""
        if self.config.window_fullscreen:
            screen = QApplication.primaryScreen().geometry()
            self.setGeometry(0, 0, screen.width(), screen.height())
        else:
            self.resize(1200, 800)
    
    def paintEvent(self, event):
        """Draw the divider between images."""
        painter = QPainter(self)
        pen = QPen(QColor(self.config.divider_color), 4, Qt.SolidLine)
        painter.setPen(pen)
        
        center_x = self.width() // 2
        painter.drawLine(center_x, 0, center_x, self.height())
    
    def resizeEvent(self, event):
        """Handle window resize by updating image display."""
        super().resizeEvent(event)
        if self.current_pair:
            self._update_image_displays()
        self.update()  # Trigger repaint for divider
    
    def keyPressEvent(self, event):
        """Handle keyboard input for image management."""
        key = event.key()
        
        # Define key mappings
        key_actions = {
            Qt.Key_A: 'discard_left',
            Qt.Key_Left: 'discard_left',
            Qt.Key_D: 'discard_right', 
            Qt.Key_Right: 'discard_right',
            Qt.Key_S: 'discard_both',
            Qt.Key_Down: 'discard_both',
            Qt.Key_W: 'keep_both',
            Qt.Key_Up: 'keep_both',
            Qt.Key_U: 'undo',
        }
        
        action = key_actions.get(key)
        if action:
            self._handle_action(action)
        else:
            event.ignore()
    
    def _handle_action(self, action: str):
        """Handle user actions."""
        try:
            if action == 'undo':
                self._handle_undo()
            elif action == 'keep_both':
                self._handle_keep_both()
            elif action in ['discard_left', 'discard_right', 'discard_both']:
                self._handle_discard(action)
        except Exception as e:
            self.logger.error(f"Error handling action {action}: {e}")
            self._show_error_dialog(f"Error: {e}")
    
    def _handle_discard(self, action: str):
        """Handle image discard actions."""
        if not self.current_pair:
            return
        
        # Determine which images to discard
        discard_left = action in ['discard_left', 'discard_both']
        discard_right = action in ['discard_right', 'discard_both']
        
        # Get images to discard from manager
        to_discard = self.image_manager.discard_current_images(
            discard_left=discard_left,
            discard_right=discard_right,
            discard_both=(action == 'discard_both')
        )
        
        if not to_discard:
            return
        
        # Create and execute command
        if len(to_discard) == 1:
            command = DiscardImageCommand(
                to_discard[0], self.image_manager.source_folder,
                self.file_handler, self.image_processor
            )
        else:
            command = DiscardMultipleImagesCommand(
                to_discard, self.image_manager.source_folder,
                self.file_handler, self.image_processor
            )
        
        try:
            self.command_manager.execute_command(command)
            self._load_next_pair()
        except FileOperationError as e:
            self.logger.error(f"Failed to discard images: {e}")
            self._show_error_dialog(f"Failed to discard images: {e}")
    
    def _handle_keep_both(self):
        """Handle keep both images action."""
        self._load_next_pair()
    
    def _handle_undo(self):
        """Handle undo action."""
        if self.command_manager.undo_last_command():
            # Refresh the current view
            self._load_next_pair()
        else:
            self._show_info_dialog("Nothing to undo")
    
    def _load_next_pair(self):
        """Load the next pair of images for comparison."""
        try:
            next_pair = self.image_manager.get_next_pair()
            
            if next_pair is None:
                self._handle_completion()
                return
            
            self.current_pair = next_pair
            self._update_image_displays()
            
        except Exception as e:
            self.logger.error(f"Failed to load next pair: {e}")
            self._show_error_dialog(f"Failed to load images: {e}")
    
    def _update_image_displays(self):
        """Update the display of both images."""
        if not self.current_pair:
            return
        
        # Calculate display dimensions
        available_width = (self.width() - 2 * self.config.padding) // 2
        available_height = self.height() - 2 * self.config.padding
        
        # Load and display each image, comparing resolutions
        images = [self.current_pair.image1_path, self.current_pair.image2_path]
        dimensions = []
        
        # Get dimensions for both images first
        for image_path in images:
            dimensions.append(self._get_image_dimensions(image_path))
        
        # Calculate pixel counts and determine which is higher
        pixel_counts = [w * h for w, h in dimensions]
        higher_res_index = 0 if pixel_counts[0] > pixel_counts[1] else 1 if pixel_counts[1] > pixel_counts[0] else -1
        
        # Display images and info with highlighting
        for i, image_path in enumerate(images):
            self._update_single_image_display(image_path, self.image_labels[i], 
                                            available_width, available_height)
            is_higher_res = (i == higher_res_index and pixel_counts[0] != pixel_counts[1])
            self._update_image_info(image_path, self.info_labels[i], is_higher_res)
    
    def _update_single_image_display(self, image_path: Path, label: QLabel, 
                                   max_width: int, max_height: int):
        """Update the display of a single image."""
        try:
            pixmap = self.image_processor.load_and_cache(
                image_path, max_width, max_height
            )
            
            label.setMaximumSize(max_width, max_height)
            label.setPixmap(pixmap)
            
        except ImageLoadError as e:
            self.logger.error(f"Failed to display image {image_path}: {e}")
            # Show error placeholder
            label.setText(f"Error loading\n{image_path.name}")
    
    def _get_image_dimensions(self, image_path: Path) -> Tuple[int, int]:
        """Get the dimensions of an image file."""
        try:
            with Image.open(image_path) as img:
                return img.size
        except Exception as e:
            self.logger.error(f"Failed to get dimensions for {image_path}: {e}")
            return (0, 0)
    
    def _update_image_info(self, image_path: Path, info_label: QLabel, is_higher_res: bool = False):
        """Update the info display for a single image."""
        try:
            width, height = self._get_image_dimensions(image_path)
            info_text = f"{image_path.name}: {width} × {height}"
            info_label.setText(info_text)
            
            # Apply green highlighting for higher resolution
            if is_higher_res:
                info_label.setStyleSheet("color: #00ff00; font-weight: bold;")
            else:
                info_label.setStyleSheet(f"color: {self.config.text_color};")
                
        except Exception as e:
            self.logger.error(f"Failed to update info for {image_path}: {e}")
            info_label.setText(f"{image_path.name}: Dimensions unknown")
            info_label.setStyleSheet(f"color: {self.config.text_color};")
    
    def _handle_completion(self):
        """Handle completion of the comparison process."""
        remaining_images = self.image_manager.get_remaining_images()
        
        if len(remaining_images) == 0:
            self._show_completion_dialog("All images processed!")
        elif len(remaining_images) == 1:
            self._show_completion_dialog(f"One image remaining: {remaining_images[0].name}")
        else:
            # This shouldn't happen, but handle gracefully
            self._show_completion_dialog(f"{len(remaining_images)} images remaining")
        
        self.close()
    
    def _show_error_dialog(self, message: str):
        """Show an error dialog to the user."""
        QMessageBox.critical(self, "Error", f"{message}\n\nCheck error.log for details.")
    
    def _show_info_dialog(self, message: str):
        """Show an info dialog to the user."""
        QMessageBox.information(self, "Info", message)
    
    def _show_completion_dialog(self, message: str):
        """Show a completion dialog to the user."""
        QMessageBox.information(self, "Comparison Complete", message)
    
    def closeEvent(self, event):
        """Handle widget close event."""
        # Clean up observer registration
        self.image_manager.remove_observer(self)
        event.accept()
    
    # Observer pattern methods
    def on_images_updated(self, available_count: int, discarded_count: int, loop_count: int):
        """Update window title with current statistics."""
        remaining_total = len(self.image_manager.get_remaining_images())
        self.setWindowTitle(
            f"Image Comparison | Remaining: {remaining_total} | "
            f"Discarded: {discarded_count} | Loop: {loop_count}"
        )
    
    def on_comparison_completed(self, remaining_images: list):
        """Handle completion notification."""
        if len(remaining_images) == 2:
            # Special case: show final two images
            self._show_info_dialog(
                f"Final two images remaining:\n{remaining_images[0].name}\n{remaining_images[1].name}"
            )


class FolderSelectionDialog:
    """Helper class for folder selection when validation fails."""
    
    @staticmethod
    def select_folder(parent=None, title="Select Image Folder") -> Optional[Path]:
        """Show folder selection dialog."""
        folder_str = QFileDialog.getExistingDirectory(parent, title)
        return Path(folder_str) if folder_str else None