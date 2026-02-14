"""Image processing and caching system for Image Comparison application."""

from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

from PIL import Image
from PyQt5.QtGui import QImage, QPixmap

from config import AppConfig
from exceptions import ImageLoadError
from logger import logger


@dataclass(frozen=True)
class CachedImageData:
    """Cached image data including renderable pixmap and original dimensions."""

    pixmap: QPixmap
    width: int
    height: int


class ImageProcessor:
    """Handles image loading, processing, and caching with LRU cache management."""

    def __init__(self, config: AppConfig):
        self.config = config
        self.logger = logger
        self._cache = OrderedDict()
        self._max_cache_size = config.max_cache_size

    def load_and_cache(self, image_path: Path, max_width: int, max_height: int) -> QPixmap:
        """
        Load an image, resize it, and cache the result.

        Args:
            image_path: Path to the image file
            max_width: Maximum width for resizing
            max_height: Maximum height for resizing

        Returns:
            QPixmap ready for display

        Raises:
            ImageLoadError: If image loading fails
        """
        pixmap, _, _ = self.load_with_metadata(image_path, max_width, max_height)
        return pixmap

    def load_with_metadata(
        self,
        image_path: Path,
        max_width: int,
        max_height: int,
    ) -> Tuple[QPixmap, int, int]:
        """Load an image and return a renderable pixmap with original dimensions."""
        cache_key = self._create_cache_key(image_path, max_width, max_height)

        if cache_key in self._cache:
            self.logger.debug(f"Cache hit for {image_path.name}")
            cached_data = self._cache.pop(cache_key)
            self._cache[cache_key] = cached_data
            return cached_data.pixmap, cached_data.width, cached_data.height

        try:
            cached_data = self._load_and_process_image(image_path, max_width, max_height)
            self._add_to_cache(cache_key, cached_data)
            self.logger.debug(f"Loaded and cached {image_path.name}")
            return cached_data.pixmap, cached_data.width, cached_data.height
        except Exception as e:
            raise ImageLoadError(str(image_path), original_error=e)

    def _load_and_process_image(
        self,
        image_path: Path,
        max_width: int,
        max_height: int,
    ) -> CachedImageData:
        """Load and process a single image."""
        try:
            with Image.open(image_path) as pil_image:
                rgb_image = pil_image.convert("RGB")
                width, height = rgb_image.size

                resized_image = self._resize_image(rgb_image, max_width, max_height)
                qimage = self._pil_to_qimage(resized_image)
                pixmap = QPixmap.fromImage(qimage)

                return CachedImageData(pixmap=pixmap, width=width, height=height)

        except OSError as e:
            raise ImageLoadError(str(image_path), "Failed to open image file", e)
        except Exception as e:
            raise ImageLoadError(str(image_path), "Failed to process image", e)

    def _resize_image(self, image: Image.Image, max_width: int, max_height: int) -> Image.Image:
        """
        Resize an image to maximize space usage while preserving aspect ratio.

        Args:
            image: PIL Image to resize
            max_width: Maximum width (target width for the available space)
            max_height: Maximum height (target height for the available space)

        Returns:
            Resized PIL Image that fills the available space
        """
        image_width, image_height = image.size

        if image_width == 0 or image_height == 0:
            self.logger.warning(f"Image has zero dimensions: {image_width}x{image_height}")
            return image

        if max_width <= 0 or max_height <= 0:
            self.logger.warning(f"Invalid max dimensions: {max_width}x{max_height}")
            return image

        scale_factor = min(max_width / image_width, max_height / image_height)

        new_width = max(1, int(image_width * scale_factor))
        new_height = max(1, int(image_height * scale_factor))

        if new_width != image_width or new_height != image_height:
            return image.resize((new_width, new_height), Image.LANCZOS)

        return image

    def _pil_to_qimage(self, pil_image: Image.Image) -> QImage:
        """Convert a PIL image to QImage."""
        rgba_image = pil_image.convert("RGBA")
        data = rgba_image.tobytes("raw", "RGBA")

        qimage = QImage(
            data,
            rgba_image.size[0],
            rgba_image.size[1],
            QImage.Format_RGBA8888,
        )

        return qimage

    def _create_cache_key(self, image_path: Path, max_width: int, max_height: int) -> str:
        """Create a unique cache key for the image and dimensions."""
        return f"{image_path.as_posix()}_{max_width}x{max_height}"

    def _add_to_cache(self, cache_key: str, cached_data: CachedImageData):
        """Add image metadata to cache with LRU eviction."""
        while len(self._cache) >= self._max_cache_size:
            oldest_key = next(iter(self._cache))
            self.logger.debug(f"Evicting from cache: {oldest_key}")
            del self._cache[oldest_key]

        self._cache[cache_key] = cached_data

    def clear_cache_entry(self, image_path: Path):
        """Remove all cache entries for a specific image."""
        keys_to_remove = [
            key for key in self._cache.keys()
            if key.startswith(image_path.as_posix())
        ]

        for key in keys_to_remove:
            del self._cache[key]
            self.logger.debug(f"Removed from cache: {key}")

    def clear_cache(self):
        """Clear the entire cache."""
        cache_size = len(self._cache)
        self._cache.clear()
        self.logger.debug(f"Cleared cache of {cache_size} entries")

    def get_cache_info(self) -> dict:
        """Get cache statistics."""
        return {
            "size": len(self._cache),
            "max_size": self._max_cache_size,
            "usage_ratio": len(self._cache) / self._max_cache_size if self._max_cache_size > 0 else 0,
        }

    def validate_image_dimensions(self, image_path: Path) -> Tuple[int, int]:
        """
        Validate image and return its dimensions without loading into cache.

        Args:
            image_path: Path to the image file

        Returns:
            Tuple of (width, height)

        Raises:
            ImageLoadError: If image cannot be opened or has invalid dimensions
        """
        try:
            with Image.open(image_path) as img:
                width, height = img.size

                if width == 0 or height == 0:
                    raise ImageLoadError(
                        str(image_path),
                        f"Invalid image dimensions: {width}x{height}",
                    )

                return width, height

        except OSError as e:
            raise ImageLoadError(str(image_path), "Failed to open image for validation", e)
