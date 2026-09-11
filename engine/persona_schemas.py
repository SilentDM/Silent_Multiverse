from pydantic import BaseModel, Field
from typing import List, Optional

class PersonaRoleplay(BaseModel):
    nome: str = Field(description="Nome do personagem ou entidade")
    titulo_ou_alcunha: str = Field(description="Ex: O Arquimago Prateado, A Bruxa dos Esporos, O Regente Traidor")
    alinhamento_moral: str = Field(description="Ex: Caótico e Neutro, Leal e Mau")
    ocupacao_ou_papel: str = Field(description="O que o personagem faz no mundo (governante, mercenário, ferreiro...)")
    
    psicologia_e_temperamento: str = Field(description="Como ele pensa, reage a ameaças, preconceitos e postura emocional")
    tom_de_voz_e_estilo_fala: str = Field(description="Ex: Fala sussurrada e enigmática, usa termos arcaicos, tom agressivo e direto")
    
    motivacao_primaria: str = Field(description="O grande objetivo de vida ou ambição imediata deste personagem")
    fraqueza_ou_medo_oculto: str = Field(description="O que ele teme, sua vulnerabilidade psicológica ou segredo guardado")
    
    bordao_ou_frase_marcante: str = Field(description="Uma frase típica que sintetiza sua visão de mundo")
    instrucoes_de_atuacao: List[str] = Field(description="Diretrizes estritas para a IA: como se comportar em discussões, o que jamais revelar de primeira...")

def persona_para_markdown(p: PersonaRoleplay) -> str:
    """Converte a persona em um documento Markdown formatado com Callouts para exibição e edição."""
    linhas = [
        f"# {p.nome}",
        f"> *\"{p.bordao_ou_frase_marcante}\"*\n",
        f"> [!summary] Perfil & Posição",
        f"> - **Título / Alcunha:** {p.titulo_ou_alcunha}",
        f"> - **Ocupação:** {p.ocupacao_ou_papel}",
        f"> - **Alinhamento:** {p.alinhamento_moral}\n",
        f"> [!quote] Voz & Temperamento",
        f"> - **Estilo de Fala:** {p.tom_de_voz_e_estilo_fala}",
        f"> - **Psicologia:** {p.psicologia_e_temperamento}\n",
        f"> [!warning] Ambições & Fraquezas",
        f"> - **Motivação:** {p.motivacao_primaria}",
        f"> - **Vulnerabilidade Oculta:** {p.fraqueza_ou_medo_oculto}\n",
        f"## 🎭 Diretrizes de Atuação (Roleplay)"
    ]
    for inst in p.instrucoes_de_atuacao:
        linhas.append(f"- {inst}")
    return "\n".join(linhas)