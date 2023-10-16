import os
import sys
import random
import shutil
from PIL import Image
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QHBoxLayout, QMessageBox, QFileDialog
from PyQt5.QtGui import QPixmap, QImage, QPainter, QPen, QColor
from PyQt5.QtCore import Qt
import logging
import sip

logging.basicConfig(filename='error.log', level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

def exception_hook(exctype, value, traceback):
    logging.error("Uncaught exception", exc_info=(exctype, value, traceback))

sys.excepthook = exception_hook

class ImageComparison(QWidget):
    DIVIDER_COLOR = '#404040'
    PADDING = 40
    SUPPORTED_EXTENSIONS = ['.png', '.jpg', '.jpeg']
    
    def selectImageFolder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Image Folder")
        if folder:
            self.image_folder = folder
            self.updateImages()

    def __init__(self, image_folder, discarded_folder):
        super().__init__()
        self.image_folder = image_folder
        self.discarded_folder = discarded_folder
        self.remaining_images = []
        self.loop_counter = 0
        self.image_labels = [QLabel(self) for _ in range(2)]
        for label in self.image_labels:
            label.setAlignment(Qt.AlignCenter)

        layout = QHBoxLayout()
        for label in self.image_labels:
            layout.addWidget(label, 1)

        self.setLayout(layout)
        self.setWindowTitle('Image Comparison')
        self.setStyleSheet("background-color: #202020; color: white;")
        self.setGeometryToScreen()

        self.updateImages()

    def paintEvent(self, event):
        painter = QPainter(self)
        pen = QPen(QColor(self.DIVIDER_COLOR), 4, Qt.SolidLine)
        painter.setPen(pen)
    
        center_x = self.width() // 2
        painter.drawLine(center_x, 0, center_x, self.height())

    def updateImages(self):
        image_files = self.getImageFiles()
        
        if not image_files:
            print("No images found. Select another folder.")
            self.selectImageFolder()
            return

        if len(image_files) == 2:
            self.remaining_images = image_files
            self.updateRemainingImages()
            self.displayRemainingImagesPopup()
            return

        if len(image_files) < 2:
            print("Finished!")
            self.close()
            return

        self.image1_path, self.image2_path = self.getRandomImages(image_files)

        self.updateImage(self.image1_path, self.image_labels[0])
        self.updateImage(self.image2_path, self.image_labels[1])

    def updateImage(self, image_path, label):
        image = Image.open(os.path.join(self.image_folder, image_path)).convert("RGB")
        max_width = (self.width() - 2 * self.PADDING) // 2
        max_height = self.height() - 2 * self.PADDING
        image = self.resizeImage(image, max_width, max_height)

        qimage = self.convertPILToQImage(image)
        pixmap = QPixmap.fromImage(qimage)
        label.setMaximumSize(max_width, max_height)
        label.setPixmap(pixmap)

    def resizeImage(self, image, max_width, max_height):
        image_width, image_height = image.size
        scale_factor_height = max_height / image_height
        scale_factor_width = max_width / image_width
        scale_factor = min(scale_factor_height, scale_factor_width)
        new_width = int(image_width * scale_factor)
        new_height = int(image_height * scale_factor)
        return image.resize((new_width, new_height), Image.LANCZOS)

    def convertPILToQImage(self, pil_image):
        data = pil_image.convert("RGBA").tobytes("raw", "RGBA")
        return QImage(data, pil_image.size[0], pil_image.size[1], QImage.Format_RGBA8888)

    def keyPressEvent(self, event):
        valid_keys = {
            Qt.Key_Left, Qt.Key_A,
            Qt.Key_Right, Qt.Key_D,
            Qt.Key_Down, Qt.Key_S,
            Qt.Key_Up, Qt.Key_W,
        }

        key = event.key()
        if key in valid_keys:
            key_mapping = {
                Qt.Key_Left: self.image1_path,
                Qt.Key_A: self.image1_path,
                Qt.Key_Right: self.image2_path,
                Qt.Key_D: self.image2_path,
                Qt.Key_Down: (self.image1_path, self.image2_path),
                Qt.Key_S: (self.image1_path, self.image2_path),
                Qt.Key_Up: None,
                Qt.Key_W: None,
            }

            image_paths = key_mapping.get(key)
            if image_paths:
                if isinstance(image_paths, tuple):
                    for image_path in image_paths:
                        self.moveToDiscarded(image_path)
                else:
                    self.moveToDiscarded(image_paths)

            self.updateImages()

        else:
            event.ignore()

    def moveToDiscarded(self, image_path):
        discarded_folder = os.path.join(self.image_folder, "discarded")
        os.makedirs(discarded_folder, exist_ok=True)

        target_path = os.path.join(discarded_folder, os.path.basename(image_path))

        if os.path.exists(target_path):
            # Check if the existing file has the same size
            if os.path.getsize(target_path) == os.path.getsize(os.path.join(self.image_folder, image_path)):
                # Replace the file if it has the same size
                os.replace(os.path.join(self.image_folder, image_path), target_path)
                print(f"{image_path} replaced in discarded folder")
            else:
                # Show an error message and exit if the file has a different size
                error_message = f"Conflicting files in discarded folder: {os.path.basename(image_path)}"
                QMessageBox.critical(self, "Error", error_message)
                sys.exit(1)
        else:
            # Move the file if it does not exist in the discarded folder
            shutil.move(os.path.join(self.image_folder, image_path), target_path)
            print(f"{image_path} moved to discarded folder")

    def getRandomImages(self, image_files):
        if not self.remaining_images:
            self.remaining_images = image_files[:]
            random.shuffle(self.remaining_images)
            self.loop_counter += 1
            print(f"Loop number {self.loop_counter}")

        if len(self.remaining_images) >= 2:
            image1_path = self.remaining_images.pop(0)
            image2_path = self.remaining_images.pop(0)
        else:
            self.remaining_images = image_files[:]
            random.shuffle(self.remaining_images)
            image1_path, image2_path = self.getRandomImages(image_files)

        return image1_path, image2_path

    def updateRemainingImages(self):
        for image_path, label in zip(self.remaining_images, self.image_labels):
            self.updateImage(image_path, label)

    def displayRemainingImagesPopup(self):
        self.updateRemainingImages()

        msg_box = QMessageBox()
        msg_box.setWindowTitle("Image Comparison")
        msg_box.setText("2 images remaining")
        msg_box.setInformativeText("Remaining images:\n\n" + "\n".join(self.remaining_images))

        msg_box.exec_()

    def getImageFiles(self):
        return [f for f in os.listdir(self.image_folder) 
                if os.path.isfile(os.path.join(self.image_folder, f)) 
                and any(f.lower().endswith(ext) for ext in self.SUPPORTED_EXTENSIONS)]

    def setGeometryToScreen(self):
        screen_geometry = QApplication.desktop().screenGeometry()
        self.setGeometry(0, 0, screen_geometry.width(), screen_geometry.height())

def main():
    print("Welcome to Image Comparison!")
    print("Instructions:")
    print("W or UP to keep both images")
    print("A or LEFT to discard left image")
    print("D or RIGHT to discard right image")
    print("S or DOWN to discard both images")
    app = QApplication(sys.argv)

    if len(sys.argv) > 1:
        folder_path = sys.argv[1]
    else:
        script_directory = os.path.dirname(os.path.abspath(__file__))
        folder_path = script_directory

    discarded_dir = os.path.join(folder_path, "discarded")
    image_comparison = ImageComparison(folder_path, discarded_dir)
    image_comparison.showMaximized()

    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
