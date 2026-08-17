"""Contratos das rotas de operação."""

from typing import Literal

from pydantic import BaseModel


class N8nErrorReport(BaseModel):
    """Falha enviada pelo Error Handler do n8n.

    Todos os campos são opcionais porque o payload do n8n varia conforme onde o erro ocorreu.
    """

    source: str | None = None
    workflow_id: str | None = None
    workflow_name: str | None = None
    execution_id: str | None = None
    execution_url: str | None = None
    last_node_executed: str | None = None
    error_message: str | None = None
    recorded_at: str | None = None


class N8nErrorReceipt(BaseModel):
    status: Literal["recorded"]
