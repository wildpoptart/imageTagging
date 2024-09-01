import sys
import os
import logging
import subprocess
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QPushButton, 
    QWidget, QLabel, QFileDialog, QListWidget, QLineEdit, QListWidgetItem, 
    QMessageBox, QMenu, QDialog, QCheckBox
)
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt, QThreadPool, QRunnable, pyqtSlot, QObject, pyqtSignal, QTimer, QEvent
import requests
from PIL import Image
import io
import gc
from .image_cache import ImageCache
from .localDB import LocalDB

from app.face_detect import face_detection_thread

# Create an instance of LocalDB
localDB = LocalDB()

# Set up logging
logging.basicConfig(level=logging.DEBUG,  # Change to DEBUG to see all logs
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler("./logs/app.log"),  # Log to file
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

class FaceDetectionTask(QRunnable):
    def __init__(self, file_path, localDB):
        super().__init__()
        self.file_path = file_path
        self.localDB = localDB

    @pyqtSlot()
    def run(self):
        face_detection_thread(self.file_path, self.localDB)  # Call the existing face detection function

class ImageTaggerApp(QMainWindow):
    def __init__(self, stop_server_func):
        super().__init__()
        logger.info("Initializing ImageTaggerApp")
        self.setWindowTitle("Image Tagger")
        self.setGeometry(100, 100, 1000, 600)

        self.image_cache = ImageCache(max_size=10)
        self.localDB = LocalDB()  # Initialize LocalDB
        self.stop_server_func = stop_server_func
        self.clear_logs()  # Clear logs when the app starts
        self.processed_images = set()  # Set to track processed images
        self.initUI()  # Initialize the UI components
        self.threadpool = QThreadPool()  # Initialize the thread pool

    def initUI(self):
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

        # Create a checkbox for recursive folder finding
        self.recursive_checkbox = QCheckBox("Allow recursive folder image finding", self)
        self.recursive_checkbox.setChecked(False)  # Default to unchecked
        left_layout.addWidget(self.recursive_checkbox)

        self.status_label = QLabel("No folder selected")
        left_layout.addWidget(self.status_label)

        # Add file count label
        self.file_count_label = QLabel("Files in database: 0")
        left_layout.addWidget(self.file_count_label)

        self.image_list = QListWidget()
        self.image_list.itemClicked.connect(self.on_image_click)
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

        # Settings Button
        self.settings_button = QPushButton("Settings")
        self.settings_button.clicked.connect(self.open_settings)
        left_layout.addWidget(self.settings_button)

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
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_processing_status)
        self.processing_attempts = 0

        # Add context menu for image list
        self.image_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.image_list.customContextMenuRequested.connect(self.show_context_menu)

        # Update file count on startup
        self.update_file_count()

    def clear_logs(self):
        log_files = [os.path.join('logs', f) for f in os.listdir('logs') if f.endswith('.log')]
        for log_file in log_files:
            if os.path.exists(log_file):
                with open(log_file, 'w') as f:
                    f.truncate(0)  # Empty the contents of the file
                print(f"Cleared contents of log file: {log_file}")
            else:
                print("Log file does not exist, nothing to clear.")

    def update_file_count(self):
        file_count = self.localDB.count_files()
        self.file_count_label.setText(f"Files in database: {file_count}")

    def is_supported_image(self, filename):
        return filename.lower().endswith(('.png', '.jpg', '.jpeg'))

    def select_folder(self):
        logger.info("Selecting folder")
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            logger.info(f"Folder selected: {folder}")
            self.selected_folder = folder
            self.status_label.setText(f"Selected folder: {folder}")
            self.process_folder(folder)
        else:
            logger.info("No folder selected")

    def process_folder(self, folder):
        allow_recursive = self.recursive_checkbox.isChecked()
        
        if allow_recursive:
            self.find_images_recursively(folder)
        else:
            self.find_images_in_folder(folder)

    def find_images_recursively(self, folder):
        for root, dirs, files in os.walk(folder):
            for file in files:
                if file.lower().endswith('.heic'):
                    logger.warning(f"Skipping unsupported HEIC file: {file}")
                elif self.is_supported_image(file):
                    full_path = os.path.join(root, file)
                    self.localDB.save_tags(file, [], full_path)
        self.update_file_count()
        self.send_folder_to_backend(folder)
        self.load_images()
        self.image_cache.clear()

    def find_images_in_folder(self, folder):
        for file in os.listdir(folder):
            if file.lower().endswith('.heic'):
                logger.warning(f"Skipping unsupported HEIC file: {file}")
            elif self.is_supported_image(file):
                full_path = os.path.join(folder, file)
                self.localDB.save_tags(file, [], full_path)
        self.update_file_count()
        self.send_folder_to_backend(folder)
        self.load_images()
        self.image_cache.clear()

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

    def on_image_click(self, item):
        if item is None:
            logger.warning("No item selected")
            return

        filename = item.text()
        file_location = self.localDB.get_file_location(filename)
        
        # If the file is not in the database, assume it's in the selected folder
        if not file_location:
            file_location = os.path.join(self.selected_folder, filename)

        if not os.path.exists(file_location):
            logger.error(f"File does not exist: {file_location}")
            self.status_label.setText("Image file not found on disk")
            return

        # Display the image
        self.display_image(file_location)

    def display_image(self, file_location):
        logger.info(f"Attempting to display image: {file_location}")
        
        self.image_label.clear()
        self.image_label.setText("Loading...")

        pixmap = self.image_cache.get(file_location)
        if pixmap is None:
            try:
                image = QImage(file_location)
                if image.isNull():
                    logger.error(f"Failed to load image: {file_location}")
                    self.image_label.setText("Failed to load image")
                    return
                pixmap = QPixmap.fromImage(image)
                self.image_cache.set(file_location, pixmap)
            except Exception as e:
                logger.exception(f"Error loading image {file_location}: {str(e)}")
                self.image_label.setText(f"Error loading image: {str(e)}")
                return

        max_width = 300  # Set your desired maximum width
        max_height = 300  # Set your desired maximum height
        self.image_label.setMaximumSize(max_width, max_height)
        self.image_label.setPixmap(pixmap)
        self.image_label.setScaledContents(True)

        # Fetch and display tags
        filename = os.path.basename(file_location)
        tags = self.localDB.get_tags(filename) or []  # Use an empty list if no tags are found
        self.tags_list.clear()
        for tag in tags:
            self.tags_list.addItem(tag)

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

    def add_tag(self):
        if self.image_list.currentItem():
            new_tag = self.new_tag_input.text().strip()
            if new_tag:
                self.tags_list.addItem(new_tag)
                self.new_tag_input.clear()
            else:
                QMessageBox.warning(self, "Invalid Tag", "Please enter a non-empty tag.")
        else:
            QMessageBox.warning(self, "No Image Selected", "Please select an image before adding a tag.")

    def save_tags(self):
        if self.image_list.currentItem():
            filename = self.image_list.currentItem().text()
            tags = [self.tags_list.item(i).text() for i in range(self.tags_list.count())]
            
            # Get the file location (works for both processed and unprocessed images)
            file_location = self.localDB.get_file_location(filename)
            if not file_location:
                file_location = os.path.join(self.selected_folder, filename)

            # Save tags to the database
            self.localDB.save_tags(filename, tags, file_location)
            
            # Update UI
            self.status_label.setText("Tags saved")
            QMessageBox.information(self, "Tags Saved", f"Tags for {filename} have been saved.")
            
            # Update file count
            self.update_file_count()
        else:
            QMessageBox.warning(self, "No Image Selected", "Please select an image before saving tags.")

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
            # Query the database for images with matching tags
            matching_images = localDB.search_images(search_tags)  # Now returns (name, file_location)
            self.image_list.clear()  # Clear the current list

            if matching_images:
                for name, file_location in matching_images:
                    self.image_list.addItem(name)  # Add image name to the list
                    # Optionally store the file location in the item data for later use
                    self.image_list.item(self.image_list.count() - 1).setData(Qt.UserRole, file_location)
                logger.info(f"Found {len(matching_images)} images")
                self.status_label.setText(f"Found {len(matching_images)} images")
            else:
                logger.info("No matching images found")
                self.status_label.setText("No matching images found")
        except Exception as e:
            logger.error(f"Error during search: {str(e)}")
            self.status_label.setText("Error during search")

    def process_images(self):
        logger.info("Starting image processing")
        try:
            response = requests.get("http://localhost:8000/process_images")
            if response.status_code == 200:
                logger.info("Processing started successfully")
                self.status_label.setText("Processing started. Please wait...")
                self.processing_attempts = 0
                self.timer.start(2000)  # Check every 2 seconds

                # Start face detection in a thread pool for each image
                for filename in os.listdir(self.selected_folder):
                    if self.is_supported_image(filename):
                        file_path = os.path.join(self.selected_folder, filename)
                        task = FaceDetectionTask(file_path, self.localDB)
                        self.threadpool.start(task)  # Start the task in the thread pool
                        self.processed_images.add(filename)  # Mark the image as processed

                self.update_file_count()  # Update count after processing images
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

        if self.processing_attempts >= 2:  # Max attempts reached
            logger.warning("Failed to retrieve tags after multiple attempts")
            self.status_label.setText("Failed to retrieve tags after multiple attempts")
            self.timer.stop()

    def show_context_menu(self, pos):
        item = self.image_list.itemAt(pos)
        if item:
            context_menu = QMenu(self)
            show_action = context_menu.addAction("Show in Explorer")
            show_action.triggered.connect(lambda: self.show_in_explorer(item.text()))
            context_menu.exec_(self.image_list.viewport().mapToGlobal(pos))

    def show_in_explorer(self, filename):
        file_location = self.localDB.get_file_location(filename)
        if not file_location:
            file_location = os.path.join(self.selected_folder, filename)
        
        directory = os.path.dirname(file_location)
        
        if os.path.exists(directory):
            if os.name == 'nt':  # For Windows
                subprocess.Popen(f'explorer /select,"{file_location}"')
            elif os.name == 'posix':  # For macOS and Linux
                if sys.platform == 'darwin':  # macOS
                    subprocess.Popen(['open', '-R', file_location])
                else:  # Linux
                    subprocess.Popen(['xdg-open', directory])
        else:
            logger.warning(f"Directory does not exist: {directory}")
            QMessageBox.warning(self, "Directory Not Found", f"The directory for {filename} could not be found.")

    def open_settings(self):
        settings_window = SettingsWindow(self)
        settings_window.exec_()  # Open the settings window

    def closeEvent(self, event):
        print("Closing application and stopping server...")
        self.stop_server_func()
        super().closeEvent(event)

class SettingsWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setGeometry(100, 100, 300, 200)

        layout = QVBoxLayout()

        # Reset Database Button
        self.reset_button = QPushButton("Reset Database")
        self.reset_button.clicked.connect(self.reset_database)
        layout.addWidget(self.reset_button)

        self.setLayout(layout)

    def reset_database(self):
        # Confirm before resetting the database
        reply = QMessageBox.question(self, 'Confirm Reset', 
                                     "Are you sure you want to reset the database?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            localDB.reset_database()  # Call the function to reset the database
            QMessageBox.information(self, 'Database Reset', "Database has been reset.")
            self.close()

class CloseHandler(QObject):
    def __init__(self, stop_server_func):
        super().__init__()
        self.stop_server_func = stop_server_func

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Close:
            print("Application is closing. Stopping server...")
            self.stop_server_func()
        return super().eventFilter(obj, event)