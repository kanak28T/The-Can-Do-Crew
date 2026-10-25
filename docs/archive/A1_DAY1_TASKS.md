# A1 Day 1 Tasks (Phase 0) - BLOCKING BETA TEAM

**Your job:** Get `event_schema.py` committed by 01:00 UTC. That unblocks Beta.

---

## Task A0.1: Register OpenCellID (5 min) ⏱️

**DO THIS FIRST - takes 24h to approve but you can do other work while waiting**

Go to: https://opencellid.org/

1. Click "Sign Up"
2. Create account (email, password)
3. Confirm email
4. Go to API key section
5. Generate API key
6. Save it locally (don't commit to repo)x`

**Why:** For tower-to-cell mapping on Day 2. If not approved, use synthetic towers instead.

---

## Task A0.2: Docker Compose Setup (45 min) ⏱️

### What is Docker & Docker Compose? (Conceptual)

**Docker** is like a "container" for your application:
- Normally: Python → FastAPI → SQLite (installed on YOUR computer)
- With Docker: Python + FastAPI + SQLite → packaged in a **container** → runs the same on ANY computer

**Docker Compose** is like a **recipe** that says:
- "Start a Python container (for FastAPI)"
- "Map port 8000 on my computer to port 8000 inside the container"
- "Create a folder for database files that persists after container stops"
- "Run these commands inside the container"

**Why we use it:**
- Beta team can run the same container without installing anything
- Consistent environment across all machines
- Easy to start/stop/rebuild

---

### Step 1: Create the `Dockerfile` (5 min)

**What it does:** Defines how to build the Docker image (a blueprint for the container)

**File location:** Root level (same level as `README.md`)

**Path:** `Dockerfile` (no extension)

```dockerfile
# Start with Python 3.10 (slim = smaller image)
FROM python:3.10-slim

# Inside the container, create /app folder
WORKDIR /app

# Copy requirements.txt from your computer → container's /app
COPY requirements.txt .

# Inside container, install Python packages from requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy entire project from your computer → container's /app
COPY . .

# When container starts, run this command
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**In simple terms:**
1. Use Python 3.10 as the base
2. Create `/app` folder inside container
3. Copy your `requirements.txt` and install dependencies
4. Copy your entire project
5. When the container runs, start FastAPI on port 8000

---

### Step 2: Create `requirements.txt` (5 min)

**What it does:** Lists all Python packages needed for the project

**File location:** Root level

**Path:** `requirements.txt`

```
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
h3==3.7.0
networkx==3.2
numpy==1.24.3
osmnx==1.7.1
rasterio==1.3.9
```

**Explanation:**
- `fastapi` = web framework (for `/ingest` and `/sse/events`)
- `uvicorn` = server that runs FastAPI
- `pydantic` = validates data schemas (like `CanonicalEvent`)
- `h3` = library for H3 hexagons (Nagpur grid)
- `networkx` = graph library (for roads, Dijkstra)
- `numpy` = numerical computing
- `osmnx` = downloads OpenStreetMap data
- `rasterio` = reads geospatial raster files

**Format:** `package_name==version` (exact versions, no surprises)

---

### Step 3: Create `docker-compose.yml` (15 min)

**What it does:** Orchestrates multiple containers and their interactions

**File location:** Root level

**Path:** `docker-compose.yml`

```yaml
# Docker Compose version (compatibility)
version: '3.8'

# Services are containers that run
services:
  
  # Service 1: FastAPI API server
  api:
    # Build from current directory's Dockerfile
    build: .
    
    # Port mapping: your_computer_port:container_port
    # "8000:8000" = access FastAPI at http://localhost:8000
    ports:
      - "8000:8000"
    
    # Volume mapping: your_computer_folder:container_folder
    # "." = root of project → "/app" in container
    # This means:
    # - Code changes on your computer instantly reflect in container (live reload)
    # - Database files persist after container stops
    volumes:
      - .:/app              # Project root → /app in container
      - ./db:/app/db        # Local db/ → /app/db in container
      - ./data:/app/data    # Local data/ → /app/data in container
    
    # Environment variables inside container
    environment:
      - DATABASE_URL=sqlite:////app/db/events.db
      - PYTHONUNBUFFERED=1  # Don't buffer Python output (see logs in real-time)
    
    # Command to run when container starts
    command: uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
    # Explanation:
    # - uvicorn = web server
    # - api.main:app = module `api/main.py`, object `app`
    # - --host 0.0.0.0 = listen on all network interfaces
    # - --port 8000 = on port 8000
    # - --reload = restart when code changes
    
    # Wait for database before starting API
    depends_on:
      - db
    
  # Service 2: SQLite database (optional, mainly for persistence)
  db:
    image: sqlite:latest
    volumes:
      - ./db:/data
```

**In simple terms:**
- `api` service: FastAPI container
- `db` service: Database storage
- When you run `docker-compose up`, it:
  1. Builds the image from `Dockerfile`
  2. Starts the `db` container
  3. Starts the `api` container on port 8000
  4. Maps your code folder → `/app` in container (live reload)
  5. Maps `./db` folder → persistent database storage

---

### Step 4: Create folder structure (5 min)

Create these folders if they don't exist:

```bash
# From root of project
mkdir -p api
mkdir -p engine
mkdir -p contracts
mkdir -p data
mkdir -p db
mkdir -p sim
mkdir -p fed
mkdir -p node
```

**Why:**
- `api/` = FastAPI code (where you'll put `main.py`)
- `engine/` = Risk scoring engine
- `contracts/` = Event schema (we'll create this)
- `data/` = Downloaded datasets (roads, population, etc.)
- `db/` = SQLite database files (persistent)

---

### Step 5: Create `api/__init__.py` (2 min)

**File location:** `api/__init__.py` (tells Python that `api/` is a package)

```python
# Empty file - just marks this folder as a Python package
```

---

### Step 6: Create `engine/__init__.py` (1 min)

**File location:** `engine/__init__.py`

```python
# Empty file - marks this folder as a Python package
```

---

### Step 7: Create `contracts/__init__.py` (1 min)

**File location:** `contracts/__init__.py`

```python
# Empty file - marks this folder as a Python package
```

---

### Step 8: Test the setup (10 min)

**Before running Docker, verify files exist:**

```bash
# List files in root
dir

# Should see:
# - docker-compose.yml
# - Dockerfile
# - requirements.txt
# - api/ (folder)
# - engine/ (folder)
# - contracts/ (folder)
# - data/ (folder)
# - db/ (folder)
```

**Build the Docker image:**

```bash
# From root of project
docker-compose build

# Output should look like:
# Building api
# Step 1/7 : FROM python:3.10-slim
# Step 2/7 : WORKDIR /app
# ...
# Successfully tagged urbanpulse_api:latest
```

**Run the containers:**

```bash
docker-compose up

# Output should look like:
# Creating db ... done
# Creating api ... done
# api_1  | INFO:     Started server process [1]
# api_1  | INFO:     Uvicorn running on http://0.0.0.0:8000
# api_1  | INFO:     Application startup complete
```

**Test if it's working (in a NEW terminal/tab):**

```bash
# Test health endpoint
curl http://localhost:8000/health

# Should return:
# {"status":"ok","version":"1.0.0"}
```

**Stop containers:**

```bash
# In the original terminal where docker-compose up is running
# Press Ctrl+C

# Or in a new terminal:
docker-compose down
```

---

### Step 9: Understand the flow (5 min)

**When you run `docker-compose up`:**

1. **Build phase:**
   - Docker reads `Dockerfile`
   - Creates a Docker image with Python 3.10 + all packages from `requirements.txt`

2. **Run phase:**
   - Starts `db` container (SQLite storage)
   - Starts `api` container with your code
   - Maps `port 8000` (your computer) → `port 8000` (container)
   - Maps `./db` folder → persistent database storage
   - Runs: `uvicorn api.main:app --reload`

3. **Live reload:**
   - You edit `api/main.py` on your computer
   - Container detects the change (because of volume mount)
   - FastAPI automatically restarts
   - No need to rebuild the container

4. **Access:**
   - Open browser: `http://localhost:8000`
   - Or use curl: `curl http://localhost:8000/health`

---

### Common errors & solutions:

**Error: "docker-compose: command not found"**
- Solution: Install Docker Desktop (includes docker-compose)
- https://www.docker.com/products/docker-desktop

**Error: "Port 8000 is already in use"**
- Solution: Change port in `docker-compose.yml` → `"8001:8000"`
- Or: Stop the service using port 8000

**Error: "Cannot find requirements.txt"**
- Solution: Verify `requirements.txt` is in the root folder (same level as Dockerfile)

**Error: "Module 'api' not found"**
- Solution: Create `api/__init__.py` (empty file)

---

### Files to create (checklist):

- [ ] `Dockerfile` (root)
- [ ] `requirements.txt` (root)
- [ ] `docker-compose.yml` (root)
- [ ] `api/__init__.py`
- [ ] `engine/__init__.py`
- [ ] `contracts/__init__.py`
- [ ] Folders: `db/`, `data/`, `sim/`, `fed/`, `node/` (created)

Once done → Move to **A0.3: event_schema.py (BLOCKER)**

---

## Task A0.3: Write `contracts/event_schema.py` (45 min) ⏱️ **BLOCKER**

**File:** `contracts/event_schema.py`

**DO THIS WITH A2. This is the BLOCKER for the entire team.**

```python
from pydantic import BaseModel, Field, validator
from typing import Optional, Literal
from datetime import datetime
from uuid import UUID
import re

class CanonicalEvent(BaseModel):
    """
    Canonical event schema. Strict validation. No PII.
    All fields required unless marked Optional.
    """
    
    event_id: str = Field(
        ..., 
        description="Unique event identifier (UUID format)",
        regex="^[a-f0-9-]{36}$"
    )
    
    domain: Literal[
        "power", "transit", "water", "health", "comms", "road"
    ] = Field(..., description="Infrastructure domain")
    
    event_type: str = Field(
        ..., 
        description="Type of event (e.g., blackout, closure, suspension)",
        min_length=1,
        max_length=50
    )
    
    entity_id: str = Field(
        ..., 
        description="Entity identifier (feeder, route, road, pump, tower, hospital)",
        min_length=1,
        max_length=100
    )
    
    h3_cell: str = Field(
        ..., 
        description="H3 resolution-9 hex cell ID",
        regex="^[a-f0-9]{15}$"
    )
    
    severity: float = Field(
        ..., 
        description="Severity on scale [0.0, 1.0]",
        ge=0.0,
        le=1.0
    )
    
    source_type: Literal[
        "official", "sensor", "crowd", "anonymous"
    ] = Field(..., description="Data source type")
    
    source_reliability: float = Field(
        ..., 
        description="Source reliability score",
        ge=0.0,
        le=1.0
    )
    
    event_timestamp: datetime = Field(
        ..., 
        description="When the event occurred (UTC)"
    )
    
    ingestion_timestamp: datetime = Field(
        ..., 
        description="When the event was ingested (UTC)"
    )
    
    parse_confidence: float = Field(
        ..., 
        description="Confidence in parsing [0.0, 1.0]",
        ge=0.0,
        le=1.0
    )
    
    scenario_tag: Optional[str] = Field(
        None, 
        description="Scenario identifier (evaluation only; never in production)",
        max_length=100
    )
    
    class Config:
        strict = True
        validate_assignment = True
    
    @validator('entity_id')
    def no_pii_in_entity(cls, v):
        """Reject phone numbers, names in entity_id"""
        # Phone numbers (various formats)
        if re.search(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', v):
            raise ValueError("Phone number detected in entity_id")
        # Common name patterns (Mr., Ms., etc.)
        if re.search(r'\b(Mr|Ms|Dr|Sr|Jr)\b', v, re.IGNORECASE):
            raise ValueError("Name/title detected in entity_id")
        return v
    
    @validator('event_type')
    def event_type_lowercase(cls, v):
        """Normalize event type to lowercase"""
        return v.lower()

# Test schema version (for coordination)
SCHEMA_VERSION = "1.0.0"
```

**Commit this file:**
```bash
git add contracts/event_schema.py
git commit -m "feat: write canonical event schema (A0.3 BLOCKER)"
git push origin priyanshu
```

**This is the BLOCKER. Once this is committed, Beta team can proceed.**

---

## Task A0.4: PII Rejection Validator (45 min) ⏱️

**File:** `api/pii_validator.py`

```python
import re
from typing import Dict, Any
from contracts.event_schema import CanonicalEvent

class PIIValidator:
    """Validate and reject events containing PII"""
    
    # Regex patterns for common PII
    PHONE_PATTERN = r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'
    EMAIL_PATTERN = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    DEVICE_ID_PATTERN = r'\b[A-F0-9]{8}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{12}\b'
    NAME_PATTERN = r'\b(Mr|Ms|Dr|Sir|Madam|John|Mary|Smith|Patel|Kumar)\b'
    
    @staticmethod
    def validate(event_dict: Dict[str, Any]) -> tuple[bool, str]:
        """
        Validate event for PII.
        Returns: (is_valid, error_message)
        """
        
        # Fields to check for PII
        pii_fields = ['entity_id', 'event_type', 'source_type']
        
        for field in pii_fields:
            if field in event_dict:
                value = str(event_dict[field])
                
                # Check phone
                if re.search(PIIValidator.PHONE_PATTERN, value):
                    return False, f"Phone number detected in field '{field}'"
                
                # Check email
                if re.search(PIIValidator.EMAIL_PATTERN, value):
                    return False, f"Email detected in field '{field}'"
                
                # Check device ID (UUID format)
                if re.search(PIIValidator.DEVICE_ID_PATTERN, value):
                    return False, f"Device ID detected in field '{field}'"
                
                # Check common names
                if re.search(PIIValidator.NAME_PATTERN, value, re.IGNORECASE):
                    return False, f"Personal name detected in field '{field}'"
        
        return True, ""

    @staticmethod
    def scrub(event_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Scrub known PII patterns (returns sanitized copy)"""
        scrubbed = event_dict.copy()
        
        for field in ['entity_id', 'event_type']:
            if field in scrubbed:
                value = str(scrubbed[field])
                # Remove phone-like patterns
                value = re.sub(PIIValidator.PHONE_PATTERN, '[REDACTED]', value)
                scrubbed[field] = value
        
        return scrubbed
```

---

## Task A0.5: POST /ingest Endpoint Stub (30 min) ⏱️

**File:** `api/main.py`

```python
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from datetime import datetime
import sqlite3
import json
from contracts.event_schema import CanonicalEvent, SCHEMA_VERSION
from api.pii_validator import PIIValidator

app = FastAPI(title="UrbanPulse", version=SCHEMA_VERSION)

# SQLite event log (append-only)
DB_PATH = "db/events.db"

def init_db():
    """Initialize SQLite event log"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            event_id TEXT PRIMARY KEY,
            domain TEXT,
            event_type TEXT,
            entity_id TEXT,
            h3_cell TEXT,
            severity REAL,
            source_type TEXT,
            source_reliability REAL,
            event_timestamp TEXT,
            ingestion_timestamp TEXT,
            parse_confidence REAL,
            scenario_tag TEXT,
            inserted_at TEXT
        )
    """)
    conn.commit()
    conn.close()

# Initialize on startup
@app.on_event("startup")
async def startup():
    init_db()

@app.post("/ingest")
async def ingest_event(data: dict):
    """
    Accept canonical events.
    Validate schema, reject PII, log to SQLite.
    """
    
    # Validate PII before schema validation
    is_valid, error_msg = PIIValidator.validate(data)
    if not is_valid:
        return JSONResponse(
            status_code=422,
            content={
                "status": "rejected",
                "reason": "PII detected",
                "details": error_msg
            }
        )
    
    # Validate schema
    try:
        event = CanonicalEvent(**data)
    except ValidationError as e:
        return JSONResponse(
            status_code=422,
            content={
                "status": "rejected",
                "reason": "Schema validation failed",
                "details": str(e)
            }
        )
    
    # Log to SQLite
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        event.event_id,
        event.domain,
        event.event_type,
        event.entity_id,
        event.h3_cell,
        event.severity,
        event.source_type,
        event.source_reliability,
        event.event_timestamp.isoformat(),
        event.ingestion_timestamp.isoformat(),
        event.parse_confidence,
        event.scenario_tag,
        datetime.utcnow().isoformat()
    ))
    
    conn.commit()
    conn.close()
    
    # Return success
    return {
        "status": "accepted",
        "event_id": event.event_id,
        "cell": event.h3_cell,
        "risk_updated": False,  # Day 2: will update
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/health")
async def health():
    """Health check"""
    return {"status": "ok", "version": SCHEMA_VERSION}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

---

## Task A0.6: GET /sse/events Mock Stream (30 min) ⏱️

**File:** `api/sse.py`

```python
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import asyncio
import json
from datetime import datetime

router = APIRouter()

# Mock events (Day 2: replace with real engine)
MOCK_EVENTS = [
    {
        "cell": "890c1d2cf37ffff",
        "risk": 0.35,
        "event_type": "mock_power"
    },
    {
        "cell": "890c1d2cf37ffff",
        "risk": 0.52,
        "event_type": "mock_transit"
    },
    {
        "cell": "890c1d2d037ffff",
        "risk": 0.41,
        "event_type": "mock_transit"
    },
]

async def event_generator():
    """Generate SSE events every 3 seconds"""
    event_id = 0
    
    while True:
        event = MOCK_EVENTS[event_id % len(MOCK_EVENTS)]
        
        sse_msg = f"""id: evt-{event_id}\nevent: cell_updated\ndata: {json.dumps(event)}\n\n"""
        yield sse_msg
        
        event_id += 1
        await asyncio.sleep(3)

@router.get("/sse/events")
async def sse_events():
    """Server-Sent Events stream"""
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )
```

**Add to `api/main.py`:**
```python
from api.sse import router as sse_router
app.include_router(sse_router)
```

---

## Task A0.7: k-Merge Stub (15 min) ⏱️

**File:** `engine/privacy.py`

```python
def merge_subcell(cell: str, k: int) -> str:
    """
    k-merge: if cell has <k expected contributors, merge to parent.
    
    Args:
        cell: H3 res-9 cell ID
        k: Minimum contributors threshold (default 5)
    
    Returns:
        cell if k met, else H3 res-8 parent cell
    
    TODO (Day 6): Implement actual k-merge logic with population floor
    """
    # Stub: just return the cell
    # Day 6: check expected_contributors[cell] < k, merge to res-8
    return cell
```

---

## Task A0.8: Download OSM Road Graph (Background, 30 min) ⏱️

**File:** `data/download_roads.py`

**Run this in parallel with other tasks (takes 10–30 min depending on internet):**

```python
import osmnx as ox
import networkx as nx

# Download Nagpur road network
print("Downloading OSM road graph for Nagpur...")
G = ox.graph_from_place("Nagpur, Maharashtra, India", network_type="drive")

# Save as GraphML
output_path = "data/nagpur_roads.graphml"
nx.write_graphml(G, output_path)

print(f"✅ Saved to {output_path}")
print(f"   Nodes: {G.number_of_nodes()}")
print(f"   Edges: {G.number_of_edges()}")
```

**Run it:**
```bash
python data/download_roads.py
# Should take 10–30 min depending on internet speed
# Output: data/nagpur_roads.graphml (~50 MB)
```

---

## Task A0.9: k-Merge Signature Stub (15 min) ⏱️

Already done above in `engine/privacy.py`.

---

## Summary: Your Phase 0 Checklist

- [ ] A0.1: Register OpenCellID (5 min, async)
- [ ] A0.2: Docker Compose + Dockerfile + requirements.txt (45 min)
- [ ] A0.3: Write `contracts/event_schema.py` with A2 (45 min) **← COMMIT THIS**
- [ ] A0.4: PII validator (`api/pii_validator.py`) (45 min)
- [ ] A0.5: POST /ingest endpoint (`api/main.py`) (30 min)
- [ ] A0.6: GET /sse/events mock stream (`api/sse.py`) (30 min)
- [ ] A0.7: k-merge stub (`engine/privacy.py`) (15 min)
- [ ] A0.8: Download roads (background) (30 min)
- [ ] A0.9: Verify all files committed (5 min)

**Total: ~3.5 hours active + 30 min background**

---

## Testing Phase 0 (Before Sending to Beta)

```bash
# 1. Spin up Docker
docker-compose up
# Should see: INFO:     Uvicorn running on http://0.0.0.0:8000

# 2. Test /health
curl http://localhost:8000/health
# Expected: {"status":"ok","version":"1.0.0"}

# 3. Test /ingest with valid event
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "event_id": "550e8400-e29b-41d4-a716-446655440000",
    "domain": "power",
    "event_type": "blackout",
    "entity_id": "feeder-F12",
    "h3_cell": "890c1d2cf37ffff",
    "severity": 1.0,
    "source_type": "official",
    "source_reliability": 0.9,
    "event_timestamp": "2026-10-25T14:30:00Z",
    "ingestion_timestamp": "2026-10-25T14:30:02Z",
    "parse_confidence": 1.0
  }'
# Expected: {"status":"accepted","event_id":"...","cell":"890c1d2cf37ffff",...}

# 4. Test /ingest with PII (should reject)
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "event_id": "550e8400-e29b-41d4-a716-446655440000",
    "domain": "power",
    "event_type": "blackout",
    "entity_id": "John Smith 555-1234",
    "h3_cell": "890c1d2cf37ffff",
    "severity": 1.0,
    "source_type": "official",
    "source_reliability": 0.9,
    "event_timestamp": "2026-10-25T14:30:00Z",
    "ingestion_timestamp": "2026-10-25T14:30:02Z",
    "parse_confidence": 1.0
  }'
# Expected: {"status":"rejected","reason":"PII detected",...}

# 5. Test /sse/events (should emit mock events every 3s)
curl -N http://localhost:8000/sse/events
# Expected: id: evt-0 / event: cell_updated / data: {...}
# (streams continuously, Ctrl+C to stop)
```

---

## Git Commits (in order)

```bash
# 1. Docker setup
git add docker-compose.yml Dockerfile requirements.txt
git commit -m "infra: Docker Compose + FastAPI setup (A0.2)"

# 2. BLOCKER - DO THIS BY 01:00 UTC
git add contracts/event_schema.py
git commit -m "feat: canonical event schema (A0.3 BLOCKER)"
git push origin priyanshu

# 3. PII validator
git add api/pii_validator.py
git commit -m "feat: PII rejection validator (A0.4)"

# 4. /ingest endpoint
git add api/main.py
git commit -m "feat: POST /ingest endpoint + SQLite logging (A0.5)"

# 5. /sse/events stream
git add api/sse.py
git commit -m "feat: GET /sse/events mock stream (A0.6)"

# 6. Privacy stub
git add engine/privacy.py
git commit -m "feat: k-merge function stub (A0.7-A0.9)"

# 7. Road graph
git add data/nagpur_roads.graphml data/download_roads.py
git commit -m "data: OSM road graph for Nagpur (A0.8)"
```

---

**BLOCKING BETA TEAM - GET SCHEMA COMMITTED BY 01:00 UTC** ⏱️

Once `event_schema.py` is committed, Beta can start building the map shell.

Go! 🚀
