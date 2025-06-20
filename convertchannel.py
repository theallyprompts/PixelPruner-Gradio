import os
from PIL import Image

def convert_images(folder_path):
    """Convert grayscale and RGBA images in the specified folder to RGB."""
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        
        try:
            with Image.open(file_path) as img:
                # Check if the image is grayscale
                if len(img.split()) == 1:
                    rgb_img = img.convert('RGB')
                    rgb_img.save(file_path)
                    print(f"Converted {filename} from Grayscale to RGB.")
                # Check if the image is RGBA
                elif img.mode == 'RGBA':
                    rgb_img = img.convert('RGB')
                    rgb_img.save(file_path)
                    print(f"Converted {filename} from RGBA to RGB.")
        except Exception as e:
            print(f"Error processing {filename}. Reason: {e}")

# Example usage:
folder_path = "C:\\Your\\Directory\\Path"
convert_images(folder_path)