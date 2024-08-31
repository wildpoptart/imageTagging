import sys
import os
import logging
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QPushButton, QWidget, QLabel, QFileDialog, QListWidget, QLineEdit, QListWidgetItem, QMessageBox
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt, QThreadPool, QRunnable, pyqtSlot, QObject, pyqtSignal, QTimer
import requests
from PIL import Image
import io
import gc
from image_cache import ImageCache
import localDB

# Set up logging
logging.basicConfig(level=logging.DEBUG,  # Change to DEBUG to see all logs
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler("app.log"),  # Log to file
                        logging.StreamHandler()           # Log to console
                    ])
logger = logging.getLogger(__name__)

class ImageLoader(QRunnable):
    class Signals(QObject):
        result = pyqtSignal(object, str)

    def __init__(self, image_path):
        super().__init__()
        self.image_path = image_path
        self.signals = self.Signals()

    @pyqtSlot()
    def run(self):
        logger.debug(f"Starting to load image: {self.image_path}")
        try:
            with Image.open(self.image_path) as pil_image:
                pil_image.thumbnail((1000, 1000), Image.LANCZOS)
                if pil_image.mode != 'RGB':
                    pil_image = pil_image.convert('RGB')
                buffer = io.BytesIO()
                pil_image.save(buffer, format="PNG")
                buffer.seek(0)
                image_data = buffer.getvalue()
                qimage = QImage.fromData(image_data)
                pixmap = QPixmap.fromImage(qimage)
            logger.debug(f"Image loaded successfully: {self.image_path}")
            self.signals.result.emit(pixmap, self.image_path)
        except Exception as e:
            logger.error(f"Failed to load image {self.image_path}: {str(e)}")
            self.signals.result.emit(None, self.image_path)
        finally:
            gc.collect()

class ImageTaggerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        logger.info("Initializing ImageTaggerApp")
        self.setWindowTitle("Image Tagger")
        self.setGeometry(100, 100, 1000, 600)

        self.image_cache = ImageCache(max_size=10)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)

        # Left panel
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        left_panel.setLayout(left_layout)
        main_layout.addWidget(left_panel)

        self.folder_button = QPushButton("Select Folder")
        self.folder_button.clicked.connect(self.select_folder)
        left_layout.addWidget(self.folder_button)

        self.status_label = QLabel("No folder selected")
        left_layout.addWidget(self.status_label)

        self.image_list = QListWidget()
        self.image_list.itemClicked.connect(self.display_image)
        left_layout.addWidget(self.image_list)

        self.process_button = QPushButton("Process Images")
        self.process_button.clicked.connect(self.process_images)
        left_layout.addWidget(self.process_button)

        # Add search functionality
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter tags to search (comma-separated)")
        search_layout.addWidget(self.search_input)
        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.search_images)
        search_layout.addWidget(self.search_button)
        left_layout.addLayout(search_layout)

        # Right panel
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        right_panel.setLayout(right_layout)
        main_layout.addWidget(right_panel)

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(self.image_label)

        self.tags_list = QListWidget()
        right_layout.addWidget(self.tags_list)

        self.new_tag_input = QLineEdit()
        self.new_tag_input.setPlaceholderText("Enter new tag")
        right_layout.addWidget(self.new_tag_input)

        self.add_tag_button = QPushButton("Add Tag")
        self.add_tag_button.clicked.connect(self.add_tag)
        right_layout.addWidget(self.add_tag_button)

        # Add save button
        self.save_button = QPushButton("Save Tags")
        self.save_button.clicked.connect(self.save_tags)
        right_layout.addWidget(self.save_button)

        self.selected_folder = ""
        self.threadpool = QThreadPool()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_processing_status)
        self.processing_attempts = 0

    def is_supported_image(self, filename):
        return filename.lower().endswith(('.png', '.jpg', '.jpeg', '.heic'))

    def select_folder(self):
        logger.info("Selecting folder")
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            logger.info(f"Folder selected: {folder}")
            self.selected_folder = folder
            self.status_label.setText(f"Selected folder: {folder}")
            self.send_folder_to_backend(folder)
            self.load_images()
            self.image_cache.clear()
        else:
            logger.info("No folder selected")

    def send_folder_to_backend(self, folder):
        logger.info(f"Sending folder to backend: {folder}")
        try:
            response = requests.post("http://localhost:8000/set_folder", json={"folder": folder})
            if response.status_code == 200:
                logger.info("Folder sent to backend successfully")
            else:
                logger.error(f"Failed to send folder to backend. Status code: {response.status_code}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Error connecting to backend: {str(e)}")

    def load_images(self):
        logger.info("Loading images")
        self.image_list.clear()
        for filename in os.listdir(self.selected_folder):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                self.image_list.addItem(filename)
        logger.info(f"Loaded {self.image_list.count()} images")

    def display_image(self, item):
        if item is None:
            logger.warning("No item selected for display")
            return

        filename = item.text()
        image_path = os.path.join(self.selected_folder, filename)
        logger.info(f"Displaying image: {image_path}")
        
        self.image_label.clear()
        self.image_label.setText("Loading...")

        cached_pixmap = self.image_cache.get(image_path)
        if cached_pixmap:
            logger.debug(f"Image found in cache: {image_path}")
            self.on_image_loaded(cached_pixmap, image_path)
        else:
            logger.debug(f"Loading image from disk: {image_path}")
            gc.collect()
            loader = ImageLoader(image_path)
            loader.signals.result.connect(self.on_image_loaded)
            self.threadpool.start(loader)

        self.update_tags(filename)

    def on_image_loaded(self, result, image_path):
        if result is None:
            logger.error(f"Failed to load image: {image_path}")
            self.image_label.setText("Failed to load image")
        else:
            logger.debug(f"Image loaded successfully: {image_path}")
            scaled_pixmap = result.scaled(400, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.image_label.setPixmap(scaled_pixmap)
            self.image_cache.put(image_path, scaled_pixmap)

    def update_tags(self, filename):
        logger.info(f"Updating tags for: {filename}")
        tags = localDB.get_tags(filename)
        self.tags_list.clear()
        for tag in tags:
            item = QListWidgetItem(tag)
            item.setFlags(item.flags() | Qt.ItemIsEditable)
            self.tags_list.addItem(item)
        logger.debug(f"Updated tags for {filename}: {tags}")

    def save_tags(self):
        logger.info("Saving tags")
        if self.image_list.currentItem():
            filename = self.image_list.currentItem().text()
            tags = [self.tags_list.item(i).text() for i in range(self.tags_list.count())]
            localDB.save_tags(filename, tags)
            self.send_tags_to_backend(filename, tags)
        else:
            logger.warning("No image selected for saving tags")

    def send_tags_to_backend(self, filename, tags):
        logger.info(f"Sending tags to backend for {filename}")
        try:
            response = requests.post("http://localhost:8000/update_tags", json={"filename": filename, "tags": tags})
            if response.status_code == 200:
                logger.info("Tags updated successfully")
            else:
                logger.error(f"Failed to update tags. Status code: {response.status_code}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Error connecting to backend: {str(e)}")

    def search_images(self):
        logger.info("Searching images")
        search_tags = [tag.strip() for tag in self.search_input.text().split(',') if tag.strip()]
        if not search_tags:
            logger.warning("No search tags provided")
            return

        try:
            response = requests.post("http://localhost:8000/search", json={"tags": search_tags})
            if response.status_code == 200:
                search_results = response.json()
                self.image_list.clear()
                for filename in search_results:
                    self.image_list.addItem(filename)
                logger.info(f"Found {len(search_results)} images")
                self.status_label.setText(f"Found {len(search_results)} images")
            else:
                logger.error(f"Failed to perform search. Status code: {response.status_code}")
                self.status_label.setText("Failed to perform search")
        except requests.exceptions.RequestException as e:
            logger.error(f"Error connecting to backend: {str(e)}")
            self.status_label.setText(f"Error connecting to backend: {e}")

    def process_images(self):
        logger.info("Starting image processing")
        try:
            response = requests.get("http://localhost:8000/process_images")
            if response.status_code == 200:
                logger.info("Processing started successfully")
                self.status_label.setText("Processing started. Please wait...")
                self.processing_attempts = 0
                self.timer.start(2000)  # Check every 2 seconds
            else:
                logger.error(f"Failed to start processing. Status code: {response.status_code}")
                self.status_label.setText("Failed to start processing")
        except requests.exceptions.RequestException as e:
            logger.error(f"Error connecting to backend: {str(e)}")
            self.status_label.setText(f"Error connecting to backend: {e}")

    def check_processing_status(self):
        logger.debug("Checking processing status")
        try:
            response = requests.get("http://localhost:8000/get_tags")
            if response.status_code == 200:
                image_tags = response.json()
                logger.debug(f"Received tags: {image_tags}")
                if image_tags:  # If tags are available
                    logger.info(f"Processed {len(image_tags)} images")
                    self.status_label.setText(f"Processed {len(image_tags)} images")
                    if self.image_list.currentItem():
                        self.update_tags(self.image_list.currentItem().text())
                    self.timer.stop()  # Stop checking once we have tags
                else:
                    logger.debug("No tags available yet, retrying...")
                    self.processing_attempts += 1
                    if self.processing_attempts >= 30:  # Max attempts reached
                        logger.warning("Failed to retrieve tags after multiple attempts")
                        self.status_label.setText("Failed to retrieve tags after multiple attempts")
                        self.timer.stop()
            else:
                logger.error(f"Failed to get tags, status code: {response.status_code}")
                self.processing_attempts += 1
        except requests.exceptions.RequestException as e:
            logger.error(f"Error connecting to backend: {str(e)}")
            self.processing_attempts += 1

        if self.processing_attempts >= 30:  # Max attempts reached
            logger.warning("Failed to retrieve tags after multiple attempts")
            self.status_label.setText("Failed to retrieve tags after multiple attempts")
            self.timer.stop()

    def add_tag(self):
        logger.info("Adding new tag")
        new_tag = self.new_tag_input.text().strip()
        if new_tag and self.image_list.currentItem():
            filename = self.image_list.currentItem().text()
            tags = localDB.get_tags(filename)
            tags.append(new_tag)
            localDB.save_tags(filename, tags)
            self.update_tags(filename)
            self.new_tag_input.clear()
            logger.info(f"Added new tag '{new_tag}' to {filename}")
        else:
            logger.warning("Failed to add tag: No tag entered or no image selected")

if __name__ == "__main__":
    logger.info("Starting application")
    app = QApplication(sys.argv)
    window = ImageTaggerApp()
    window.show()
    sys.exit(app.exec_())