# CourtSplits
CourtSplits is an NBA stats app where you search by player or team, set filters and stat thresholds, and see how often those thresholds actually hit over the season, with full box scores and real historical betting lines for every game. (Built for analytics, not as a bet tracker)

## Demo
![CourtSplits team search](docs/screenshots/CourtSplitsTeamDemo.png)<br>
![CourtSplits player search](docs/screenshots/CourtSplitsPlayerDemo.png)

## Features
-Search by player or team, with filters like opponent, home/away, position, date range, rest days, back-to-back, season type, and more<br>
-Set over/under/equals thresholds on any stat, with a global toggle for inclusive vs strict comparisons<br>
-See historical occurrence rates: hit count, percentage, and full sample size, always paginated<br>
-Drill into any game for the full box score, both teams, every player, and DNPs with the real reason<br>
-Real historical odds for every game: spread, total, moneyline, and halftime lines, with the winning side highlighted<br>
-Live current-season data that updates without needing a redeploy, blended right in with the frozen historical seasons<br>
-A layered system for player positions that pulls from multiple real sources to keep PG/SG/SF/PF/C labels consistent

## Technologies
-Backend: Python 3.13, FastAPI, pandas, Pydantic<br>
-Storage: Parquet (pyarrow) for the frozen historical seasons, PostgreSQL (psycopg) for the live season and analytics<br>
-Frontend: TypeScript, React 19, Vite<br>
-Testing: pytest for the backend, Playwright for checking the frontend

## Project Structure
-`engine/`: the core stats engine, where `query.py` handles player and team query logic, `data.py` loads and caches the data, `game_detail.py` builds a single game's box score, `live_db.py` reads the live season from Postgres, and `analytics.py` logs anonymous usage. All pure functions, no web-framework dependency, fully unit tested<br>
-`api/`: the FastAPI layer, `main.py` for routes and `schemas.py` for validating requests and responses<br>
-`scripts/`: the data pipeline, including `preprocess.py` to turn raw Excel into Parquet, `ingest_live_data.py` to load a live-season workbook into Postgres, and `fetch_from_drive.py` to pull the daily workbook from Google Drive<br>
-`data/`: the raw source workbooks in `raw/` and the processed Parquet files the app actually serves in `processed/`<br>
-`db/`: a hand-written Postgres schema in `schema.sql`, no ORM or migration framework<br>
-`frontend/`: the React and Vite app, with `src/components/` holding the search screens, results tables, and the game detail modal<br>
-`tests/`: the pytest suite

## Build and Run
### Requirements
-Python 3.13<br>
-Node.js, for the frontend<br>
-PostgreSQL, optional: only needed for live-season data and usage analytics, and without it everything just falls back to the committed historical Parquet data

## Backend
`.venv/bin/uvicorn api.main:app --app-dir . --port 8000 --reload`<br>
Runs the API at `http://127.0.0.1:8000`, with interactive docs at `/docs`.

## Frontend
`cd frontend`<br>
`npm install`<br>
`npm run dev`<br>
Runs the app at `http://localhost:5173`, using `VITE_API_BASE_URL` from `frontend/.env`.

## Running Tests
`.venv/bin/python3 -m pytest tests/ -q`<br>
A few live-data tests get skipped unless `TEST_DATABASE_URL` points at a real local Postgres.

## How It Works
The project splits into three pieces: a data pipeline, a query engine, and two thin layers on top for serving it.

Historical data comes in as static Excel workbooks from BigDataBall, a paid provider rather than a live API. `scripts/preprocess.py` cleans those sheets up and turns them into Parquet files, computing a handful of derived columns (margin, combined totals, rest-day buckets) along the way. Those Parquet files get loaded once per process with `functools.lru_cache`, so past seasons, which are done and never change, are basically free to query after that first load.

The current season works differently. A Postgres database holds rows that get refreshed daily, and `engine/data.py` merges those live rows into the historical Parquet data, deduping by game ID and letting live data win on conflict, using a short TTL cache instead of `lru_cache` since this data actually changes. None of the layers above that merge, the query engine, the API, the frontend, need to know two different storage backends are even involved.

`engine/query.py` sits on top of all that: plain functions that take a DataFrame and some filter params and return a dict, no HTTP, no database, no side effects. That's what keeps the engine easy to unit test. FastAPI (`api/main.py`) is just a thin routing and validation layer over those functions, and the React frontend renders the JSON with no router at all, since switching views is just local `useState` in `App.tsx`.

## What I Learned
-Postgres might just not be configured, and the app has to handle that gracefully: the live-season feature and the analytics logging both need to behave exactly like the old Parquet-only app when `DATABASE_URL` isn't set, and any connection failure gets swallowed instead of turning a normal request into a 500<br>
-Two caching strategies living side by side: `lru_cache` for historical seasons that never change, and a small hand-rolled TTL cache for the live season that refreshes daily. Also had to get dtypes right so a Postgres row and a Parquet row could be combined without pandas quietly upcasting a column<br>
-Anonymizing usage data without any accounts: hash each visitor's IP with a private, server-side salt instead of storing the raw IP, since IPv4 addresses are few enough to brute-force a lookup table against an unsalted hash<br>
-Not trusting the raw data at face value: a schedule-context tag from the data provider looked like it meant rest days, but didn't, and that only got caught by spot-checking real games against an outside source

## Future Improvements
-Disable or remove filters that become redundant or impossible once another filter is picked, instead of letting someone search a combination that can never match anything<br>
-Pull in more historical betting-line data, like player prop lines, beyond spread, total, and moneyline<br>
-Switch live-season ingestion from a full truncate-and-reload to an incremental upsert<br>
-Add an in-app help page for a couple of known rough edges, like how the period checkboxes on the team screen interact with the full-game total field
