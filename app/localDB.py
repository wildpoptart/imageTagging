import sqlite3
from sqlite3 import Error

DATABASE = 'data/image_tags.db'

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
                      tags TEXT,
                      file_location TEXT)''')  # New column for file location
    except Error as e:
        print(e)

def save_tags(image_name, tags, file_location):
    conn = create_connection()
    with conn:
        c = conn.cursor()
        tags_str = ', '.join(tags)
        c.execute("INSERT OR REPLACE INTO images (name, tags, file_location) VALUES (?, ?, ?)",
                  (image_name, tags_str, file_location))

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

def search_images(tags):
    conn = create_connection()  # Use your existing connection function
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

def reset_database():
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS images")  # Drop the images table
    create_table(conn)  # Recreate the table
    conn.commit()
    conn.close()
    
initialize_db()