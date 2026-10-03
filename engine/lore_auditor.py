"""
Auditoria de Lore: procura incoerências, furos de cronologia e conceitos órfãos
no projeto inteiro. Antes vivia dentro do gui.py (prompt incluso).
"""
import core.ai_utils as au
import core.cache_gemini as cg
import core.eventos as ev
import engine.project_utils as pu
from core.i18n import t, tc
from core.prompts import carregar_prompt


def executar_auditoria():
    """Reconstrói o contexto do mundo e pede o relatório. Devolve o Markdown (ou None se cancelado)."""
    ev.log(t("auditoria.log_reconstruindo"))
    cg.force_rebuild_world_context()
    if pu.is_cancelled():
        return None
    ev.log(t("auditoria.log_enviando"))
    return au.ask_ai(
        contents=carregar_prompt("auditoria_usuario", projeto=pu.PASTA_PROJETO),
        system_instruction=carregar_prompt("auditoria_sistema"),
        temperature=0.2,
        use_world_context=True,
    )


def caminho_padrao_relatorio():
    return pu.PASTA_EXPORTS / tc("auditoria.nome_relatorio", projeto=pu.PASTA_PROJETO)


def salvar_relatorio(caminho, texto: str):
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(texto)
