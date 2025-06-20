import os
import shutil
from PIL import Image, ImageOps, UnidentifiedImageError

def check_images(source_dir, destination_dir):
    if not os.path.exists(destination_dir):
        os.makedirs(destination_dir)

    for root, dirs, files in os.walk(source_dir):
        for file in files:
            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                file_path = os.path.join(root, file)
                try:
                    with Image.open(file_path) as img:
                        img.verify()  # Verify if the image is corrupted
                        img = Image.open(file_path)  # Reopen for further checks
                        ImageOps.exif_transpose(img)  # Simple operation to check loadability
                except (IOError, UnidentifiedImageError):
                    print(f"Moving corrupted/truncated image: {file_path}")
                    shutil.move(file_path, os.path.join(destination_dir, file))

if __name__ == "__main__":
    source_directory = input("Enter the source directory path: ")
    destination_directory = os.path.join(source_directory, 'TruncatedImages')
    check_images(source_directory, destination_directory)
