"""
Vercel Serverless Entry Point for SAKHI Backend API
This file is the entry point for Vercel's Python runtime.
"""

from app.main_minimal import app

# Vercel will automatically handle the ASGI server
# Do NOT use uvicorn.run() here - Vercel manages that
