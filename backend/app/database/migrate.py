"""Aplica as migrações SQL pendentes.

Uso: python -m app.database.migrate
"""

import logging
from pathlib import Path

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.database.connection import close_pool, connection

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).parent / "migrations"

CREATE_CONTROL_TABLE = """
create table if not exists schema_migrations (
    version    text primary key,
    applied_at timestamptz not null default now()
)
"""


def pending_migrations(applied: set[str]) -> list[Path]:
    """Migrações ainda não aplicadas, em ordem de nome de arquivo."""
    return [path for path in sorted(MIGRATIONS_DIR.glob("*.sql")) if path.stem not in applied]


def run_migrations() -> list[str]:
    """Aplica o que falta e devolve os nomes aplicados agora."""
    with connection() as conn:
        conn.execute(CREATE_CONTROL_TABLE)
        rows = conn.execute("select version from schema_migrations").fetchall()
        applied = {row["version"] for row in rows}

        applied_now = []
        for migration in pending_migrations(applied):
            logger.info("Aplicando migração %s", migration.stem)
            conn.execute(migration.read_text(encoding="utf-8"))
            conn.execute("insert into schema_migrations (version) values (%s)", (migration.stem,))
            applied_now.append(migration.stem)

    return applied_now


def main() -> None:
    configure_logging(get_settings().log_level)
    try:
        applied = run_migrations()
    finally:
        close_pool()

    if applied:
        logger.info("Migrações aplicadas: %s", ", ".join(applied))
    else:
        logger.info("Nenhuma migração pendente.")


if __name__ == "__main__":
    main()
