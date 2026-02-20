"""Pytest configuration and fixtures"""
import pytest
import tempfile
import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np


@pytest.fixture
def temp_image_dir():
    """Create a temporary directory for test images"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_english_image(temp_image_dir):
    """Create a sample image with English text"""
    img = Image.new('RGB', (400, 200), color='white')
    draw = ImageDraw.Draw(img)
    
    # Draw some text
    text = "Ingredients: Water, Sugar, Salt"
    draw.text((20, 80), text, fill='black')
    
    # Save image
    image_path = temp_image_dir / "english_label.jpg"
    img.save(image_path)
    
    return str(image_path)


@pytest.fixture
def sample_hindi_image(temp_image_dir):
    """Create a sample image with Hindi text"""
    img = Image.new('RGB', (400, 200), color='white')
    draw = ImageDraw.Draw(img)
    
    # Draw some text (using English as placeholder for Hindi)
    text = "सामग्री: पानी, चीनी, नमक"
    try:
        draw.text((20, 80), text, fill='black')
    except:
        # Fallback if font doesn't support Hindi
        draw.text((20, 80), "Ingredients: Water, Sugar, Salt", fill='black')
    
    # Save image
    image_path = temp_image_dir / "hindi_label.jpg"
    img.save(image_path)
    
    return str(image_path)


@pytest.fixture
def low_quality_image(temp_image_dir):
    """Create a low quality/blurry image"""
    img = Image.new('RGB', (200, 100), color='white')
    draw = ImageDraw.Draw(img)
    
    # Draw small, low contrast text
    text = "Tiny Text"
    draw.text((10, 40), text, fill='gray')
    
    # Save image
    image_path = temp_image_dir / "low_quality.jpg"
    img.save(image_path, quality=10)  # Low quality JPEG
    
    return str(image_path)


@pytest.fixture
def empty_image(temp_image_dir):
    """Create an empty image with no text"""
    img = Image.new('RGB', (400, 200), color='white')
    
    # Save image
    image_path = temp_image_dir / "empty.jpg"
    img.save(image_path)
    
    return str(image_path)


@pytest.fixture
def invalid_image_path():
    """Return a path to a non-existent image"""
    return "/nonexistent/path/to/image.jpg"
