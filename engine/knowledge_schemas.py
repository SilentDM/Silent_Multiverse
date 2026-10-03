from pydantic import BaseModel, Field
from typing import List, Optional

class FaixaResultadoLore(BaseModel):
    faixa_d20: str = Field(description="Ex: '≤ 5', '6 a 10', '11 a 15', '16 a 20', '21 a 25', '26+'")
    nivel_informacao: str = Field(description="Ex: Rumor Popular, Fato Básico, Operacional, Conhecimento Privilegiado, Segredo de Cúpula")
    o_que_sabe: str = Field(description="O texto exato e prático que o Mestre deve narrar ou ler para o jogador.")

class TesteDePericiaConhecimento(BaseModel):
    pericia: str = Field(description="Ex: História (INT), Investigação (INT), Natureza (INT), Religião (INT), Arcanismo (INT) ou Sobrevivência (SAB)")
    foco_do_teste: str = Field(description="O que essa perícia específica avalia sobre a entidade (ex: 'Origens e alianças políticas da Guilda')")
    faixas: List[FaixaResultadoLore] = Field(description="As 5 ou 6 faixas de resultado ordenadas do 5 até o 25+")

class CompendioConhecimento(BaseModel):
    tema_entidade: str = Field(description="Nome do sujeito analisado (ex: 'Guilda dos Mineradores do Martelo Negro')")
    resumo_mestre: str = Field(description="Uma frase resumindo o que é crucial o Mestre ter em mente ao passar essas informações.")
    testes: List[TesteDePericiaConhecimento] = Field(description="Normalmente 1 a 3 perícias aplicáveis (ex: História para política, Investigação para segredos urbanos)")

def compendio_para_markdown(comp: CompendioConhecimento) -> str:
    """Tabelas de Testes de Conhecimento em Markdown (padrão Obsidian), no idioma ativo."""
    from core.i18n import tc
    linhas = [
        "\n---\n",
        tc("md.conhecimento.titulo"),
        tc("md.conhecimento.guia"),
        tc("md.conhecimento.uso", tema=comp.tema_entidade),
        tc("md.conhecimento.nota", resumo=comp.resumo_mestre) + "\n",
    ]
    for teste in comp.testes:
        linhas.append(tc("md.conhecimento.teste", pericia=teste.pericia))
        linhas.append(f"*{teste.foco_do_teste}*\n")
        linhas.append(tc("md.conhecimento.cabecalho"))
        linhas.append("| :---: | :--- | :--- |")
        for faixa in teste.faixas:
            linhas.append(f"| **{faixa.faixa_d20}** | *{faixa.nivel_informacao}* | {faixa.o_que_sabe} |")
        linhas.append("")
    return "\n".join(linhas)
