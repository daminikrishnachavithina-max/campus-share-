# Campus Book Share

Campus Book Share is a local-first web app concept for college students to share books, notes, past papers, lab equipment, and other study resources. A student can post what they **HAVE** or **NEED**. The app checks potential matches with a locally running Ollama model and lets matched students exchange messages.

The interface uses a pastel theme. Listings, matches, and chat messages are stored in a local SQLite database.

## Features

- Create **HAVE** and **NEED** posts.
- Categorize books, notes/past papers, lab equipment/tools, and other items.
- Choose whether an item is lent, given free, or sold.
- Optionally mark a request as urgent and enter a price for items being sold.
- Compare potential matches with a local Ollama model.
- View matches, copy contact details, and mark an exchange as done.
- Keep a separate chat history for matches, including completed exchanges.
- Store app data locally in `campus_share.db`.
- Run the web interface on the same computer without a cloud service.

## Requirements

- Python 3.10 or newer recommended.
- [Ollama](https://ollama.com/) installed locally.
- The model `qwen2.5-coder:7b` downloaded in Ollama for AI matching.

The app uses Python's standard library, so no `pip install` is required.

## Run on Windows

1. Install Python and Ollama.
2. Open PowerShell and download the model once while connected to the internet:

   ```powershell
   ollama pull qwen2.5-coder:7b
   ```

3. Start Ollama if it is not already running.
4. Download or clone this repository, then open PowerShell in the project folder.
5. Start the app:

   ```powershell
   python campus_share.py
   ```

6. Open <http://localhost:8000> in your browser.

Keep the PowerShell window open while using the app. Press `Ctrl+C` in PowerShell to stop it.

## Run on macOS or Linux

Make sure Python and Ollama are installed, download the model with `ollama pull qwen2.5-coder:7b`, then run:

```bash
python3 campus_share.py
```

Open <http://localhost:8000> in your browser.

## Offline use

After Python, Ollama, and the model have been installed/downloaded, the app's local web server and AI matching can run without sending prompts to a cloud AI service. Internet access is needed for initial installation/model download and for GitHub access. Ollama must be running for AI matching.

## Data and privacy notes

- The database file `campus_share.db` is created locally when the app starts.
- The database is excluded from Git by `.gitignore`; do not commit real student names, contact information, or chat messages.
- This prototype does not implement college authentication or production-grade access control.
- By default, the server binds to `127.0.0.1`, so it is accessible only from the same computer. Other students on other computers cannot use the same instance unless you deliberately configure a shared host/network deployment and add appropriate security controls.

## Project journey

The project began with the idea of helping students find books and study resources within their college instead of relying on scattered group messages. It developed into a local web app with:

1. **Resource listings:** students can post what they have or need.
2. **AI-assisted matching:** the app asks a local Ollama model whether two differently worded items refer to the same resource.
3. **Match management:** students can view matches and mark exchanges as complete.
4. **Persistent messaging:** conversations are saved in SQLite and remain accessible from the Chats area after an exchange is marked done.
5. **Interface polish:** the web interface has a pastel theme and separate Home, Matches, and Chats views.
6. **Local-first approach:** listings and messages are stored on the local computer, and AI matching uses a local model rather than a cloud API.

## Repository contents

- `campus_share.py` — complete Python application, including the embedded HTML/CSS/JavaScript interface and local HTTP API.
- `README.md` — project description, setup, run instructions, and development journey.
- `.gitignore` — excludes local database files and common temporary files.
- `LICENSE` — MIT license.

## Limitations and future work

This is a prototype. Possible next steps include college login, stronger authorization and validation, improved database migrations, tests, deployment for multiple students on a campus network, and a shared database/server for cross-device messaging.
