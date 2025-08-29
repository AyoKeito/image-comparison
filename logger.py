"""Improved logging system for Image Comparison application."""

import logging
import sys
from pathlib import Path
from typing import Optional


class AppLogger:
    """Centralized logging configuration for the application."""
    
    def __init__(self, log_file: Path = Path("error.log"), console_level: int = logging.INFO):
        self.log_file = log_file
        self.logger = logging.getLogger("ImageComparison")
        self.logger.setLevel(logging.DEBUG)
        
        # Clear any existing handlers
        self.logger.handlers.clear()
        
        # File handler for detailed logging
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        # Console handler for user feedback
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(console_level)
        
        # Formatter
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        simple_formatter = logging.Formatter(
            '%(levelname)s: %(message)s'
        )
        
        file_handler.setFormatter(detailed_formatter)
        console_handler.setFormatter(simple_formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        # Set up exception hook
        self._setup_exception_hook()
    
    def _setup_exception_hook(self):
        """Set up global exception handler."""
        def exception_hook(exc_type, exc_value, exc_traceback):
            if issubclass(exc_type, KeyboardInterrupt):
                # Allow Ctrl+C to work normally
                sys.__excepthook__(exc_type, exc_value, exc_traceback)
                return
                
            self.logger.critical(
                "Uncaught exception",
                exc_info=(exc_type, exc_value, exc_traceback)
            )
        
        sys.excepthook = exception_hook
    
    def get_logger(self) -> logging.Logger:
        """Get the configured logger instance."""
        return self.logger
    
    @classmethod
    def setup_global_logger(cls, log_file: Optional[Path] = None, 
                          console_level: int = logging.INFO) -> logging.Logger:
        """Set up the global application logger and return it."""
        if log_file is None:
            log_file = Path("error.log")
        
        app_logger = cls(log_file, console_level)
        return app_logger.get_logger()


# Global logger instance
logger = AppLogger.setup_global_logger()