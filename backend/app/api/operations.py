"""Rotas auxiliares de operação.

Registro de falhas vindas da automação (n8n). Ver RN-91: apenas log estruturado, sem tabela.
"""

import logging

from fastapi import APIRouter, status

from app.schemas.operations import N8nErrorReceipt, N8nErrorReport

router = APIRouter(prefix="/operations", tags=["operations"])

logger = logging.getLogger(__name__)


@router.post("/n8n-errors", response_model=N8nErrorReceipt, status_code=status.HTTP_202_ACCEPTED)
def register_n8n_error(report: N8nErrorReport) -> N8nErrorReceipt:
    logger.error(
        "Falha em workflow n8n | workflow=%s (%s) | execução=%s | node=%s | erro=%s",
        report.workflow_name,
        report.workflow_id,
        report.execution_id,
        report.last_node_executed,
        report.error_message,
    )
    return N8nErrorReceipt(status="recorded")
