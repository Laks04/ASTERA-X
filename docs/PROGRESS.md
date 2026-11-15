# ASTERA progress

Last updated 2026-11-15. Status distinguishes implemented preview features from production integrations. A feature is not considered production-complete merely because a screen exists.

## Phase 1 — Foundation
- [x] Monorepo, FastAPI, auth foundation, shared TypeScript package, Docker Compose, `.env.example`.
- [x] PostgreSQL/pgvector schema and Alembic baseline (reported validated by prior project test report).
- [x] Next.js application shell and Expo Router shell.
- [ ] Password reset, email verification, logout/revocation and guest account lifecycle.

## Phase 2 — Backend & NASA data foundation
- [x] Explicit Alembic revision, source registry, Moon catalogue parser/ingestion service, ingestion jobs and provenance models.
- [x] Mission, artifact, location, image, source and verification models/APIs.
- [x] Role-restricted ingestion and reviewer verification workflow.
- [ ] Full NASA PDF ingestion and manual review of flagged source rows remain owner-side tasks.
- [ ] Docker/managed PostgreSQL and Redis-backed production validation.

## Phase 3 — Challenge source registry & archive experience (web preview implemented; backend integration partial)
- [x] Added NSSDCA and the NASA mission resource URLs supplied by the project owner to the source registry seed.
- [x] Registry seed records the supplied official Resources listing as `listed_verified` with check date 2026-11-15 for 14 exact supplied source entries; the Moon catalogue is `not_listed_verified`; other supplemental sources remain unknown.
- [x] Built a searchable/filterable mission collection experience, mission detail pages, source links and lifecycle summaries.
- [ ] Fetch and normalize actual NSSDCA page content into Mission/Artifact database rows.
- [ ] Human-review and promote records from the real source evidence.
- [ ] Ingest item-level equipment records and images.

## Phase 4 — Planetary maps (conceptual UI preview implemented)
- [x] Moon/Mars surface explorer interface with destination switcher and clear conceptual/non-coordinate disclaimer.
- [ ] Integrate LROC/HiRISE imagery and map tiles.
- [ ] Add verified artifact coordinates, rover traverses, map layer controls and coordinate uncertainty.

## Phase 5 — 3D Universe (interactive preview implemented)
- [x] Interactive Three.js / React Three Fiber solar-system model with selectable planets, orbit controls, stars and Saturn rings.
- [ ] Calibrated planetary data, scientifically meaningful trajectories, celestial object detail panels and performance profiling.
- [ ] Connect mission and artifact data to 3D objects.

## Phase 6 — Space Academy (functional learning preview implemented)
- [x] Learning paths and interactive source-grounded knowledge check.
- [ ] Full lesson content, rich diagrams, lesson authoring, assessment persistence and certificates.

## Phase 7 — ASTERA AI (limited source-linked preview implemented)
- [x] Chat interface with bounded responses and direct NASA source links for a few supplied topics.
- [ ] Backend RAG pipeline, embeddings ingestion, provider configuration, citations, prompt-injection defenses and evaluation.

## Phase 8 — Simulator & gamification (conceptual simulator implemented)
- [x] Interactive mission-stage activity and control slider, clearly labelled as illustrative.
- [ ] Physics-validated orbital/landing/rover simulations, user XP, achievements, badges and leaderboards.

## Phase 9 — Mobile application (navigation preview implemented)
- [x] Expo Router tab navigation and initial archive/academy/universe/profile screens.
- [ ] Connect mobile screens to APIs, implement authentication, synchronized progress, native maps and performant 3D.

## Phase 10 — Final debugging, integration, QA and deployment
- [ ] Full backend/frontend/mobile build and end-to-end validation.
- [ ] Security, accessibility, responsive, performance and scientific accuracy audits.
- [ ] Production hosting, monitoring, backups, mobile release and final acceptance.

## Important data integrity notes
- The mission collection cards are curated source-linked summaries based on the challenge resources supplied by the project owner. They are not a substitute for extracted, reviewed NSSDCA records.
- The planetary map is an illustrative surface explorer, not a coordinate-accurate map.
- The solar system is stylized and not to scale; it does not show real-time ephemerides.
- The simulator is an educational interaction, not a validated flight dynamics model.
- The AI screen is a small deterministic source-linked demo, not a deployed LLM/RAG system.
- The frontend uses the live archive API when records are available and otherwise displays the curated collection preview.

## Run locally
See `README.md` for setup instructions. Backend tests require the project dependencies including `pgvector`; frontend build requires installing the npm workspace dependencies.
