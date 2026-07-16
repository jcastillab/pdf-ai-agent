"""Esquema inicial.

Revision ID: 0001_initial
"""

from pathlib import Path

from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    path = Path(__file__).parents[4] / "database" / "migrations" / "0001_initial.sql"
    op.execute(path.read_text(encoding="utf-8"))


def downgrade() -> None:
    raise RuntimeError(
        "El downgrade destructivo no está habilitado. Restaura un backup de Supabase."
    )
