"""Custom exception hierarchy for Image Comparison application."""

from typing import Optional


class ImageComparisonError(Exception):
    """Base exception for all Image Comparison application errors."""
    
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(message)
        self.original_error = original_error
        self.message = message
    
    def __str__(self):
        if self.original_error:
            return f"{self.message} (caused by: {self.original_error})"
        return self.message


class FolderValidationError(ImageComparisonError):
    """Raised when folder validation fails."""
    pass


class UserCancelledError(ImageComparisonError):
    """Raised when the user cancels an interactive workflow."""
    pass


class ImageLoadError(ImageComparisonError):
    """Raised when image loading fails."""
    
    def __init__(self, image_path: str, message: str = None, original_error: Exception = None):
        self.image_path = image_path
        if message is None:
            message = f"Failed to load image: {image_path}"
        super().__init__(message, original_error)


class FileOperationError(ImageComparisonError):
    """Raised when file operations fail."""
    
    def __init__(self, operation: str, source_path: str, target_path: str = None, 
                 message: str = None, original_error: Exception = None):
        self.operation = operation
        self.source_path = source_path
        self.target_path = target_path
        
        if message is None:
            if target_path:
                message = f"Failed to {operation} '{source_path}' to '{target_path}'"
            else:
                message = f"Failed to {operation} '{source_path}'"
        
        super().__init__(message, original_error)


class CacheError(ImageComparisonError):
    """Raised when cache operations fail."""
    pass


class ConfigurationError(ImageComparisonError):
    """Raised when configuration is invalid."""
    pass


class InsufficientImagesError(ImageComparisonError):
    """Raised when there are not enough images to compare."""
    
    def __init__(self, available_count: int, required_count: int = 2):
        self.available_count = available_count
        self.required_count = required_count
        message = f"Insufficient images for comparison: {available_count} available, {required_count} required"
        super().__init__(message)