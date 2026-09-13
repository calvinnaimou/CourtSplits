# courtSplitz

![Player search results](docs/screenshots/CourtSplitsPlayerDemo.png)
![Team search results](docs/screenshots/CourtSplitsTeamDemo.png)

An NBA statistical trend-analysis web app. Search by player or team, set filters and stat thresholds (points, rebounds, assists, shooting splits, and more), and see how often those thresholds have actually hit across the season — with full box scores and historical betting-line context (spread/total/moneyline) for every game. Built as an analytics tool, not a bet tracker.

## Features

- Search by player or by team, with configurable filters (opponent, home/away, position, date range, rest days, back-to-back, season type, and more)
- Numeric threshold conditions (over/under/equals) on any stat, with a global inclusive/strict toggle
- Historical occurrence-rate results — hit count, percentage, and full sample size, paginated
- Per-game drill-down: full box score for both teams, every player, and DNPs with real reasons
- Real historical odds data per game (spread, total, moneyline, half-time lines) with the winning side highlighted
- Live current-season data that updates without a redeploy, blended transparently with frozen historical seasons
- Anonymous, privacy-preserving usage analytics (no accounts, no raw IPs stored)
- A layered player-position system reconciling multiple real-world data sources into consistent PG/SG/SF/PF/C labels

## Technologies

- **Backend**: Python 3.13, FastAPI, pandas, Pydantic
- **Storage**: Parquet (pyarrow) for frozen historical seasons, PostgreSQL (psycopg) for the live current season and analytics
- **Frontend**: TypeScript, React 19, Vite
- **Testing**: pytest (backend), Playwright (frontend verification)

## Project Structure

- `engine/` — the core stats engine: `query.py` (player/team query logic), `data.py` (cached data loading), `game_detail.py` (single-game box scores), `live_db.py` (Postgres live-season reads), `analytics.py` (anonymous usage logging). Pure functions, no web-framework dependency, fully unit-testable.
- `api/` — the FastAPI layer (`main.py` routes, `schemas.py` request/response validation)
- `scripts/` — the data pipeline: `preprocess.py` (raw Excel → Parquet), `ingest_live_data.py` (loads a live-season workbook into Postgres), `fetch_from_drive.py` (pulls the daily workbook from Google Drive), `espn_positions.py`, `validate.py`
- `data/` — raw source workbooks (`raw/`) and the processed Parquet files the app actually serves (`processed/`)
- `db/` — hand-written Postgres schema (`schema.sql`), no ORM or migration framework
- `frontend/` — the React + Vite app (`src/components/` holds the search screens, results tables, and game-detail modal)
- `tests/` — the pytest suite

## Build and Run

### Requirements

- Python 3.13
- Node.js (for the frontend)
- PostgreSQL (optional — only needed for live current-season data and usage analytics; without it, everything falls back to the committed historical Parquet data)

### Backend

```
.venv/bin/uvicorn api.main:app --app-dir . --port 8000 --reload
```

Serves the API at `http://127.0.0.1:8000`, with interactive Swagger docs at `/docs`.

### Frontend

```
cd frontend
npm install
npm run dev
```

Serves the app at `http://localhost:5173`, reading `VITE_API_BASE_URL` from `frontend/.env`.

### Running Tests

```
.venv/bin/python3 -m pytest tests/ -q
```

A handful of live-data tests are skipped unless `TEST_DATABASE_URL` points at a real local Postgres instance.

## How It Works

The project splits cleanly into a data pipeline, a query engine, and two thin presentation layers on top.

Raw historical data arrives as static Excel workbooks (from BigDataBall, a paid provider — not a live API). `scripts/preprocess.py` cleans and reshapes those sheets into a handful of Parquet files, computing derived columns like margin, combined totals, and rest-day buckets along the way. Those Parquet files are loaded once per process via `functools.lru_cache`, so historical seasons — which are finished and never change — are effectively free to query after the first hit.

The current, in-progress season works differently: a Postgres database holds rows that get refreshed daily, and `engine/data.py` merges those live rows on top of the historical Parquet data (deduped by game ID, live wins on conflict) behind a short TTL cache instead of an `lru_cache`, since that data is genuinely mutable. Everything upstream of that merge — the query engine, the API, the frontend — is unaware that two different storage backends are involved.

On top of that sits `engine/query.py`: pure functions that take a DataFrame and a bag of filter parameters and return a plain dict — no HTTP, no database, no side effects — which is what makes the whole engine straightforward to unit test. FastAPI (`api/main.py`) is a thin routing/validation layer over those functions, and the React frontend consumes the resulting JSON with no router library at all — view switching is just local `useState` in `App.tsx`.

## What I Learned

**Postgres, and designing around a database that might not be there.** The live-season feature needed to behave identically whether or not `DATABASE_URL` was set — no live database shouldn't mean broken app, it should mean "acts like the old parquet-only version." That pushed every Postgres-touching function (`fetch_live_rows`, `log_query`) toward the same shape: try the operation, catch failures broadly, and degrade to "as if this feature didn't exist" rather than surfacing a 500. Getting the dtype handling right when merging a Postgres query result with a Parquet DataFrame was its own small trap — pandas will happily upcast a column (e.g. an `int` column touching a `NaN` becomes `float`) if the two sources don't agree on nullability, so `fetch_live_rows` explicitly casts every column to match the Parquet dtypes before the two get concatenated.

**Two different caching strategies for two different kinds of truth.** Historical seasons are immutable once the season ends, so `lru_cache` (load once, cache forever) is exactly right for them. The live season is the opposite — it changes every day — so it needed a small hand-rolled TTL cache instead, refreshing at most once per interval instead of never. Having both caching strategies live side by side in the same file, gated on whether `DATABASE_URL` is set, made it easy to reason about which one applied where, but it also meant being careful that a code change to one path couldn't accidentally affect the other.

**Anonymizing usage data without accounts.** The analytics table needed to answer "how many queries, how many distinct visitors" without ever persisting anything that traces back to a real person. The approach that stuck was hashing each visitor's IP with a private, server-side salt (`sha256(salt + ip)`) rather than storing IPs directly — the salt matters because IPv4 space is small enough (~4 billion addresses) to brute-force a lookup table against an unsalted hash. Logging itself is fire-and-forget: a failed insert (or a missing `DATABASE_URL`) is swallowed and logged server-side, never allowed to turn a successful API response into a 500.

**Data quality is not always what the source claims it is.** More than one column that looked authoritative turned out not to be trustworthy at face value — a schedule-context tag from the data provider was being mistaken for actual rest-day counts, and mixed-format odds strings couldn't be parsed by position (home/away) the way they first appeared to be, only by numeric magnitude. Both were only caught by spot-checking real games against an independent source, which reinforced treating "the raw data says X" as a hypothesis to verify, not a fact to build on directly.

## Future Improvements

- An in-app help page for a couple of known UX rough edges (e.g. how period-based team filters interact with the full-game total field)
- Finish and verify the Google Drive integration for fully automated daily live-season ingestion (currently untested against a real Drive folder, since the season it targets hasn't started yet)
- Move live-season ingestion from a full truncate-and-reload to an incremental upsert
- Surface the anonymous usage analytics somewhere (currently write-only)
