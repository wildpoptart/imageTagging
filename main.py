from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
import os
from PIL import Image
import torch
from torchvision import transforms
from torchvision.models import resnet50, ResNet50_Weights
from typing import List, Dict
import multiprocessing
import json
from functools import partial
import pyexiv2
from io import BytesIO
import base64
import localDB
import logging

# Set up logging
logging.basicConfig(filename='main_api.log', level=logging.DEBUG, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI()

class FolderRequest(BaseModel):
    folder: str

class TagsUpdateRequest(BaseModel):
    filename: str
    tags: List[str]

class SearchRequest(BaseModel):
    tags: List[str]

class ProcessingStatus(BaseModel):
    total: int
    processed: int
    current_file: str

processing_status = ProcessingStatus(total=0, processed=0, current_file="")

selected_folder = ""

# Load pre-trained ResNet model
logger.info("Loading pre-trained ResNet model")
model = resnet50(weights=ResNet50_Weights.DEFAULT)
model.eval()

# Image preprocessing
preprocess = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

# Load ImageNet class labels
logger.info("Loading ImageNet class labels")
with open("imagenet_classes.txt", "r") as f:
    categories = [s.strip() for s in f.readlines()]

@app.get("/")
async def root():
    logger.info("Root endpoint accessed")
    return {"message": "Image Tagger API is running"}

@app.post("/set_folder")
async def set_folder(folder_request: FolderRequest):
    global selected_folder
    selected_folder = folder_request.folder
    logger.info(f"Folder set to: {selected_folder}")
    return {"message": f"Folder set to: {selected_folder}"}

@app.get("/process_images")
async def process_images(background_tasks: BackgroundTasks):
    logger.info("Processing images requested")
    if not selected_folder:
        logger.warning("No folder selected for processing")
        return {"error": "No folder selected"}

    global processing_status
    image_files = [f for f in os.listdir(selected_folder) if is_supported_image(f)]
    processing_status = ProcessingStatus(total=len(image_files), processed=0, current_file="")
    
    logger.info(f"Starting background task to process {len(image_files)} images")
    background_tasks.add_task(process_images_task, background_tasks)
    
    return {"message": "Processing started"}

@app.get("/get_tags")
async def get_tags():
    logger.info("Retrieving all tags")
    return localDB.get_all_tags()

async def process_images_task(background_tasks):
    logger.info("Starting image processing task")
    for filename in os.listdir(selected_folder):
        if is_supported_image(filename):
            file_path = os.path.join(selected_folder, filename)
            logger.debug(f"Processing image: {file_path}")
            try:
                tags = await process_image(file_path)
                localDB.save_tags(filename, tags)
                logger.info(f"Tags saved to database for {filename}: {tags}")
            except Exception as e:
                logger.error(f"Error processing {filename}: {str(e)}")
            # Update processing status
            processing_status.processed += 1
            processing_status.current_file = filename
            logger.debug(f"Processed {processing_status.processed} out of {processing_status.total} images")
    logger.info("Image processing task completed")

async def process_image(file_path):
    logger.debug(f"Processing individual image: {file_path}")
    filename = os.path.basename(file_path)
    tags = generate_tags(file_path)
    
    # Save tags to the database instead of the image
    localDB.save_tags(filename, tags)
    logger.info(f"Tags saved to database for {filename}: {tags}")
    
    return tags

@app.get("/processing_status")
async def get_processing_status():
    logger.debug(f"Current processing status: {processing_status}")
    return processing_status

@app.post("/update_tags")
async def update_tags(data: dict):
    logger.info(f"Updating tags for: {data.get('filename')}")
    filename = data.get("filename")
    tags = data.get("tags")
    if not filename or tags is None:
        logger.warning("Invalid data for tag update")
        return {"error": "Invalid data"}
    
    # Update the database
    localDB.save_tags(filename, tags)
    
    logger.info(f"Tags updated successfully for: {filename}")
    return {"message": "Tags updated successfully"}

@app.post("/search")
async def search_images(search_request: SearchRequest):
    logger.info(f"Searching images with tags: {search_request.tags}")
    return localDB.search_images(search_request.tags)

def is_supported_image(filename):
    return filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp'))

def generate_tags(image_path):
    logger.debug(f"Generating tags for: {image_path}")
    try:
        image = Image.open(image_path)
        if image.mode != 'RGB':
            image = image.convert('RGB')
        input_tensor = preprocess(image)
        input_batch = input_tensor.unsqueeze(0)

        with torch.no_grad():
            output = model(input_batch)

        probabilities = torch.nn.functional.softmax(output[0], dim=0)
        top5_prob, top5_catid = torch.topk(probabilities, 5)
        
        tags = [categories[idx] for idx in top5_catid]
        logger.debug(f"Generated tags for {image_path}: {tags}")
        return tags
    except Exception as e:
        logger.error(f"Error generating tags for {image_path}: {str(e)}")
        return []

def save_tags_to_image(file_path, tags):
    logger.debug(f"Saving tags to image: {file_path}")
    try:
        tags_str = ", ".join(tags)
        
        with pyexiv2.Image(file_path) as img:
            # Save tags in the Iptc.Application2.Keywords field
            img.modify_iptc({'Iptc.Application2.Keywords': tags})
            # Also save as XMP for better compatibility
            img.modify_xmp({'Xmp.dc.subject': tags})
        
        logger.info(f"Tags saved to {file_path}: {tags}")
    except Exception as e:
        logger.error(f"Error saving tags to {file_path}: {str(e)}")

# Initialize the database
logger.info("Initializing database")
localDB.initialize_db()

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting FastAPI server")
    uvicorn.run(app, host="0.0.0.0", port=8000)