# DEADLines app

A local assignment tracker that helps users manage tasks, deadlines, and notes while maintaining progress tracking through a local database.

## Features

* Add assignments with deadlines and notes
* Track and manage tasks
* Local achievement system
* Stores all data in a local `.db` file
* No account or internet connection required

## Getting Started

### 1. Clone the repository

`git clone https://github.com/talioni/DEADLines-prototype.git`

### 2. Install dependencies

`pip install flask flask-cors`

### 3. Run the application

`py app.py`

### 4. Open in browser

Open the URL shown in the terminal (usually):

`http://127.0.0.1:5000`

## Usage

* Add assignments with deadlines and notes
* Mark assignments as completed
* Track progress and achievements
* All data is saved automatically in `assignments.db`

## Stopping the Application

Press `Ctrl + C` in the terminal to stop the server.

All data remains stored in `assignments.db` and will be available when the application is restarted.

## Tech Stack

* Python
* Flask
* Flask-CORS
* SQLite

## Data Storage

All application data is stored locally in:

`assignments.db`

No external services or accounts are used.

## Future Improvements

Ease of use updates.
