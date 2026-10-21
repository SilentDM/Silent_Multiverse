"""
Conteúdo do projeto para o módulo do Foundry (sistema dnd5e): fichas de NPC, lojas e imagens.

A IA preenche um formato pensado para o Foundry (números separados, códigos do dnd5e: tamanhos,
perícias, tipos de dano), e o SilentModule (funcionalidade Silent Nexus, no Foundry) o converte em Atores
e Itens. As respostas ficam em cache pela data do arquivo, para não gastar a cota gratuita do Gemini
gerando de novo a mesma ficha.
"""
import hashlib
import html
import json
import re
from pathlib import Path
from typing import List, Literal

from pydantic import BaseModel, Field

import core.ai_utils as au
import core.propriedades as propriedades
import engine.expander as ex
import engine.homebrew as homebrew
import engine.project_utils as pu
from core.i18n import t
from core.prompts import carregar_prompt

EXTENSOES_IMAGEM = (".webp", ".png", ".jpg", ".jpeg")
PASTAS_DE_NPC = {"npc", "npcs", "personagens", "personagem", "characters", "character", "monstros", "monstro",
                 "monsters", "monster", "criaturas", "creatures", "bestiario", "bestiary"}
TIPOS_DE_NPC = {"npc", "monstro", "monster", "criatura", "creature", "personagem", "character"}
TIPOS_DE_LOJA = {"loja", "shop", "store", "mercador", "merchant", "mercado", "market"}


class ErroFoundry(Exception):
    pass


# ----------------------------------------------------------------------
# FORMATOS (resposta estruturada da IA)
# ----------------------------------------------------------------------
Tamanho = Literal["tiny", "sm", "med", "lg", "huge", "grg"]
TipoCriatura = Literal["aberration", "beast", "celestial", "construct", "dragon", "elemental", "fey", "fiend",
                       "giant", "humanoid", "monstrosity", "ooze", "plant", "undead"]
TipoDano = Literal["acid", "bludgeoning", "cold", "fire", "force", "lightning", "necrotic", "piercing", "poison",
                   "psychic", "radiant", "slashing", "thunder"]
Pericia = Literal["acr", "ani", "arc", "ath", "dec", "his", "ins", "itm", "inv", "med", "nat", "prc", "prf", "per",
                  "rel", "slt", "ste", "sur"]
Atributo = Literal["str", "dex", "con", "int", "wis", "cha"]
Condicao = Literal["blinded", "charmed", "deafened", "exhaustion", "frightened", "grappled", "incapacitated",
                   "invisible", "paralyzed", "petrified", "poisoned", "prone", "restrained", "stunned", "unconscious"]


class AtaqueFoundry(BaseModel):
    nome: str = Field(description="Nome do ataque (ex.: Cimitarra, Mordida, Raio de Fogo)")
    alcance: Literal["melee", "ranged"] = Field(description="melee para corpo a corpo, ranged para à distância")
    classificacao: Literal["weapon", "spell"] = Field(description="weapon para armas e ataques naturais, spell para ataques mágicos")
    alcance_pes: int = Field(description="Alcance em pés (5 para corpo a corpo comum, 10 para alcance longo, ou a distância normal)")
    alcance_longo_pes: int = Field(description="Alcance longo em pés para ataques à distância (0 se não houver)")
    dados_quantidade: int = Field(description="Quantidade de dados de dano (o 1 de 1d6)")
    dados_faces: int = Field(description="Faces do dado de dano: 4, 6, 8, 10 ou 12 (o 6 de 1d6)")
    tipo_dano: TipoDano = Field(description="Tipo do dano")
    descricao: str = Field(description="Efeitos extras do ataque além do dano (vazio se não houver)")
    fonte: str = Field(description="Crédito exato da opção homebrew usada, copiado da lista (vazio se não veio de lá)")


class HabilidadeFoundry(BaseModel):
    nome: str = Field(description="Nome do traço ou da ação especial")
    ativacao: Literal["passive", "action", "bonus", "reaction", "legendary"] = Field(
        description="passive para traços, action, bonus, reaction ou legendary para o que se usa")
    descricao: str = Field(description="Texto completo da regra")
    fonte: str = Field(description="Crédito exato da opção homebrew usada, copiado da lista (vazio se não veio de lá)")


class FichaFoundry(BaseModel):
    nome: str = Field(description="Nome do NPC ou da criatura, como no arquivo")
    tamanho: Tamanho = Field(description="Tamanho no código do dnd5e")
    tipo_criatura: TipoCriatura = Field(description="Tipo de criatura no código do dnd5e")
    subtipo: str = Field(description="Subtipo ou raça (ex.: humano, elfo), vazio se não houver")
    alinhamento: str = Field(description="Alinhamento")
    classe_armadura: int = Field(description="Classe de Armadura")
    pontos_de_vida: int = Field(description="Pontos de vida médios")
    formula_pv: str = Field(description="Dados de vida com bônus (ex.: 6d8 + 12)")
    deslocamento_pes: int = Field(description="Deslocamento a pé em pés (30 para um humano)")
    voo_pes: int = Field(description="Deslocamento de voo em pés (0 se não voa)")
    natacao_pes: int = Field(description="Deslocamento de natação em pés (0 se não tem)")
    escalada_pes: int = Field(description="Deslocamento de escalada em pés (0 se não tem)")
    forca: int = Field(description="Força (1 a 30)")
    destreza: int = Field(description="Destreza (1 a 30)")
    constituicao: int = Field(description="Constituição (1 a 30)")
    inteligencia: int = Field(description="Inteligência (1 a 30)")
    sabedoria: int = Field(description="Sabedoria (1 a 30)")
    carisma: int = Field(description="Carisma (1 a 30)")
    testes_resistencia: List[Atributo] = Field(description="Atributos com proficiência em testes de resistência")
    pericias: List[Pericia] = Field(description="Perícias com proficiência, nos códigos do dnd5e")
    nivel_desafio: float = Field(description="Nível de Desafio como número (0.125, 0.25, 0.5, 1 a 30)")
    visao_escuro_pes: int = Field(description="Visão no escuro em pés (0 se não tem)")
    idiomas: List[str] = Field(description="Idiomas que fala")
    resistencias: List[TipoDano] = Field(description="Resistências a dano")
    imunidades: List[TipoDano] = Field(description="Imunidades a dano")
    imunidades_condicao: List[Condicao] = Field(description="Imunidades a condições")
    ataques: List[AtaqueFoundry] = Field(description="Ataques com rolagem de ataque e dano")
    habilidades: List[HabilidadeFoundry] = Field(description="Traços e ações especiais que não são ataques simples")
    biografia_publica: str = Field(description="O que os jogadores podem saber sobre ele: aparência, papel, reputação. Sem segredos")
    biografia_mestre: str = Field(description="Tudo para o Mestre: personalidade, motivações, segredos e como usar na mesa")


class ItemLoja(BaseModel):
    nome: str = Field(description="Nome do item como aparece na loja, no idioma do projeto")
    nome_srd: str = Field(description="Nome exato do item equivalente no SRD em inglês (ex.: Longsword, Potion of Healing), vazio se for um item próprio do mundo")
    tipo: Literal["weapon", "equipment", "consumable", "tool", "loot", "container"] = Field(description="Tipo de item no dnd5e")
    preco_po: float = Field(description="Preço em peças de ouro")
    quantidade: int = Field(description="Quantidade em estoque")
    descricao: str = Field(description="Descrição curta do item, com o sabor da loja")


class LojaFoundry(BaseModel):
    nome: str = Field(description="Nome da loja")
    dono: str = Field(description="Nome do dono ou atendente")
    descricao: str = Field(description="Descrição da loja para os jogadores")
    itens: List[ItemLoja] = Field(description="Os itens à venda")


# ----------------------------------------------------------------------
# ARQUIVOS DO PROJETO
# ----------------------------------------------------------------------
def _raiz() -> Path:
    return Path(pu.CAMINHO_PROJETO).resolve()


def caminho_do_arquivo(relativo: str) -> Path:
    """Caminho absoluto de um arquivo do projeto, recusando qualquer coisa fora da pasta do projeto."""
    caminho = (_raiz() / (relativo or "")).resolve()
    if _raiz() not in caminho.parents and caminho != _raiz():
        raise ErroFoundry(t("foundry.erro_fora_do_projeto"))
    if not caminho.is_file():
        raise ErroFoundry(t("foundry.erro_arquivo", nome=relativo))
    return caminho


def _tipo(texto: str) -> str:
    valor = propriedades.valor_de(propriedades.ler(texto), "type")
    return str(valor).strip().lower() if valor and not isinstance(valor, list) else ""


def _indice_imagens() -> dict:
    """{nome do arquivo de imagem sem extensão, em minúsculas: caminho} de todas as imagens do projeto."""
    indice = {}
    for imagem in _raiz().rglob("*"):
        if imagem.suffix.lower() in EXTENSOES_IMAGEM and not pu.arquivo_em_pasta_ignorada(imagem):
            indice.setdefault(imagem.stem.lower(), imagem)
            indice.setdefault(imagem.name.lower(), imagem)
    return indice


def imagem_do_arquivo(caminho: Path, indice: dict = None):
    """A imagem com o mesmo nome do arquivo (em qualquer pasta do projeto), ou a primeira ![[imagem]] do texto."""
    indice = _indice_imagens() if indice is None else indice
    if caminho.stem.lower() in indice:
        return indice[caminho.stem.lower()]
    try:
        texto = caminho.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
    for achado in re.finditer(r"!\[\[([^\]|#]+)", texto):
        nome = Path(achado.group(1).strip()).name.lower()
        if nome in indice:
            return indice[nome]
    return None


def listar_arquivos() -> list:
    """Os arquivos .md do projeto (sem segredos de fora), marcando os que parecem NPCs ou lojas."""
    itens, indice = [], _indice_imagens()
    for caminho in sorted(_raiz().rglob("*.md")):
        if pu.arquivo_em_pasta_ignorada(caminho):
            continue
        relativo = caminho.relative_to(_raiz()).as_posix()
        try:
            inicio = caminho.read_text(encoding="utf-8", errors="ignore")[:3000]
        except OSError:
            continue
        tipo = _tipo(inicio)
        pastas = {p.lower() for p in caminho.relative_to(_raiz()).parts[:-1]}
        imagem = imagem_do_arquivo(caminho, indice)
        itens.append({
            "arquivo": relativo,
            "nome": caminho.stem,
            "pasta": caminho.parent.relative_to(_raiz()).as_posix() if caminho.parent != _raiz() else "",
            "npc": tipo in TIPOS_DE_NPC or bool(pastas & PASTAS_DE_NPC),
            "loja": tipo in TIPOS_DE_LOJA,
            "segredo": propriedades.eh_segredo(inicio),
            "imagem": imagem.relative_to(_raiz()).as_posix() if imagem else None,
        })
    return itens


# ----------------------------------------------------------------------
# GERAÇÃO (com cache pela data do arquivo)
# ----------------------------------------------------------------------
def _pasta_cache() -> Path:
    pasta = pu.PASTA_LOGS / "foundry" / re.sub(r'[\\/:*?"<>|]', "_", str(pu.PASTA_PROJETO))
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta


def _arquivo_cache(tipo: str, caminho: Path, extra: str = "") -> Path:
    chave = hashlib.sha1(f"{tipo}|{caminho}|{caminho.stat().st_mtime_ns}{extra}".encode("utf-8")).hexdigest()[:20]
    return _pasta_cache() / f"{tipo}_{chave}.json"


def _opcoes_homebrew(texto: str) -> str:
    """O bloco de opções homebrew para o prompt da ficha (vazio sem fontes escolhidas ou sem nada relacionado)."""
    opcoes = homebrew.candidatos(texto)
    return carregar_prompt("foundry_homebrew", opcoes=homebrew.texto_para_prompt(opcoes)) if opcoes else ""


def _gerar(tipo: str, relativo: str, esquema, prompt: str, forcar: bool) -> dict:
    caminho = caminho_do_arquivo(relativo)
    # As fontes de homebrew escolhidas entram na chave do cache da ficha: trocá-las gera a ficha de novo
    cache = _arquivo_cache(tipo, caminho, homebrew.assinatura() if tipo == "ficha" else "")
    if cache.exists() and not forcar:
        return json.loads(cache.read_text(encoding="utf-8"))
    texto = caminho.read_text(encoding="utf-8", errors="ignore")
    variaveis = {"arquivo": caminho.stem, "conteudo": texto}
    if tipo == "ficha":
        variaveis["homebrew"] = _opcoes_homebrew(texto)
    resposta = au.ask_ai(
        contents=carregar_prompt(f"foundry_{prompt}_usuario", **variaveis),
        system_instruction=carregar_prompt(f"foundry_{prompt}_sistema"),
        temperature=0.3, response_schema=esquema, use_world_context=True)
    dados = esquema.model_validate_json(ex.remover_markdown_fences(str(resposta))).model_dump()
    dados["fonte"] = relativo
    cache.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
    return dados


def _html(texto: str) -> str:
    """Texto simples da IA em parágrafos HTML (as fichas do Foundry guardam HTML)."""
    blocos = [b.strip() for b in re.split(r"\n\s*\n", texto or "") if b.strip()]
    return "".join(f"<p>{html.escape(b).replace(chr(10), '<br>')}</p>" for b in blocos)


def gerar_ficha(relativo: str, forcar: bool = False) -> dict:
    dados = _gerar("ficha", relativo, FichaFoundry, "ficha", forcar)
    dados["biografia_publica_html"] = _html(dados.get("biografia_publica", ""))
    dados["biografia_mestre_html"] = _html(dados.get("biografia_mestre", ""))
    for item in dados.get("habilidades", []) + dados.get("ataques", []):
        item["descricao_html"] = _html(item.get("descricao", ""))
        if item.get("fonte"):
            # Crédito do autor do homebrew no fim da descrição
            item["descricao_html"] += f"<p><em>{html.escape(t('foundry.fonte_homebrew', fonte=item['fonte']))}</em></p>"
    return dados


def gerar_loja(relativo: str, forcar: bool = False) -> dict:
    dados = _gerar("loja", relativo, LojaFoundry, "loja", forcar)
    dados["descricao_html"] = _html(dados.get("descricao", ""))
    for item in dados.get("itens", []):
        item["descricao_html"] = _html(item.get("descricao", ""))
    return dados


# ----------------------------------------------------------------------
# O SILENTMODULE NO FOUNDRY
# ----------------------------------------------------------------------
# Quem usa a ponte é o SilentModule (funcionalidade Silent Nexus), instalado à parte no Foundry.
ID_MODULO = "silent-module"


def pasta_dados_foundry():
    """A pasta Data do Foundry (lida de %LOCALAPPDATA%/FoundryVTT/Config/options.json), ou None."""
    import os
    local = Path(os.environ.get("LOCALAPPDATA", "")) / "FoundryVTT"
    try:
        opcoes = json.loads((local / "Config" / "options.json").read_text(encoding="utf-8"))
        base = Path(opcoes.get("dataPath") or local)
    except (OSError, ValueError):
        base = local
    dados = base / "Data"
    return dados if dados.is_dir() else None


def versao_modulo(pasta: Path):
    try:
        return json.loads((Path(pasta) / "module.json").read_text(encoding="utf-8")).get("version")
    except (OSError, ValueError):
        return None
