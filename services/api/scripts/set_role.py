"""Promote a user: python scripts/set_role.py user@example.com reviewer|admin|user  (run on the server; there is no public endpoint for this)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import select  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.models import User  # noqa: E402

if __name__ == "__main__":
    email, role = sys.argv[1].lower(), sys.argv[2]
    if role not in ("user", "reviewer", "admin"):
        raise SystemExit("role must be user, reviewer or admin")
    db = SessionLocal(); u = db.scalar(select(User).where(User.email == email))
    if not u: raise SystemExit("no such user")
    u.role = role; db.commit(); print(f"{email} is now {role}")
