# ASTERA — Every Mission Leaves a Mark

ASTERA is an independent space-exploration archive and learning experience about the spacecraft, landers, rovers, instruments and probes that remain part of humanity's exploration story. It distinguishes surface hardware, inactive orbital spacecraft, probes still travelling, and records whose final state is not established. ASTERA is not endorsed by NASA.

## What is included

### Web application
- Cosmic-themed responsive Next.js experience with a searchable, filterable curated mission collection.
- Mission detail pages with lifecycle context, source links and explicit evidence limitations.
- Interactive 3D solar-system orientation model (stylized and not to scale).
- Moon and Mars mission-reference atlas (schematic; no unverified coordinates are plotted).
- Space Academy knowledge checks, local learning progress, relationship graph and mission timeline.
- Mission-design calculator with adjustable thrust, mass and duration (idealized classroom physics only).
- Source-bounded ASTERA Q&A preview with citations to the curated NASA mission pages.
- Scientific signal workbench with generated teaching signals clearly labelled as simulated, not NASA observations.

### Backend
- FastAPI API with PostgreSQL/pgvector persistence, SQLAlchemy models and Alembic migrations.
- Authentication endpoints, mission/artifact archive endpoints, source registry, ingestion-job tracking and human verification workflow.
- NSSDCA/NASA source registry seeded automatically on container startup.
- Conservative NASA mission-page retrieval adapter that only accepts HTTPS pages on registered NASA hosts; extraction is provenance-captured and still requires human review.
- Moon catalogue PDF ingestion parser and verification workflow. The PDF parser is not automatically run at startup; use the documented ingestion command after reviewing the source and database.

### Mobile companion
- Expo Router app with Home, Archive, Academy, Universe and Profile tabs.
- Additional native screens for the schematic planetary atlas, mission calculator and source-bounded ASTERA Q&A.
- The mobile universe screen is a lightweight orientation view; the web app contains the interactive WebGL solar-system experience.

## Quick start — Docker Compose (recommended)

Requirements: Docker Desktop with the Linux container engine enabled.

From the extracted project root, open PowerShell and run:

```powershell
docker compose -f infrastructure/docker-compose.yml up --build
```

The first build downloads base images and installs dependencies inside the containers, so it can take several minutes. When the services are healthy, open:

- Web: http://localhost:3000
- API: http://localhost:8000
- API documentation: http://localhost:8000/docs
- Readiness: http://localhost:8000/api/v1/health
- Liveness: http://localhost:8000/api/v1/live

Stop the stack without deleting database data:

```powershell
docker compose -f infrastructure/docker-compose.yml down
```

To deliberately erase local database/cache volumes as well (this permanently deletes local data):

```powershell
docker compose -f infrastructure/docker-compose.yml down -v
```

The Compose stack includes PostgreSQL 16 with pgvector, Redis 7, the FastAPI API and the Next.js development server. PostgreSQL and Redis data persist in named Docker volumes.

## Local development without the full Compose stack

1. Copy `.env.example` to `.env` and replace the development JWT secret before sharing or deploying.
2. Start PostgreSQL/Redis with the Compose file, or provide compatible services separately.
3. From the repository root run `npm install`.
4. In `services/api`, create and activate a Python 3.11 virtual environment, then run `pip install -r requirements.txt`.
5. Set `DATABASE_URL` to your database and run from `services/api`:

   ```bash
   alembic upgrade head
   python scripts/seed_registry.py
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

6. In another terminal from the repository root:

   ```bash
   npm run web
   ```

7. For the Expo app, run `npm run mobile`. On a physical phone, set `EXPO_PUBLIC_API_URL` to the computer's LAN IP, not `localhost`.

## Useful commands

```bash
npm run build:web       # production build of the web app
npm run typecheck:web   # TypeScript check for the web app
npm run test:api        # backend test suite
npm run seed:api        # seed NASA source registry (database must be migrated)
npm run stack:up        # Docker Compose stack
npm run stack:down      # stop stack, keep persistent volumes
```

## Data integrity and current boundaries

- The mission cards are curated educational summaries linked to the official NASA resources supplied for ASTERA. A link in the registry does not mean the underlying dataset was downloaded or processed.
- NSSDCA source metadata is seeded into the registry. The mission-page adapter is a controlled retrieval tool, not a full structured NSSDCA ingestion pipeline.
- The Moon catalogue is supplementary to the challenge resource list. Its parser preserves printed text and flags questionable coordinates for human review. Do not publish inferred or corrected coordinates without a documented review.
- Mission lifecycle categories are intentionally distinct: operational, still travelling, mission-completed hardware left on a surface, decommissioned/dormant, lost contact/failed, crashed/impacted and unknown/unverified.
- The planetary atlas is schematic, not a GIS layer. The 3D universe is stylized and not to scale. The mission calculator is a constant-force educational model, not a validated flight simulator.
- Scientific workbench traces are locally generated teaching signals, not real ALSEP observations.
- ASTERA AI is a small source-bounded preview, not a live LLM, embedding pipeline or complete RAG service. It abstains when its curated response set does not support an answer.
- Guest learning progress is stored locally in the browser. Secure authentication endpoints exist in the API; full account-linked progress synchronization is not yet connected to every client screen.
- The Compose configuration uses local-development credentials by default. Change all secrets, configure TLS, review CORS, add backups/monitoring and complete security testing before any public deployment.

## Verification notes

The delivery archive includes the source code, tests, migrations, container definitions and setup documentation. Python syntax compilation and project-structure checks were run during packaging. Full npm installation/Next.js build, database-backed pytest execution, Docker image build and Expo device build could not be completed in this packaging environment because dependency downloads and Docker execution were unavailable. Run the commands above on your machine to complete environment-specific verification.
