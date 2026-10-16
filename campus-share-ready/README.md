# Campus Share

Campus Share is a local-first web app for college students to share books, notes, past papers, lab equipment and other study resources. A student posts what they HAVE or NEED. The app checks potential matches with a locally running open-weight model through Ollama and lets matched students chat.

The interface uses a pastel theme. Listings, matches and chat messages are stored in a local SQLite database. Built for Hacktoberfest 2026 (theme: AI belongs to everyone).

## Features
- Create HAVE and NEED posts in categories: books, notes/past papers, lab equipment/tools, other
- Choose Lend, Give free or Sell (with a price), and mark a request as urgent
- AI matching: a local model decides whether differently worded posts are the same item
- Contact details are hidden in the public list and shown only to the two matched students
- Copy contact, mark an exchange as done
- Separate chat for each match, which stays available after the exchange is done
- All data is stored locally in `campus_share.db`

## Requirements
- Python 3.10 or newer (standard library only, no pip install)
- Ollama installed locally
- The model `qwen3.5:4b` downloaded in Ollama

## Run on Windows
1. Install Python and Ollama.
2. Download the model once while connected to the internet:
```
   ollama pull qwen3.5:4b
```
3. Make sure Ollama is running.
4. Download or clone this repository and open PowerShell in the project folder.
5. Start the app:
```
   python campus_share_pastel.py
```
6. Open http://localhost:8000 in your browser. Keep the PowerShell window open. Press Ctrl+C to stop.

On macOS or Linux, use `python3 campus_share_pastel.py`.

The first match can take up to a minute while the model loads into memory.

## Offline use
After Python, Ollama and the model are installed, the web server and AI matching run without a cloud AI service. Internet is needed only for the first install, the model download and GitHub.

## Why open-weight AI
- Privacy: student names, hostels and contacts never leave the machine
- Offline: the model, database and web page all run locally
- Cost: no per-use bill

## Data and privacy notes
- `campus_share.db` is created locally and excluded from Git. Do not commit real student names, contacts or messages.
- This prototype has no college login: the name you enter identifies you.
- The server binds to 127.0.0.1, so only the same computer can use it. Sharing it with other students needs a deliberate network setup and proper security.

## Repository contents
- `campus_share_pastel.py`: the complete app (embedded HTML, CSS and JavaScript, plus the local HTTP API)
- `campus_share.py`: an earlier prototype
- `README.md`, `LICENSE` (MIT), `.gitignore`

## Limitations and future work
This is a prototype. Next steps: college login, stronger authorization and validation, tests, and a deployment that lets many students on a campus network use one shared instance.

## Note on AI assistance
I used an AI assistant while learning and building this project. The AI inside the app is only the local open-weight model.
