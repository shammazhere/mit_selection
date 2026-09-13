# Silent Shift - Backend: Fusion, Drift & API (Person 3)

This is Person 3's contribution to the Silent Shift project - the backend layer for risk fusion, CUSUM drift detection, explanation generation, and the REST API.

## Architecture

```
/backend/
├── drift/       # CUSUM drift detection
├── fusion/      # Risk fusion engine + multipliers
├── explain/     # Explanation generator
└── api/         # FastAPI endpoints + feedback persistence
```

## Contracts

### Contract A (Input) - Person 2 → Person 3

```
daily_user_scores.csv with fields:
- user_id, date, self_score, peer_score
- cohort_used, cohort_size, fallback_applied, role
```

### Contract B (Output) - Person 3 → Person 1

```
GET    /queue          - Ranked risk queue
GET    /case/{user_id} - Case detail view
POST   /feedback       - Record false positive
```

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Generate Sample Data (if needed)

```bash
python backend/generate_sample_data.py
```

This creates `data/daily_user_scores.csv` and `data/scores.db` with sample Contract A data.

### 3. Run the Pipeline

```bash
python backend/pipeline.py
```

This loads Contract A data, processes it through the fusion pipeline, and stores results in the database.

### 4. Start the API Server

```bash
uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload
```

## API Endpoints

### GET /queue

Returns the ranked risk queue:

```json
{
  "items": [
    {
      "user_id": "u001",
      "name": "Alice Chen",
      "role": "Senior Engineer",
      "risk_score": 78.5,
      "severity": "high",
      "last_updated": "2026-09-13T10:00:00"
    }
  ],
  "total_count": 10,
  "timestamp": "2026-09-13T10:00:00"
}
```

### GET /case/{user_id}

Returns case details:

```json
{
  "user_id": "u001",
  "risk_score": 78.5,
  "self_score": 0.82,
  "peer_score": 0.74,
  "drift_score": 0.69,
  "cohort_used": "department",
  "fallback_applied": true,
  "explanation_text": "Flagged: activity is unlike this user's own 90-day history... and has trended upward for 7 consecutive days.",
  "cusum_path": [0.1, 0.2, 0.4, 0.8, 1.5, 2.8, 4.5, 6.2],
  "event_timeline": [...],
  "severity": "high",
  "multipliers_applied": {"role": 1.5, "time": 1.0, "data_sensitivity": 1.0, "decay": 1.0},
  "score_components": {...},
  "last_updated": "2026-09-13T10:00:00"
}
```

### POST /feedback

Records investigator feedback:

```json
POST /feedback
Content-Type: application/json

{
  "user_id": "u001",
  "is_false_positive": true,
  "reason": "This was expected activity during project deadline"
}
```

Response:

```json
{
  "status": "success",
  "message": "Feedback recorded successfully",
  "feedback_id": "1",
  "timestamp": "2026-09-13T10:00:00"
}
```

## Key Components

### 1. CUSUM Drift Detection (`backend/drift/cusum.py`)

- Runs on **locked** pre-multiplier fused score
- Stores raw cumulative-sum path per user
- Detects sustained upward trends over multiple days

### 2. Risk Fusion Engine (`backend/fusion/fusion.py`)

- Combines self_score, peer_score, drift into 0-100 risk score
- Applies role/time/data-sensitivity multipliers
- Applies score decay for days without new anomalies

### 3. Explanation Generator (`backend/explain/generator.py`)

- Creates plain-English explanations from fusion inputs
- Explicitly discloses when department fallback was used
- Includes self-baseline, peer-baseline, and drift explanations

### 4. Database (`backend/api/database.py`)

- SQLite persistence for risk scores
- Feedback storage with down-weighting
- Cache for API responses

## Multipliers

| Multiplier | Condition | Effect |
|------------|-----------|--------|
| Role sensitivity | Admin/privileged account | 1.3-1.5x weight |
| Time of access | Before 7am or after 8pm | 1.3-1.4x weight |
| Data sensitivity | Confidential/USB data | 1.3-1.4x weight |
| Score decay | Each day without anomalies | Gradual reduction |

## Testing

```bash
# Test the pipeline
python backend/pipeline.py

# Test the API (in separate terminal)
uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload

# Test endpoints
curl http://localhost:8000/queue
curl http://localhost:8000/case/u001
curl -X POST http://localhost:8000/feedback \
  -H "Content-Type: application/json" \
  -d '{"user_id":"u001","is_false_positive":true,"reason":"test"}'
```

## Person 3 Deliverables

- ✅ CUSUM running on locked pre-multiplier score; raw path stored
- ✅ Risk fusion engine with all four multipliers
- ✅ Explanation generator, including fallback disclosure
- ✅ GET /queue, GET /case/{id}, POST /feedback all live
- ✅ Feedback down-weighting implemented

## License

MIT Hackathon - Problem Statement 16
