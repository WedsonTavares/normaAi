"""Conexão com o PostgreSQL.

Um único pool para a aplicação. As consultas ficam nos services, em SQL explícito.
"""

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from psycopg import Connection
from psycopg import Error as PsycopgError
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool, PoolTimeout

from app.core.config import get_settings
from app.core.errors import ExternalServiceError

logger = logging.getLogger(__name__)

# As consultas usam dict_row, então cada linha chega como dicionário coluna -> valor.
Row = dict[str, Any]

_pool: ConnectionPool[Connection[Row]] | None = None


def get_pool() -> ConnectionPool[Connection[Row]]:
    """Pool único, criado na primeira utilização."""
    global _pool
    if _pool is None:
        database_url = get_settings().database_url
        if not database_url:
            raise ExternalServiceError("Banco de dados não configurado.")
        _pool = ConnectionPool[Connection[Row]](
            database_url,
            min_size=1,
            max_size=5,
            kwargs={"row_factory": dict_row},
            open=True,
        )
    return _pool


@contextmanager
def connection() -> Iterator[Connection[Row]]:
    """Conexão do pool. Faz commit ao sair sem erro e rollback se houver exceção.

    Só falhas do próprio banco viram ExternalServiceError. Erros da aplicação levantados
    dentro do bloco (documento não encontrado, arquivo inválido) sobem intactos — caso
    contrário um 404 chegaria ao usuário como 502.
    """
    try:
        with get_pool().connection() as conn:
            yield conn
    except (PsycopgError, PoolTimeout) as exc:
        logger.exception("Falha ao acessar o banco de dados")
        raise ExternalServiceError("Falha ao acessar o banco de dados.") from exc


def close_pool() -> None:
    """Fecha o pool. Usado no desligamento da aplicação e nos testes."""
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None
