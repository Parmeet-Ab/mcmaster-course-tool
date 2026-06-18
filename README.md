# McMaster Course Tool
A full-stack tool that helps McMaster students make course decisions without hunting through multiple websites. Search any course code and instantly get an AI-generated course summary, condensed prerequisites, the current professor, and their Rate My Professor rating, all in one place.

---

## What It Does

Students at McMaster have to cross-reference the academic calendar, the timetable system, and Rate My Professor separately just to answer "is this course worth taking?" This tool automates that entire workflow.

Type a course code (e.g. `Chem 1A03`) into the Chrome extension popup, and within seconds you get:
- A 2-sentence, AI-generated plain-language summary of what the course is about
- The course units, plus prerequisites and antirequisites condensed by AI to fit the popup
- The professor(s) teaching it this semester, pulled from the live timetable API
- Their Rate My Professor overall rating, difficulty score, and review count

A loading spinner shows while the request is in flight so it's always clear the extension is working.

---

## Architecture

```
Chrome Extension (popup.js)
        │
Flask REST API (app.py) — deployed on Railway
        │
        ├─── scraper.py -> McMaster Academic Calendar(BeautifulSoup)
        ├─── scraper.py -> McMaster Timetable API (XML parsing)
        ├─── scraper.py -> Rate My Professor (GraphQL API)
        └─── summarizer.py -> Google Gemini (AI summary + requisite shortening)
```

The backend runs two scraping tasks concurrently using `ThreadPoolExecutor` so the calendar lookup(to get course information) and timetable fetch(for professor information) happen in parallel, keeping response times low.

A pre-built index (`data/courses.json`, `data/professors.json`) is generated once per semester. In the past I attempted to have it direcrtly acess the information for professors, however, due to secuirty measures made on the academic calender, this process has to occur once per semester instead. 

---

## AI Features
The Google Gemini API is used to make the data student-friendly:

- **Course summary** — a 2-sentence plain-language overview generated from the title and description

- **Requisite shortening** — prerequisites and antirequisites are condensed to just course codes and essential conditions(cleaning up data scraped)

---

## Data & Deployment

The scraped index files are **not committed to the repo** In production they live on a **Railway persistent volume**, with the app reading from a configurable `DATA_DIR` (defaulting to local `data/` in development, set to the mounted volume path on Railway). This keeps the public repo clean while the deployed app still has the data it needs.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Chrome Extension | JavaScript|
| Backend API | Python, Flask |
| Web Scraping | BeautifulSoup, requests |
| AI / LLM | Google Gemini API (summaries + requisite condensing) |
| External API | Rate My Professor GraphQL, McMaster Timetable XML API |
| Storage | Railway persistent volume (scraped data kept out of the repo) |
| Deployment | Railway, Gunicorn |

---

## Running Locally
Download the chrome-extension folder. 

To use the Chrome extension: go to `chrome://extensions`, enable Developer Mode, click "Load unpacked", and select the `chrome-extension/` folder.

## NOTE: This is not offically from McMaster
