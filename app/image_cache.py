from collections import OrderedDict
from PyQt5.QtGui import QPixmap
import os
import json

# Define the cache path
CACHE_PATH = os.path.join(os.path.dirname(__file__), '../data/image_cache.json')

class ImageCache:
    def __init__(self, max_size=10):
        self.max_size = max_size
        self.cache = OrderedDict()

    def get(self, key):
        if key in self.cache:
            # Move the accessed item to the end (most recently used)
            self.cache.move_to_end(key)
            return self.cache[key]
        return None

    def put(self, key, value):
        if key in self.cache:
            # If key already exists, move it to the end
            self.cache.move_to_end(key)
        elif len(self.cache) >= self.max_size:
            # If cache is full, remove the least recently used item
            self.cache.popitem(last=False)
        self.cache[key] = value

    def clear(self):
        self.cache.clear()

def load_cache():
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH, 'r') as f:
            return json.load(f)
    return {}

def save_cache(data):
    with open(CACHE_PATH, 'w') as f:
        json.dump(data, f)