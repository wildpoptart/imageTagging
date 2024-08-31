# Image Tags Database

This project is a simple SQLite database application for managing image tags. It allows you to create a database, save tags for images, retrieve tags, and search for images based on tags.

## Features

- Create and initialize a SQLite database.
- Save tags associated with images.
- Retrieve tags for a specific image.
- Get all tags for all images.
- Search for images based on tags.

## Requirements

- Python 3.x
- SQLite3

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd <repository-directory>
   ```

2. Install the required packages (if any):
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. Initialize the database:
   ```python
   from localDB import initialize_db
   initialize_db()
   ```

2. Save tags for an image:
   ```python
   from localDB import save_tags
   save_tags('image1.jpg', ['tag1', 'tag2'])
   ```

3. Retrieve tags for an image:
   ```python
   from localDB import get_tags
   tags = get_tags('image1.jpg')
   print(tags)
   ```

4. Search for images by tags:
   ```python
   from localDB import search_images
   results = search_images(['tag1'])
   print(results)
   ```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.