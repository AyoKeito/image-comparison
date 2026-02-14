"""Main application class with dependency injection for Image Comparison."""

import sys
from pathlib import Path
from typing import Optional

from PyQt5.QtWidgets import QApplication, QMessageBox

from commands import CommandManager
from config import AppConfig
from exceptions import FolderValidationError, ImageComparisonError, UserCancelledError
from file_operations import FileOperationHandler
from folder_validation import validate_image_folder
from image_manager import ImageManager
from image_processor import ImageProcessor
from logger import logger
from ui_widget import ImageComparisonWidget, FolderSelectionDialog


class Application:
    """Main application class that wires together all components."""

    EXIT_SUCCESS = 0
    EXIT_USER_CANCELLED = 2
    EXIT_VALIDATION_FAILURE = 3
    EXIT_UNEXPECTED_ERROR = 4
    
    def __init__(self, config: AppConfig, initial_folder: Optional[Path] = None):
        self.config = config
        self.initial_folder = initial_folder
        self.logger = logger
        
        # Components (will be initialized in create_components)
        self.qt_app: Optional[QApplication] = None
        self.file_handler: Optional[FileOperationHandler] = None
        self.image_processor: Optional[ImageProcessor] = None
        self.command_manager: Optional[CommandManager] = None
        self.image_manager: Optional[ImageManager] = None
        self.ui_widget: Optional[ImageComparisonWidget] = None
    
    def create_components(self):
        """Create and wire together all application components."""
        
        # Create Qt application
        self.qt_app = QApplication(sys.argv)
        self.qt_app.setApplicationName("Image Comparison")
        self.qt_app.setApplicationVersion("2.0.0")
        
        # Create core components
        self.file_handler = FileOperationHandler(self.config)
        self.image_processor = ImageProcessor(self.config)
        self.command_manager = CommandManager()
        
        # Validate and get folder path
        folder_path = self._get_validated_folder()
        
        # Create image manager with validated folder
        self.image_manager = ImageManager(
            folder_path, self.config, self.file_handler
        )
        
        # Create UI widget
        self.ui_widget = ImageComparisonWidget(
            self.image_manager, self.image_processor, 
            self.file_handler, self.command_manager, self.config
        )
        
    
    def _get_validated_folder(self) -> Path:
        """Get and validate the folder path, with user interaction if needed."""
        if self.initial_folder:
            try:
                return validate_image_folder(self.initial_folder, self.file_handler)
            except FolderValidationError as error:
                self.logger.warning(str(error))
            except Exception as error:
                self.logger.error(f"Error validating folder {self.initial_folder}: {error}")

        # If we reach here, we need to prompt user for folder
        return self._prompt_for_folder()
    
    def _prompt_for_folder(self) -> Path:
        """Prompt user to select a valid folder.

        Raises:
            UserCancelledError: If the user cancels folder selection.
            FolderValidationError: If a valid folder is not selected within max attempts.
        """
        max_attempts = self.config.max_folder_validation_attempts
        attempts = 0

        while attempts < max_attempts:
            folder_path = FolderSelectionDialog.select_folder(
                title="Select Image Folder"
            )

            if not folder_path:
                # Bubble up cancellation so the entrypoint can decide process exit behavior.
                raise UserCancelledError("Folder selection was cancelled by the user")
            
                # User cancelled
                sys.exit(0)

            try:
                return validate_image_folder(folder_path, self.file_handler)
            except FolderValidationError as error:
                self.logger.warning(str(error))
                self._show_warning(str(error))
            except Exception as error:
                self.logger.error(f"Error validating selected folder: {error}")
                self._show_error(f"Error accessing folder: {error}")

            attempts += 1

        # If we reach here, user failed to select valid folder
        raise FolderValidationError(f"Failed to select valid folder after {max_attempts} attempts")
    
    def _show_error(self, message: str):
        """Show error message to user."""
        QMessageBox.critical(None, "Error", f"{message}\n\nCheck error.log for details.")
    
    def _show_warning(self, message: str):
        """Show warning message to user.""" 
        QMessageBox.warning(None, "Warning", message)
    
    def _show_info(self, message: str):
        """Show info message to user."""
        QMessageBox.information(None, "Information", message)
    
    def run(self) -> int:
        """Run the application and return deterministic exit codes."""
        try:
            self.create_components()

            # Show UI
            if self.config.window_fullscreen:
                self.ui_widget.showMaximized()
            else:
                self.ui_widget.show()

            # Print instructions to console
            self._print_instructions()

            # Run Qt event loop and normalize exit status to deterministic codes
            qt_exit_code = self.qt_app.exec_()
            if qt_exit_code == 0:
                return self.EXIT_SUCCESS

            self.logger.error(f"Qt event loop exited with code {qt_exit_code}")
            return self.EXIT_UNEXPECTED_ERROR

        except UserCancelledError as e:
            self.logger.info(str(e))
            return self.EXIT_USER_CANCELLED

        except FolderValidationError as e:
            self.logger.error(f"Folder validation failed: {e}")
            self._show_error(f"Folder validation failed: {e}")
            return self.EXIT_VALIDATION_FAILURE

        except ImageComparisonError as e:
            self.logger.error(f"Application error: {e}")
            self._show_error(f"Application error: {e}")
            return self.EXIT_UNEXPECTED_ERROR

        except Exception as e:
            self.logger.critical(f"Unexpected error: {e}", exc_info=True)
            self._show_error(f"Unexpected error: {e}")
            return self.EXIT_UNEXPECTED_ERROR

        finally:
            self._cleanup()
    
    def _print_instructions(self):
        """Print usage instructions to console."""
        print("\n" + "="*50)
        print("Image Comparison - Instructions")
        print("="*50)
        print("W or UP ARROW    : Keep both images")
        print("A or LEFT ARROW  : Discard left image")  
        print("D or RIGHT ARROW : Discard right image")
        print("S or DOWN ARROW  : Discard both images")
        print("U                : Undo last discard")
        print("="*50)
        print("Discarded images are moved to 'discarded' subfolder")
        print("All operations are logged to 'error.log'")
        print("="*50 + "\n")
    
    def _cleanup(self):
        """Clean up application resources."""
        try:
            if self.image_processor:
                self.image_processor.clear_cache()
            
            if self.command_manager:
                self.command_manager.clear_history()
            
            if self.config:
                self.config.save_to_file()  # Save any config changes
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
    
    @classmethod
    def create_from_args(cls, folder_path: Optional[str] = None) -> 'Application':
        """
        Create application instance from command line arguments.
        
        Args:
            folder_path: Optional folder path from command line
            
        Returns:
            Configured Application instance
        """
        # Load configuration
        config = AppConfig.load_from_file()
        
        # Convert folder path to Path object if provided
        initial_folder = Path(folder_path) if folder_path else None
        
        return cls(config, initial_folder)
    
    def get_statistics(self) -> dict:
        """Get current application statistics."""
        stats = {"app_initialized": False}
        
        if self.image_manager:
            stats.update(self.image_manager.get_statistics())
            stats["app_initialized"] = True
        
        if self.image_processor:
            stats["cache_info"] = self.image_processor.get_cache_info()
        
        if self.command_manager:
            stats["command_history_size"] = self.command_manager.get_history_size()
            stats["can_undo"] = self.command_manager.can_undo()
        
        return stats