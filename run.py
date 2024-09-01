import sys
import threading
import uvicorn
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer
from app.main import app as fastapi_app
from app.app import ImageTaggerApp, CloseHandler
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ServerThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.server = uvicorn.Server(uvicorn.Config(fastapi_app, host="0.0.0.0", port=8000))

    def run(self):
        self.server.run()

    def stop(self):
        self.server.should_exit = True

def start_fastapi():
    logger.info("Starting FastAPI server")
    server_thread.start()

def stop_server():
    logger.info("Stopping FastAPI server")
    server_thread.stop()
    server_thread.join()

if __name__ == "__main__":
    logger.info("Starting application")
    
    server_thread = ServerThread()
    
    # Start FastAPI server in a separate thread
    start_fastapi()
    
    # Start the local application
    app = QApplication(sys.argv)
    
    # Create and install event filter
    close_handler = CloseHandler(stop_server)
    app.installEventFilter(close_handler)
    
    window = ImageTaggerApp(stop_server)
    window.show()
    
    # Use a timer to check if the server has stopped
    shutdown_timer = QTimer()
    shutdown_timer.timeout.connect(lambda: None)
    shutdown_timer.start(100)
    
    # Ensure the application exits cleanly
    sys.exit(app.exec_())