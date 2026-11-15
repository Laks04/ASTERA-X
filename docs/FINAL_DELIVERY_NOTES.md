# ASTERA integrated development delivery

This archive consolidates the current ASTERA web experience, FastAPI backend foundation, Expo mobile companion and a one-command Docker Compose development stack.

## Start

From the extracted project root, run:

```powershell
docker compose -f infrastructure/docker-compose.yml up --build
```

Then open `http://localhost:3000` for the web application and `http://localhost:8000/docs` for API documentation. See `README.md` for requirements, stop commands, local development and troubleshooting.

## Implemented application flows

- Searchable curated mission archive and individual mission detail pages.
- Stylized interactive 3D solar-system explorer.
- Schematic Moon/Mars mission-reference atlas.
- Space Academy quiz and local learning progress.
- Mission relationship visualization and mission timeline.
- Educational constant-force mission calculator.
- Simulated scientific signal workbench with explicit simulated-data labels.
- Source-bounded Q&A preview with NASA citations.
- FastAPI authentication, mission/artifact archive, source registry, ingestion job and human verification routes.
- Expo Router companion with archive, academy, universe, profile, maps, simulator and Q&A entry points.

## Important limitations

The archive does not claim production completion of structured NASA data ingestion, verified terrain/GIS, real ALSEP observations, live orbital ephemerides, full spacecraft physics, live LLM/RAG, full mobile WebGL parity or production deployment/security. These are explicitly described in `docs/DELIVERY_STATUS.md` and `docs/BUILD_REPORT.md`.

## Validation

Python syntax, JSON manifests, Compose YAML and offline project structure checks passed. npm installation timed out in the packaging environment, pytest could not collect without `pgvector`, and Docker/Expo builds were not run here. Complete those checks on the target machine after downloading the dependencies.
