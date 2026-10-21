"""
Ranking e ordem de uso dos modelos Gemini (página "Performance Gemini").

A interface só exibe os cartões; ordenar, mover e salvar a ordem acontece aqui.
"""
import os

import core.ai_gemini as ag
import core.config as cfg
import engine.project_utils as pu

MODO_AUTOMATICO = "automatico"
MODO_MANUAL = "manual"


def _arquivo():
    return pu.log_path("models.json")


def tem_chave() -> bool:
    return bool(os.getenv("GOOGLE_API_KEY", "").strip())


def listar() -> list:
    """Modelos na ordem de uso atual (o primeiro é o principal)."""
    return pu.ler_json_seguro(_arquivo(), pu.LOCK_MODELS, padrao=[])


def modo_ordenacao() -> str:
    return cfg.obter("modelos_modo_ordenacao", MODO_AUTOMATICO)


def definir_modo(modo: str):
    cfg.atualizar_configuracoes({"modelos_modo_ordenacao": modo})
    if modo == MODO_AUTOMATICO:
        dados = listar()
        if dados:
            dados.sort(key=ag._criterio_ordenacao_eficiencia)
            pu.salvar_json_seguro(_arquivo(), dados, pu.LOCK_MODELS)


def _salvar_ordem(lista: list):
    nomes = [m["name"] for m in lista]
    ag.reordenar_modelos_manualmente(nomes)
    cfg.atualizar_configuracoes({"ordem_manual_modelos": nomes})


def mover(indice: int, delta: int) -> bool:
    lista = listar()
    novo = indice + delta
    if not (0 <= indice < len(lista) and 0 <= novo < len(lista)):
        return False
    lista[indice], lista[novo] = lista[novo], lista[indice]
    _salvar_ordem(lista)
    return True


def tornar_principal(indice: int):
    """Move o modelo para a posição #1. Devolve o nome de exibição (ou None)."""
    lista = listar()
    if not (0 < indice < len(lista)):
        return None
    item = lista.pop(indice)
    lista.insert(0, item)
    _salvar_ordem(lista)
    return item.get("display_name") or item["name"]


def atualizar_lista():
    """Busca o catálogo de modelos da API, sem mandar mensagens (não gasta cota). Mantém o histórico de uso."""
    ag.findmodel(forcar=True)
    return listar()


def testar(nome: str) -> dict:
    """Testa um único modelo com uma mensagem curta (gasta 1 pedido da cota dele)."""
    return ag.testar_modelo(nome)


def metricas(modelo: dict, agora: float = None) -> dict:
    """Valores prontos para exibir num cartão. tempo e taxa ficam None enquanto o modelo não foi usado."""
    tentativas = int(modelo.get("attempts") or 0)
    sucessos = int(modelo.get("success") or 0)
    try:
        tempo = float(modelo["responsetime"]) if modelo.get("responsetime") else None
    except (TypeError, ValueError):
        tempo = None
    descanso = float(modelo.get("resting_until") or 0) if ag.modelo_descansando(modelo, agora) else None
    return {
        "nome": modelo.get("display_name") or modelo.get("name", "?"),
        "id": modelo.get("name", ""),
        "tempo": tempo,
        "sucessos": sucessos,
        "tentativas": tentativas,
        "taxa": sucessos / tentativas * 100 if tentativas else None,
        "tokens": int(modelo.get("maxinputtokens") or 0),
        "score": modelo.get("quality_score") or 0,
        "descanso_ate": descanso,
    }


def hora_do_descanso(momento: float) -> str:
    """'04:00' se for hoje, '21/10 04:00' se for outro dia (no horário deste PC)."""
    import time
    local = time.localtime(momento)
    hoje = time.localtime()
    if (local.tm_year, local.tm_yday) == (hoje.tm_year, hoje.tm_yday):
        return time.strftime("%H:%M", local)
    return time.strftime("%d/%m %H:%M", local)


def atualizar_se_necessario():
    """Na inicialização: refaz o ranking só se a lista estiver vazia ou com mais de 7 dias."""
    ag.findmodel()
