from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)

# the .db file
DB = "assignments.db"

# creates the tables when the app starts, but doesnt overwrite it if its already there
def setup():
    conn = sqlite3.connect(DB)
    conn.execute("""CREATE TABLE IF NOT EXISTS assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        subject TEXT,
        deadline TEXT,
        notes TEXT,
        completed INTEGER DEFAULT 0,  -- 0 = not done, 1 = done
        completed_at TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS achievements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        assignment_id INTEGER,  -- which assignment this belongs to
        type TEXT,
        label TEXT,  -- the text that shows up on screen
        earned_at TEXT DEFAULT (datetime('now'))
    )""")
    conn.commit()
    conn.close()


# takes whatever the user typed as deadline and turns it into a proper datetime string so the database can sort correctly
def parse_deadline(raw):
    raw = raw.strip().replace("T", " ")
    for fmt in ["%m/%d/%Y %H:%M:%S", "%m/%d/%Y %H:%M", "%m/%d/%Y"]:
        try:
            return datetime.strptime(raw, fmt).isoformat()
        except:
            pass
    return None  # return None if nothing worked instead of storing garbage


# deciding what achievent to give
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
        return None  # if the date parsing fails just don't give an achievement


# displays html when opened in browser
@app.route("/")
def index():
    return send_from_directory(os.path.dirname(os.path.abspath(__file__)), "index.html")


# returns assignments sorted by deadline, incomplete first
@app.route("/api/assignments", methods=["GET"])
def get_assignments():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM assignments ORDER BY completed ASC, deadline ASC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


# adds new assignment to database
@app.route("/api/assignments", methods=["POST"])
@app.route("/api/assignments", methods=["POST"])
def add_assignment():
    data = request.json
    if not data.get("title") or not data.get("deadline"):
        return jsonify({"error": "need a title and deadline"}), 400

    deadline = parse_deadline(data["deadline"])

    # reject if the date string was unreadable
    if deadline is None:
        return jsonify({"error": "invalid date format"}), 400

    # reject if the deadline is in the past
    if datetime.fromisoformat(deadline) < datetime.now():
        return jsonify({"error": "deadline is in the past"}), 400

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cur = conn.execute(
        "INSERT INTO assignments (title, subject, deadline, notes) VALUES (?, ?, ?, ?)",
        (data["title"], data.get("subject", ""), deadline, data.get("notes", ""))
    )
    conn.commit()
    row = conn.execute("SELECT * FROM assignments WHERE id = ?", (cur.lastrowid,)).fetchone()
    conn.close()
    return jsonify(dict(row)), 201


# handles marking as done/undone, and also any field edits
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
            # marking as done: save the time and check for an achievement
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
            # unmarking as done and remove the achievement
            conn.execute("UPDATE assignments SET completed = 0, completed_at = NULL WHERE id = ?", (id,))
            conn.execute("DELETE FROM achievements WHERE assignment_id = ?", (id,))

    # updates any other fields
    for field in ["title", "subject", "deadline", "notes"]:
        if field in data:
            conn.execute(f"UPDATE assignments SET {field} = ? WHERE id = ?", (data[field], id))

    conn.commit()
    updated = dict(conn.execute("SELECT * FROM assignments WHERE id = ?", (id,)).fetchone())
    conn.close()

    if new_achievement:
        updated["new_achievement"] = new_achievement
    return jsonify(updated)


# deletes an assignment and its achievement if it exists
@app.route("/api/assignments/<int:id>", methods=["DELETE"])
def delete_assignment(id):
    conn = sqlite3.connect(DB)
    conn.execute("DELETE FROM achievements WHERE assignment_id = ?", (id,))
    conn.execute("DELETE FROM assignments WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return jsonify({"deleted": id})


# returns all earned achievements with the assignment title attached
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


if __name__ == "__main__":
    setup()
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, port=port)
