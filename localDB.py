import sqlite3
from sqlite3 import Error

DATABASE = 'image_tags.db'

def create_connection():
    conn = None
    try:
        conn = sqlite3.connect(DATABASE)
        return conn
    except Error as e:
        print(e)
    return conn

def initialize_db():
    conn = create_connection()
    if conn is not None:
        create_table(conn)
    else:
        print("Error! Cannot create the database connection.")

def create_table(conn):
    try:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS images
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      name TEXT NOT NULL UNIQUE,
                      tags TEXT)''')
    except Error as e:
        print(e)

def save_tags(image_name, tags):
    conn = create_connection()
    with conn:
        c = conn.cursor()
        tags_str = ', '.join(tags)
        c.execute("INSERT OR REPLACE INTO images (name, tags) VALUES (?, ?)",
                  (image_name, tags_str))

def get_tags(image_name):
    conn = create_connection()
    with conn:
        c = conn.cursor()
        c.execute("SELECT tags FROM images WHERE name = ?", (image_name,))
        result = c.fetchone()
        return result[0].split(', ') if result else []

def get_all_tags():
    conn = create_connection()
    with conn:
        c = conn.cursor()
        c.execute("SELECT name, tags FROM images")
        results = c.fetchall()
        return {name: tags.split(', ') for name, tags in results}

def search_images(search_tags):
    conn = create_connection()
    with conn:
        c = conn.cursor()
        query = "SELECT name, tags FROM images WHERE " + " AND ".join(["tags LIKE ?" for _ in search_tags])
        params = ['%' + tag + '%' for tag in search_tags]
        c.execute(query, params)
        results = c.fetchall()
        return {name: tags.split(', ') for name, tags in results}
