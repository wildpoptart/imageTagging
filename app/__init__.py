# app/__init__.py

from .main import app

__all__ = ['app']

"""
Image Tagging Application Package
"""

# Import necessary modules for the package
from .main import app  # Import the FastAPI app
from .localDB import *  # Import all database functions
from .image_cache import *  # Import all image caching functions
from .text_extract import *  # Import all text extraction functions

# You can also define package-level variables or functions here if needed