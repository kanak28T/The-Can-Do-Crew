# UrbanPulse Nagpur - Deployment Guide

## Option 1: Render.com (Recommended - Free Tier Available)

### Why Render?
- ✅ Free tier: 750 hours/month (perfect for demos/presentations)
- ✅ Built-in SSL certificates
- ✅ SSE support with no timeout issues
- ✅ Easy deployment from GitHub
- ✅ Singapore region available (low latency for India)

### Prerequisites
1. GitHub account with this repo pushed
2. Render.com account (sign up at https://render.com)

### Deployment Steps

#### Step 1: Connect GitHub Repository
1. Go to https://render.com/dashboard
2. Click **"New +"** → **"Blueprint"**
3. Connect your GitHub account if not already connected
4. Select this repository: `The-Can-Do-Crew`

#### Step 2: Deploy with Blueprint
Render will automatically detect `render.yaml` and create TWO services:

**Backend API** (`urbanpulse-api`):
- Type: Web Service
- Environment: Python
- Build: `pip install -r requirements.txt`
- Start: `uvicorn api.main:app --host 0.0.0.0 --port $PORT`
- URL: `https://urbanpulse-api.onrender.com` (your actual URL will differ)

**Frontend** (`urbanpulse-frontend`):
- Type: Static Site
- Build: `cd web && npm install && npm run build`
- Publish: `./web/dist`

#### Step 3: Update Frontend Environment Variable
After backend deploys, Render gives you the actual backend URL.

1. Go to **urbanpulse-frontend** service settings
2. Add environment variable:
   - Key: `VITE_API_BASE_URL`
   - Value: `https://urbanpulse-api-XXXX.onrender.com` (copy your actual backend URL)
3. Click **"Save Changes"** — frontend will rebuild automatically

#### Step 4: Verify Deployment
1. Open your frontend URL: `https://urbanpulse-frontend.onrender.com`
2. Check browser console for connection status
3. Click "Start Simulation" — should see live map updates
4. Verify SSE connection status shows "LIVE" (green dot)

### Expected Deploy Time
- Backend: ~3-5 minutes
- Frontend: ~2-4 minutes
- **Total: ~7 minutes**

---

## Option 2: Railway.app (Alternative - $5/month)

Railway offers better performance but requires payment.

### Deployment Steps

#### Step 1: Install Railway CLI
```bash
npm i -g @railway/cli
railway login
```

#### Step 2: Initialize Project
```bash
railway init
railway link
```

#### Step 3: Deploy Backend
```bash
railway up --service backend
```

Railway will detect `railway.json` config automatically.

#### Step 4: Deploy Frontend
```bash
cd web
railway up --service frontend
```

#### Step 5: Set Environment Variables
```bash
railway variables set VITE_API_BASE_URL=https://your-backend.railway.app
```

---

## Option 3: Docker (Self-Hosted VPS)

If you have your own server (AWS EC2, DigitalOcean, etc.):

### Prerequisites
- VPS with Docker installed
- Domain name (optional but recommended)

### Deployment Steps

#### Step 1: SSH into Server
```bash
ssh user@your-server.com
```

#### Step 2: Clone Repository
```bash
git clone https://github.com/yourusername/The-Can-Do-Crew.git
cd The-Can-Do-Crew
```

#### Step 3: Build Frontend
```bash
cd web
npm install
VITE_API_BASE_URL=http://your-server.com:8000 npm run build
cd ..
```

#### Step 4: Build & Run Docker
```bash
docker build -t urbanpulse .
docker run -d -p 8000:8000 --name urbanpulse-api urbanpulse
```

#### Step 5: Serve Frontend with Nginx
```bash
sudo apt install nginx
sudo cp -r web/dist/* /var/www/html/
sudo systemctl restart nginx
```

Frontend: http://your-server.com
Backend API: http://your-server.com:8000

---

## Troubleshooting

### SSE Connection Fails
**Symptom:** Map doesn't update, status shows "RECONNECTING"

**Fix:**
1. Check backend `/health` endpoint: `https://your-backend.com/health`
2. Verify CORS is enabled (backend already has `CORS_ORIGIN=*` in render.yaml)
3. Check browser console for CORS errors
4. Ensure `VITE_API_BASE_URL` matches your actual backend URL

### 502 Bad Gateway
**Symptom:** API calls return 502 errors

**Fix:**
1. Backend crashed — check Render logs: Dashboard → urbanpulse-api → Logs
2. Common crash causes:
   - Missing dependencies in `requirements.txt`
   - Database file permissions (SQLite `events.db`)
   - Port binding issues

**Solution:** Backend auto-restarts on Render. If persistent, check logs.

### Frontend Shows "API Connection Failed"
**Symptom:** Dashboard loads but shows no data

**Fix:**
1. Verify `VITE_API_BASE_URL` is set correctly in frontend environment
2. Test backend directly: `curl https://your-backend.com/api/zones`
3. Check browser Network tab for failed API calls
4. Ensure backend `/api/*` routes are responding

### Build Fails
**Symptom:** Render build fails with npm or pip errors

**Fix:**
1. **Frontend:** Ensure Node.js version matches (18+)
   - Add to render.yaml: `node_version: "18"`
2. **Backend:** Ensure Python version matches (3.12+)
   - Already set in render.yaml: `env: python` (uses Python 3.12)
3. Check for missing dependencies in `requirements.txt` or `package.json`

---

## Performance Notes

### Free Tier Limitations (Render)
- Backend **spins down after 15 minutes of inactivity**
- First request after spin-down takes ~30-60 seconds to wake up
- Solution for presentations:
  1. Open dashboard 2 minutes before presenting
  2. OR: use `deploy/keep_warm.py` script (pings every 10 minutes)
  3. OR: upgrade to paid tier ($7/month) for always-on

### Keep-Warm Script
```bash
# Run locally to keep backend alive
python deploy/keep_warm.py https://your-backend.com/health
```

---

## Post-Deployment Checklist

- [ ] Backend `/health` endpoint responds
- [ ] Frontend loads at your deployment URL
- [ ] SSE connection shows "LIVE" status
- [ ] "Start Simulation" button triggers map updates
- [ ] Zone cards show real Nagpur ward names
- [ ] Intervention log records approve/reject actions
- [ ] Light/dark theme toggle works
- [ ] Explainability modal shows driver details
- [ ] No console errors in browser DevTools

---

## Recommended: Render.com

**For your presentation, I strongly recommend Render** because:
1. **Free** — no credit card required for demo
2. **Fast setup** — 7 minutes total
3. **SSL included** — secure HTTPS by default
4. **SSE friendly** — no timeout issues
5. **GitHub integration** — auto-deploy on push

**Next Steps:**
1. Push latest code to GitHub (already done ✅)
2. Go to https://render.com and sign up
3. Create "New Blueprint" → select this repo
4. Wait 7 minutes
5. Update frontend `VITE_API_BASE_URL` with backend URL
6. Share your live dashboard URL! 🚀
