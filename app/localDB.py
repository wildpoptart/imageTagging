import sqlite3
from sqlite3 import Error
from PIL import Image
from colorthief import ColorThief
import os

class LocalDB:
    DATABASE = 'data/image_tags.db'

    def __init__(self):
        self.initialize_db()
        self.color_rgb_values = [
            (255, 0, 0),      # red
            (0, 255, 0),      # green
            (0, 0, 255),      # blue
            (255, 255, 0),    # yellow
            (128, 0, 128),    # purple
            (255, 165, 0),    # orange
            (255, 192, 203),  # pink
            (165, 42, 42),    # brown
            (128, 128, 128),  # gray
            (0, 0, 0),        # black
            (255, 255, 255),  # white
            (0, 255, 255),    # cyan
            (255, 0, 255),    # magenta
            (0, 255, 0),      # lime
            (75, 0, 130),     # indigo
            (0, 128, 128),    # teal
            (128, 0, 0),      # maroon
            (0, 0, 128),      # navy
            (128, 128, 0),    # olive
            (192, 192, 192),  # silver
            (0, 255, 255),    # aqua
            (255, 0, 255),    # fuchsia
            (220, 20, 60),    # crimson
            (255, 127, 80),   # coral
            (240, 230, 140),  # khaki
            (221, 160, 221),  # plum
            (238, 130, 238),  # violet
            (210, 180, 140),  # tan
            (64, 224, 208),   # turquoise
            (250, 128, 114),  # salmon
            (255, 215, 0),    # gold
            (218, 112, 214),  # orchid
            (230, 230, 250),  # lavender
            (245, 245, 220),  # beige
            (255, 250, 205),  # lemon
            (255, 255, 0),    # mustard
            (0, 128, 0),      # emerald
            (255, 0, 0),      # ruby
            (0, 0, 255),      # sapphire
            (138, 43, 226),   # blueviolet
            (0, 255, 127),    # springgreen
            (240, 230, 140),  # khaki
            (255, 248, 220),  # bisque
            (139, 69, 19),    # saddle brown
            (210, 180, 140),  # tan
            (255, 127, 80),   # coral
            (184, 134, 11),   # dark goldenrod
            (205, 92, 92),    # indian red
            (165, 42, 42),    # brown
            (178, 34, 34),    # firebrick
            (139, 69, 19),    # saddle brown
            (85, 107, 47),    # dark olive green
            (107, 142, 35),   # olive drab
            (124, 252, 0),    # lawn green
            (0, 100, 0),      # dark green
            (154, 205, 50),   # yellow green
            (34, 139, 34),    # forest green
            (50, 205, 50),    # lime green
            (144, 238, 144),  # light green
            (143, 188, 143),  # light sea green
            (46, 139, 87),    # sea green
            (60, 179, 113),   # medium sea green
            (32, 178, 170),   # light sea green
            (0, 255, 255),    # cyan
            (0, 206, 209),    # dark turquoise
            (72, 209, 204),   # medium turquoise
            (47, 79, 79),     # dark slate gray
            (0, 128, 128),    # teal
            (0, 139, 139),    # dark cyan
            (0, 191, 255),    # deep sky blue
            (30, 144, 255),   # dodger blue
            (135, 206, 235),  # sky blue
            (70, 130, 180),   # steel blue
            (176, 196, 222),  # light steel blue
            (173, 216, 230),  # light blue
            (176, 224, 230),  # powder blue
            (175, 238, 238),  # pale turquoise
            (240, 248, 255),  # alice blue
            (0, 191, 255),    # deep sky blue
            (100, 149, 237),  # cornflower blue
            (25, 25, 112),    # midnight blue
            (0, 0, 128),      # navy
            (0, 0, 139),      # dark blue
            (0, 0, 205),      # medium blue
            (65, 105, 225),   # royal blue
            (138, 43, 226),   # blue violet
            (75, 0, 130),     # indigo
            (72, 61, 139),    # dark slate blue
            (106, 90, 205),   # slate blue
            (123, 104, 238),  # medium slate blue
            (147, 112, 219),  # medium purple
            (139, 0, 139),    # dark magenta
            (148, 0, 211),    # dark violet
            (153, 50, 204),   # medium orchid
            (186, 85, 211),   # medium violet red
            (128, 0, 128),    # purple
            (216, 191, 216),  # thistle
            (221, 160, 221),  # plum
            (238, 130, 238),  # violet
            (255, 0, 255),    # magenta
            (218, 112, 214),  # orchid
            (199, 21, 133),   # medium violet red
            (219, 112, 147),  # pale violet red
            (255, 20, 147),   # deep pink
            (255, 105, 180),  # hot pink
            (255, 182, 193),  # light pink
            (255, 192, 203),  # pink
            (250, 235, 215),  # beige
            (245, 245, 220)   # light gray
        ]
        print(len(self.color_rgb_values))

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
        colors = [
            "red",
            "green",
            "blue",
            "yellow",
            "purple",
            "orange",
            "pink",
            "brown",
            "gray",
            "black",
            "white",
            "cyan",
            "magenta",
            "lime",
            "indigo",
            "teal",
            "maroon",
            "navy",
            "olive",
            "silver",
            "aqua",
            "fuchsia",
            "crimson",
            "coral",
            "khaki",
            "plum",
            "violet",
            "tan",
            "turquoise",
            "salmon",
            "gold",
            "orchid",
            "lavender",
            "beige",
            "lemon",
            "mustard",
            "emerald",
            "ruby",
            "sapphire",
            "blueviolet",
            "springgreen",
            "khaki",
            "bisque",
            "saddle brown",
            "tan",
            "coral",
            "dark goldenrod",
            "indian red",
            "brown",
            "firebrick",
            "saddle brown",
            "dark olive green",
            "olive drab",
            "lawn green",
            "dark green",
            "yellow green",
            "forest green",
            "lime green",
            "light green",
            "light sea green",
            "sea green",
            "medium sea green",
            "light sea green",
            "cyan",
            "dark turquoise",
            "medium turquoise",
            "dark slate gray",
            "teal",
            "dark cyan",
            "deep sky blue",
            "dodger blue",
            "sky blue",
            "steel blue",
            "light steel blue",
            "light blue",
            "powder blue",
            "pale turquoise",
            "alice blue",
            "deep sky blue",
            "cornflower blue",
            "midnight blue",
            "navy",
            "dark blue",
            "medium blue",
            "royal blue",
            "blue violet",
            "indigo",
            "dark slate blue",
            "slate blue",
            "medium slate blue",
            "medium purple",
            "dark magenta",
            "dark violet",
            "medium orchid",
            "medium violet red",
            "purple",
            "thistle",
            "plum",
            "violet",
            "magenta",
            "orchid",
            "medium violet red",
            "pale violet red",
            "deep pink",
            "hot pink",
            "light pink",
            "pink",
            "beige",
            "light gray"
        ]
        
        # Ensure colors and color_rgb_values have the same length
        colors = colors[:len(self.color_rgb_values)]
        
        # Calculate the closest color based on Euclidean distance
        distances = [(r - c[0])**2 + (g - c[1])**2 + (b - c[2])**2 for c in self.color_rgb_values]
        closest_color_index = distances.index(min(distances))
        return colors[closest_color_index]

    def save_tags(self, image_name, tags, file_location):
        # Add color tags to the existing tags
        color_tags = self.get_main_colors(file_location)  # Get colors from the image
        tags.extend(color_tags)  # Combine existing tags with color tags
        tags = list(set(tags))  # Remove duplicates from tags

        conn = self.create_connection()
        with conn:
            c = conn.cursor()
            tags_str = ', '.join(tags)
            c.execute("""
                INSERT OR REPLACE INTO images (name, tags, file_location, processed)
                VALUES (?, ?, ?, ?)
            """, (image_name, tags_str, file_location, True))

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
            return bool(result and result[0])

    def set_processed(self, image_name, processed):
        conn = self.create_connection()
        with conn:
            c = conn.cursor()
            c.execute("UPDATE images SET processed = ? WHERE name = ?", (processed, image_name))

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