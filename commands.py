"""Command pattern implementation for undo functionality."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional

from file_operations import FileOperationHandler
from image_processor import ImageProcessor
from exceptions import FileOperationError
from logger import logger


class Command(ABC):
    """Abstract base class for all commands."""
    
    @abstractmethod
    def execute(self):
        """Execute the command."""
        pass
    
    @abstractmethod
    def undo(self):
        """Undo the command."""
        pass
    
    @abstractmethod
    def can_undo(self) -> bool:
        """Check if the command can be undone."""
        pass


class DiscardImageCommand(Command):
    """Command to discard an image by moving it to the discarded folder."""
    
    def __init__(self, image_path: Path, source_folder: Path, 
                 file_handler: FileOperationHandler, image_processor: ImageProcessor):
        self.image_path = image_path
        self.source_folder = source_folder
        self.file_handler = file_handler
        self.image_processor = image_processor
        self.target_path: Optional[Path] = None
        self.original_source_path: Optional[Path] = None
        self.executed = False
        self.logger = logger
    
    def execute(self):
        """Move the image to the discarded folder."""
        try:
            self.target_path, self.original_source_path = self.file_handler.move_to_discarded(
                self.image_path, self.source_folder
            )
            
            # Clear from image cache
            self.image_processor.clear_cache_entry(self.image_path)
            
            self.executed = True
            self.logger.info(f"Discarded image: {self.image_path.name}")
            
        except FileOperationError as e:
            self.logger.error(f"Failed to discard image {self.image_path}: {e}")
            raise
    
    def undo(self):
        """Restore the image from the discarded folder."""
        if not self.can_undo():
            raise FileOperationError(
                "undo", str(self.target_path) if self.target_path else "unknown",
                message="Cannot undo: command was not executed successfully"
            )
        
        try:
            self.file_handler.restore_from_discarded(
                self.target_path, self.original_source_path
            )
            
            # Reset state
            self.target_path = None
            self.original_source_path = None
            self.executed = False
            
            self.logger.info(f"Restored image: {self.image_path.name}")
            
        except FileOperationError as e:
            self.logger.error(f"Failed to restore image {self.image_path}: {e}")
            raise
    
    def can_undo(self) -> bool:
        """Check if the command can be undone."""
        return (self.executed and 
                self.target_path is not None and 
                self.original_source_path is not None and
                self.target_path.exists())


class DiscardMultipleImagesCommand(Command):
    """Command to discard multiple images as a single operation."""
    
    def __init__(self, image_paths: List[Path], source_folder: Path,
                 file_handler: FileOperationHandler, image_processor: ImageProcessor):
        self.image_paths = image_paths
        self.source_folder = source_folder
        self.file_handler = file_handler
        self.image_processor = image_processor
        self.discard_commands: List[DiscardImageCommand] = []
        self.logger = logger
    
    def execute(self):
        """Execute all discard commands."""
        self.discard_commands.clear()
        
        for image_path in self.image_paths:
            command = DiscardImageCommand(
                image_path, self.source_folder, 
                self.file_handler, self.image_processor
            )
            
            try:
                command.execute()
                self.discard_commands.append(command)
            except FileOperationError as e:
                self.logger.error(f"Failed to discard {image_path}: {e}")
                # Continue with other images
                continue
        
        self.logger.info(f"Discarded {len(self.discard_commands)} images")
    
    def undo(self):
        """Undo all discard commands in reverse order."""
        if not self.can_undo():
            raise FileOperationError(
                "undo", "multiple images",
                message="Cannot undo: no images were successfully discarded"
            )
        
        # Undo in reverse order
        restored_count = 0
        for command in reversed(self.discard_commands):
            try:
                command.undo()
                restored_count += 1
            except FileOperationError as e:
                self.logger.error(f"Failed to restore image: {e}")
                # Continue with other images
                continue
        
        self.discard_commands.clear()
        self.logger.info(f"Restored {restored_count} images")
    
    def can_undo(self) -> bool:
        """Check if at least one command can be undone."""
        return any(command.can_undo() for command in self.discard_commands)


class CommandManager:
    """Manages command execution and undo history."""
    
    def __init__(self, max_history_size: int = 50):
        self.max_history_size = max_history_size
        self.history: List[Command] = []
        self.logger = logger
    
    def execute_command(self, command: Command):
        """Execute a command and add it to history."""
        try:
            command.execute()
            
            # Add to history
            self.history.append(command)
            
            # Limit history size
            while len(self.history) > self.max_history_size:
                self.history.pop(0)
            
            self.logger.debug(f"Executed command: {type(command).__name__}")
            
        except Exception as e:
            self.logger.error(f"Failed to execute command {type(command).__name__}: {e}")
            raise
    
    def undo_last_command(self) -> bool:
        """
        Undo the last executed command.
        
        Returns:
            True if undo was successful, False if no command to undo
        """
        if not self.history:
            self.logger.debug("No commands to undo")
            return False
        
        # Find the last command that can be undone
        for i in range(len(self.history) - 1, -1, -1):
            command = self.history[i]
            if command.can_undo():
                try:
                    command.undo()
                    self.history.remove(command)
                    self.logger.debug(f"Undid command: {type(command).__name__}")
                    return True
                except Exception as e:
                    self.logger.error(f"Failed to undo command {type(command).__name__}: {e}")
                    # Remove failed command from history
                    self.history.remove(command)
                    return False
        
        self.logger.debug("No undoable commands found")
        return False
    
    def clear_history(self):
        """Clear the command history."""
        history_size = len(self.history)
        self.history.clear()
        self.logger.debug(f"Cleared command history of {history_size} commands")
    
    def get_history_size(self) -> int:
        """Get the current history size."""
        return len(self.history)
    
    def can_undo(self) -> bool:
        """Check if there are any undoable commands."""
        return any(command.can_undo() for command in self.history)