# Vercel Deployment Guide for SAKHI

## Overview
This guide will help you deploy both the frontend and backend of SAKHI to Vercel.

## Prerequisites
1. Vercel account (sign up at https://vercel.com)
2. Vercel CLI installed: `npm install -g vercel`
3. Git repository pushed to GitHub

## Deployment Strategy

### Option 1: Single Vercel Project (Recommended for Demo)
Deploy everything in one project with the backend as serverless functions.

### Option 2: Two Separate Projects
- One for frontend (static site)
- One for backend (serverless API)

## Step-by-Step Deployment

### Method 1: Using Vercel Dashboard (Easiest)

#### 1. Deploy Backend + Frontend Together

1. Go to https://vercel.com/dashboard
2. Click "Add New" → "Project"
3. Import your GitHub repository: `Swaliha-CA/Sakhi`
4. Configure the project:
   - **Framework Preset:** Other
   - **Root Directory:** `tinkher`
   - **Build Command:** (leave empty)
   - **Output Directory:** `.`
   - **Install Command:** `pip install -r requirements.txt`

5. Add Environment Variables (if needed):
   - Click "Environment Variables"
   - Add any secrets from your `.env` file

6. Click "Deploy"

7. After deployment, note your URL: `https://your-project.vercel.app`

8. Update the API URL:
   - Go to your project settings
   - Note the deployment URL
   - Update `js/config.js` and `frontend/js/config.js`:
     ```javascript
     BASE_URL: window.location.hostname === 'localhost' 
         ? 'http://localhost:8000' 
         : 'https://your-project.vercel.app',
     ```
   - Commit and push changes (Vercel will auto-redeploy)

### Method 2: Using Vercel CLI

#### 1. Install Vercel CLI
```bash
npm install -g vercel
```

#### 2. Login to Vercel
```bash
vercel login
```

#### 3. Deploy from Project Root
```bash
cd tinkher
vercel
```

Follow the prompts:
- Set up and deploy? **Y**
- Which scope? (select your account)
- Link to existing project? **N**
- Project name? **sakhi** (or your choice)
- Directory? **./tinkher**
- Override settings? **N**

#### 4. Deploy to Production
```bash
vercel --prod
```

### Method 3: Two Separate Deployments

#### Backend Deployment

1. Create a new Vercel project for backend
2. Set root directory to `tinkher`
3. Use these settings:
   ```json
   {
     "builds": [
       {
         "src": "app/main_minimal.py",
         "use": "@vercel/python"
       }
     ],
     "routes": [
       {
         "src": "/api/(.*)",
         "dest": "app/main_minimal.py"
       }
     ]
   }
   ```

4. Note the backend URL: `https://sakhi-backend.vercel.app`

#### Frontend Deployment

1. Create a new Vercel project for frontend
2. Set root directory to `tinkher`
3. Update `js/config.js` with backend URL:
   ```javascript
   BASE_URL: 'https://sakhi-backend.vercel.app'
   ```
4. Deploy as static site

## Configuration Files Created

### 1. `vercel.json`
Main configuration for Vercel deployment:
- Defines Python backend build
- Routes API calls to backend
- Serves static frontend files

### 2. `requirements.txt`
Python dependencies for the backend:
- FastAPI
- Uvicorn
- Pydantic
- Other required packages

### 3. `.vercelignore`
Files to exclude from deployment:
- Test files
- Cache files
- Local database
- Development files

### 4. `api/index.py`
Serverless function entry point for the backend

## Post-Deployment Steps

### 1. Update API URL in Frontend

After getting your Vercel URL, update both config files:

**File: `js/config.js`** (root)
**File: `frontend/js/config.js`**

```javascript
BASE_URL: window.location.hostname === 'localhost' 
    ? 'http://localhost:8000' 
    : 'https://YOUR-ACTUAL-VERCEL-URL.vercel.app',
```

### 2. Test the Deployment

Visit your Vercel URL and test:
- ✅ Main dashboard loads
- ✅ API status shows "Connected"
- ✅ OCR module opens
- ✅ Alternatives module works
- ✅ All modules accessible

### 3. Configure Custom Domain (Optional)

1. Go to Vercel Dashboard → Your Project → Settings → Domains
2. Add your custom domain (e.g., `sakhi.health`)
3. Follow DNS configuration instructions
4. Update `js/config.js` with your custom domain

### 4. Set Up Environment Variables

If you have sensitive data in `.env`:

1. Go to Vercel Dashboard → Your Project → Settings → Environment Variables
2. Add each variable:
   - `DATABASE_URL`
   - `API_KEY`
   - etc.

## Troubleshooting

### Issue: API calls fail with CORS error

**Solution:** Add CORS middleware to `app/main_minimal.py`:
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Issue: Backend routes return 404

**Solution:** Check `vercel.json` routes configuration. API routes should match your FastAPI endpoints.

### Issue: Build fails

**Solution:** 
1. Check `requirements.txt` has all dependencies
2. Ensure Python version compatibility
3. Check Vercel build logs for specific errors

### Issue: Database not persisting

**Solution:** Vercel serverless functions are stateless. For production:
1. Use external database (PostgreSQL, MongoDB Atlas)
2. Or use Vercel KV/Postgres add-ons
3. Update database connection in `app/db/sqlite_manager.py`

## Vercel Limits (Free Tier)

- **Bandwidth:** 100 GB/month
- **Serverless Function Execution:** 100 GB-hours/month
- **Serverless Function Duration:** 10 seconds max
- **Deployments:** Unlimited

For production with high traffic, consider upgrading to Pro plan.

## GitHub Integration

Vercel automatically deploys when you push to GitHub:
- **Push to `main`** → Production deployment
- **Push to other branches** → Preview deployment
- **Pull requests** → Preview deployment with unique URL

## Monitoring

After deployment, monitor your app:
1. Vercel Dashboard → Analytics
2. Check function logs
3. Monitor API response times
4. Set up alerts for errors

## Next Steps

1. ✅ Deploy to Vercel
2. ✅ Update API URLs in config files
3. ✅ Test all modules
4. 🔄 Set up custom domain
5. 🔄 Configure production database
6. 🔄 Set up monitoring and alerts
7. 🔄 Enable HTTPS (automatic with Vercel)

## Support

- Vercel Docs: https://vercel.com/docs
- FastAPI on Vercel: https://vercel.com/guides/deploying-fastapi-with-vercel
- SAKHI Issues: https://github.com/Swaliha-CA/Sakhi/issues

---

**Ready to deploy?** Run `vercel` in the `tinkher` directory!
