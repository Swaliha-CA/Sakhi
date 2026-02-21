"""
Vercel serverless function entry point for SAKHI backend API
"""
import sys
from pathlib import Path

# Add parent directory to path so we can import app
root_path = Path(__file__).parent.parent
sys.path.insert(0, str(root_path))

# Import the FastAPI app
from app.main_minimal import app

# Export for Vercel
app = app
