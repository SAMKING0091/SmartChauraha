# SmartChauraha — Adaptive Traffic Signal Management System

A full-stack interactive simulation of an AI-optimised 4-way traffic intersection.

---

## Files

| File | Description |
|------|-------------|
| `traffic_backend.py` | Flask API — simulation engine, AI logic, all state |
| `traffic_frontend.html` | React UI — open directly in a browser |

---

## Quick Start

### 1. Start the Backend

```bash
# Install dependencies (once)
pip install flask flask-cors

# Run
python traffic_backend.py
# → Running on http://localhost:5000
```

### 2. Open the Frontend

Open `traffic_frontend.html` in any modern browser (Chrome / Firefox / Edge).

> **Note:** The frontend polls `http://localhost:5000/api/state` every 900ms.
> If the backend is not running, a yellow warning appears at the bottom-right.

---

## Features

### Intersection Simulation
- Live 4-way intersection with animated signal lights (R/Y/G)
- Vehicle dot visualisation per lane — density drives animation
- Countdown timer ring on the junction centre

### AI Signal Logic
- Rule-based: green time = f(density, time-of-day)
- Priority routing: lane with highest density gets next green
- Conflict-safe: only one green direction active at any time

### Emergency Override
- Select a lane and click "Activate Emergency"
- Immediately forces that direction green, pauses normal cycle
- Click "Clear Emergency" to resume auto mode

### Manual / Police Override
- Switch to MANUAL mode, then click any direction button
- Frontend shows officer-override badge; AI resumes on AUTO

### Time-of-Day Modes
- **PEAK**: green timings ×1.3 (busy rush hours)
- **NORMAL**: standard timings
- **NIGHT**: green timings ×0.7 (low traffic)

### Dashboard
- Signal status per lane with colour-coded badges
- Real-time density progress bars
- 30-second sparkline trend charts per direction
- System metrics: phase, timer, vehicle queue counts

### Density Sliders
- Manually override lane density from the left panel
- AI reacts immediately to changes

---

## API Reference

| Endpoint | Method | Body | Description |
|----------|--------|------|-------------|
| `/api/state` | GET | — | Full system snapshot |
| `/api/emergency` | POST | `{active, direction}` | Toggle emergency |
| `/api/mode` | POST | `{mode}` | AUTO or MANUAL |
| `/api/manual_signal` | POST | `{direction}` | Force a direction green |
| `/api/time_of_day` | POST | `{time_of_day}` | PEAK / NORMAL / NIGHT |
| `/api/density` | POST | `{direction, value}` | Override lane density 0–100 |

---

## Architecture

```
traffic_frontend.html          traffic_backend.py
   React (CDN)          ──────▶   Flask + CORS
   Polls /api/state               In-memory state dict
   Posts control events           Background thread (1Hz tick)
                                  AI logic: compute_green_time()
                                           pick_next_direction()
```

No database, no build step, no npm required.
