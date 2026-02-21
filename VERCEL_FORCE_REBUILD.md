# Force Vercel to Rebuild with Python Runtime

## The Problem
Vercel is still using an old cached build that doesn't detect Python. Even though we added:
- ✅ `api/index.py` (entry point)
- ✅ `vercel.json` (Python runtime config)
- ✅ `requirements.txt` (dependencies)

Vercel needs to be told to **rebuild from scratch**.

## Solution: Manual Redeploy in Vercel Dashboard

### Step 1: Go to Vercel Dashboard
1. Visit https://vercel.com/dashboard
2. Find your project: **sakhitinkerher**
3. Click on it

### Step 2: Go to Deployments Tab
1. Click "Deployments" in the top menu
2. You'll see a list of all deployments

### Step 3: Redeploy with Cache Clear
1. Find the LATEST deployment (should be from today)
2. Click the **three dots (⋯)** on the right
3. Select **"Redeploy"**
4. **IMPORTANT:** Check the box that says:
   ```
   ☑ Use existing Build Cache
   ```
   **UNCHECK THIS BOX!** (This forces a fresh build)
5. Click **"Redeploy"**

### Step 4: Watch the Build Logs
1. Click on the new deployment that's building
2. Click "Building" to see live logs
3. Look for these SUCCESS indicators:

```
✓ Installing Python dependencies...
✓ Installing sqlalchemy==2.0.36
✓ Installing fastapi==0.115.0
✓ Build completed
```

### Step 5: Test the Deployment
Once build completes (2-3 minutes), test:

```bash
# Health check
curl https://sakhitinkerher.vercel.app/health

# API docs
https://sakhitinkerher.vercel.app/docs

# ASHA endpoint
curl https://sakhitinkerher.vercel.app/api/v1/asha/workers
```

## Alternative: Redeploy via CLI

If you have Vercel CLI installed:

```bash
cd tinkher
vercel --prod --force
```

The `--force` flag bypasses cache.

## What to Look For in Build Logs

### ✅ SUCCESS - You'll see:
```
Installing build runtime...
Detected Python project
Installing dependencies from requirements.txt
Successfully installed sqlalchemy-2.0.36
Build completed in 45s
```

### ❌ FAILURE - You'll see:
```
No Python runtime detected
Treating as static site
```

If you see the failure message, the issue is that Vercel isn't seeing the `vercel.json` file.

## Nuclear Option: Delete and Reconnect Project

If redeploying doesn't work:

1. Go to Project Settings
2. Scroll to bottom: "Delete Project"
3. Delete the project
4. Go back to Vercel dashboard
5. Click "Add New Project"
6. Import from GitHub: `Swaliha-CA/Sakhi`
7. **Root Directory:** Leave as `.` (root)
8. **Framework Preset:** Other
9. Click "Deploy"

This forces Vercel to re-detect everything from scratch.

## Verification Checklist

After redeployment, verify these files exist in Vercel:

- [ ] `api/index.py` exists
- [ ] `vercel.json` exists in root
- [ ] `requirements.txt` exists in root
- [ ] `app/` folder exists
- [ ] Build logs show "Installing Python dependencies"
- [ ] No "ModuleNotFoundError: sqlalchemy" in runtime logs

## Expected Timeline

- **Trigger redeploy:** 30 seconds
- **Build time:** 2-3 minutes
- **Total:** ~3-4 minutes until working

## Why This Happens

Vercel caches builds aggressively. When you:
1. First deployed → No `api/` folder → Cached as "static site"
2. Added `api/index.py` → Vercel still uses old cache
3. Need to force rebuild → Clears cache → Detects Python

This is a common issue with Vercel + FastAPI projects.

## Contact Me If Still Broken

If after clean rebuild you still see:
```
ModuleNotFoundError: No module named 'sqlalchemy'
```

Then we need to check:
1. Is `requirements.txt` in the correct location? (root, not in `api/`)
2. Is `vercel.json` properly formatted? (no JSON syntax errors)
3. Is GitHub repo structure correct?

But 99% of the time, a clean rebuild fixes it! 🚀
