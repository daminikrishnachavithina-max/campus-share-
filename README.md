# Campus Share

A college-only app where students post what they **have** or **need**: books, notes, past papers, lab equipment. A local open-weight AI model matches similar items, even when they are written differently, so students can find each other and borrow, take for free, or buy within their own college.

Built for Hacktoberfest 2026 (theme: AI belongs to everyone).

## The problem
A 1st year student has an exam in 2 days and cannot buy the book in time. A senior in the same college already has it, but they do not know each other. WhatsApp requests get buried, and cloud marketplaces are not built for one campus and collect students' personal details.

## What it does
- Post an item you HAVE or NEED, with a category, and offer it as Lend, Give free or Sell
- Mark a need as urgent (for example "exam in 1 day")
- The local AI model matches different names for the same item, for example "DBMS by Korth" and "Database System Concepts"
- Contact details are hidden in the public list and shown only to the two matched students
- A private chat for each match, which stays open after the item is handed over
- Mark as done when the exchange is finished

## Why open-weight AI
- **Privacy:** student names, hostels and contacts never leave the machine
- **Offline:** the model, database and web page all run locally with no internet
- **Cost:** no per-use bill

## Tech stack
- Model: `qwen3.5:4b` (open-weight) through Ollama
- Backend: Python 3 standard library only (`http.server`, `sqlite3`, `json`, `urllib`)
- Database: SQLite
- Frontend: HTML, CSS and JavaScript, with no frameworks and no external libraries

## How to run
1. Install [Ollama](https://ollama.com/download) and open it
2. Download the model:
```
   ollama pull qwen3.5:4b
```
3. Install Python 3 and run:
```
   python campus_share_pastel.py
```
4. Open http://localhost:8000 (it opens automatically)

The first match can take up to a minute while the model loads into memory.

## Limitations (version 1)
- No college login: the name you enter identifies you
- Runs on one machine; other students cannot connect from their own phones yet
- Chat is not real time (it refreshes every few seconds)

## Next steps
- College accounts and login
- Run on one college computer so students can join over the campus Wi-Fi
- Notifications and a return reminder
- Better ranking of urgent requests

## Note on AI assistance
I used an AI assistant while learning and building this project. The AI inside the app is only the local open-weight model.

## License
MIT
