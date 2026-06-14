# assignment tracker backend
# sqlite for storage, ollama (qwen2.5:1.5b) for time estimates

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3
import os
import requests
import json
import re
from datetime import datetime

app = Flask(__name__)
CORS(app)

DB = "assignments.db"

# ollama config
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen2.5:1.5b"


# creates tables on first run, safe to call every time
def setup():
    conn = sqlite3.connect(DB)
    conn.execute("""CREATE TABLE IF NOT EXISTS assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        subject TEXT,
        deadline TEXT,
        notes TEXT,
        estimated_hours REAL,
        estimated_breakdown TEXT,
        completed INTEGER DEFAULT 0,  -- 0 = not done, 1 = done
        completed_at TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    )""")
    # added these two columns after the first version shipped, so we need to migrate old dbs
    for col in ["estimated_hours REAL", "estimated_breakdown TEXT"]:
        try:
            conn.execute(f"ALTER TABLE assignments ADD COLUMN {col}")
        except:
            pass  # already there, move on
    conn.execute("""CREATE TABLE IF NOT EXISTS achievements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        assignment_id INTEGER,
        type TEXT,
        label TEXT,
        earned_at TEXT DEFAULT (datetime('now'))
    )""")
    conn.commit()
    conn.close()


# turn whatever date string the user typed into ISO format so sqlite can sort it
# returns None if nothing matched so the caller can reject it instead of storing garbage
def parse_deadline(raw):
    raw = raw.strip().replace("T", " ")
    for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d",
                "%m/%d/%Y %H:%M:%S", "%m/%d/%Y %H:%M", "%m/%d/%Y"]:
        try:
            return datetime.strptime(raw, fmt).isoformat()
        except:
            pass
    return None


# pick an achievement based on how many days early the assignment was finished
def get_achievement(deadline_str, completed_str):
    try:
        deadline = datetime.fromisoformat(deadline_str)
        completed = datetime.fromisoformat(completed_str)
        days_early = (deadline - completed).total_seconds() / 86400

        if days_early >= 7:
            return {"type": "week_early", "label": "Week Ahead: finished 7+ days early!"}
        elif days_early >= 3:
            return {"type": "days_early", "label": "Ahead of Schedule: finished 3+ days early!"}
        elif days_early >= 1:
            return {"type": "day_early", "label": "Finished with a day to spare!"}
        elif days_early >= 0:
            return {"type": "just_in_time", "label": "Procrastinating, are we?"}
        else:
            return {"type": "late", "label": "Better late than never I guess."}
    except:
        return None  # bad date strings, just skip


@app.route("/")
def index():
    return send_from_directory(os.path.dirname(os.path.abspath(__file__)), "index.html")


# all assignments, incomplete first, then sorted by deadline
@app.route("/api/assignments", methods=["GET"])
def get_assignments():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM assignments ORDER BY completed ASC, deadline ASC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


# title and deadline are required, everything else optional
@app.route("/api/assignments", methods=["POST"])
def add_assignment():
    data = request.json
    if not data.get("title") or not data.get("deadline"):
        return jsonify({"error": "need a title and deadline"}), 400

    deadline = parse_deadline(data["deadline"])

    if deadline is None:
        return jsonify({"error": "invalid date format"}), 400

    if datetime.fromisoformat(deadline) < datetime.now():
        return jsonify({"error": "deadline is in the past"}), 400

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cur = conn.execute(
        "INSERT INTO assignments (title, subject, deadline, notes, estimated_hours, estimated_breakdown) VALUES (?, ?, ?, ?, ?, ?)",
        (data["title"], data.get("subject", ""), deadline, data.get("notes", ""),
         data.get("estimated_hours"), data.get("estimated_breakdown"))
    )
    conn.commit()
    row = conn.execute("SELECT * FROM assignments WHERE id = ?", (cur.lastrowid,)).fetchone()
    conn.close()
    return jsonify(dict(row)), 201


# handles both completion toggling and regular field edits
@app.route("/api/assignments/<int:id>", methods=["PATCH"])
def update_assignment(id):
    data = request.json
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    row = conn.execute("SELECT * FROM assignments WHERE id = ?", (id,)).fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "not found"}), 404

    assignment = dict(row)
    new_achievement = None

    if "completed" in data:
        if data["completed"] and not assignment["completed"]:
            # marking done: record when and check if they earned a badge
            now = datetime.now().isoformat()
            conn.execute("UPDATE assignments SET completed = 1, completed_at = ? WHERE id = ?", (now, id))
            ach = get_achievement(assignment["deadline"], now)
            if ach:
                conn.execute(
                    "INSERT INTO achievements (assignment_id, type, label) VALUES (?, ?, ?)",
                    (id, ach["type"], ach["label"])
                )
                new_achievement = ach
        elif not data["completed"]:
            # unmarking as done, undo everything
            conn.execute("UPDATE assignments SET completed = 0, completed_at = NULL WHERE id = ?", (id,))
            conn.execute("DELETE FROM achievements WHERE assignment_id = ?", (id,))

    # update whichever text fields were included in the request
    for field in ["title", "subject", "deadline", "notes"]:
        if field in data:
            conn.execute(f"UPDATE assignments SET {field} = ? WHERE id = ?", (data[field], id))

    conn.commit()
    updated = dict(conn.execute("SELECT * FROM assignments WHERE id = ?", (id,)).fetchone())
    conn.close()

    # attach the achievement to the response so the UI can show the badge right away
    if new_achievement:
        updated["new_achievement"] = new_achievement
    return jsonify(updated)


# delete the assignment and its achievement if there is one
@app.route("/api/assignments/<int:id>", methods=["DELETE"])
def delete_assignment(id):
    conn = sqlite3.connect(DB)
    conn.execute("DELETE FROM achievements WHERE assignment_id = ?", (id,))
    conn.execute("DELETE FROM assignments WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return jsonify({"deleted": id})


# all achievements, newest first, with the assignment title joined in
@app.route("/api/achievements", methods=["GET"])
def get_achievements():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT a.*, b.title as assignment_title
        FROM achievements a
        JOIN assignments b ON a.assignment_id = b.id
        ORDER BY a.earned_at DESC
    """).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


# ask ollama to estimate keyboard time for the assignment
@app.route("/api/estimate", methods=["POST"])
def estimate():
    data = request.get_json()
    description = data.get("description", "").strip()
    if not description:
        return jsonify({"error": "no description provided"}), 400

    # few-shot prompt with concrete examples so the model has a reference frame to calibrate against
    # low temperature keeps the output consistent across repeated calls
    prompt = f"""Estimate keyboard time only for a first-year CS student doing this assignment. Keyboard time means actively typing and testing code — not reading the task, not thinking, not watching tutorials.

Examples (use these to calibrate your answer):
- "print hello world" -> 0.25h
- "write a for loop that prints 1 to 10" -> 0.25h
- "function that returns whether a number is even" -> 0.25h
- "function that checks if a number is prime" -> 0.5h
- "simple calculator with +/-/*// using if/else" -> 0.5h
- "flask route that returns JSON from a list" -> 0.5h
- "read a CSV and print rows that match a condition" -> 0.75h
- "todo app with add, delete, and list commands" -> 1.25h
- "flask app with a database and two routes" -> 1.5h

Assignment: {description}

Rules:
- Single-concept exercises usually take 0.25h to 0.5h
- Multi-step exercises: 0.5h to 1.0h
- Small projects: 1.0h to 2.0h
- Never output more than 2.0
- When unsure, pick the lower end

Reply ONLY with this JSON, nothing else:
{{"hours": <number>}}"""

    try:
        res = requests.post(OLLAMA_URL, json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.3,
                "num_predict": 32  # the reply is tiny, no need to let it ramble
            }
        }, timeout=30)

        raw = res.json()["response"]
        match = re.search(r'\{.*?\}', raw, re.DOTALL)
        if match:
            parsed = json.loads(match.group())
            h = float(parsed.get("hours", 0.5))

            # small models overshoot even with a strict prompt, scale down a bit
            h = h * 0.75

            return jsonify({"hours": round(max(0.25, min(2.0, h)), 2)})

        return jsonify({"error": "model gave an unexpected response"}), 500
    except requests.exceptions.ConnectionError:
        return jsonify({"error": "ollama is not running - start it with: ollama serve"}), 503
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    setup()
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, port=port)
