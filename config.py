"""Configuration management for Image Comparison application."""

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Optional


@dataclass
class AppConfig:
    """Application configuration with default values and file persistence."""
    
    # UI Configuration
    divider_color: str = '#404040'
    padding: int = 40
    background_color: str = '#202020'
    text_color: str = 'white'
    
    # Image Configuration
    supported_extensions: List[str] = field(default_factory=lambda: ['.png', '.jpg', '.webp', '.jpeg'])
    max_cache_size: int = 100
    max_image_size: tuple = (1920, 1080)
    
    # File Operation Configuration
    max_filename_conflicts: int = 1000
    discarded_folder_name: str = "discarded"
    
    # Application Behavior
    max_folder_validation_attempts: int = 5
    window_fullscreen: bool = True
    
    @classmethod
    def load_from_file(cls, config_path: Optional[Path] = None) -> 'AppConfig':
        """Load configuration from JSON file, creating default if not found."""
        if config_path is None:
            config_path = Path("config.json")
            
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return cls(**data)
            except (json.JSONDecodeError, TypeError, ValueError) as e:
                # If config file is corrupted, use defaults and log warning
                print(f"Warning: Invalid config file {config_path}: {e}. Using defaults.")
        
        return cls()
    
    def save_to_file(self, config_path: Optional[Path] = None):
        """Save current configuration to JSON file."""
        if config_path is None:
            config_path = Path("config.json")
            
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(asdict(self), f, indent=2)
        except OSError as e:
            print(f"Warning: Could not save config to {config_path}: {e}")
    
    def get_normalized_extensions(self) -> List[str]:
        """Get supported extensions normalized to lowercase."""
        return [ext.lower() for ext in self.supported_extensions]