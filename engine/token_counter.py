"""
Analisador de tamanho do projeto (tokens).

Mede, arquivo por arquivo, quanto do projeto entra no contexto do mundo
enviado às IAs, usando EXATAMENTE as mesmas regras de project_utils
(pastas ignoradas, TODOs, rascunhos e filtro de segredos para jogadores).

- As contagens por arquivo são ESTIMATIVAS locais (instantâneas, sem custo).
- A contagem EXATA do contexto completo usa o endpoint gratuito de contagem
  de tokens do provedor ativo (Gemini ou Claude) e serve para calibrar as
  estimativas por arquivo.
"""
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import core.ai_utils as au
import core.secret_filter as sf
import engine.project_utils as pu
from core.i18n import t

# Português em Markdown fica em torno de 3,5 caracteres por token nos tokenizadores atuais.
CHARS_POR_TOKEN_ESTIMADO = 3.5
LIMITE_CONTEXTO_PADRAO = 1_000_000

MOTIVOS_EXCLUSAO = ("vazio", "todo", "rascunho", "marcador", "segredo", "erro_leitura")


def estimar_tokens(chars: int) -> int:
    return int(round(chars / CHARS_POR_TOKEN_ESTIMADO)) if chars else 0


@dataclass
class ArquivoAnalisado:
    caminho_relativo: Path
    bytes_disco: int
    chars_mestre: int          # caracteres que entram no contexto do Mestre (com cabeçalho)
    chars_jogador: int         # caracteres que entram no contexto dos Jogadores (após filtro de segredos)
    motivo_mestre: Optional[str] = None
    motivo_jogador: Optional[str] = None

    @property
    def estado(self) -> str:
        """Chave do estado: um motivo de exclusão, 'oculto', 'parcial' ou 'incluido'."""
        if self.motivo_mestre:
            return self.motivo_mestre
        if self.motivo_jogador == "segredo":
            return "oculto"
        if self.chars_jogador < self.chars_mestre:
            return "parcial"
        return "incluido"

    @property
    def situacao(self) -> str:
        return t(f"relatorio.situacao.{self.estado}")


@dataclass
class AnaliseProjeto:
    nome_projeto: str
    raiz: Path
    arquivos: list = field(default_factory=list)
    chars_bundle_mestre: int = 0
    chars_bundle_jogador: int = 0
    bundle_mestre: str = ""
    bundle_jogador: str = ""

    @property
    def bytes_total(self) -> int:
        return sum(a.bytes_disco for a in self.arquivos)

    @property
    def arquivos_incluidos(self) -> int:
        return sum(1 for a in self.arquivos if not a.motivo_mestre)

    @property
    def overhead_chars_mestre(self) -> int:
        """Estrutura de pastas + índice + separadores (tudo que não é conteúdo de arquivo)."""
        return max(0, self.chars_bundle_mestre - sum(a.chars_mestre for a in self.arquivos))

    @property
    def overhead_chars_jogador(self) -> int:
        return max(0, self.chars_bundle_jogador - sum(a.chars_jogador for a in self.arquivos))


def analisar_projeto() -> AnaliseProjeto:
    """Lê todos os .md do projeto ativo e mede quanto cada um ocupa no contexto do Mestre e dos Jogadores."""
    raiz = Path(pu.CAMINHO_PROJETO)
    analise = AnaliseProjeto(nome_projeto=pu.PASTA_PROJETO, raiz=raiz)
    if not raiz.exists():
        return analise

    # Lê os termos secretos uma única vez (o filtro do contexto real lê a cada arquivo)
    termos_secretos = sf.obter_termos_secretos_configurados()

    for f_path in sorted(raiz.rglob("*.md")):
        if pu.arquivo_em_pasta_ignorada(f_path):
            continue

        try:
            bytes_disco = f_path.stat().st_size
        except OSError:
            bytes_disco = 0

        rel = f_path.relative_to(raiz)
        content = pu.ler_markdown(f_path)
        if content is None:
            analise.arquivos.append(ArquivoAnalisado(rel, bytes_disco, 0, 0, "erro_leitura", "erro_leitura"))
            continue

        filtrado_mestre, motivo_mestre = pu.avaliar_conteudo_para_contexto(content, is_dm=True)
        filtrado_jogador, motivo_jogador = pu.avaliar_conteudo_para_contexto(
            content, is_dm=False, termos_secretos=termos_secretos, caminho_relativo=rel
        )

        chars_mestre = len(pu.formatar_bloco_contexto(f_path.name, filtrado_mestre)) if filtrado_mestre else 0
        chars_jogador = len(pu.formatar_bloco_contexto(f_path.name, filtrado_jogador)) if filtrado_jogador else 0

        analise.arquivos.append(ArquivoAnalisado(
            rel, bytes_disco, chars_mestre, chars_jogador, motivo_mestre, motivo_jogador
        ))

    # Bundles reais (mesma função usada pelos provedores de IA)
    analise.bundle_mestre = pu.montar_contexto_mundo(is_dm=True)
    analise.bundle_jogador = pu.montar_contexto_mundo(is_dm=False)
    analise.chars_bundle_mestre = len(analise.bundle_mestre)
    analise.chars_bundle_jogador = len(analise.bundle_jogador)
    return analise


# ----------------------------------------------------------------------
# LIMITES E CONTAGEM EXATA POR PROVEDOR
# ----------------------------------------------------------------------
def _primeiro_modelo_gemini() -> Optional[dict]:
    data = pu.ler_json_seguro(pu.log_path("models.json"), pu.LOCK_MODELS, padrao=[])
    return data[0] if data else None


def obter_limite_contexto_local() -> tuple[int, str]:
    """Limite de contexto do provedor ativo sem chamar a API (para exibição imediata)."""
    provedor = au.obter_provedor_ativo()
    if provedor == "claude":
        import core.ai_claude as ac
        return LIMITE_CONTEXTO_PADRAO, f"Claude ({ac.DEFAULT_MODEL})"
    if provedor == "pro":
        import core.ai_pro as ap
        return 128_000, t("relatorio.limite_openai", modelo=ap.DEFAULT_MODEL)
    modelo = _primeiro_modelo_gemini()
    if modelo and modelo.get("maxinputtokens"):
        return int(modelo["maxinputtokens"]), f"Gemini ({modelo.get('display_name') or modelo['name']})"
    return LIMITE_CONTEXTO_PADRAO, t("relatorio.limite_gemini_tipico")


def contar_tokens_exatos(texto: str) -> dict:
    """
    Conta os tokens de um texto usando o endpoint gratuito do provedor ativo.
    Retorna {"tokens": int, "provedor": str, "limite": int|None}.
    Lança RuntimeError se o provedor não oferecer contagem ou a chamada falhar.
    """
    provedor = au.obter_provedor_ativo()

    if provedor == "claude":
        import core.ai_claude as ac
        client = ac.get_claude_client()
        if not client:
            raise RuntimeError("Nenhuma chave da API Claude (CLAUDE_TOKEN) configurada.")
        if not texto.strip():
            return {"tokens": 0, "provedor": f"Claude ({ac.DEFAULT_MODEL})", "limite": None}
        resposta = client.messages.count_tokens(
            model=ac.DEFAULT_MODEL,
            messages=[{"role": "user", "content": texto}],
        )
        limite = None
        try:
            limite = getattr(client.models.retrieve(ac.DEFAULT_MODEL), "max_input_tokens", None)
        except Exception:
            pass
        return {"tokens": resposta.input_tokens, "provedor": f"Claude ({ac.DEFAULT_MODEL})", "limite": limite}

    if provedor == "pro":
        raise RuntimeError("O provedor OpenAI (Pro) não oferece contagem exata de tokens por API. Use a estimativa.")

    import core.ai_gemini as ag
    client = ag.get_gemini_client(timeout_seconds=120)
    if not client:
        raise RuntimeError("Nenhuma chave da API Gemini (GOOGLE_API_KEY) configurada.")
    modelo = _primeiro_modelo_gemini()
    nome_modelo = modelo["name"] if modelo else "gemini-2.5-flash"
    if not texto.strip():
        return {"tokens": 0, "provedor": f"Gemini ({nome_modelo})", "limite": None}
    resposta = client.models.count_tokens(model=nome_modelo, contents=texto)
    limite = int(modelo["maxinputtokens"]) if modelo and modelo.get("maxinputtokens") else None
    return {"tokens": resposta.total_tokens, "provedor": f"Gemini ({nome_modelo})", "limite": limite}


def formatar_bytes(n: int) -> str:
    for unidade in ("B", "KB", "MB", "GB"):
        if n < 1024 or unidade == "GB":
            return f"{n:.0f} {unidade}" if unidade == "B" else f"{n:.1f} {unidade}"
        n /= 1024


def gerar_resumo_texto(analise: AnaliseProjeto, fator_mestre: float = 1.0, fator_jogador: float = 1.0,
                       limite: int = LIMITE_CONTEXTO_PADRAO, exato: bool = False,
                       total_mestre: Optional[int] = None, total_jogador: Optional[int] = None) -> str:
    """Resumo em texto (Markdown) para copiar e compartilhar."""
    tok_m = total_mestre if total_mestre is not None else int(round(estimar_tokens(analise.chars_bundle_mestre) * fator_mestre))
    tok_j = total_jogador if total_jogador is not None else int(round(estimar_tokens(analise.chars_bundle_jogador) * fator_jogador))
    tipo = t("relatorio.contagem_exata") if exato else t("relatorio.contagem_estimada")
    linhas = [
        t("relatorio.resumo_titulo", projeto=analise.nome_projeto),
        "",
        t("relatorio.resumo_arquivos", total=len(analise.arquivos), incluidos=analise.arquivos_incluidos),
        t("relatorio.resumo_disco", tamanho=formatar_bytes(analise.bytes_total)),
        t("relatorio.resumo_tokens_mestre", tipo=tipo, tokens=f"{tok_m:,}", pct=f"{tok_m / limite:.0%}", limite=f"{limite:,}"),
        t("relatorio.resumo_tokens_jogador", tipo=tipo, tokens=f"{tok_j:,}", pct=f"{tok_j / limite:.0%}", limite=f"{limite:,}"),
        "",
        t("relatorio.resumo_maiores"),
    ]
    maiores = sorted(analise.arquivos, key=lambda a: a.chars_mestre, reverse=True)[:15]
    for a in maiores:
        if a.chars_mestre:
            tokens = int(round(estimar_tokens(a.chars_mestre) * fator_mestre))
            linhas.append(f"- {a.caminho_relativo.as_posix()}: {tokens:,} tokens")
    return "\n".join(linhas)


# ----------------------------------------------------------------------
# ÁRVORE DO RELATÓRIO (agrupada por pasta, ordenável)
# ----------------------------------------------------------------------
@dataclass
class NoRelatorio:
    tipo: str            # "pasta" | "arquivo"
    nome: str
    bytes_disco: int
    chars_mestre: int
    chars_jogador: int
    situacao: str
    estado: str          # para arquivos: incluido/parcial/oculto/<motivo>; para pastas: "pasta"
    filhos: list = field(default_factory=list)


COLUNAS_ORDENACAO = ("nome", "tamanho", "tok_m", "tok_j", "pct", "situacao")


def montar_arvore_relatorio(analise: AnaliseProjeto, coluna: str = "tok_m", decrescente: bool = True) -> list:
    """Nós de primeiro nível (pastas com subtotais e arquivos), ordenados pela coluna escolhida."""
    pastas = {}
    for arq in analise.arquivos:
        for pasta in arq.caminho_relativo.parents:
            if str(pasta) == ".":
                continue
            info = pastas.setdefault(pasta, {"bytes": 0, "cm": 0, "cj": 0, "n": 0, "incl": 0})
            info["bytes"] += arq.bytes_disco
            info["cm"] += arq.chars_mestre
            info["cj"] += arq.chars_jogador
            info["n"] += 1
            info["incl"] += 0 if arq.motivo_mestre else 1

    filhos = {}
    for pasta, info in pastas.items():
        no = NoRelatorio("pasta", pasta.name, info["bytes"], info["cm"], info["cj"],
                         t("relatorio.situacao_pasta", total=info["n"], incluidos=info["incl"]), "pasta")
        filhos.setdefault(pasta.parent, []).append((pasta, no))
    for arq in analise.arquivos:
        no = NoRelatorio("arquivo", arq.caminho_relativo.stem, arq.bytes_disco, arq.chars_mestre,
                         arq.chars_jogador, arq.situacao, arq.estado)
        filhos.setdefault(arq.caminho_relativo.parent, []).append((None, no))

    def chave(no: NoRelatorio):
        return {
            "nome": no.nome.lower(),
            "tamanho": no.bytes_disco,
            "tok_m": no.chars_mestre,
            "pct": no.chars_mestre,
            "tok_j": no.chars_jogador,
            "situacao": no.situacao,
        }.get(coluna, no.chars_mestre)

    def montar(pasta_rel) -> list:
        itens = filhos.get(pasta_rel, [])
        itens.sort(key=lambda par: chave(par[1]), reverse=decrescente)
        if coluna == "nome":
            itens.sort(key=lambda par: par[1].tipo != "pasta")  # pastas primeiro (ordenação estável)
        resultado = []
        for pasta, no in itens:
            if pasta is not None:
                no.filhos = montar(pasta)
            resultado.append(no)
        return resultado

    return montar(Path("."))
