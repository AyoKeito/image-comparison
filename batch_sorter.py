import os
import sys
import random
import shutil
from PIL import Image
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QHBoxLayout, QMessageBox, QFileDialog, QVBoxLayout
from PyQt5.QtGui import QPixmap, QImage, QPainter, QPen, QColor
from PyQt5.QtCore import Qt
import logging
from enum import Enum
import traceback

# Logging setup
logging.basicConfig(filename='error.log', level=logging.DEBUG, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

def exception_hook(exctype, value, traceback):
    error_msg = f"An unexpected error occurred:\n{value}\nCheck error.log for details."
    logging.error("Uncaught exception", exc_info=(exctype, value, traceback))
    QMessageBox.critical(None, "Critical Error", error_msg)
    sys.exit(1)

sys.excepthook = exception_hook

# Configuration constants
class Config(Enum):
    DIVIDER_COLOR = '#404040'
    PADDING = 40
    SUPPORTED_EXTENSIONS = ['.png', '.jpg', '.webp', '.jpeg']
    BACKGROUND_COLOR = '#202020'
    TEXT_COLOR = 'white'

class ImageComparison(QWidget):
    def __init__(self, image_folder, discarded_folder):
        super().__init__()
        self.image_folder = self.validate_folder(image_folder)
        self.discarded_folder = discarded_folder
        self.remaining_images = []
        self.loop_counter = 0
        self.discarded_count = 0
        self.image_cache = {}
        self.undo_stack = []
        self.image_labels = [QLabel(self) for _ in range(2)]
        self.image1_path = None
        self.image2_path = None
        for label in self.image_labels:
            label.setAlignment(Qt.AlignCenter)

        main_layout = QVBoxLayout()
        image_layout = QHBoxLayout()
        for label in self.image_labels:
            image_layout.addWidget(label, 1)

        main_layout.addLayout(image_layout)
        self.setLayout(main_layout)
        self.setWindowTitle('Image Comparison')
        self.apply_theme()
        self.setGeometryToScreen()
        self.updateImages()

    def apply_theme(self):
        """Apply the dark theme to the widget."""
        self.setStyleSheet(f"background-color: {Config.BACKGROUND_COLOR.value}; color: {Config.TEXT_COLOR.value};")

    def paintEvent(self, event):
        """Draw the divider between images."""
        painter = QPainter(self)
        pen = QPen(QColor(Config.DIVIDER_COLOR.value), 4, Qt.SolidLine)
        painter.setPen(pen)
        center_x = self.width() // 2
        painter.drawLine(center_x, 0, center_x, self.height())

    def resizeEvent(self, event):
        """Handle window resize by updating images and redrawing the divider."""
        super().resizeEvent(event)
        self.updateImages()
        self.update()

    def validate_folder(self, folder):
        """Ensure the folder exists, is readable, and contains images."""
        while True:
            if not folder or not os.path.exists(folder) or not os.path.isdir(folder):
                folder = QFileDialog.getExistingDirectory(self, "Select Image Folder")
                if not folder:
                    sys.exit("No valid folder selected.")
            image_files = self.get_image_files(folder)
            if not image_files:
                QMessageBox.warning(self, "No Images", "The selected folder contains no supported images. Please select another folder.")
                folder = QFileDialog.getExistingDirectory(self, "Select Image Folder")
                if not folder:
                    sys.exit("No valid folder selected.")
            else:
                break
        return folder

    def updateImages(self):
        """Load and display two random images, handling edge cases."""
        image_files = self.get_image_files(self.image_folder)
        
        logging.debug(f"Images in folder: {len(image_files)}, Images in memory: {len(self.remaining_images)}")

        # Refresh remaining_images when it’s low or at the start of a new loop
        if len(self.remaining_images) < 2:
            self.remaining_images = image_files[:]
            # Exclude current pair if they’re still in the folder
            if self.image1_path and self.image1_path in self.remaining_images:
                self.remaining_images.remove(self.image1_path)
            if self.image2_path and self.image2_path in self.remaining_images:
                self.remaining_images.remove(self.image2_path)
            random.shuffle(self.remaining_images)
            self.loop_counter += 1
            logging.debug(f"Refreshed images for loop {self.loop_counter} with {len(self.remaining_images)} images")

        self.update_window_title(len(image_files))

        if len(image_files) == 2:
            logging.debug("Exactly 2 images remaining")
            self.remaining_images = image_files
            self.update_remaining_images()
            self.display_remaining_images_popup()
            return

        if len(image_files) < 2:
            logging.info("Finished processing all images.")
            self.close()
            return

        self.image1_path, self.image2_path = self.get_random_images(self.remaining_images)
        if self.image1_path is None or self.image2_path is None:
            error_msg = "Failed to get two images for comparison"
            logging.error(error_msg)
            QMessageBox.critical(self, "Critical Error", error_msg + "\nCheck error.log for details.")
            self.close()
            return

        self.update_image(self.image1_path, self.image_labels[0])
        self.update_image(self.image2_path, self.image_labels[1])

    def update_window_title(self, remaining_count):
        """Update the window title with current progress."""
        self.setWindowTitle(f"Image Comparison | Remaining: {remaining_count} | Discarded: {self.discarded_count} | Loop: {self.loop_counter}")

    def select_image_folder(self):
        """Prompt user to select a new image folder."""
        folder = QFileDialog.getExistingDirectory(self, "Select Image Folder")
        if folder:
            self.image_folder = folder
            self.updateImages()

    def update_image(self, image_path, label):
        """Load, resize, and display an image in the given label."""
        if not image_path:
            error_msg = "No image path provided for update"
            logging.error(error_msg)
            QMessageBox.critical(self, "Critical Error", error_msg + "\nCheck error.log for details.")
            return

        max_width = (self.width() - 2 * Config.PADDING.value) // 2
        max_height = self.height() - 2 * Config.PADDING.value

        full_path = os.path.join(self.image_folder, image_path)
        try:
            if image_path not in self.image_cache:
                with Image.open(full_path) as img:
                    image = img.convert("RGB")
                    self.image_cache[image_path] = self.resize_image(image, max_width, max_height)
            
            qimage = self.convert_pil_to_qimage(self.image_cache[image_path])
            pixmap = QPixmap.fromImage(qimage)
            label.setMaximumSize(max_width, max_height)
            label.setPixmap(pixmap)
        except (IOError, ValueError) as e:
            error_msg = f"Failed to load image {image_path}: {e}"
            logging.error(error_msg)
            QMessageBox.critical(self, "Critical Error", error_msg + "\nCheck error.log for details.")
            if image_path in self.remaining_images:
                self.remaining_images.remove(image_path)

    def resize_image(self, image, max_width, max_height):
        """Resize an image while preserving aspect ratio."""
        image_width, image_height = image.size
        scale_factor = min(max_width / image_width, max_height / image_height)
        new_width = int(image_width * scale_factor)
        new_height = int(image_height * scale_factor)
        return image.resize((new_width, new_height), Image.LANCZOS)

    def convert_pil_to_qimage(self, pil_image):
        """Convert a PIL image to QImage."""
        data = pil_image.convert("RGBA").tobytes("raw", "RGBA")
        return QImage(data, pil_image.size[0], pil_image.size[1], QImage.Format_RGBA8888)

    def keyPressEvent(self, event):
        """Handle keypress events for image management."""
        key = event.key()
        logging.debug(f"Key pressed: {key}")

        key_mapping = {
            Qt.Key_Left: self.image1_path,
            Qt.Key_A: self.image1_path,
            Qt.Key_Right: self.image2_path,
            Qt.Key_D: self.image2_path,
            Qt.Key_Down: (self.image1_path, self.image2_path),
            Qt.Key_S: (self.image1_path, self.image2_path),
            Qt.Key_Up: "keep_both",
            Qt.Key_W: "keep_both",
            Qt.Key_U: "undo",
        }

        action = key_mapping.get(key)
        logging.debug(f"Action for key {key}: {action}")

        if action == "undo" and self.undo_stack:
            logging.debug("Performing undo action")
            self.undo_last_action()
        elif action == "keep_both":
            logging.debug("Keeping both images, moving to next pair")
            self.updateImages()
        elif action:
            logging.debug(f"Discarding image(s): {action}")
            if isinstance(action, tuple):
                for image_path in action:
                    if image_path:
                        self.move_to_discarded(image_path)
                        if image_path in self.remaining_images:
                            self.remaining_images.remove(image_path)
                    else:
                        logging.warning("Attempted to discard a None image path")
            else:
                if action:
                    self.move_to_discarded(action)
                    if action in self.remaining_images:
                        self.remaining_images.remove(action)
                else:
                    logging.warning("Attempted to discard a None image path")
            self.updateImages()
        else:
            logging.debug(f"Ignoring key: {key}")
            event.ignore()

    def move_to_discarded(self, image_path):
        """Move an image to the discarded folder."""
        try:
            discarded_folder = os.path.join(self.image_folder, "discarded")
            os.makedirs(discarded_folder, exist_ok=True)
            source_path = os.path.join(self.image_folder, image_path)
            target_path = os.path.join(discarded_folder, os.path.basename(image_path))

            if os.path.exists(target_path):
                if os.path.getsize(target_path) == os.path.getsize(source_path):
                    os.replace(source_path, target_path)
                else:
                    raise ValueError(f"Conflicting file sizes for {image_path}")
            else:
                shutil.move(source_path, target_path)
            self.undo_stack.append((target_path, source_path))
            self.discarded_count += 1
            logging.debug(f"Moved {image_path} to discarded folder. Discarded count: {self.discarded_count}")
        except (OSError, ValueError) as e:
            error_msg = f"Failed to move {image_path}: {e}"
            logging.error(error_msg)
            QMessageBox.critical(self, "Critical Error", error_msg + "\nCheck error.log for details.")

    def undo_last_action(self):
        """Revert the last discard action."""
        if self.undo_stack:
            target_path, source_path = self.undo_stack.pop()
            try:
                shutil.move(target_path, source_path)
                self.discarded_count -= 1
                logging.debug(f"Undo: Restored {os.path.basename(source_path)}. Discarded count: {self.discarded_count}")
                self.remaining_images.append(os.path.basename(source_path))
                self.updateImages()
            except OSError as e:
                error_msg = f"Failed to undo {source_path}: {e}"
                logging.error(error_msg)
                QMessageBox.critical(self, "Critical Error", error_msg + "\nCheck error.log for details.")

    def get_random_images(self, image_files):
        """Select two random images from the list."""
        if len(image_files) < 2:
            logging.warning(f"Not enough images to compare: {len(image_files)} remaining")
            return None, None

        if len(image_files) == 2:
            image1 = image_files.pop(0)
            image2 = image_files.pop(0)
        else:
            selected = random.sample(image_files, 2)
            image1 = selected[0]
            image2 = selected[1]
            image_files.remove(image1)
            image_files.remove(image2)

        logging.debug(f"Selected pair: {image1}, {image2}")
        return image1, image2

    def update_remaining_images(self):
        """Display the last two images."""
        for image_path, label in zip(self.remaining_images, self.image_labels):
            self.update_image(image_path, label)

    def display_remaining_images_popup(self):
        """Show a popup with the last two images."""
        self.update_remaining_images()
        msg_box = QMessageBox()
        msg_box.setWindowTitle("Image Comparison")
        msg_box.setText("2 images remaining")
        msg_box.setInformativeText("Remaining images:\n\n" + "\n".join(self.remaining_images))
        msg_box.exec_()

    def get_image_files(self, folder=None):
        """Retrieve list of supported image files from the specified folder."""
        folder = folder or self.image_folder
        try:
            return [f for f in os.listdir(folder) 
                    if os.path.isfile(os.path.join(folder, f)) 
                    and any(f.lower().endswith(ext) for ext in Config.SUPPORTED_EXTENSIONS.value)]
        except OSError as e:
            error_msg = f"Failed to list images in {folder}: {e}"
            logging.error(error_msg)
            QMessageBox.critical(self, "Critical Error", error_msg + "\nCheck error.log for details.")
            return []

    def setGeometryToScreen(self):
        """Set window size to match primary screen."""
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(0, 0, screen.width(), screen.height())

def main():
    """Main entry point for the application."""
    print("Welcome to Image Comparison!")
    print("Instructions:")
    print("W or UP: Keep both images")
    print("A or LEFT: Discard left image")
    print("D or RIGHT: Discard right image")
    print("S or DOWN: Discard both images")
    print("U: Undo last discard")
    app = QApplication(sys.argv)

    folder_path = sys.argv[1] if len(sys.argv) > 1 else None
    discarded_dir = os.path.join(folder_path if folder_path else os.path.dirname(os.path.abspath(__file__)), "discarded")
    image_comparison = ImageComparison(folder_path, discarded_dir)
    image_comparison.showMaximized()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()