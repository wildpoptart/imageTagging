import sqlite3
from sqlite3 import Error
from PIL import Image
from colorthief import ColorThief
import os

class LocalDB:
    DATABASE = 'data/image_tags.db'

    def __init__(self):
        self.initialize_db()

    def create_connection(self):
        conn = None
        try:
            conn = sqlite3.connect(self.DATABASE)
            return conn
        except Error as e:
            print(e)
        return conn

    def initialize_db(self):
        conn = self.create_connection()
        if conn is not None:
            self.create_table(conn)
        else:
            print("Error! Cannot create the database connection.")

    def create_table(self, conn):
        try:
            c = conn.cursor()
            c.execute('''CREATE TABLE IF NOT EXISTS images
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          name TEXT NOT NULL UNIQUE,
                          tags TEXT,
                          file_location TEXT,
                          processed BOOLEAN NOT NULL DEFAULT 0)''')  # New column for processed status
        except Error as e:
            print(e)

    def get_main_colors(self, image_path, num_colors=3):
        color_thief = ColorThief(image_path)
        palette = color_thief.get_palette(color_count=num_colors)
        return [self.rgb_to_color_name(rgb) for rgb in palette]

    def rgb_to_color_name(self, rgb):
        r, g, b = rgb

        # Define a mapping of RGB ranges to color names
        if r > 200 and g > 200 and b > 200:
            return "white"
        elif r < 50 and g < 50 and b < 50:
            return "black"
        elif r > 200 and g < 50 and b < 50:
            return "red"
        elif r < 50 and g > 200 and b < 50:
            return "lime"
        elif r < 50 and g < 50 and b > 200:
            return "blue"
        elif r > 200 and g > 200 and b < 50:
            return "yellow"
        elif r > 200 and g < 50 and b > 200:
            return "magenta"
        elif r < 50 and g > 200 and b > 200:
            return "cyan"
        elif r > 150 and g > 75 and b < 75:
            return "orange"
        elif r > 200 and g > 100 and b < 100:
            return "salmon"
        elif r > 100 and g > 200 and b < 100:
            return "chartreuse"
        elif r > 100 and g < 100 and b > 200:
            return "violet"
        elif r > 200 and g < 200 and b > 100:
            return "peach"
        elif r < 100 and g > 100 and b < 100:
            return "brown"
        elif r > 100 and g > 100 and b > 100:
            return "light gray"
        elif r > 150 and g < 150 and b < 150:
            return "dark gray"
        elif r > 200 and g < 200 and b < 200:
            return "light red"
        elif r < 200 and g > 200 and b < 200:
            return "light green"
        elif r < 200 and g < 200 and b > 200:
            return "light blue"
        elif r > 100 and g < 100 and b < 100:
            return "dark red"
        elif r < 100 and g > 100 and b > 100:
            return "dark green"
        elif r < 100 and g < 100 and b > 100:
            return "dark blue"
        elif r > 200 and g > 150 and b < 150:
            return "light salmon"
        elif r > 150 and g > 200 and b > 150:
            return "light chartreuse"
        elif r < 150 and g > 200 and b > 150:
            return "light cyan"
        elif r > 150 and g < 150 and b > 200:
            return "light violet"
        elif r > 200 and g > 200 and b > 100:
            return "light yellow"
        elif r > 100 and g > 150 and b < 200:
            return "light pink"
        elif r < 200 and g < 100 and b < 100:
            return "dark brown"
        elif r > 100 and g < 50 and b < 50:
            return "dark red"
        elif r < 100 and g > 100 and b < 50:
            return "olive"
        elif r < 100 and g < 100 and b < 200:
            return "navy"
        elif r > 200 and g < 100 and b > 100:
            return "light coral"
        elif r < 150 and g > 150 and b < 150:
            return "gray"
        elif r > 100 and g > 100 and b < 50:
            return "gold"
        elif r > 200 and g > 100 and b > 200:
            return "orchid"
        elif r < 50 and g > 100 and b > 50:
            return "sea green"
        elif r > 100 and g < 100 and b > 100:
            return "slate blue"
        elif r < 50 and g < 200 and b < 50:
            return "light olive"
        elif r > 150 and g > 200 and b < 150:
            return "light chartreuse"
        elif r < 100 and g > 50 and b < 100:
            return "medium violet red"
        else:
            return "gray"  # Default color

    def save_tags(self, image_name, tags, file_location):
        # Check if the image has already been processed
        if self.is_processed(image_name):
            print(f"{image_name} has already been processed. Skipping.")
            return

        # Add color tags to the existing tags
        color_tags = self.get_main_colors(file_location)  # Get colors from the image
        tags.extend(color_tags)  # Combine existing tags with color tags
        tags = list(set(tags))  # Remove duplicates from tags

        conn = self.create_connection()
        with conn:
            c = conn.cursor()
            tags_str = ', '.join(tags)
            c.execute("INSERT OR REPLACE INTO images (name, tags, file_location, processed) VALUES (?, ?, ?, ?)",
                      (image_name, tags_str, file_location, True))  # Set processed to True

    def get_tags(self, image_name):
        conn = self.create_connection()
        with conn:
            c = conn.cursor()
            c.execute("SELECT tags FROM images WHERE name = ?", (image_name,))
            result = c.fetchone()
            return result[0].split(', ') if result else []

    def get_all_tags(self):
        conn = self.create_connection()
        with conn:
            c = conn.cursor()
            c.execute("SELECT name, tags FROM images")
            results = c.fetchall()
            return {name: tags.split(', ') for name, tags in results}

    def search_images(self, tags):
        conn = self.create_connection()  # Use your existing connection function
        cursor = conn.cursor()
        
        # Create a base query for fuzzy matching
        query = "SELECT name, file_location FROM images WHERE "
        query_conditions = []
        query_params = []

        for tag in tags:
            query_conditions.append("tags LIKE ?")
            query_params.append(f"%{tag}%")  # Fuzzy match using wildcards

        query += " OR ".join(query_conditions)  # Combine conditions with OR

        cursor.execute(query, query_params)
        
        results = cursor.fetchall()
        conn.close()
        
        return [(row[0], row[1]) for row in results]  # Return name and file location

    def reset_database(self):
        conn = self.create_connection()
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS images")  # Drop the images table
        self.create_table(conn)  # Recreate the table
        conn.commit()
        conn.close()

    def is_processed(self, image_name):
        conn = self.create_connection()
        with conn:
            c = conn.cursor()
            c.execute("SELECT processed FROM images WHERE name = ?", (image_name,))
            result = c.fetchone()
            return result[0] == 1 if result else False  # Return True if processed, else False

    def count_files(self):
        conn = self.create_connection()
        with conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM images")
            count = c.fetchone()[0]  # Get the count from the result
        return count

    def get_file_location(self, image_name):
        conn = self.create_connection()
        with conn:
            c = conn.cursor()
            c.execute("SELECT file_location FROM images WHERE name = ?", (image_name,))
            result = c.fetchone()
            return result[0] if result else None