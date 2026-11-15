"""Offline structural checks for an ASTERA checkout; does not replace full builds/tests."""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "apps/web/app/page.tsx", "apps/web/app/missions/[slug]/page.tsx",
    "apps/web/components/ArchiveExplorer.tsx", "apps/web/components/UniverseCanvas.tsx",
    "apps/mobile/app/ai.tsx", "apps/mobile/app/maps.tsx", "apps/mobile/app/simulator.tsx",
    "services/api/app/main.py", "services/api/app/api/v1/archive.py",
    "services/api/app/api/v1/auth.py", "services/api/app/api/v1/data.py",
    "services/api/app/api/v1/verification.py", "services/api/app/api/v1/health.py",
    "services/api/scripts/seed_registry.py", "services/api/requirements-runtime.txt",
    "apps/mobile/tsconfig.json", "apps/web/app/error.tsx", "apps/web/app/not-found.tsx",
    "services/api/alembic/versions/0001_initial_schema.py",
    "Dockerfile.api", "Dockerfile.web", "infrastructure/docker-compose.yml",
]
missing = [name for name in REQUIRED if not (ROOT / name).is_file()]
if missing:
    print("Missing required files:", *missing, sep="\n- ")
    sys.exit(1)

for manifest in ROOT.rglob("package.json"):
    json.loads(manifest.read_text(encoding="utf-8"))
for manifest in [ROOT / "apps/mobile/app.json", ROOT / "apps/web/tsconfig.json", ROOT / ".devcontainer/devcontainer.json"]:
    json.loads(manifest.read_text(encoding="utf-8"))

# Verify relative TS/TSX imports resolve within the project.
missing_imports: list[str] = []
for source in list((ROOT / "apps/web").rglob("*.ts")) + list((ROOT / "apps/web").rglob("*.tsx")) + list((ROOT / "apps/mobile").rglob("*.ts")) + list((ROOT / "apps/mobile").rglob("*.tsx")):
    content = source.read_text(encoding="utf-8")
    for spec in re.findall(r"(?:from\s*|import\s*\()\s*['\"](\.{1,2}/[^'\"]+)['\"]", content):
        target = (source.parent / spec)
        candidates = [target, target.with_suffix(".ts"), target.with_suffix(".tsx"), target / "index.ts", target / "index.tsx"]
        if not any(candidate.exists() for candidate in candidates):
            missing_imports.append(f"{source.relative_to(ROOT)} -> {spec}")
if missing_imports:
    print("Unresolved relative imports:", *missing_imports, sep="\n- ")
    sys.exit(1)
print("ASTERA offline structural checks passed.")
print("Note: run npm install/build, pytest with PostgreSQL, Docker Compose and Expo checks on a machine with dependencies installed.")
