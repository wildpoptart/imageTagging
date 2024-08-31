from PIL import Image
import pytesseract
import localDB

def extract_text_from_image(image_path):
    """Extract text from an image and return it as a string."""
    try:
        # Open the image file
        img = Image.open(image_path)
        # Use pytesseract to do OCR on the image
        text = pytesseract.image_to_string(img)
        return text.strip()  # Return the extracted text
    except Exception as e:
        print(f"Error extracting text from {image_path}: {e}")
        return ""

def add_text_as_tag(image_name, image_path):
    """Extract text from the image and add it to the tags in the database."""
    extracted_text = extract_text_from_image(image_path)
    if extracted_text:
        # Get existing tags from the database
        existing_tags = localDB.get_tags(image_name)
        if existing_tags:
            new_tags = f"{existing_tags}, {extracted_text}"
        else:
            new_tags = extracted_text
        # Save updated tags back to the database
        localDB.save_tags(image_name, new_tags)
        print(f"Updated tags for {image_name}: {new_tags}")
    else:
        print(f"No text extracted from {image_path}.")
