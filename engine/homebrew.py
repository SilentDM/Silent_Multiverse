"""
Homebrew da comunidade do 5etools (repositório TheGiddyLimit/homebrew) para enriquecer as fichas do Foundry.

Nada de homebrew vem com o programa: o Mestre escolhe as fontes em Opções → Foundry e só elas são baixadas,
para este PC (.silent_data/homebrew). Na hora de montar uma ficha, as raças, sub-raças, habilidades de
criaturas e talentos dessas fontes que combinam com o NPC vão para a IA como opções, com o crédito do autor.
"""
import hashlib
import json
import re
import unicodedata
import urllib.parse
import urllib.request
from functools import lru_cache
from pathlib import Path

import core.config as cfg
import engine.project_utils as pu

ENDERECO = "https://raw.githubusercontent.com/TheGiddyLimit/homebrew/master/"
INDICE = "_generated/index-props.json"
TIPOS = ("race", "subrace", "monster", "feat")

# Aventuras e livros completos ficam de fora (ali estão, por exemplo, as aventuras oficiais do Adventurers League),
# assim como fontes que se apresentam como material oficial
PASTAS_FORA = {"adventure", "book"}
TERMOS_OFICIAIS = ("d&d 4ed", "adventurers league", "wizards of the coast", "wotc", "unearthed arcana",
                   "dungeons & dragons", "critical role", "plane shift", "free league")

LIMITE_CANDIDATOS = 12
LIMITE_POR_CRIATURA = 3
LIMITE_TEXTO = 450

# Nomes em português -> como aparecem no homebrew (em inglês)
EQUIVALENTES = {
    "anao": "dwarf", "anaos": "dwarf", "elfo": "elf", "elfa": "elf", "elfos": "elf",
    "humano": "human", "humana": "human", "humanos": "human", "gnomo": "gnome", "gnoma": "gnome",
    "pequenino": "halfling", "pequenina": "halfling", "draconato": "dragonborn", "draconata": "dragonborn",
    "meio-elfo": "half-elf", "meia-elfa": "half-elf", "meio-orc": "half-orc", "meia-orc": "half-orc",
    "orc": "orc", "orque": "orc", "goblin": "goblin", "hobgoblin": "hobgoblin", "kobold": "kobold",
    "golias": "goliath", "tritao": "triton", "gnoll": "gnoll", "minotauro": "minotaur",
    "centauro": "centaur", "satiro": "satyr", "fada": "fey", "fadas": "fey", "feerico": "fey", "feerica": "fey",
    "morto-vivo": "undead", "morta-viva": "undead", "mortos-vivos": "undead", "zumbi": "zombie",
    "esqueleto": "skeleton", "vampiro": "vampire", "vampira": "vampire", "fantasma": "ghost", "espectro": "specter",
    "lich": "lich", "dragao": "dragon", "dragoes": "dragon", "draco": "dragon", "demonio": "fiend",
    "demonios": "fiend", "diabo": "fiend", "infernal": "fiend", "abissal": "fiend", "celestial": "celestial",
    "anjo": "celestial", "constructo": "construct", "golem": "golem", "aberracao": "aberration",
    "besta": "beast", "fera": "beast", "elemental": "elemental", "gigante": "giant", "gigantes": "giant",
    "monstruosidade": "monstrosity", "gosma": "ooze", "limo": "ooze", "planta": "plant", "lobisomem": "werewolf",
    "licantropo": "lycanthrope", "bruxa": "hag", "feiticeiro": "sorcerer", "feiticeira": "sorcerer",
    "mago": "wizard", "maga": "wizard", "clerigo": "cleric", "cleriga": "cleric", "paladino": "paladin",
    "guerreiro": "warrior", "guerreira": "warrior", "ladino": "rogue", "ladina": "rogue", "bardo": "bard",
    "druida": "druid", "patrulheiro": "ranger", "monge": "monk", "bruxo": "warlock",
    "mercador": "merchant", "sacerdote": "priest", "sacerdotisa": "priest", "cultista": "cultist",
    "assassino": "assassin", "assassina": "assassin", "pirata": "pirate", "marinheiro": "sailor",
    "cavaleiro": "knight", "nobre": "noble", "guarda": "guard", "bandido": "bandit", "cacador": "hunter",
}
PALAVRAS_VAZIAS = {"the", "and", "with", "from", "for", "your", "you", "its", "that", "this", "of", "a", "an",
                   "race", "races", "variant", "folk", "kin", "feat", "trait", "action"}


# ----------------------------------------------------------------------
# PASTAS, CATÁLOGO E FONTES ESCOLHIDAS
# ----------------------------------------------------------------------
def _pasta() -> Path:
    pasta = pu.PASTA_DADOS_NEXUS / "homebrew"
    (pasta / "fontes").mkdir(parents=True, exist_ok=True)
    return pasta


def _baixar(caminho: str) -> bytes:
    endereco = ENDERECO + urllib.parse.quote(caminho)
    pedido = urllib.request.Request(endereco, headers={"User-Agent": "SilentMultiverse"})
    with urllib.request.urlopen(pedido, timeout=60) as resposta:
        return resposta.read()


def _autor_e_titulo(caminho: str):
    nome = Path(caminho).stem
    autor, _, titulo = nome.partition(";")
    return (autor.strip(), titulo.strip()) if titulo else ("", nome.strip())


def parece_oficial(caminho: str) -> bool:
    texto = caminho.lower()
    return any(termo in texto for termo in TERMOS_OFICIAIS)


def atualizar_catalogo(baixar=_baixar) -> list:
    """Baixa o índice do repositório e monta o catálogo das fontes com raças, criaturas ou talentos."""
    indice = json.loads(baixar(INDICE).decode("utf-8"))
    fontes = {}
    for tipo in TIPOS:
        for caminho, pasta in (indice.get(tipo) or {}).items():
            if pasta in PASTAS_FORA or parece_oficial(caminho):
                continue
            autor, titulo = _autor_e_titulo(caminho)
            fonte = fontes.setdefault(caminho, {"arquivo": caminho, "autor": autor, "titulo": titulo, "tipos": []})
            if tipo not in fonte["tipos"]:
                fonte["tipos"].append(tipo)
    catalogo_novo = sorted(fontes.values(), key=lambda f: (f["autor"].lower(), f["titulo"].lower()))
    (_pasta() / "catalogo.json").write_text(json.dumps(catalogo_novo, ensure_ascii=False), encoding="utf-8")
    return catalogo_novo


def catalogo() -> list:
    try:
        return json.loads((_pasta() / "catalogo.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []


def fontes_escolhidas() -> list:
    return list(cfg.obter("homebrew_fontes", []) or [])


def _arquivo_local(caminho: str) -> Path:
    return _pasta() / "fontes" / (hashlib.sha1(caminho.encode("utf-8")).hexdigest()[:20] + ".json")


def ativar_fonte(caminho: str, baixar=_baixar) -> str:
    """Baixa a fonte para este PC e a marca como escolhida."""
    dados = baixar(caminho)
    json.loads(dados.decode("utf-8"))                        # recusa o que não for JSON válido
    _arquivo_local(caminho).write_bytes(dados)
    _carregar.cache_clear()
    escolhidas = fontes_escolhidas()
    if caminho not in escolhidas:
        cfg.atualizar_configuracoes({"homebrew_fontes": escolhidas + [caminho]})
    return caminho


def desativar_fonte(caminho: str):
    cfg.atualizar_configuracoes({"homebrew_fontes": [f for f in fontes_escolhidas() if f != caminho]})
    _arquivo_local(caminho).unlink(missing_ok=True)
    _carregar.cache_clear()


def assinatura() -> str:
    """Muda quando as fontes escolhidas mudam (faz as fichas serem geradas de novo com as opções novas)."""
    escolhidas = sorted(fontes_escolhidas())
    return hashlib.sha1("|".join(escolhidas).encode("utf-8")).hexdigest()[:10] if escolhidas else ""


# ----------------------------------------------------------------------
# FORMATO DO 5ETOOLS -> TEXTO
# ----------------------------------------------------------------------
ATAQUES = {"mw": "Melee Weapon Attack:", "rw": "Ranged Weapon Attack:", "mw,rw": "Melee or Ranged Weapon Attack:",
           "ms": "Melee Spell Attack:", "rs": "Ranged Spell Attack:", "ms,rs": "Melee or Ranged Spell Attack:",
           "m": "Melee Attack Roll:", "r": "Ranged Attack Roll:", "m,r": "Melee or Ranged Attack Roll:"}
ATRIBUTOS = {"str": "Strength", "dex": "Dexterity", "con": "Constitution", "int": "Intelligence",
             "wis": "Wisdom", "cha": "Charisma"}
ROTULOS = {"h": "Hit: ", "actSaveFail": "Failure:", "actSaveSuccess": "Success:",
           "actSaveSuccessOrFail": "Failure or Success:", "actTrigger": "Trigger:", "actResponse": "Response:"}
_TAG = re.compile(r"\{@(\w+)\s*([^{}]*)\}")


def _tag(achado) -> str:
    nome, conteudo = achado.group(1), achado.group(2).strip()
    partes = conteudo.split("|")
    if nome in ROTULOS:
        return ROTULOS[nome]
    if nome in ("atk", "atkr"):
        return ATAQUES.get(conteudo.replace(" ", ""), "Attack:")
    if nome == "hit":
        return f"+{conteudo}" if conteudo and conteudo[0] not in "+-" else conteudo
    if nome == "dc":
        return f"DC {partes[0]}"
    if nome == "recharge":
        return f"(Recharge {partes[0]}–6)" if partes[0] and partes[0] != "6" else "(Recharge 6)"
    if nome == "actSave":
        return f"{ATRIBUTOS.get(partes[0], partes[0].title())} Saving Throw:"
    if nome == "chance":
        return f"{partes[0]} percent"
    if len(partes) > 2 and partes[2]:
        return partes[2]
    return partes[0]


def converter_texto(texto: str) -> str:
    anterior = None
    while anterior != texto:                                  # tags aninhadas: resolve de dentro para fora
        anterior, texto = texto, _TAG.sub(_tag, texto)
    return texto


def texto_das_entradas(entradas) -> str:
    """As 'entries' do 5etools (texto, listas, tabelas, subtítulos) em texto corrido."""
    linhas = []

    def andar(entrada, prefixo=""):
        if isinstance(entrada, str):
            linhas.append(prefixo + converter_texto(entrada))
        elif isinstance(entrada, list):
            for item in entrada:
                andar(item, prefixo)
        elif isinstance(entrada, dict):
            tipo = entrada.get("type")
            nome = converter_texto(entrada.get("name", "")) if entrada.get("name") else ""
            if tipo == "list":
                for item in entrada.get("items", []):
                    andar(item, "• ")
            elif tipo == "table":
                if entrada.get("caption"):
                    linhas.append(converter_texto(entrada["caption"]))
                for linha in entrada.get("rows", []):
                    if isinstance(linha, list):
                        linhas.append(" | ".join(texto_das_entradas([c]) for c in linha))
            else:
                filhos = entrada.get("entries", entrada.get("entry", entrada.get("items", [])))
                inicio = len(linhas)
                andar(filhos, prefixo)
                if nome and len(linhas) > inicio:
                    linhas[inicio] = f"{prefixo}{nome}. {linhas[inicio][len(prefixo):]}"
                elif nome:
                    linhas.append(prefixo + nome + ".")

    andar(entradas)
    return "\n".join(l for l in linhas if l.strip())


# ----------------------------------------------------------------------
# CANDIDATOS
# ----------------------------------------------------------------------
def _simplificar(texto: str) -> str:
    texto = unicodedata.normalize("NFD", str(texto or "").lower())
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")


def palavras(texto: str) -> set:
    achadas = set(re.findall(r"[a-z][a-z'-]{2,}", _simplificar(texto)))
    return {p for p in achadas if p not in PALAVRAS_VAZIAS}


def palavras_do_npc(texto: str) -> set:
    """Palavras do arquivo do NPC, com os equivalentes em inglês dos nomes de raças e criaturas."""
    achadas = palavras(texto)
    for palavra in list(achadas):
        equivalente = EQUIVALENTES.get(palavra)
        if equivalente:
            achadas |= set(equivalente.split("-")) | {equivalente}
    return achadas


def _credito(dados: dict, caminho: str) -> dict:
    """{sigla da fonte: 'Título — autores'} a partir do _meta do arquivo."""
    creditos = {}
    for fonte in (dados.get("_meta") or {}).get("sources", []):
        autores = ", ".join(a for a in fonte.get("authors", []) if isinstance(a, str))
        titulo = fonte.get("full") or _autor_e_titulo(caminho)[1]
        creditos[fonte.get("json")] = f"{titulo} — {autores}" if autores else titulo
    return creditos


def _tipo_criatura(valor) -> str:
    if isinstance(valor, dict):
        valor = valor.get("type")
    if isinstance(valor, dict):                               # {"choose": [...]}
        valor = (valor.get("choose") or [""])[0]
    return str(valor or "").lower()


ATIVACOES = {"trait": "passive", "action": "action", "bonus": "bonus", "reaction": "reaction", "legendary": "legendary"}
RESUMO_RACA_FORA = {"age", "alignment", "size", "languages", "ability score increase", "speed"}


@lru_cache(maxsize=64)
def _carregar(caminho: str) -> tuple:
    """Todas as opções de uma fonte baixada: raças, sub-raças, habilidades de criaturas e talentos."""
    try:
        dados = json.loads(_arquivo_local(caminho).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ()
    creditos = _credito(dados, caminho)
    padrao = next(iter(creditos.values()), _autor_e_titulo(caminho)[1])
    opcoes = []

    def credito(item):
        return creditos.get(item.get("source"), padrao)

    for raca in dados.get("race", []) + dados.get("subrace", []):
        if not isinstance(raca, dict) or not raca.get("name"):
            continue
        nome = raca["name"] if not raca.get("raceName") else f"{raca['raceName']} ({raca['name']})"
        tracos = [e for e in raca.get("entries", []) if not (isinstance(e, dict) and str(e.get("name", "")).lower() in RESUMO_RACA_FORA)]
        texto = texto_das_entradas(tracos)
        if texto:
            opcoes.append({"tipo": "race", "nome": nome, "texto": texto, "credito": credito(raca),
                           "chaves": palavras(f"{raca['name']} {raca.get('raceName', '')}"), "criatura": "", "ativacao": "passive"})

    for monstro in dados.get("monster", []):
        if not isinstance(monstro, dict) or not monstro.get("name"):
            continue
        tipo = _tipo_criatura(monstro.get("type"))
        for chave, ativacao in ATIVACOES.items():
            for habilidade in monstro.get(chave) or []:
                if not isinstance(habilidade, dict) or not habilidade.get("name"):
                    continue
                texto = texto_das_entradas(habilidade.get("entries", []))
                if texto:
                    opcoes.append({"tipo": "monster", "nome": converter_texto(habilidade["name"]), "texto": texto,
                                   "credito": credito(monstro), "chaves": palavras(habilidade["name"]),
                                   "criatura": monstro["name"], "chaves_criatura": palavras(monstro["name"]),
                                   "tipo_criatura": tipo, "nd": str(monstro.get("cr", "")) if not isinstance(monstro.get("cr"), dict)
                                   else str(monstro["cr"].get("cr", "")), "ativacao": ativacao})

    for talento in dados.get("feat", []):
        if not isinstance(talento, dict) or not talento.get("name"):
            continue
        texto = texto_das_entradas(talento.get("entries", []))
        if texto:
            requisitos = json.dumps(talento.get("prerequisite", []), ensure_ascii=False)
            opcoes.append({"tipo": "feat", "nome": talento["name"], "texto": texto, "credito": credito(talento),
                           "chaves": palavras(talento["name"]), "requisitos": palavras(requisitos),
                           "criatura": "", "ativacao": "passive"})
    return tuple(opcoes)


def _pontos(opcao: dict, chaves_npc: set) -> int:
    if opcao["tipo"] == "race":
        return 10 * len(opcao["chaves"] & chaves_npc)
    if opcao["tipo"] == "feat":
        return 4 * len(opcao["chaves"] & chaves_npc) + 6 * len(opcao["requisitos"] & chaves_npc)
    pontos = 6 * len(opcao["chaves_criatura"] & chaves_npc) + 2 * len(opcao["chaves"] & chaves_npc)
    if opcao["tipo_criatura"] and opcao["tipo_criatura"] in chaves_npc:
        pontos += 1
    return pontos


def candidatos(texto_npc: str, limite: int = LIMITE_CANDIDATOS) -> list:
    """As opções das fontes escolhidas que mais combinam com o texto do NPC (vazio sem fontes ou sem relação)."""
    chaves = palavras_do_npc(texto_npc)
    pontuadas = []
    for caminho in fontes_escolhidas():
        for opcao in _carregar(caminho):
            pontos = _pontos(opcao, chaves)
            if pontos > 0:
                pontuadas.append((pontos, opcao))
    pontuadas.sort(key=lambda par: -par[0])
    escolhidas, vistos, por_criatura = [], set(), {}
    for _, opcao in pontuadas:
        chave = (opcao["tipo"], opcao["nome"].lower())
        criatura = opcao.get("criatura")
        if chave in vistos or (criatura and por_criatura.get(criatura, 0) >= LIMITE_POR_CRIATURA):
            continue
        vistos.add(chave)
        if criatura:
            por_criatura[criatura] = por_criatura.get(criatura, 0) + 1
        escolhidas.append(opcao)
        if len(escolhidas) >= limite:
            break
    return escolhidas


def texto_para_prompt(opcoes: list) -> str:
    """As opções num bloco curto para a IA, cada uma com o crédito exato que ela deve copiar no campo 'fonte'."""
    blocos = []
    for opcao in opcoes:
        texto = opcao["texto"] if len(opcao["texto"]) <= LIMITE_TEXTO else opcao["texto"][:LIMITE_TEXTO].rsplit(" ", 1)[0] + "…"
        origem = {"race": "raça", "feat": "talento"}.get(opcao["tipo"])
        if not origem:
            origem = f"habilidade de {opcao['criatura']}" + (f", ND {opcao['nd']}" if opcao.get("nd") else "")
        blocos.append(f"- {opcao['nome']} ({origem}; {opcao['ativacao']}) [fonte: {opcao['credito']}]\n  {texto}")
    return "\n".join(blocos)
