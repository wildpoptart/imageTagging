import sys
import threading
import uvicorn
from PyQt5.QtWidgets import QApplication
from app.main import app as fastapi_app  # Import your FastAPI app
from app.app import ImageTaggerApp  # Import your local app class
from app.localDB import LocalDB  # Import localDB if needed
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def start_fastapi():
    logger.info("Starting FastAPI server")
    uvicorn.run(fastapi_app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    logger.info("Starting application")
    
    # Start FastAPI server in a separate thread
    fastapi_thread = threading.Thread(target=start_fastapi)
    fastapi_thread.start()
    
    # Start the local application
    app = QApplication(sys.argv)
    window = ImageTaggerApp()
    window.show()
    
    # Ensure the application exits cleanly
    sys.exit(app.exec_())