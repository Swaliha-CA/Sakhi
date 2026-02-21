# SAKHI - Quick Start Guide

Get the complete SAKHI platform running in 5 minutes!

## Prerequisites

- Python 3.8+
- pip (Python package manager)
- Modern web browser

## Step 1: Install Dependencies

```bash
cd tinkher
pip install -r requirements.txt
```

## Step 2: Set Up Environment

Create a `.env` file (optional, has defaults):

```bash
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=True

# Database
DATABASE_URL=sqlite:///./data/local.db

# Redis (optional)
REDIS_URL=redis://localhost:6379

# LLM API Keys (optional)
OPENAI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here
```

## Step 3: Initialize Database

```bash
python -c "from app.db.sqlite_manager import get_sqlite_manager; get_sqlite_manager()"
```

## Step 4: Seed Sample Data (Optional)

```bash
python app/db/seed_alternative_products.py
```

## Step 5: Start Backend Server

```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

## Step 6: Start Frontend

Open a new terminal:

```bash
cd frontend
python -m http.server 8080
```

## Step 7: Access the Application

Open your browser and navigate to:
- **Frontend:** http://localhost:8080
- **API Docs:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/health

## Features Available

### 1. OCR Product Scanner
- Upload product images
- Extract text in multiple languages
- Get toxicity scores
- Find safer alternatives

### 2. Product Alternatives
- Search by category
- Filter by price and region
- Add to shopping list
- Export shopping list

### 3. Voice AI Screening
- EPDS screening
- PHQ-9 screening
- Multi-language support
- Real-time transcription

### 4. Notifications
- Product updates
- Health alerts
- Shopping reminders

## API Endpoints

### OCR
- `POST /api/v1/ocr/extract-text` - Extract text from image
- `POST /api/v1/ocr/detect-language` - Detect language

### Alternatives
- `POST /api/v1/alternatives/find` - Find alternatives
- `GET /api/v1/alternatives/shopping-list/{user_id}` - Get shopping list
- `POST /api/v1/alternatives/shopping-list` - Add to list
- `DELETE /api/v1/alternatives/shopping-list/{user_id}/{item_id}` - Remove

### Voice
- `POST /api/v1/voice/stt` - Speech to text
- `POST /api/v1/voice/tts` - Text to speech
- `POST /api/v1/voice/screening/start` - Start screening
- `POST /api/v1/voice/screening/respond` - Respond to question

### Notifications
- `GET /api/v1/alternatives/notifications/{user_id}` - Get notifications
- `POST /api/v1/alternatives/notifications/{user_id}/{notification_id}/read` - Mark read

## Testing the APIs

### Using cURL

**Health Check:**
```bash
curl http://localhost:8000/health
```

**OCR Extract (with image):**
```bash
curl -X POST "http://localhost:8000/api/v1/ocr/extract-text" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@product_label.jpg"
```

**Find Alternatives:**
```bash
curl -X POST "http://localhost:8000/api/v1/alternatives/find" \
  -H "Content-Type: application/json" \
  -d '{
    "product_category": "cosmetics",
    "current_score": 45,
    "limit": 5
  }'
```

### Using Swagger UI

Navigate to http://localhost:8000/docs for interactive API documentation.

## Troubleshooting

### Backend Won't Start

**Issue:** Port 8000 already in use
```bash
# Find and kill process
lsof -ti:8000 | xargs kill -9  # Mac/Linux
netstat -ano | findstr :8000   # Windows
```

**Issue:** Module not found
```bash
pip install -r requirements.txt --upgrade
```

### Frontend Can't Connect to Backend

1. Check backend is running: `curl http://localhost:8000/health`
2. Check CORS settings in `app/main.py`
3. Verify `frontend/js/config.js` has correct BASE_URL

### Database Issues

**Reset database:**
```bash
rm data/local.db
python -c "from app.db.sqlite_manager import get_sqlite_manager; get_sqlite_manager()"
```

### OCR Not Working

**Issue:** No OCR engines available
- Install Tesseract OCR: https://github.com/tesseract-ocr/tesseract
- Or use cloud OCR services (configure in `.env`)

### Voice Features Not Working

**Issue:** Microphone access denied
- Grant microphone permissions in browser
- Use HTTPS or localhost (required for getUserMedia API)

**Issue:** Speech recognition fails
- Check Bhashini API configuration
- Verify internet connection for cloud STT

## Development Mode

### Hot Reload Backend
```bash
uvicorn app.main:app --reload
```

### Watch Frontend Changes
Use a tool like `browser-sync`:
```bash
npx browser-sync start --server frontend --files "frontend/**/*"
```

## Production Deployment

### Backend
```bash
# Install production server
pip install gunicorn

# Run with gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Frontend
1. Build and minify assets
2. Deploy to static hosting (Netlify, Vercel, GitHub Pages)
3. Update `API_CONFIG.BASE_URL` to production backend URL

## Next Steps

1. **Explore the Demo:** Try all features in the frontend
2. **Read API Docs:** Visit http://localhost:8000/docs
3. **Check Tests:** Run `pytest tests/`
4. **Customize:** Modify components in `frontend/js/components/`
5. **Add Features:** Extend backend services in `app/services/`

## Support

- **Documentation:** See README.md and frontend/README.md
- **API Reference:** http://localhost:8000/docs
- **GitHub:** https://github.com/Swaliha-CA/Sakhi

## Quick Commands Reference

```bash
# Start everything
cd tinkher
python -m uvicorn app.main:app --reload &
cd frontend && python -m http.server 8080

# Run tests
pytest tests/ -v

# Check code quality
flake8 app/
black app/

# View logs
tail -f logs/app.log

# Stop all
pkill -f uvicorn
pkill -f "http.server"
```

---

**You're all set!** 🚀

The SAKHI platform is now running with:
- ✅ Backend API at http://localhost:8000
- ✅ Frontend UI at http://localhost:8080
- ✅ Full API integration
- ✅ Real-time features
- ✅ Production-ready code

Enjoy exploring the platform!
