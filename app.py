import gradio as gr
import os
from PIL import Image
import tempfile
import shutil
from pathlib import Path
import zipfile
import json
import math

class ImagePrepApp:
    def __init__(self):
        self.images = []
        self.current_index = 0
        self.temp_dir = tempfile.mkdtemp()
        self.output_dir = os.path.join(self.temp_dir, "crops")
        self.thumbnails_dir = os.path.join(self.temp_dir, "thumbnails")
        self.display_dir = os.path.join(self.temp_dir, "display")
        self.selected_for_deletion = set()  # Track selected files for deletion
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.thumbnails_dir, exist_ok=True)
        os.makedirs(self.display_dir, exist_ok=True)
        
        # Preset crop dimensions
        self.crop_presets = {
            "512x512": (512, 512),
            "768x768": (768, 768),
            "1024x1024": (1024, 1024),
            "2048x2048": (2048, 2048),
            "512x768": (512, 768),
            "768x512": (768, 512),
            "Custom": (0, 0)
        }
        
        # Display size options
        self.display_sizes = {
            "Small (600x480)": (600, 480),
            "Medium (800x600)": (800, 600),
            "Large (1000x750)": (1000, 750),
            "X-Large (1200x900)": (1200, 900),
            "Original Size": (0, 0)
        }
        
        # Current zoom and crop settings
        self.current_zoom = 1.0
        self.current_crop_width = 512
        self.current_crop_height = 512
        
    def calculate_gallery_height(self, num_images, columns=8):
        """Calculate optimal gallery height based on number of images"""
        # For galleries to scroll properly in Gradio, we need consistent heights
        # Return a reasonable fixed height that works for most cases
        if num_images <= 8:  # 1 row
            return 150
        elif num_images <= 16:  # 2 rows  
            return 250
        elif num_images <= 24:  # 3 rows
            return 350
        else:  # 4+ rows - use scrolling
            return 400
    
    def calculate_output_gallery_height(self, num_images, columns=6):
        """Calculate optimal output gallery height based on number of images"""
        # For galleries to scroll properly in Gradio, we need consistent heights
        if num_images <= 6:  # 1 row
            return 150
        elif num_images <= 12:  # 2 rows
            return 250
        elif num_images <= 18:  # 3 rows
            return 350
        else:  # 4+ rows - use scrolling
            return 400
        
    def create_thumbnail(self, image_path, size=(150, 150)):
        """Create thumbnail for gallery display"""
        try:
            with Image.open(image_path) as img:
                img.thumbnail(size, Image.Resampling.LANCZOS)
                thumb_filename = f"thumb_{os.path.basename(image_path)}"
                thumb_path = os.path.join(self.thumbnails_dir, thumb_filename)
                img.save(thumb_path, "JPEG", quality=85)
                return thumb_path
        except Exception as e:
            print(f"Error creating thumbnail: {e}")
            return image_path
    
    def create_display_image(self, image_path, display_size_name="Medium (800x600)"):
        """Create display-sized image based on selected display size"""
        try:
            with Image.open(image_path) as img:
                if display_size_name == "Original Size":
                    # Return original image
                    display_filename = f"display_{os.path.basename(image_path)}"
                    display_path = os.path.join(self.display_dir, display_filename)
                    img.save(display_path, "JPEG", quality=95)
                    return display_path, img.size
                else:
                    # Resize to fit within specified size
                    max_size = self.display_sizes[display_size_name]
                    img.thumbnail(max_size, Image.Resampling.LANCZOS)
                    display_filename = f"display_{os.path.basename(image_path)}"
                    display_path = os.path.join(self.display_dir, display_filename)
                    img.save(display_path, "JPEG", quality=90)
                    return display_path, img.size
        except Exception as e:
            print(f"Error creating display image: {e}")
            return image_path, (0, 0)
        
    def load_images_from_folder(self, files):
        """Load images from uploaded files"""
        if not files:
            return "No files uploaded", [], gr.update()
        
        self.images = []
        supported_formats = ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff')
        
        for file in files:
            if file.name.lower().endswith(supported_formats):
                self.images.append(file.name)
        
        if not self.images:
            return "No supported image files found", [], gr.update()
        
        self.current_index = 0
        
        # Create thumbnails for gallery
        thumbnail_paths = []
        for img_path in self.images:
            thumb_path = self.create_thumbnail(img_path)
            thumbnail_paths.append(thumb_path)
        
        return (
            f"✅ Successfully loaded {len(self.images)} images", 
            thumbnail_paths,
            gr.update(visible=True)  # Show cropping tab
        )
    
    def select_from_gallery(self, evt: gr.SelectData, display_size_name):
        """Select image from thumbnail gallery"""
        if evt.index < len(self.images):
            self.current_index = evt.index
            self.current_zoom = 1.0  # Reset zoom
            
            # Create display-sized version for cropping interface
            original_path = self.images[self.current_index]
            display_path, display_size = self.create_display_image(original_path, display_size_name)
            
            # Load display image
            display_image = Image.open(display_path)
            
            return (
                display_image, 
                f"Image {self.current_index + 1} of {len(self.images)} - Display: {display_size[0]}x{display_size[1]}",
                1.0  # Reset zoom slider
            )
        return None, "0/0", 1.0
    
    def update_display_size(self, display_size_name):
        """Update display size when dropdown changes"""
        if not self.images:
            return None, "No images loaded"
        
        # Recreate display image with new size
        original_path = self.images[self.current_index]
        display_path, display_size = self.create_display_image(original_path, display_size_name)
        display_image = Image.open(display_path)
        
        return (
            display_image,
            f"Image {self.current_index + 1} of {len(self.images)} - Display: {display_size[0]}x{display_size[1]}"
        )
    
    def update_crop_dimensions(self, preset_choice, custom_width, custom_height):
        """Update crop dimensions based on preset selection"""
        if preset_choice == "Custom":
            self.current_crop_width = int(custom_width) if custom_width > 0 else 512
            self.current_crop_height = int(custom_height) if custom_height > 0 else 512
            return gr.update(visible=True), custom_width, custom_height
        else:
            width, height = self.crop_presets[preset_choice]
            self.current_crop_width = width
            self.current_crop_height = height
            return gr.update(visible=False), width, height
    
    def update_zoom(self, zoom_value):
        """Update zoom level for cropping"""
        # Ensure zoom_value is a float, not a string
        try:
            zoom_val = float(zoom_value)
            self.current_zoom = zoom_val
            return f"Zoom: {zoom_val:.1f}x"
        except (ValueError, TypeError):
            # If conversion fails, return default
            self.current_zoom = 1.0
            return "Zoom: 1.0x"
    
    def navigate_image(self, direction, display_size_name="Medium (800x600)"):
        """Navigate to next or previous image"""
        if not self.images:
            return None, "No images loaded", 1.0
        
        if direction == "next":
            self.current_index = (self.current_index + 1) % len(self.images)
        elif direction == "prev":
            self.current_index = (self.current_index - 1) % len(self.images)
        
        self.current_zoom = 1.0  # Reset zoom
        
        # Create display-sized version for cropping interface
        original_path = self.images[self.current_index]
        display_path, display_size = self.create_display_image(original_path, display_size_name)
        
        # Load display image
        display_image = Image.open(display_path)
        
        return (
            display_image, 
            f"Image {self.current_index + 1} of {len(self.images)} - Display: {display_size[0]}x{display_size[1]}",
            1.0  # Reset zoom slider
        )
    
    def toggle_gallery_drawer(self, current_visibility):
        """Toggle the visibility of the gallery drawer"""
        return not current_visibility
    
    def process_crop_click(self, image, crop_preset, custom_width, custom_height, zoom_value, display_size_name, evt: gr.SelectData):
        """Process crop when user clicks on image with zoom consideration"""
        if image is None or not self.images:
            return None, "No image loaded"
        
        try:
            # Get crop dimensions
            if crop_preset == "Custom":
                base_crop_width = int(custom_width) if custom_width > 0 else 100
                base_crop_height = int(custom_height) if custom_height > 0 else 100
            else:
                base_crop_width, base_crop_height = self.crop_presets[crop_preset]
            
            # Apply zoom to crop dimensions (CORRECTED: higher zoom = smaller crop area)
            effective_crop_width = int(base_crop_width / zoom_value)
            effective_crop_height = int(base_crop_height / zoom_value)
            
            # Get click coordinates from display image
            click_x = evt.index[0] if evt.index else 0
            click_y = evt.index[1] if evt.index else 0
            
            # Load original full-resolution image
            original_image = Image.open(self.images[self.current_index])
            orig_width, orig_height = original_image.size
            
            # Get display image dimensions
            display_width, display_height = image.size
            
            # Calculate scale factors
            scale_x = orig_width / display_width
            scale_y = orig_height / display_height
            
            # Convert click coordinates to original image coordinates
            orig_click_x = int(click_x * scale_x)
            orig_click_y = int(click_y * scale_y)
            
            # Center crop box on click point in original coordinates
            crop_x = max(0, min(orig_click_x - effective_crop_width // 2, orig_width - effective_crop_width))
            crop_y = max(0, min(orig_click_y - effective_crop_height // 2, orig_height - effective_crop_height))
            
            # Ensure crop dimensions fit within original image
            actual_crop_width = min(effective_crop_width, orig_width - crop_x)
            actual_crop_height = min(effective_crop_height, orig_height - crop_y)
            
            # Crop from original full-resolution image
            cropped = original_image.crop((crop_x, crop_y, crop_x + actual_crop_width, crop_y + actual_crop_height))
            
            # Resize to target dimensions
            cropped = cropped.resize((base_crop_width, base_crop_height), Image.Resampling.LANCZOS)
            
            zoom_info = f" (Zoom: {zoom_value:.1f}x)" if zoom_value != 1.0 else ""
            return cropped, f"Cropped: {base_crop_width}x{base_crop_height} from ({crop_x}, {crop_y}){zoom_info}"
            
        except Exception as e:
            return None, f"Error cropping image: {str(e)}"
    
    def save_crop(self, cropped_image):
        """Save cropped image to output directory"""
        if cropped_image is None:
            return "No cropped image to save", gr.update()
        
        try:
            # Generate filename
            base_name = os.path.splitext(os.path.basename(self.images[self.current_index]))[0]
            crop_count = len([f for f in os.listdir(self.output_dir) if f.startswith(base_name)]) + 1
            output_filename = f"{base_name}_crop_{crop_count}.png"
            output_path = os.path.join(self.output_dir, output_filename)
            
            # Save the image
            cropped_image.save(output_path, "PNG")
            
            # Check if this is the first crop saved - if so, make download tab visible
            total_crops = len([f for f in os.listdir(self.output_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
            tab_update = gr.update(visible=True) if total_crops == 1 else gr.update()
            
            return f"✅ Saved as {output_filename}", tab_update
            
        except Exception as e:
            return f"❌ Error saving image: {str(e)}", gr.update()
    
    def get_output_gallery(self):
        """Get list of output images for gallery"""
        if not os.path.exists(self.output_dir):
            return []
        
        output_files = []
        for filename in sorted(os.listdir(self.output_dir)):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                file_path = os.path.join(self.output_dir, filename)
                output_files.append(file_path)
        
        return output_files
    
    def create_clean_thumbnail(self, image_path, max_thumb_size=150):
        """Create clean thumbnail without text overlay for output gallery"""
        try:
            with Image.open(image_path) as img:
                # Get original dimensions for caption
                width, height = img.size
                
                # Calculate thumbnail size while preserving aspect ratio
                aspect_ratio = width / height
                if aspect_ratio > 1:  # Wider than tall
                    thumb_width = max_thumb_size
                    thumb_height = int(max_thumb_size / aspect_ratio)
                else:  # Taller than wide or square
                    thumb_height = max_thumb_size
                    thumb_width = int(max_thumb_size * aspect_ratio)
                
                # Resize image to calculated thumbnail size
                img_resized = img.resize((thumb_width, thumb_height), Image.Resampling.LANCZOS)
                
                # Save clean thumbnail
                base_filename = os.path.splitext(os.path.basename(image_path))[0]
                clean_filename = f"clean_{base_filename}.jpg"
                clean_path = os.path.join(self.thumbnails_dir, clean_filename)
                img_resized.save(clean_path, "JPEG", quality=85)
                
                return clean_path, f"{width}×{height}"
                
        except Exception as e:
            print(f"Error creating clean thumbnail: {e}")
            return image_path, "Error"

    def toggle_file_selection(self, evt: gr.SelectData):
        """Toggle selection of a file for deletion when left-clicked"""
        try:
            # Get original file paths (not the display tuples)
            original_files = self.get_output_gallery()
            if evt.index < len(original_files):
                file_path = original_files[evt.index]
                filename = os.path.basename(file_path)
                
                if file_path in self.selected_for_deletion:
                    self.selected_for_deletion.remove(file_path)
                    status = f"🔵 Deselected: {filename}"
                else:
                    self.selected_for_deletion.add(file_path)
                    status = f"🔴 Selected for deletion: {filename}"
                
                # Return updated gallery with visual indicators
                updated_gallery = self.get_output_gallery_with_selection_visual()
                selected_names = [os.path.basename(f) for f in self.selected_for_deletion]
                selection_text = f"Selected ({len(selected_names)}): {', '.join(selected_names) if selected_names else 'None'}"
                
                return list(updated_gallery), selection_text, status
            
            # If click failed, return current state
            current_gallery = self.get_output_gallery_with_selection_visual()
            return list(current_gallery), "No file selected", "Click failed"
        except Exception as e:
            current_gallery = self.get_output_gallery_with_selection_visual()
            return list(current_gallery), f"Error: {str(e)}", f"Error selecting file: {str(e)}"
    
    def select_all_files(self):
        """Select all files for deletion"""
        output_files = self.get_output_gallery()
        self.selected_for_deletion = set(output_files)
        selected_names = [os.path.basename(f) for f in self.selected_for_deletion]
        selection_text = f"Selected ({len(selected_names)}): {', '.join(selected_names) if selected_names else 'None'}"
        updated_gallery = self.get_output_gallery_with_selection_visual()
        return updated_gallery, selection_text, f"Selected all {len(selected_names)} files"
    
    def clear_file_selection(self):
        """Clear all file selections"""
        self.selected_for_deletion = set()
        updated_gallery = self.get_output_gallery_with_selection_visual()
        return updated_gallery, "Selected (0): None", "Cleared all selections"
    
    def delete_selected_crops(self):
        """Delete multiple selected crops"""
        if not self.selected_for_deletion:
            updated_gallery = self.get_output_gallery_with_selection_visual()
            return updated_gallery, "No files selected for deletion", "Selected (0): None"
        
        try:
            deleted_count = 0
            deleted_names = []
            for file_path in list(self.selected_for_deletion):
                if os.path.exists(file_path):
                    deleted_names.append(os.path.basename(file_path))
                    os.remove(file_path)
                    deleted_count += 1
            
            # Clear selection after deletion
            self.selected_for_deletion = set()
            updated_gallery = self.get_output_gallery_with_selection_visual()
            return updated_gallery, f"🗑️ Deleted {deleted_count} files: {', '.join(deleted_names)}", "Selected (0): None"
        except Exception as e:
            updated_gallery = self.get_output_gallery_with_selection_visual()
            return updated_gallery, f"❌ Error deleting files: {str(e)}", "Selected (0): None"
    
    def download_all_crops(self):
        """Create a zip file with all cropped images"""
        if not os.path.exists(self.output_dir) or not os.listdir(self.output_dir):
            return None, "No crops to download"
        
        try:
            zip_path = os.path.join(self.temp_dir, "cropped_images.zip")
            
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                for filename in os.listdir(self.output_dir):
                    if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                        file_path = os.path.join(self.output_dir, filename)
                        zipf.write(file_path, filename)
            
            return zip_path, f"📦 Created zip with {len(os.listdir(self.output_dir))} images"
        except Exception as e:
            return None, f"❌ Error creating zip: {str(e)}"
    
    def get_output_gallery_with_selection_visual(self):
        """Get list of output images with selection indicators using Gradio captions"""
        if not os.path.exists(self.output_dir):
            return []
        
        output_files = []
        for filename in sorted(os.listdir(self.output_dir)):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                file_path = os.path.join(self.output_dir, filename)
                
                # Create clean thumbnail and get dimensions
                clean_thumb_path, dimensions = self.create_clean_thumbnail(file_path)
                
                # Create caption with dimensions and selection status
                if file_path in self.selected_for_deletion:
                    caption = f"{dimensions} • 🔴 SELECTED"
                else:
                    caption = f"{dimensions}"
                
                display_item = (clean_thumb_path, caption)
                output_files.append(display_item)
        
        return output_files
    
    def refresh_output_gallery(self):
        """Refresh output gallery with dynamic height"""
        gallery_data = self.get_output_gallery_with_selection_visual()
        return gallery_data

# Initialize the app
app = ImagePrepApp()

# Create the Gradio interface with tabs
with gr.Blocks(title="Image Prep Tool", theme=gr.themes.Soft(), css="""
    #main_crop_image {
        max-height: none !important;
        height: auto !important;
    }
    #main_crop_image img {
        max-height: none !important;
        height: auto !important;
        max-width: 100% !important;
    }
    /* Remove Gradio's default blue selection border */
    #output_gallery .selected,
    #output_gallery .thumbnail.selected {
        border: 1px solid #374151 !important; /* Use default border instead of blue */
        box-shadow: none !important;
        transform: none !important;
    }
    /* Hover effect for better UX */
    #output_gallery .thumbnail:hover {
        border: 2px solid #4a9eff !important;
        box-shadow: 0 0 8px rgba(74, 158, 255, 0.5) !important;
        transform: scale(1.02) !important;
        transition: all 0.2s ease !important;
    }
    .about-section {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    .step-card {
        background: #7382bb;
        border-left: 4px solid #007bff;
        padding: 15px;
        margin: 10px 0;
        border-radius: 0 8px 8px 0;
        color: #212529;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    /* Remove drawer styling - keep it simple */
    .gallery-drawer {
        border: 2px solid #e0e0e0;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 20px;
        background: #fafafa;
        transition: all 0.3s ease;
    }
    /* Drawer toggle button styling */
    .drawer-toggle {
        background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%) !important;
        color: white !important;
        font-weight: bold !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 10px 15px !important;
        margin-bottom: 10px !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2) !important;
    }
    .drawer-toggle:hover {
        background: linear-gradient(135deg, #45a049 0%, #3d8b40 100%) !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 8px rgba(0,0,0,0.3) !important;
    }
""") as demo:
    gr.Markdown("# ✂️ PixelPruner")
    gr.Markdown("Quick and Easy Dataset Prep!")
    
    with gr.Tabs() as tabs:
        # TAB 0: ABOUT & USAGE (NEW - FRONT TAB)
        with gr.Tab("📖 About & Usage", id="about_tab"):
            with gr.Column():
                # Hero Section
                gr.HTML("""
                <div class="about-section">
                    <h2>🎯 Welcome to PixelPruner v1.1</h2>
                    <p style="font-size: 18px; margin-bottom: 0;">
                        Streamline your workflow and achieve perfect image crops every time with PixelPruner! 
                    </p>
                </div>
                """)                

                # How to Use
                gr.Markdown("## 🚀 How to Use PixelPruner")
                
                gr.HTML("""
                <div class="step-card">
                    <h3>Step 1: Load Your Images</h3>
                    <p>Go to the <strong>📂 Load Images</strong> tab and upload your image files. PixelPruner supports PNG, JPG, JPEG, GIF, BMP, and TIFF formats.</p>
                </div>
                """)
                
                gr.HTML("""
                <div class="step-card">
                    <h3>Step 2: Select and Configure</h3>
                    <p>Move to the <strong>✂️ Crop Images</strong> tab. Click on thumbnails to select images, then choose your desired crop dimensions.</p>
                </div>
                """)
                
                gr.HTML("""
                <div class="step-card">
                    <h3>Step 3: Crop with Precision</h3>
                    <p>Click anywhere on the main image to crop at that location. Use the zoom slider to control crop area size.</p>
                </div>
                """)
                
                gr.HTML("""
                <div class="step-card">
                    <h3>Step 4: Save and Manage</h3>
                    <p>Save crops you like, then use the <strong>📦 Preview & Download Crops</strong> tab to review, delete unwanted crops, and download your final dataset as a ZIP file.</p>
                </div>
                """)              
                
                # Technical Details
                gr.Markdown("## ⚙️ Technical Details")
                
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("""
                        **🖼️ Image Processing:**
                        - High-quality LANCZOS resampling for all operations
                        - Crops are extracted from original full-resolution images
                        - Display images are optimized for performance without quality loss
                        - Supports images of any size and aspect ratio
                        """)
                    
                    with gr.Column():
                        gr.Markdown("""
                        **📁 File Management:**
                        - Temporary files are automatically cleaned up
                        - Crops saved as PNG for maximum quality
                        - Batch operations for efficient workflow
                        - ZIP export maintains original quality
                        """)                
               
                gr.Markdown("---")
                gr.Markdown("*Ready to start cropping? Head over to the **📂 Load Images** tab to begin!*")
        
        # TAB 1: IMAGE LOADING
        with gr.Tab("📂 Load Images", id="load_tab"):
            gr.Markdown("## Upload Your Images")
            gr.Markdown("Select multiple image files to begin processing")
            
            with gr.Row():
                with gr.Column():
                    files_input = gr.File(
                        label="Choose Image Files",
                        file_count="multiple",
                        file_types=["image"],
                        height=200
                    )
                    
                    load_status = gr.Textbox(
                        label="Load Status", 
                        interactive=False,
                        placeholder="No images loaded yet..."
                    )
                    
                    gr.Markdown("### 📋 Supported Formats")
                    gr.Markdown("PNG, JPG, JPEG, GIF, BMP, TIFF")
        
        # TAB 2: CROPPING
        with gr.Tab("✂️ Crop Images", id="crop_tab", visible=False) as crop_tab:
            gr.Markdown("## Image Cropping")
            
            with gr.Row():
                # Left column - Image selection and cropping
                with gr.Column(scale=2):
                    # Collapsible Gallery Section
                    gallery_visible = gr.State(True)  # Track drawer visibility state
                    
                    with gr.Row():
                        gr.Markdown("### 🖼️ Select Image to Crop")
                        toggle_btn = gr.Button(
                            "🔽 Hide Gallery", 
                            variant="secondary",
                            size="sm",
                            scale=1
                        )
                    
                    with gr.Column(visible=True) as gallery_section:
                        image_gallery = gr.Gallery(
                            label="Click thumbnail to select image",
                            show_label=True,
                            columns=8,
                            object_fit="cover",
                            allow_preview=False,
                            container=True,
                            interactive=True
                        )
                        
                        with gr.Row():
                            image_info = gr.Textbox(
                                label="Current Image Info", 
                                interactive=False,
                                placeholder="Select an image from the gallery above",
                                scale=2
                            )
                            
                            display_size_dropdown = gr.Dropdown(
                                choices=list(app.display_sizes.keys()),
                                value="Medium (800x600)",
                                label="Display Size",
                                scale=1
                            )
                    
                    gr.Markdown("### 🎯 Click on image to crop at that location")
                    current_image = gr.Image(
                        label="Click to Crop", 
                        type="pil",
                        interactive=True,
                        height=600,
                        container=True,
                        show_label=True,
                        elem_id="main_crop_image",
                        sources=[]
                    )
                    
                    # Navigation buttons
                    with gr.Row():
                        prev_btn = gr.Button("⬅️ Previous Image", variant="secondary", scale=1)
                        next_btn = gr.Button("Next Image ➡️", variant="secondary", scale=1)
                
                # Right column - Crop settings and preview
                with gr.Column(scale=1):
                        gr.Markdown("### 🔲 Crop Settings")
                        
                        crop_preset = gr.Dropdown(
                            choices=list(app.crop_presets.keys()),
                            value="512x512",
                            label="Crop Dimensions"
                        )
                        
                        with gr.Group(visible=False) as custom_group:
                            custom_width = gr.Number(label="Custom Width", value=512, minimum=1)
                            custom_height = gr.Number(label="Custom Height", value=512, minimum=1)
                        
                        # Zoom slider
                        gr.Markdown("### 🔍 Zoom Control")
                        gr.Markdown("*Higher zoom = closer view (smaller crop area)*")
                        zoom_slider = gr.Slider(
                            minimum=0.1,
                            maximum=3.0,
                            step=0.1,
                            value=1.0,
                            label="Zoom Level",
                            interactive=True
                        )
                        zoom_info = gr.Textbox(
                            value="Zoom: 1.0x",
                            label="Zoom Info",
                            interactive=False
                        )
                        
                        # Hidden fields to store current crop dimensions
                        current_crop_width = gr.Number(value=512, visible=False)
                        current_crop_height = gr.Number(value=512, visible=False)
                        
                        gr.Markdown("### 🖼️ Crop Preview")
                        cropped_image = gr.Image(
                            label="Cropped Result", 
                            type="pil",
                            height=300,
                            sources=[]
                        )
                        
                        crop_status = gr.Textbox(
                            label="Crop Info", 
                            interactive=False,
                            placeholder="Click on image to create crop"
                        )
                        
                        save_btn = gr.Button("💾 Save Crop", variant="primary", size="lg")
                        save_status = gr.Textbox(label="Save Status", interactive=False)
        
        # TAB 3: DOWNLOAD MANAGEMENT
        with gr.Tab("📦 Preview & Download Crops", id="download_tab", visible=False) as download_tab:
            gr.Markdown("## Manage Your Cropped Images")
            
            with gr.Row():
                refresh_btn = gr.Button("🔄 Refresh Gallery", variant="secondary")
                download_all_btn = gr.Button("📦 Prepare ZIP for Download", variant="primary")
            
            download_status = gr.Textbox(label="Download Status", interactive=False)
            download_file = gr.File(label="Download ZIP", visible=False)
            
            gr.Markdown("### 🖼️ Saved Crops")
            gr.Markdown("**Left-click on images to select/deselect for deletion**")
            
            output_gallery = gr.Gallery(
                label="Cropped Images",
                show_label=True,
                columns=6,  # Reduced columns to give more space
                object_fit="contain",  # Changed from "cover" to "contain" to preserve aspect ratio
                allow_preview=False,
                show_download_button=False,
                selected_index=None,  # Prevent persistent selection
                elem_id="output_gallery"
            )
            
            # Multi-select for deletion
            gr.Markdown("### 🗑️ Batch Delete")
            gr.Markdown("*Click images above to select them, then use buttons below*")
            
            with gr.Row():
                select_all_btn = gr.Button("☑️ Select All", variant="secondary")
                clear_selection_btn = gr.Button("🔄 Clear Selection", variant="secondary")
                delete_selected_btn = gr.Button("🗑️ Delete Selected", variant="stop")
            
            selected_files_display = gr.Textbox(
                label="Selected Files (click images to select)", 
                interactive=False,
                placeholder="No files selected - click on images above to select them"
            )
            delete_status = gr.Textbox(label="Delete Status", interactive=False)
    
    # Event handlers
    
    # Toggle gallery section visibility
    def update_toggle_button_and_gallery(current_visibility):
        new_visibility = not current_visibility
        if new_visibility:
            button_text = "🔽 Hide Gallery"
        else:
            button_text = "🔼 Show Gallery"
        return new_visibility, gr.update(value=button_text), gr.update(visible=new_visibility)
    
    toggle_btn.click(
        update_toggle_button_and_gallery,
        inputs=[gallery_visible],
        outputs=[gallery_visible, toggle_btn, gallery_section]
    )
    
    # Load images
    files_input.upload(
        app.load_images_from_folder,
        inputs=[files_input],
        outputs=[load_status, image_gallery, crop_tab]
    )
    
    # Gallery selection in crop tab
    image_gallery.select(
        app.select_from_gallery,
        inputs=[display_size_dropdown],
        outputs=[current_image, image_info, zoom_slider]
    )
    
    # Display size change
    display_size_dropdown.change(
        app.update_display_size,
        inputs=[display_size_dropdown],
        outputs=[current_image, image_info]
    )
    
    # Navigation buttons
    prev_btn.click(
        lambda display_size: app.navigate_image("prev", display_size),
        inputs=[display_size_dropdown],
        outputs=[current_image, image_info, zoom_slider]
    )
    
    next_btn.click(
        lambda display_size: app.navigate_image("next", display_size),
        inputs=[display_size_dropdown],
        outputs=[current_image, image_info, zoom_slider]
    )
    
    # Crop preset change handler
    crop_preset.change(
        app.update_crop_dimensions,
        inputs=[crop_preset, current_crop_width, current_crop_height],
        outputs=[custom_group, current_crop_width, current_crop_height]
    )
    
    # Custom dimensions update
    custom_width.change(
        lambda w: w,
        inputs=[custom_width],
        outputs=[current_crop_width]
    )
    
    custom_height.change(
        lambda h: h,
        inputs=[custom_height],
        outputs=[current_crop_height]
    )
    
    # Zoom slider update
    zoom_slider.change(
        app.update_zoom,
        inputs=[zoom_slider],
        outputs=[zoom_info]
    )
    
    # Image click for cropping
    current_image.select(
        app.process_crop_click,
        inputs=[current_image, crop_preset, custom_width, custom_height, zoom_slider, display_size_dropdown],
        outputs=[cropped_image, crop_status]
    )
    
    # Save crop
    save_btn.click(
        app.save_crop,
        inputs=[cropped_image],
        outputs=[save_status, download_tab]
    )
    
    # Download tab functions
    refresh_btn.click(
        app.refresh_output_gallery,
        outputs=[output_gallery]
    )
    
    # Auto-refresh gallery when download tab is selected
    download_tab.select(
        app.refresh_output_gallery,
        outputs=[output_gallery]
    )
    
    # Gallery selection for deletion
    output_gallery.select(
        app.toggle_file_selection,
        outputs=[output_gallery, selected_files_display, delete_status]
    )
    
    # Batch selection controls
    select_all_btn.click(
        app.select_all_files,
        outputs=[output_gallery, selected_files_display, delete_status]
    )
    
    clear_selection_btn.click(
        app.clear_file_selection,
        outputs=[output_gallery, selected_files_display, delete_status]
    )
    
    delete_selected_btn.click(
        app.delete_selected_crops,
        outputs=[output_gallery, delete_status, selected_files_display]
    )
    
    # Download all crops
    download_all_btn.click(
        app.download_all_crops,
        outputs=[download_file, download_status]
    ).then(
        lambda: gr.update(visible=True),
        outputs=[download_file]
    )

if __name__ == "__main__":
    demo.launch(share=True)