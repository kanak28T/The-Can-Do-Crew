# Test Docker Compose Setup (A0.2 Verification)

## Files Created ✅

You now have:
- ✅ `Dockerfile` — Blueprint for the container
- ✅ `requirements.txt` — Python packages to install
- ✅ `docker-compose.yml` — Orchestration config
- ✅ `api/__init__.py` — Marks api/ as Python package
- ✅ `engine/__init__.py` — Marks engine/ as Python package
- ✅ `contracts/__init__.py` — Marks contracts/ as Python package

---

## Quick Test (5 min)

### Step 1: Build the Docker image

```bash
# From root of project
docker-compose build

# Expected output:
# Building api
# ...
# Successfully tagged urbanpulse_api:latest
```

### Step 2: Start the containers

```bash
docker-compose up

# Expected output:
# Creating db ... done
# Creating api ... done
# api_1  | INFO:     Started server process
# api_1  | INFO:     Uvicorn running on http://0.0.0.0:8000
# api_1  | INFO:     Application startup complete
```

### Step 3: Test the API (in a NEW terminal/tab)

```bash
# Test health endpoint
curl http://localhost:8000/health

# Expected response:
# {"status":"ok","version":"1.0.0"}
```

### Step 4: Stop containers

```bash
# Back in the terminal running docker-compose up
# Press Ctrl+C

# Or in new terminal:
docker-compose down
```

---

## Understanding the Docker Flow

```
Your Computer                  Docker Container
─────────────────              ────────────────

Dockerfile ─────→ Creates Docker image (blueprint)
                         │
                         ↓
docker-compose.yml → Starts 2 containers:
                     1. api (FastAPI)
                     2. db (SQLite)
                         │
                         ↓
api/ folder ────→ Mounted at /app in container
requirements.txt → Installed inside container
                         │
                         ↓
port 8000 ← mapped → port 8000 in container
localhost:8000      
    ↓
Browser/curl → Accesses FastAPI inside container
```

---

## Common Commands

### Build image
```bash
docker-compose build
```

### Start containers
```bash
docker-compose up
```

### Start in background
```bash
docker-compose up -d
```

### View logs
```bash
docker-compose logs -f api
# (-f = follow, shows new logs in real-time)
```

### Stop containers
```bash
docker-compose down
```

### Rebuild and restart
```bash
docker-compose up --build
```

### Remove everything (careful!)
```bash
docker-compose down -v
# (-v = remove volumes, including database!)
```

---

## If Something Goes Wrong

### "docker-compose: command not found"
- Install Docker Desktop from https://www.docker.com/products/docker-desktop

### "Port 8000 is already in use"
- Change port in docker-compose.yml: `"8001:8000"` (use 8001 instead)
- Or stop whatever is using port 8000

### "Module 'api' not found"
- Verify `api/__init__.py` exists
- Verify you ran: `docker-compose build` (not just `docker-compose up`)

### "Cannot find requirements.txt"
- Verify `requirements.txt` exists in root folder (same level as `docker-compose.yml`)

### Containers won't start
- Check logs: `docker-compose logs`
- Rebuild: `docker-compose down` → `docker-compose build` → `docker-compose up`

---

## Next Steps

Once Docker is working:
1. ✅ A0.2 complete (Docker setup)
2. → A0.3: Write `contracts/event_schema.py` (with A2) **← BLOCKER**
3. → A0.4: PII validator
4. → A0.5: `/ingest` endpoint
5. → A0.6: `/sse/events` stream

---

**You're ready for the next task!**
