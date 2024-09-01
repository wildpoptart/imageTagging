import cv2
import os
import time
import logging
import numpy as np
from .localDB import LocalDB

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.FileHandler('logs/face_detection.log')  # Log to a file
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Load the gender detection model
gender_net = cv2.dnn.readNetFromCaffe('facial_detection/gender_deploy.prototxt', 'facial_detection/gender_net.caffemodel')
gender_list = ['Male', 'Female']

def detect_faces(image_path):
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    
    # Load the image
    image = cv2.imread(image_path)
    if image is None:
        logger.error(f"Image not found: {image_path}")
        return None, None  # Return None for both if the image is not found

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)

    if len(faces) > 0:
        logger.info(f"Detected {len(faces)} face(s) in {image_path}")
    else:
        logger.info(f"No faces detected in {image_path}")

    return faces, image  # Return detected faces and the image

def classify_gender(face_image):
    # Prepare the image for gender classification
    blob = cv2.dnn.blobFromImage(face_image, 1.0, (227, 227), (104.0, 177.0, 123.0))
    gender_net.setInput(blob)
    gender_preds = gender_net.forward()
    gender = gender_list[gender_preds[0].argmax()]  # Get the gender with the highest probability
    return gender

def face_detection_thread(image_path, localDB):
    logger.info(f"Starting face detection for {image_path}")
    while True:
        faces, image = detect_faces(image_path)
        if faces is None or image is None:
            logger.error(f"Face detection failed for {image_path}. Exiting thread.")
            break  # Exit the thread if face detection fails

        for (x, y, w, h) in faces:
            face_image = image[y:y+h, x:x+w]  # Extract the face region
            gender = classify_gender(face_image)  # Classify gender
            logger.info(f"Detected {gender} in {image_path}")

            # If a face is detected, add the 'face' and gender tags
            existing_tags = localDB.get_tags(os.path.basename(image_path))
            if 'face' not in existing_tags:
                existing_tags.append('face')
            if gender.lower() not in existing_tags:
                existing_tags.append(gender.lower())  # Add 'male' or 'female' tag

            localDB.save_tags(os.path.basename(image_path), existing_tags, image_path)
            logger.info(f"Added tags to {image_path}: {existing_tags}")

        time.sleep(5)  # Check every 5 seconds
