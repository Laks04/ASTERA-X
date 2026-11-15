# ASTERA delivery status

## Included and wired
- Next.js web workspace, route navigation, searchable archive, curated mission detail routes, interactive 3D orientation scene, schematic Moon/Mars atlas, academy quiz, local progress, mission calculator, science teaching-signal workbench and source-bounded Q&A.
- Expo Router mobile companion with five main tabs and additional native maps, simulator and Q&A screens.
- FastAPI routers for authentication, mission/artifact archive, NASA source registry, catalogue ingestion jobs and human verification.
- PostgreSQL/pgvector schema and Alembic initial migration.
- Idempotent source-registry seeding command, API liveness/readiness endpoints and Docker Compose service orchestration.
- Dockerfiles for API and web, development-container configuration and PowerShell start/stop helpers.
- Mission detail pages now resolve the curated mission slugs used by archive cards.

## Known boundaries (not represented as complete)
- NSSDCA is registered as a challenge-listed source and the page retrieval adapter is available, but structured ingestion of every NSSDCA mission record is not complete.
- The NASA Moon catalogue parser is available; the original PDF has not been automatically ingested into a live database by this archive.
- GIS terrain layers, verified coordinates, live orbital ephemerides, verified rover traverses and source-backed image catalogs are not connected.
- The 3D model is a stylized educational model, not to scale or an ephemeris.
- The simulator is a constant-force classroom calculation, not a spacecraft dynamics engine.
- The science chart data is simulated and labelled as such.
- ASTERA AI is a deterministic source-bounded preview; live LLM/RAG integration requires provider credentials, ingestion, embeddings, retrieval evaluation and safety testing.
- Mobile has native companion screens, but it does not have full WebGL feature parity with the web universe explorer.
- Authentication API routes exist; all user-facing screens are not yet connected to account-backed synchronization.

## Verification performed for this package
- Python `compileall` syntax check passed for the API, migration and tests.
- Archive structure and required application folders were checked.
- A full npm dependency install and Next.js build could not be completed in the packaging environment (npm package installation did not finish before timeout).
- Database-backed pytest could not run because the packaging environment did not have the `pgvector` Python package installed and no PostgreSQL service was available.
- Docker Compose image build and Expo device build were not run in this environment.

The project is delivered as an integrated development build, not certified as production-ready. Follow `README.md` for first startup and environment-specific checks.
