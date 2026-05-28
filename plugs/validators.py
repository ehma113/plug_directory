import os
from django.core.exceptions import ValidationError
from PIL import Image # Requires Pillow

MAX_FILE_SIZE_MB = 5 # Maximum 5MB upload
ALLOWED_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.webp', '.gif']

def validate_image_file(image_file):
    """
    CEO FIX: The Image Bouncer. 
    Prevents malicious file uploads, oversized files, and dirty filenames.
    """
    # 1. Check File Size
    if image_file.size > MAX_FILE_SIZE_MB * 1024 * 1024:
        raise ValidationError(f'Image file too large ( > {MAX_FILE_SIZE_MB}MB ).')

    # 2. Check Extension
    ext = os.path.splitext(image_file.name)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(f'Unsupported file type: {ext}. Only images are allowed.')

    # 3. Verify it's a REAL image (Not a fake script renamed to .jpg)
    try:
        img = Image.open(image_file)
        img.verify() # Verifies the file data is a valid image
    except Exception:
        raise ValidationError('Uploaded file is not a valid image or is corrupted.')
    
    # 4. Sanitize filename (Remove paths/directories)
    image_file.name = os.path.basename(image_file.name)
