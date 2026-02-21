# Quick Deploy to Vercel - SAKHI

## 🚀 Two Deployment Options

### Option A: Combined Deployment (Easiest - One URL for Everything)
Deploy frontend + backend together in one Vercel project.

### Option B: Separate Deployments (Recommended for Production)
Deploy frontend and backend as separate projects.

---

## Option A: Combined Deployment (Recommended for Demo)

### Step 1: Install Vercel CLI
```bash
npm install -g vercel
```

### Step 2: Login to Vercel
```bash
vercel login
```

### Step 3: Deploy from tinkher directory
```bash
cd tinkher
vercel
```

Answer the prompts:
- **Set up and deploy?** Y
- **Which scope?** (select your account)
- **Link to existing project?** N
- **Project name?** sakhi
- **Directory?** ./
- **Override settings?** N

### Step 4: Deploy to Production
```bash
vercel --prod
```

### Step 5: Update API URL
After deployment, you'll get a URL like: `https://sakhi-xyz.vercel.app`

Update these files:
1. `js/config.js` (line 3)
2. `frontend/js/config.js` (line 3)

Replace:
```javascript
BASE_URL: window.location.hostname === 'localhost' 
    ? 'http://localhost:8000' 
    : 'https://your-vercel-backend.vercel.app',
```

With your actual URL:
```javascript
BASE_URL: window.location.hostname === 'localhost' 
    ? 'http://localhost:8000' 
    : 'https://sakhi-xyz.vercel.app',
```

### Step 6: Commit and Push
```bash
git add .
git commit -m "Update API URL for Vercel deployment"
git push origin main
```

Vercel will automatically redeploy!

---

## Option B: Separate Deployments

### Backend Deployment

#### Step 1: Deploy Backend
```bash
cd tinkher
vercel --name sakhi-backend --config vercel-backend.json
```

Note the URL: `https://sakhi-backend-xyz.vercel.app`

#### Step 2: Deploy to Production
```bash
vercel --prod --name sakhi-backend --config vercel-backend.json
```

### Frontend Deployment

#### Step 1: Update API URL
Edit `js/config.js` and `frontend/js/config.js`:
```javascript
BASE_URL: window.location.hostname === 'localhost' 
    ? 'http://localhost:8000' 
    : 'https://sakhi-backend-xyz.vercel.app',
```

#### Step 2: Deploy Frontend
```bash
vercel --name sakhi-frontend --config vercel-frontend.json
```

#### Step 3: Deploy to Production
```bash
vercel --prod --name sakhi-frontend --config vercel-frontend.json
```

---

## Using Vercel Dashboard (No CLI Needed)

### Method 1: Import from GitHub

1. Go to https://vercel.com/new
2. Click "Import Git Repository"
3. Select your repository: `Swaliha-CA/Sakhi`
4. Configure:
   - **Root Directory:** `tinkher`
   - **Framework Preset:** Other
   - **Build Command:** (leave empty)
   - **Output Directory:** `.`
   - **Install Command:** `pip install -r requirements.txt`
5. Click "Deploy"
6. Wait 2-3 minutes for deployment
7. Get your URL and update config files
8. Push changes to GitHub (auto-redeploys)

### Method 2: Drag & Drop (Quick Test)

1. Go to https://vercel.com/new
2. Drag the `tinkher` folder into the upload area
3. Wait for deployment
4. Test your app!

---

## Post-Deployment Checklist

- [ ] Visit your Vercel URL
- [ ] Check API status indicator (should show "Connected")
- [ ] Test OCR module
- [ ] Test Alternatives module
- [ ] Test Voice AI module
- [ ] Test Notifications module
- [ ] Test Exposure Tracking module
- [ ] Verify all 15 modules are visible
- [ ] Check Malayalam language support

---

## Troubleshooting

### Issue: "Module not found" error
**Solution:** Make sure `requirements.txt` is in the `tinkher` directory

### Issue: API returns 404
**Solution:** Check that `api/index.py` exists and `vercel.json` routes are correct

### Issue: CORS errors
**Solution:** CORS is already configured in `app/main_minimal.py`. If issues persist, check browser console for specific errors.

### Issue: Frontend loads but API offline
**Solution:** 
1. Check if backend deployed successfully
2. Verify API URL in `js/config.js` matches your Vercel backend URL
3. Check Vercel function logs for errors

### Issue: Database errors
**Solution:** SQLite doesn't persist on Vercel serverless. For production:
- Use Vercel Postgres
- Or use external database (Supabase, PlanetScale, etc.)

---

## Environment Variables (If Needed)

If you have secrets in `.env`:

1. Go to Vercel Dashboard → Your Project → Settings → Environment Variables
2. Add variables:
   - `DATABASE_URL`
   - `API_KEY`
   - etc.
3. Redeploy

---

## Custom Domain (Optional)

1. Go to Vercel Dashboard → Your Project → Settings → Domains
2. Add domain: `sakhi.health` or `app.sakhi.health`
3. Follow DNS instructions
4. Update config files with custom domain

---

## Monitoring

After deployment:
1. Check Vercel Dashboard → Analytics
2. Monitor function execution times
3. Check error logs
4. Set up alerts

---

## Cost (Free Tier Limits)

- ✅ 100 GB bandwidth/month
- ✅ 100 GB-hours serverless execution/month
- ✅ Unlimited deployments
- ✅ Automatic HTTPS
- ✅ Global CDN

Perfect for demos and small-scale production!

---

## Quick Commands Reference

```bash
# Deploy preview
vercel

# Deploy production
vercel --prod

# Check deployment status
vercel ls

# View logs
vercel logs

# Remove deployment
vercel rm sakhi
```

---

## Need Help?

- Vercel Docs: https://vercel.com/docs
- FastAPI on Vercel: https://vercel.com/guides/deploying-fastapi-with-vercel
- GitHub Issues: https://github.com/Swaliha-CA/Sakhi/issues

---

**Ready? Run `vercel` in the tinkher directory!** 🚀
