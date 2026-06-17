# DEADLines app
A local assignment tracker that helps users manage tasks, deadlines, and notes while maintaining progress tracking through a local database. Includes an optional AI-powered time estimate for each assignment, generated locally via Ollama.

## Features
* Add assignments with title, subject, deadline (date and time), and notes
* Subject autocomplete based on subjects you've already used
* Optional AI time estimate for how long an assignment will take, based on your notes
* Filter assignments by all, active, or done
* Color-coded rows that highlight assignments due soon
* Mark assignments as completed or undo that
* Local achievement system based on how early an assignment was finished
* Stores all data in a local `.db` file
* No account required

## Getting Started

### 1. Clone the repository
`git clone https://github.com/talioni/DEADLines-prototype.git`

### 2. Install dependencies
`pip install flask flask-cors requests`

### 3. Set up Ollama (for time estimates)
The time estimate feature uses a local Ollama model. This step is optional — the app works fine without it, you just won't get time estimates.

* Install Ollama from https://ollama.com
* Pull the model used by the app:
`ollama pull qwen2.5:1.5b`
* Make sure Ollama is running before you use the estimate feature:
`ollama serve`

### 4. Run the application
`py app.py`

### 5. Open in browser
Open the URL shown in the terminal (usually):
`http://127.0.0.1:5000`

### Video demonstration
https://youtu.be/o2NbqU7tBJs?si=jvqaigWHTuse8EUU

## Usage
* Add assignments with a title, subject, deadline, and notes
* If you add notes, the app will try to estimate how long the assignment will take
* Mark assignments as completed, or uncheck them to undo
* Filter the list to show all, active, or completed assignments
* Track progress and achievements
* Delete assignments you no longer need
* All data is saved automatically in `assignments.db`

## Stopping the Application
Press `Ctrl + C` in the terminal to stop the server.
All data remains stored in `assignments.db` and will be available when the application is restarted.

## Tech Stack
* Python
* Flask
* Flask-CORS
* SQLite
* Ollama (qwen2.5:1.5b) for time estimates

## Data Storage
All application data is stored locally in:
`assignments.db`
No external services or accounts are used. The only network activity is the local connection to Ollama, if it's running.

## Future Improvements
Ease of use updates.
