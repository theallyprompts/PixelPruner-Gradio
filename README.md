# PixelPruner Gradio
PixelPruner Gradio is a web-based image cropping application designed for AI dataset preparation and image processing workflows. Built with Gradio, it offers an intuitive browser interface for cropping, managing, and downloading processed images. Perfect for preparing training datasets, cropping AI-generated art, or any batch image processing task.

This is the Gradio implementation of the Python app/windows desktop app [https://github.com/theallyprompts/PixelPruner](https://github.com/theallyprompts/PixelPruner)

#### Also available as a [HuggingFace Space](https://huggingface.co/spaces/TheAllyPrompts/PixelPruner)!

## Features
### 🚀 **Web-Based Interface**
- **Browser Access**: Run locally or share via Gradio's built-in sharing feature
- **No Installation Required**: Works in any modern web browser
- **Cross-Platform**: Compatible with Windows, macOS, and Linux

### 📁 **Multi-Format Support** 
- **Input Formats**: PNG, JPG, JPEG, GIF, BMP, and TIFF
- **Output Format**: High-quality PNG crops for maximum compatibility
- **Batch Processing**: Upload and process multiple images simultaneously

---

## Quick Start Guide

### 1. **Installation**

```bash
# Clone the repository
git clone https://github.com/theallyprompts/PixelPruner-Gradio
cd PixelPruner

# Install dependencies
pip install gradio pillow

# Run the application
python app.py

#Optional
For WEBP support (if needed)
pip install pillow[webp]
```

# Requirements

## System Requirements
- **Python**: 3.7 or higher
- **RAM**: 4GB minimum, 8GB+ recommended for large images
- **Storage**: Temporary space equal to ~3x total input image size
- **Browser**: Any modern web browser (Chrome, Firefox, Safari, Edge)

## Created By...
[TheAlly](https://www.linkedin.com/in/allynicoll/) - Bringing efficient image processing to the web! If PixelPruner Gradio has improved your workflow, consider [supporting development](https://ko-fi.com/theallyprompts)!
