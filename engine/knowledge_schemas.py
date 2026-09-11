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
    """Converte a estrutura Pydantic em tabelas ricas no padrão Obsidian para inserir no arquivo."""
    linhas = [
        f"\n---\n",
        f"## 🎲 Verificações de Conhecimento (Lore Checks)",
        f"> [!tip] Guia Rápido para o Mestre",
        f"> Use as tabelas abaixo quando os jogadores perguntarem o que seus personagens sabem sobre **{comp.tema_entidade}**.",
        f"> *Nota do Mestre:* {comp.resumo_mestre}\n"
    ]

    for t in comp.testes:
        linhas.append(f"### Teste de {t.pericia}")
        linhas.append(f"*{t.foco_do_teste}*\n")
        linhas.append("| d20 + Bônus | Nível | Informação Revelada ao Jogador |")
        linhas.append("| :---: | :--- | :--- |")
        
        for f in t.faixas:
            linhas.append(f"| **{f.faixa_d20}** | *{f.nivel_informacao}* | {f.o_que_sabe} |")
        
        linhas.append("")

    return "\n".join(linhas)