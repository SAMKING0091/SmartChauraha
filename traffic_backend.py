"""
 SmartChauraha - Backend
Flask API with in-memory simulation logic

Run:
   
    python traffic_backend.py
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import random
import time
import threading

app = Flask(__name__)
CORS(app)

# ─────────────────────────────────────────────
# STATE — all in-memory, no database
# ─────────────────────────────────────────────

DIRECTIONS = ["NORTH", "SOUTH", "EAST", "WEST"]

state = {
    "signals": {
        "NORTH": "RED",
        "SOUTH": "RED",
        "EAST":  "RED",
        "WEST":  "RED",
    },
    "density": {
        "NORTH": 0,
        "SOUTH": 0,
        "EAST":  0,
        "WEST":  0,
    },
    "vehicle_count": {
        "NORTH": 0,
        "SOUTH": 0,
        "EAST":  0,
        "WEST":  0,
    },
    "active_direction": "NORTH",
    "phase": "GREEN",        # GREEN | YELLOW | RED_ALL
    "timer": 0,
    "max_timer": 10,
    "emergency": {
        "active": False,
        "direction": None,
    },
    "cycle_count": 0,
    "mode": "AUTO",          # AUTO | MANUAL | EMERGENCY
    "time_of_day": "NORMAL", # PEAK | NORMAL | NIGHT
    "history": [],           # last N density readings per direction
}

# Simulation timing constants (seconds)
YELLOW_DURATION = 3
MIN_GREEN = 6
MAX_GREEN = 20

# ─────────────────────────────────────────────
# AI LOGIC — rule-based signal optimisation
# ─────────────────────────────────────────────

def density_to_label(d: int) -> str:
    if d < 30:   return "LOW"
    if d < 70:   return "MEDIUM"
    return "HIGH"

def compute_green_time(density: int, time_of_day: str) -> int:
    """
    Weighted rule:
      base = 6s
      each density point above 30 adds proportional time
      peak hours multiply by 1.3, night by 0.7
    """
    base = MIN_GREEN
    extra = max(0, density - 30) / 70 * (MAX_GREEN - MIN_GREEN)
    green = int(base + extra)
    multipliers = {"PEAK": 1.3, "NORMAL": 1.0, "NIGHT": 0.7}
    green = int(green * multipliers.get(time_of_day, 1.0))
    return max(MIN_GREEN, min(MAX_GREEN, green))

def pick_next_direction() -> str:
    """
    Pick the direction with the highest vehicle density.
    Tie-break: round-robin.
    """
    densities = state["density"]
    current = state["active_direction"]
    idx = DIRECTIONS.index(current)
    
    # Find direction with max density (excluding current)
    candidates = [(d, densities[d]) for d in DIRECTIONS if d != current]
    candidates.sort(key=lambda x: -x[1])
    
    if candidates and candidates[0][1] > densities[current]:
        return candidates[0][0]
    # Round-robin fallback
    return DIRECTIONS[(idx + 1) % 4]

# ─────────────────────────────────────────────
# BACKGROUND SIMULATION LOOP
# ─────────────────────────────────────────────

def simulation_loop():
    """
    Runs in a daemon thread.
    Every second: update densities, advance timer, switch phases.
    """
    while True:
        time.sleep(1)
        tick()

def tick():
    s = state

    # ── Update vehicle densities (simulate arrival/departure) ──
    for d in DIRECTIONS:
        delta = random.randint(-8, 12)
        # Active green lane: vehicles leave faster
        if d == s["active_direction"] and s["phase"] == "GREEN":
            delta -= 10
        new_val = s["density"][d] + delta
        s["density"][d] = max(0, min(100, new_val))
        s["vehicle_count"][d] = int(s["density"][d] / 10)

    # Keep rolling history (last 30 ticks per direction)
    entry = {"ts": int(time.time()), **{d: s["density"][d] for d in DIRECTIONS}}
    s["history"].append(entry)
    if len(s["history"]) > 30:
        s["history"].pop(0)

    # ── Emergency override ──
    if s["emergency"]["active"]:
        ed = s["emergency"]["direction"]
        for d in DIRECTIONS:
            s["signals"][d] = "GREEN" if d == ed else "RED"
        s["active_direction"] = ed
        s["phase"] = "GREEN"
        s["mode"] = "EMERGENCY"
        s["timer"] = 0
        return

    # ── Manual mode — don't auto-advance ──
    if s["mode"] == "MANUAL":
        s["timer"] = max(0, s["timer"] - 1)
        return

    # ── AUTO mode: advance timer ──
    s["timer"] = max(0, s["timer"] - 1)

    if s["timer"] == 0:
        advance_phase()

def advance_phase():
    s = state
    if s["phase"] == "GREEN":
        # Transition to yellow
        s["phase"] = "YELLOW"
        s["signals"][s["active_direction"]] = "YELLOW"
        s["timer"] = YELLOW_DURATION

    elif s["phase"] == "YELLOW":
        # All-red gap then switch
        for d in DIRECTIONS:
            s["signals"][d] = "RED"
        s["phase"] = "RED_ALL"
        s["timer"] = 1

    elif s["phase"] == "RED_ALL":
        # Pick next direction, go green
        s["cycle_count"] += 1
        next_dir = pick_next_direction()
        s["active_direction"] = next_dir
        green_t = compute_green_time(s["density"][next_dir], s["time_of_day"])
        s["max_timer"] = green_t
        s["timer"] = green_t
        s["phase"] = "GREEN"
        for d in DIRECTIONS:
            s["signals"][d] = "GREEN" if d == next_dir else "RED"

# Kick off with an initial green
state["signals"]["NORTH"] = "GREEN"
state["timer"] = compute_green_time(50, "NORMAL")
state["max_timer"] = state["timer"]
state["phase"] = "GREEN"
for d in DIRECTIONS:
    state["density"][d] = random.randint(10, 80)

threading.Thread(target=simulation_loop, daemon=True).start()

# ─────────────────────────────────────────────
# API ROUTES
# ─────────────────────────────────────────────

@app.route("/api/state")
def get_state():
    s = state
    return jsonify({
        "signals":    s["signals"],
        "density":    {d: s["density"][d] for d in DIRECTIONS},
        "density_label": {d: density_to_label(s["density"][d]) for d in DIRECTIONS},
        "vehicle_count": s["vehicle_count"],
        "active_direction": s["active_direction"],
        "phase":      s["phase"],
        "timer":      s["timer"],
        "max_timer":  s["max_timer"],
        "emergency":  s["emergency"],
        "cycle_count": s["cycle_count"],
        "mode":       s["mode"],
        "time_of_day": s["time_of_day"],
        "history":    s["history"][-10:],  # last 10 for chart
    })

@app.route("/api/emergency", methods=["POST"])
def set_emergency():
    data = request.json
    active    = data.get("active", False)
    direction = data.get("direction", "NORTH")
    state["emergency"]["active"]    = active
    state["emergency"]["direction"] = direction if active else None
    if not active:
        # Resume AUTO mode
        state["mode"] = "AUTO"
        state["phase"] = "RED_ALL"
        state["timer"] = 1
        for d in DIRECTIONS:
            state["signals"][d] = "RED"
    return jsonify({"ok": True, "emergency": state["emergency"]})

@app.route("/api/mode", methods=["POST"])
def set_mode():
    mode = request.json.get("mode", "AUTO")
    if mode in ("AUTO", "MANUAL"):
        state["mode"] = mode
    return jsonify({"ok": True, "mode": state["mode"]})

@app.route("/api/manual_signal", methods=["POST"])
def manual_signal():
    """Force a specific direction green (manual / police override)."""
    direction = request.json.get("direction")
    if direction not in DIRECTIONS:
        return jsonify({"error": "Invalid direction"}), 400
    state["mode"] = "MANUAL"
    state["active_direction"] = direction
    state["phase"] = "GREEN"
    green_t = compute_green_time(state["density"][direction], state["time_of_day"])
    state["timer"] = green_t
    state["max_timer"] = green_t
    for d in DIRECTIONS:
        state["signals"][d] = "GREEN" if d == direction else "RED"
    return jsonify({"ok": True})

@app.route("/api/time_of_day", methods=["POST"])
def set_time_of_day():
    tod = request.json.get("time_of_day", "NORMAL")
    if tod in ("PEAK", "NORMAL", "NIGHT"):
        state["time_of_day"] = tod
    return jsonify({"ok": True, "time_of_day": state["time_of_day"]})

@app.route("/api/density", methods=["POST"])
def set_density():
    """Allow frontend to manually set density for a lane."""
    direction = request.json.get("direction")
    value     = request.json.get("value", 50)
    if direction in DIRECTIONS:
        state["density"][direction] = max(0, min(100, int(value)))
    return jsonify({"ok": True})

if __name__ == "__main__":
    app.run(debug=False, port=5000)
