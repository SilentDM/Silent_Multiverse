# engine/persona_schemas.py
from pydantic import BaseModel, Field
from typing import List, Optional

class PersonaRoleplay(BaseModel):
    # Identidade Básica
    nome: str = Field(description="Nome do personagem ou entidade")
    titulo_ou_alcunha: str = Field(description="Ex: O Arquimago Prateado, A Bruxa dos Esporos, O Regente Traidor")
    alinhamento_moral: str = Field(description="Ex: Caótico e Bom, Neutro e Mau, Leal e Neutro")
    ocupacao_ou_papel: str = Field(description="O que o personagem faz no mundo (ex: Mestre de Guilda, Guarda Real, Ferreiro)")

    # Características Físicas / Visuais (em Português para a Ficha)
    genero: str = Field(description="Ex: Masculino, Feminino, Andrógino")
    raca: str = Field(description="Ex: Humano, Elfo da Lua, Anão da Colina, Meio-Orc, Tiefling")
    idade_aparente: str = Field(description="Ex: Jovem adulto (aparenta 22 anos), Meia-idade (aparenta 50 anos), Ancião")
    tom_de_pele: str = Field(description="Ex: Pálida como mármore, Morena bronzeada, Cinzenta com runas")
    cabelo: str = Field(description="Ex: Longo e desgrenhado preto corvo, Curto prateado com tranças, Careca")
    olhos: str = Field(description="Ex: Âmbar penetrantes, Azuis gélidos, Negros sem íris visível")
    vestimentas_e_acessorios: str = Field(description="Roupas, mantos, couraças, anéis, colares ou itens típicos que carrega no corpo")
    tracos_marcantes: str = Field(description="Cicatrizes, marcas de nascença, tatuagens rúnicas, queimaduras ou adornos faciais")

    # Mente & Interpretação
    psicologia_e_temperamento: str = Field(description="Como ele pensa, reage a provocações, preconceitos e postura emocional")
    tom_de_voz_e_estilo_fala: str = Field(description="Ex: Voz rouca e pausada, sarcástico e veloz, tom solene e sussurrado")
    motivacao_primaria: str = Field(description="O grande objetivo de vida ou ambição imediata deste personagem")
    fraqueza_ou_medo_oculto: str = Field(description="O que ele teme, sua vulnerabilidade psicológica ou segredo guardado")
    bordao_ou_frase_marcante: str = Field(description="Uma frase típica que sintetiza sua visão de mundo")
    instrucoes_de_atuacao: List[str] = Field(description="Diretrizes estritas para a IA: como agir em discussões, o que jamais revelar de primeira...")

    # Prompt em Inglês otimizado para Geração de Imagem
    prompt_visual_ingles: str = Field(
        description=(
            "Prompt descritivo completo em INGLÊS, altamente detalhado para geradores de imagem (Flux / Stable Diffusion). "
            "Deve descrever o busto/retrato do personagem, focando em rosto, cabelo, olhos, pele, expressão emocional, "
            "vestimenta superior, iluminação dramática (rim lighting) e estética dark fantasy/concept art."
        )
    )

def persona_para_markdown(p: PersonaRoleplay) -> str:
    """Converte a persona em um documento Markdown formatado com Callouts para exibição e edição na IDE."""
    linhas = [
        f"# {p.nome}",
        f"> *\"{p.bordao_ou_frase_marcante}\"*\n",
        f"> [!summary] Perfil & Posição",
        f"> - **Título / Alcunha:** {p.titulo_ou_alcunha}",
        f"> - **Ocupação:** {p.ocupacao_ou_papel}",
        f"> - **Alinhamento:** {p.alinhamento_moral}\n",
        f"> [!abstract] Características Visuais",
        f"> - **Gênero & Raça:** {p.genero} | {p.raca} ({p.idade_aparente})",
        f"> - **Pele & Olhos:** Pele {p.tom_de_pele} | Olhos {p.olhos}",
        f"> - **Cabelo:** {p.cabelo}",
        f"> - **Marcas / Cicatrizes:** {p.tracos_marcantes}",
        f"> - **Vestimentas & Adornos:** {p.vestimentas_e_acessorios}\n",
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