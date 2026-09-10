from pydantic import BaseModel, Field
from typing import List, Optional

# --- SUB-SCHEMAS DE MECÂNICAS ---

class TabelaResultadosD20(BaseModel):
    cd_base: int = Field(description="Classe de Dificuldade de referência (ex: 12, 14, 15)")
    pericia_ou_atributo: str = Field(description="Perícia e Atributo testados (ex: Sobrevivência (SAB), Arcanismo (INT))")
    ate_5_falha_critica: str = Field(description="Consequência para rolagem <= 5: complicação severa, dano, perda de recurso")
    de_6_a_10_falha_parcial: str = Field(description="Consequência para rolagem 6 a 10: falha padrão ou sucesso com custo")
    de_11_a_15_sucesso: str = Field(description="Consequência para rolagem 11 a 15: sucesso operacional normal")
    de_16_a_20_excelente: str = Field(description="Consequência para rolagem 16 a 20: sucesso rápido com vantagem tática")
    acima_21_critico: str = Field(description="Consequência para rolagem 21+: revelação extraordinária, atalho ou segredo")

class AtributosDND(BaseModel):
    forca: str = Field(default="10 (+0)", description="Ex: 16 (+3)")
    destreza: str = Field(default="10 (+0)", description="Ex: 14 (+2)")
    constituicao: str = Field(default="10 (+0)", description="Ex: 14 (+2)")
    inteligencia: str = Field(default="10 (+0)", description="Ex: 10 (+0)")
    sabedoria: str = Field(default="10 (+0)", description="Ex: 12 (+1)")
    carisma: str = Field(default="10 (+0)", description="Ex: 8 (-1)")

class StatblockDND(BaseModel):
    nome: str = Field(description="Nome da criatura/NPC")
    tipo_e_alinhamento: str = Field(description="Ex: Humanoide Médio (Humano), Neutro e Mau")
    ca: int = Field(description="Classe de Armadura")
    pv: str = Field(description="Pontos de vida com fórmula (ex: 45 (6d8 + 18))")
    deslocamento: str = Field(default="9m", description="Ex: 9m, voo 18m")
    atributos: AtributosDND = Field(default_factory=AtributosDND)
    pericias: str = Field(default="Nenhuma", description="Ex: Percepção +4, Furtividade +5")
    sentidos: str = Field(default="Percepção passiva 10", description="Ex: Visão no escuro 18m, Percepção passiva 14")
    nd_e_xp: str = Field(description="Ex: ND 2 (450 XP)")
    ataque_multiplo: Optional[str] = Field(None, description="Descrição do ataque múltiplo, se houver")
    ataque_principal: str = Field(description="Nome, bônus e dano do ataque principal")
    habilidade_especial: Optional[str] = Field(None, description="Habilidade passiva ou magia inata marcante")

# --- AS 5 SALAS DA DUNGEON ---

class Sala1Guardiao(BaseModel):
    titulo_sala: str = Field(description="Nome da sala de entrada")
    narracao: str = Field(description="Texto sensorial imersivo de apresentação")
    ameaca_inicial: str = Field(description="Sentinelas, terreno perigoso ou armadilha de entrada")
    teste_d20: TabelaResultadosD20

class Sala2Enigma(BaseModel):
    titulo_sala: str = Field(description="Nome da câmara do puzzle")
    narracao: str = Field(description="Descrição visual do quebra-cabeça ou obstáculo")
    natureza_desafio: str = Field(description="Mecanismo, runas, fenda mortal, abismo ou puzzle")
    teste_d20: TabelaResultadosD20
    recompensa_de_sucesso: str = Field(description="O que ganham se superarem o puzzle com inteligência")

class Sala3Reviravolta(BaseModel):
    titulo_sala: str = Field(description="Nome da câmara de tensão")
    narracao: str = Field(description="Descrição do cenário onde ocorre a quebra de expectativa")
    a_reviravolta: str = Field(description="A complicação inesperada, traição, refém ou revelação")
    dilema_moral: str = Field(description="A escolha difícil entre duas opções conflitantes")
    teste_d20: TabelaResultadosD20

class Sala4Climax(BaseModel):
    titulo_sala: str = Field(description="Nome do covil/câmara do combate principal")
    narracao: str = Field(description="Descrição épica e opressiva do confronto final")
    efeito_ambiental_covil: str = Field(description="Ação do covil que dispara na Iniciativa 20 a cada rodada")
    interacao_dinamica: str = Field(description="Elementos do cenário que os jogadores podem destruir ou usar")
    teste_d20: TabelaResultadosD20

class Sala5Consequencias(BaseModel):
    titulo_sala: str = Field(description="Nome do local de rescaldo/saída")
    narracao: str = Field(description="Sensação do pós-batalha")
    tesouros: List[str] = Field(description="Lista de recompensas (ouro, itens mágicos, documentos)")
    complicacao_fuga: str = Field(description="Perigo ou tensão ao tentar sair da dungeon")
    evolucao_mundo: str = Field(description="Impacto positivo e negativo gerado no mundo pela vitória")
    gancho_futuro: str = Field(description="Semente para a próxima aventura ou local correlato")

# --- MODELO MESTRE DA AVENTURA ---

class ModuloAventura5Rooms(BaseModel):
    titulo_aventura: str = Field(description="Nome épico da Aventura")
    nivel_recomendado: str = Field(description="Ex: 4 Personagens de 3º Nível")
    premissa_e_gancho: str = Field(description="Resumo do conflito central e gancho de engajamento")
    localizacao_mundo: str = Field(description="Nome da região ou cidade do projeto (use [[Wikilink]])")
    tom_e_atmosfera: str = Field(description="Clima sensorial e tom do local")
    relogio_de_eventos: str = Field(description="Consequência de demorar ou fazer descanso longo")
    
    oponente_principal: StatblockDND = Field(description="Ficha completa do chefe ou antagonista")
    
    sala1: Sala1Guardiao
    sala2: Sala2Enigma
    sala3: Sala3Reviravolta
    sala4: Sala4Climax
    sala5: Sala5Consequencias

def formatar_tabela_d20(t: TabelaResultadosD20, label_contexto: str) -> str:
    return f"""### 🎲 Teste: {t.pericia_ou_atributo} (CD Base: {t.cd_base})

| Resultado d20 | Desfecho do Teste ({label_contexto}) |
| :--- | :--- |
| **≤ 5 (Falha Crítica)** | {t.ate_5_falha_critica} |
| **6 - 10 (Falha Parcial)** | {t.de_6_a_10_falha_parcial} |
| **11 - 15 (Sucesso Básico)** | {t.de_11_a_15_sucesso} |
| **16 - 20 (Sucesso Excepcional)** | {t.de_16_a_20_excelente} |
| **21+ (Crítico / Revelação)** | {t.acima_21_critico} |
"""

def aventura_5rooms_para_markdown(adv: ModuloAventura5Rooms) -> str:
    linhas = []
    
    # Metadados Obsidian Frontmatter
    linhas.append("---")
    linhas.append("tipo: aventura")
    linhas.append("status: rascunho")
    linhas.append("sistema: D&D 5e")
    linhas.append(f"nivel_recomendado: \"{adv.nivel_recomendado}\"")
    linhas.append("---\n")

    # Título & Visão Geral
    linhas.append(f"# {adv.titulo_aventura}\n")
    linhas.append("> [!summary] 📜 Visão Geral da Aventura")
    linhas.append(f"> - **Premissa & Gancho:** {adv.premissa_e_gancho}")
    linhas.append(f"> - **Localização:** {adv.localizacao_mundo}")
    linhas.append(f"> - **Tom & Atmosfera:** {adv.tom_e_atmosfera}")
    linhas.append(f"> - **Relógio de Eventos:** {adv.relogio_de_eventos}\n")
    linhas.append("---\n")

    # Statblock do Vilão
    op = adv.oponente_principal
    at = op.atributos
    linhas.append("## ⚔️ Oponentes Principais (Statblocks)\n")
    linhas.append(f"> [!danger] Monstro / Vilão Principal: [[{op.nome}]]")
    linhas.append(f"> *{op.tipo_e_alinhamento}*")
    linhas.append(f"> - **Classe de Armadura:** {op.ca}")
    linhas.append(f"> - **Pontos de Vida:** {op.pv}")
    linhas.append(f"> - **Deslocamento:** {op.deslocamento}")
    linhas.append("> ")
    linhas.append("> | FOR | DES | CON | INT | SAB | CAR |")
    linhas.append("> | :---: | :---: | :---: | :---: | :---: | :---: |")
    linhas.append(f"> | {at.forca} | {at.destreza} | {at.constituicao} | {at.inteligencia} | {at.sabedoria} | {at.carisma} |")
    linhas.append("> ")
    linhas.append(f"> - **Perícias:** {op.pericias}")
    linhas.append(f"> - **Sentidos:** {op.sentidos}")
    linhas.append(f"> - **Nível de Desafio (ND):** {op.nd_e_xp}")
    linhas.append("> ")
    linhas.append("> **AÇÕES**")
    if op.ataque_multiplo:
        linhas.append(f"> - **Ataque Múltiplo:** {op.ataque_multiplo}")
    linhas.append(f"> - **Ataque Principal:** {op.ataque_principal}")
    if op.habilidade_especial:
        linhas.append(f"> - **Habilidade Especial:** {op.habilidade_especial}")
    linhas.append("\n---\n")

    # SALA 1
    s1 = adv.sala1
    linhas.append(f"## SALA 1: {s1.titulo_sala} (O Guardião da Entrada)")
    linhas.append("> [!quote] Narração para os Jogadores")
    for l in s1.narracao.splitlines(): linhas.append(f"> {l}")
    linhas.append(f"\n- **Ameaça / Obstáculo:** {s1.ameaca_inicial}\n")
    linhas.append(formatar_tabela_d20(s1.teste_d20, "SALA 1"))
    linhas.append("---\n")

    # SALA 2
    s2 = adv.sala2
    linhas.append(f"## SALA 2: {s2.titulo_sala} (O Enigma ou Obstáculo)")
    linhas.append("> [!quote] Narração para os Jogadores")
    for l in s2.narracao.splitlines(): linhas.append(f"> {l}")
    linhas.append(f"\n- **Natureza do Desafio:** {s2.natureza_desafio}")
    linhas.append(f"- **Recompensa por Maestria:** {s2.recompensa_de_sucesso}\n")
    linhas.append(formatar_tabela_d20(s2.teste_d20, "SALA 2"))
    linhas.append("---\n")

    # SALA 3
    s3 = adv.sala3
    linhas.append(f"## SALA 3: {s3.titulo_sala} (Ponto de Tensão / Reviravolta)")
    linhas.append("> [!quote] Narração para os Jogadores")
    for l in s3.narracao.splitlines(): linhas.append(f"> {l}")
    linhas.append(f"\n- **A Reviravolta:** {s3.a_reviravolta}")
    linhas.append(f"- **O Dilema Moral:** {s3.dilema_moral}\n")
    linhas.append(formatar_tabela_d20(s3.teste_d20, "SALA 3"))
    linhas.append("---\n")

    # SALA 4
    s4 = adv.sala4
    linhas.append(f"## SALA 4: {s4.titulo_sala} (O Clímax)")
    linhas.append("> [!quote] Narração para os Jogadores")
    for l in s4.narracao.splitlines(): linhas.append(f"> {l}")
    linhas.append(f"\n- **Efeito do Covil (Iniciativa 20):** {s4.efeito_ambiental_covil}")
    linhas.append(f"- **Interação Tática de Cenário:** {s4.interacao_dinamica}\n")
    linhas.append(formatar_tabela_d20(s4.teste_d20, "SALA 4"))
    linhas.append("---\n")

    # SALA 5
    s5 = adv.sala5
    linhas.append(f"## SALA 5: {s5.titulo_sala} (Recompensa e Consequências)")
    linhas.append("> [!quote] Narração para os Jogadores")
    for l in s5.narracao.splitlines(): linhas.append(f"> {l}")
    linhas.append("\n- **Tesouros & Achados:**")
    for t in s5.tesouros: linhas.append(f"  - {t}")
    linhas.append(f"- **Tensão / Fuga:** {s5.complicacao_fuga}")
    linhas.append(f"- **Evolução do Mundo:** {s5.evolucao_mundo}")
    linhas.append(f"- **Gancho Futuro:** {s5.gancho_futuro}\n")

    return "\n".join(linhas).strip()