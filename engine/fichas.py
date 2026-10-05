"""
Fichas de combate de NPCs e monstros.

No 5e a IA preenche um schema e o programa confere a matemática do SRD 5.1
(modificador de atributo, bônus de proficiência e XP pelo Nível de Desafio) antes de
montar o Markdown. Nos outros sistemas a ficha vem em texto, no formato do sistema.
"""
import re
from fractions import Fraction
from typing import List

from pydantic import BaseModel, Field

from core.i18n import tc

# SRD 5.1: XP por Nível de Desafio
XP_POR_ND = {"0": 10, "1/8": 25, "1/4": 50, "1/2": 100, "1": 200, "2": 450, "3": 700, "4": 1100, "5": 1800,
             "6": 2300, "7": 2900, "8": 3900, "9": 5000, "10": 5900, "11": 7200, "12": 8400, "13": 10000,
             "14": 11500, "15": 13000, "16": 15000, "17": 18000, "18": 20000, "19": 22000, "20": 25000,
             "21": 33000, "22": 41000, "23": 50000, "24": 62000, "25": 75000, "26": 90000, "27": 105000,
             "28": 120000, "29": 135000, "30": 155000}
ATRIBUTOS = ("forca", "destreza", "constituicao", "inteligencia", "sabedoria", "carisma")


class Habilidade(BaseModel):
    nome: str = Field(description="Nome do traço ou ação")
    descricao: str = Field(description="Texto completo da regra (bônus de ataque, alcance, dano, CD e efeito)")


class FichaCombate5e(BaseModel):
    nome: str = Field(description="Nome da criatura ou NPC")
    tamanho_tipo_alinhamento: str = Field(description="Ex.: Humanoide Médio (humano), Neutro e Mau")
    classe_armadura: int = Field(description="Classe de Armadura")
    armadura: str = Field(default="", description="De onde vem a CA (ex.: armadura natural, cota de malha)")
    pontos_de_vida: int = Field(description="Pontos de vida médios")
    dados_de_vida: str = Field(description="Dados de vida com o bônus de Constituição (ex.: 6d8 + 12)")
    deslocamento: str = Field(description="Ex.: 9 m, voo 18 m")
    forca: int = Field(description="Valor de Força (1 a 30)")
    destreza: int = Field(description="Valor de Destreza (1 a 30)")
    constituicao: int = Field(description="Valor de Constituição (1 a 30)")
    inteligencia: int = Field(description="Valor de Inteligência (1 a 30)")
    sabedoria: int = Field(description="Valor de Sabedoria (1 a 30)")
    carisma: int = Field(description="Valor de Carisma (1 a 30)")
    testes_de_resistencia: str = Field(default="", description="Ex.: Con +5, Sab +3 (vazio se nenhum)")
    pericias: str = Field(default="", description="Ex.: Percepção +4, Furtividade +5 (vazio se nenhuma)")
    resistencias_e_imunidades: str = Field(default="", description="Resistências, imunidades e vulnerabilidades (vazio se nenhuma)")
    sentidos: str = Field(description="Ex.: visão no escuro 18 m, Percepção passiva 14")
    idiomas: str = Field(default="", description="Idiomas que fala ou entende")
    nivel_de_desafio: str = Field(description="Nível de Desafio no formato do SRD: 0, 1/8, 1/4, 1/2 ou 1 a 30")
    tracos: List[Habilidade] = Field(default_factory=list, description="Traços passivos")
    acoes: List[Habilidade] = Field(description="Ações, incluindo ataques")
    reacoes: List[Habilidade] = Field(default_factory=list, description="Reações (se houver)")
    acoes_lendarias: List[Habilidade] = Field(default_factory=list, description="Ações lendárias (só para criaturas lendárias)")


def modificador(valor: int) -> int:
    return (int(valor) - 10) // 2


def formatar_mod(valor: int) -> str:
    mod = modificador(valor)
    return f"{valor} ({'+' if mod >= 0 else ''}{mod})"


def normalizar_nd(nd: str) -> str:
    """'ND 2 (450 XP)' -> '2'; '0.5' -> '1/2'. Valores fora da tabela viram o mais próximo."""
    texto = str(nd).strip()
    achado = re.search(r"\d+\s*/\s*\d+|\d+(?:[.,]\d+)?", texto)
    if not achado:
        return "1"
    bruto = achado.group(0).replace(" ", "").replace(",", ".")
    try:
        valor = Fraction(bruto) if "/" in bruto else Fraction(bruto).limit_denominator(8)
    except (ValueError, ZeroDivisionError):
        return "1"
    candidatos = {k: Fraction(k) for k in XP_POR_ND}
    return min(candidatos, key=lambda k: abs(candidatos[k] - valor))


def bonus_proficiencia(nd: str) -> int:
    valor = Fraction(normalizar_nd(nd))
    return 2 if valor < 5 else min(9, 2 + (int(valor) - 1) // 4)


def ficha_5e_para_markdown(ficha: FichaCombate5e) -> str:
    nd = normalizar_nd(ficha.nivel_de_desafio)
    linhas = [f"## {tc('ficha.titulo')}", f"*{tc('ficha.sistema', sistema='5e (SRD 5.1)')}*", "",
              f"**{ficha.nome}** — *{ficha.tamanho_tipo_alinhamento}*", "",
              f"- **{tc('md.aventura.ca')}:** {ficha.classe_armadura}" + (f" ({ficha.armadura})" if ficha.armadura else ""),
              f"- **{tc('md.aventura.pv')}:** {ficha.pontos_de_vida} ({ficha.dados_de_vida})",
              f"- **{tc('md.aventura.deslocamento')}:** {ficha.deslocamento}", "",
              "| " + " | ".join(tc(f"ficha.attr.{a}") for a in ATRIBUTOS) + " |",
              "| " + " | ".join(":---:" for _ in ATRIBUTOS) + " |",
              "| " + " | ".join(formatar_mod(getattr(ficha, a)) for a in ATRIBUTOS) + " |", ""]
    for campo, chave in (("testes_de_resistencia", "ficha.resistencia"), ("pericias", "md.aventura.pericias"),
                         ("resistencias_e_imunidades", "ficha.imunidades"), ("sentidos", "md.aventura.sentidos"),
                         ("idiomas", "ficha.idiomas")):
        valor = getattr(ficha, campo).strip()
        if valor:
            linhas.append(f"- **{tc(chave)}:** {valor}")
    linhas.append(f"- **{tc('md.aventura.nd')}:** {nd} ({XP_POR_ND[nd]:,} XP) — "
                  f"{tc('ficha.proficiencia')} +{bonus_proficiencia(nd)}")
    for chave, lista in (("ficha.tracos", ficha.tracos), ("ficha.acoes", ficha.acoes), ("ficha.reacoes", ficha.reacoes),
                         ("ficha.lendarias", ficha.acoes_lendarias)):
        if lista:
            linhas += ["", f"### {tc(chave)}"] + [f"- **{h.nome}.** {h.descricao}" for h in lista]
    return "\n".join(linhas).strip() + "\n"


# ----------------------------------------------------------------------
# SEÇÃO DA FICHA DENTRO DO ARQUIVO
# ----------------------------------------------------------------------
def _nomes_da_secao() -> list:
    import core.i18n as i18n
    nomes = []
    for idioma in i18n.IDIOMAS:
        titulo = i18n.traduzir("ficha.titulo", idioma, "")
        nome = re.sub(r"[^\w\s]", "", titulo).strip().lower()
        if nome:
            nomes.append(nome)
    return nomes


def substituir_secao_ficha(texto: str, secao_nova: str) -> str:
    """Troca a seção '## Ficha de Combate' existente pela nova; se não houver, acrescenta no fim."""
    linhas = texto.rstrip().splitlines()
    nomes = _nomes_da_secao()
    inicio = next((i for i, l in enumerate(linhas) if l.startswith("## ")
                   and any(n in re.sub(r"[^\w\s]", "", l[3:]).strip().lower() for n in nomes)), None)
    if inicio is None:
        return "\n".join(linhas).rstrip() + "\n\n" + secao_nova.strip() + "\n"
    fim = next((i for i in range(inicio + 1, len(linhas)) if re.match(r"^#{1,2} ", linhas[i])), len(linhas))
    return "\n".join(linhas[:inicio] + secao_nova.strip().splitlines() + ([""] if fim < len(linhas) else []) + linhas[fim:]).rstrip() + "\n"
