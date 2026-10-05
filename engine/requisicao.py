"""
Requisição: tudo o que o Mestre escolhe antes de um pedido de nível médio à IA
(Melhorar arquivo, Aventura, Testes de Conhecimento, Ficha de Combate, Conselho).

A aba Requisições monta um objeto destes com os padrões do projeto e deixa trocar o que
for preciso só para aquele pedido. O WorldBuilder monta um por ação, automaticamente.
As ferramentas leem daqui: eixos de estilo, diretrizes extras, arquivos de referência,
modo, profundidade, público, dados de mesa, segredo e criatividade.
"""
import json
import re
from dataclasses import dataclass, field, asdict, fields
from pathlib import Path

import engine.project_utils as pu
import engine.style_manager as estilo
from core.i18n import t, tc

TIPOS = ("melhorar", "aventura", "conhecimento", "ficha", "conselho")
MODOS = ("reescrever", "acrescentar")
PROFUNDIDADES = ("curto", "medio", "detalhado")
PUBLICOS = ("mestre", "jogadores")
CRIATIVIDADES = ("conservador", "equilibrado", "ousado")
TEMPERATURAS = {"conservador": 0.3, "ousado": 0.9}
LIMITE_REFERENCIA = 12000          # caracteres por arquivo de referência
CAMPOS_PRESET = ("genero", "tom", "clima", "escrita", "diretrizes_extras", "modo", "profundidade", "publico",
                 "nivel_grupo", "jogadores", "segredo", "criatividade")


@dataclass
class Requisicao:
    tipo: str
    caminho: str
    objetivo: str = ""
    genero: str = ""
    tom: str = ""
    clima: str = ""
    escrita: str = ""
    diretrizes_extras: str = ""
    referencias: list = field(default_factory=list)
    modo: str = "reescrever"
    profundidade: str = "medio"
    publico: str = "mestre"
    nivel_grupo: int = 0
    jogadores: int = 0
    segredo: bool = False
    criatividade: str = "equilibrado"
    criatura: str = "npc"          # só para Ficha de Combate: "npc" ou "monstro"

    # --- leitura pelas ferramentas ---
    def escolhas_estilo(self) -> dict:
        return {eixo: getattr(self, eixo) for eixo in estilo.EIXOS if getattr(self, eixo)}

    def temperatura(self, base: float) -> float:
        return TEMPERATURAS.get(self.criatividade, base)

    def bloco_prompt(self) -> str:
        """Instruções desta requisição para o pedido à IA ('' se tudo estiver no padrão)."""
        linhas = []
        if self.diretrizes_extras.strip():
            linhas.append(tc("req.prompt.extras", texto=self.diretrizes_extras.strip()))
        if self.profundidade != "medio":
            linhas.append(tc(f"req.prompt.profundidade.{self.profundidade}"))
        if self.publico == "jogadores":
            linhas.append(tc("req.prompt.publico_jogadores"))
        if self.modo == "acrescentar" and self.tipo == "melhorar":
            linhas.append(tc("req.prompt.acrescentar"))
        if self.nivel_grupo:
            linhas.append(tc("req.prompt.nivel", nivel=self.nivel_grupo))
        if self.jogadores:
            linhas.append(tc("req.prompt.jogadores", total=self.jogadores))
        if self.segredo:
            linhas.append(tc("req.prompt.segredo"))
        referencias = self.texto_referencias()
        if not linhas and not referencias:
            return ""
        partes = ["", tc("req.prompt.cabecalho")] + [f"- {linha}" for linha in linhas]
        if referencias:
            partes += ["", tc("req.prompt.referencias"), referencias]
        return "\n".join(partes) + "\n"

    def texto_referencias(self) -> str:
        blocos = []
        for caminho in self.referencias:
            arquivo = Path(caminho)
            if not arquivo.is_absolute():
                arquivo = Path(pu.CAMINHO_PROJETO) / arquivo
            if arquivo.is_file() and arquivo.resolve() != Path(self.caminho).resolve():
                texto = arquivo.read_text(encoding="utf-8", errors="ignore")[:LIMITE_REFERENCIA]
                blocos.append(f"--- {arquivo.name} ---\n{texto.strip()}")
        return "\n\n".join(blocos)

    def para_dict(self) -> dict:
        return asdict(self)


def nova(tipo: str, caminho: str, objetivo: str = "", **campos) -> Requisicao:
    """Requisição com os padrões do projeto nos eixos de estilo."""
    req = Requisicao(tipo=tipo if tipo in TIPOS else "melhorar", caminho=str(caminho), objetivo=objetivo or "",
                     **estilo.padroes())
    validos = {f.name for f in fields(Requisicao)}
    for chave, valor in campos.items():
        if chave in validos and valor is not None:
            setattr(req, chave, valor)
    return req


def de_dict(dados: dict) -> Requisicao:
    validos = {f.name for f in fields(Requisicao)}
    return nova(dados.get("tipo", "melhorar"), dados.get("caminho", ""),
                **{k: v for k, v in dados.items() if k in validos and k not in ("tipo", "caminho")})


# ----------------------------------------------------------------------
# REFERÊNCIAS SUGERIDAS
# ----------------------------------------------------------------------
def sugerir_referencias(caminho, limite: int = 20) -> list:
    """[(caminho_absoluto, motivo)]: arquivos citados por este ([[links]]) e os que citam este."""
    import engine.arquivos as arq
    alvo = Path(caminho).resolve()
    sugestoes, vistos = [], {str(alvo)}
    try:
        texto = alvo.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        texto = ""
    for nome in re.findall(r"(?<!!)\[\[([^\]]+)\]\]", texto):
        destino = arq.resolver_wikilink(nome)
        if destino and str(Path(destino).resolve()) not in vistos:
            vistos.add(str(Path(destino).resolve()))
            sugestoes.append((str(Path(destino).resolve()), t("req.ref_citado")))
    padrao = re.compile(r"\[\[\s*" + re.escape(re.sub(r"_v\d+$", "", alvo.stem)) + r"\s*(?:[#|][^\]]*)?\]\]", re.IGNORECASE)
    for arquivo in Path(pu.CAMINHO_PROJETO).rglob("*.md"):
        if len(sugestoes) >= limite:
            break
        if pu.arquivo_em_pasta_ignorada(arquivo) or str(arquivo.resolve()) in vistos:
            continue
        conteudo = pu.ler_markdown(arquivo) or ""
        if padrao.search(conteudo):
            vistos.add(str(arquivo.resolve()))
            sugestoes.append((str(arquivo.resolve()), t("req.ref_cita_este")))
    return sugestoes[:limite]


def estimar_tokens(req: Requisicao) -> int:
    """Estimativa do tamanho do pedido (arquivo + referências + estilo), sem contar o contexto do mundo."""
    import engine.expander as ex
    import engine.markdown_spans as ms
    try:
        texto = Path(req.caminho).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        texto = ""
    total = texto + req.objetivo + req.bloco_prompt() + ex.carregar_diretrizes_estilo(req.escolhas_estilo())
    return ms.estatisticas(total)["tokens"]


# ----------------------------------------------------------------------
# PRESETS
# ----------------------------------------------------------------------
def _arquivo_presets() -> Path:
    return pu.PASTA_LOGS / "presets_requisicao.json"


def listar_presets() -> list:
    try:
        return sorted(json.loads(_arquivo_presets().read_text(encoding="utf-8")).keys(), key=str.lower)
    except Exception:
        return []


def salvar_preset(nome: str, req: Requisicao):
    nome = (nome or "").strip()
    if not nome:
        return
    try:
        dados = json.loads(_arquivo_presets().read_text(encoding="utf-8"))
    except Exception:
        dados = {}
    dados[nome] = {campo: getattr(req, campo) for campo in CAMPOS_PRESET}
    _arquivo_presets().parent.mkdir(parents=True, exist_ok=True)
    _arquivo_presets().write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")


def aplicar_preset(nome: str, req: Requisicao) -> Requisicao:
    try:
        dados = json.loads(_arquivo_presets().read_text(encoding="utf-8")).get(nome, {})
    except Exception:
        dados = {}
    for campo in CAMPOS_PRESET:
        if campo in dados:
            setattr(req, campo, dados[campo])
    return req


def excluir_preset(nome: str):
    try:
        dados = json.loads(_arquivo_presets().read_text(encoding="utf-8"))
    except Exception:
        return
    if dados.pop(nome, None) is not None:
        _arquivo_presets().write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
