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
    mapa_imagem: Optional[str] = Field(default=None, description="Nome do arquivo da imagem gerada do battlemap")

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
    from core.i18n import tc
    return "\n".join([
        tc("md.d20.titulo", pericia=t.pericia_ou_atributo, cd=t.cd_base),
        "",
        tc("md.d20.cabecalho", contexto=label_contexto),
        "| :--- | :--- |",
        f"| **{tc('md.d20.falha_critica')}** | {t.ate_5_falha_critica} |",
        f"| **{tc('md.d20.falha_parcial')}** | {t.de_6_a_10_falha_parcial} |",
        f"| **{tc('md.d20.sucesso')}** | {t.de_11_a_15_sucesso} |",
        f"| **{tc('md.d20.excelente')}** | {t.de_16_a_20_excelente} |",
        f"| **{tc('md.d20.critico')}** | {t.acima_21_critico} |",
        "",
    ])


def _narracao(linhas, texto):
    from core.i18n import tc
    linhas.append(tc("md.aventura.narracao"))
    for linha in texto.splitlines():
        linhas.append(f"> {linha}")


def aventura_5rooms_para_markdown(adv: ModuloAventura5Rooms) -> str:
    """Módulo de aventura em Markdown (com callouts do Obsidian), no idioma ativo."""
    from core.i18n import tc
    linhas = [
        "---",
        tc("md.aventura.fm_tipo"),
        tc("marcador.rascunho"),
        tc("md.aventura.fm_sistema"),
        f"{tc('md.aventura.fm_nivel')}: \"{adv.nivel_recomendado}\"",
        "---\n",
        f"# {adv.titulo_aventura}\n",
        tc("md.aventura.visao_geral"),
        f"> - **{tc('md.aventura.premissa')}:** {adv.premissa_e_gancho}",
        f"> - **{tc('md.aventura.localizacao')}:** {adv.localizacao_mundo}",
        f"> - **{tc('md.aventura.tom')}:** {adv.tom_e_atmosfera}",
        f"> - **{tc('md.aventura.relogio')}:** {adv.relogio_de_eventos}\n",
        "---\n",
    ]

    op, at = adv.oponente_principal, adv.oponente_principal.atributos
    linhas += [
        tc("md.aventura.oponentes") + "\n",
        tc("md.aventura.vilao", nome=op.nome),
        f"> *{op.tipo_e_alinhamento}*",
        f"> - **{tc('md.aventura.ca')}:** {op.ca}",
        f"> - **{tc('md.aventura.pv')}:** {op.pv}",
        f"> - **{tc('md.aventura.deslocamento')}:** {op.deslocamento}",
        "> ",
        tc("md.aventura.atributos_cabecalho"),
        "> | :---: | :---: | :---: | :---: | :---: | :---: |",
        f"> | {at.forca} | {at.destreza} | {at.constituicao} | {at.inteligencia} | {at.sabedoria} | {at.carisma} |",
        "> ",
        f"> - **{tc('md.aventura.pericias')}:** {op.pericias}",
        f"> - **{tc('md.aventura.sentidos')}:** {op.sentidos}",
        f"> - **{tc('md.aventura.nd')}:** {op.nd_e_xp}",
        "> ",
        f"> **{tc('md.aventura.acoes')}**",
    ]
    if op.ataque_multiplo:
        linhas.append(f"> - **{tc('md.aventura.ataque_multiplo')}:** {op.ataque_multiplo}")
    linhas.append(f"> - **{tc('md.aventura.ataque_principal')}:** {op.ataque_principal}")
    if op.habilidade_especial:
        linhas.append(f"> - **{tc('md.aventura.habilidade_especial')}:** {op.habilidade_especial}")
    linhas.append("\n---\n")

    s1 = adv.sala1
    linhas.append(tc("md.aventura.sala1", titulo=s1.titulo_sala))
    _narracao(linhas, s1.narracao)
    linhas.append(f"\n- **{tc('md.aventura.ameaca')}:** {s1.ameaca_inicial}\n")
    linhas += [formatar_tabela_d20(s1.teste_d20, tc("md.aventura.rotulo_sala", n=1)), "---\n"]

    s2 = adv.sala2
    linhas.append(tc("md.aventura.sala2", titulo=s2.titulo_sala))
    _narracao(linhas, s2.narracao)
    linhas.append(f"\n- **{tc('md.aventura.natureza')}:** {s2.natureza_desafio}")
    linhas.append(f"- **{tc('md.aventura.recompensa')}:** {s2.recompensa_de_sucesso}\n")
    linhas += [formatar_tabela_d20(s2.teste_d20, tc("md.aventura.rotulo_sala", n=2)), "---\n"]

    s3 = adv.sala3
    linhas.append(tc("md.aventura.sala3", titulo=s3.titulo_sala))
    _narracao(linhas, s3.narracao)
    linhas.append(f"\n- **{tc('md.aventura.reviravolta')}:** {s3.a_reviravolta}")
    linhas.append(f"- **{tc('md.aventura.dilema')}:** {s3.dilema_moral}\n")
    linhas += [formatar_tabela_d20(s3.teste_d20, tc("md.aventura.rotulo_sala", n=3)), "---\n"]

    s4 = adv.sala4
    linhas.append(tc("md.aventura.sala4", titulo=s4.titulo_sala))
    _narracao(linhas, s4.narracao)
    linhas.append("")
    if getattr(s4, "mapa_imagem", None):
        linhas.append(tc("md.aventura.mapa"))
        linhas.append(f"> ![[{s4.mapa_imagem}]]\n")
    linhas.append(f"- **{tc('md.aventura.covil')}:** {s4.efeito_ambiental_covil}")
    linhas.append(f"- **{tc('md.aventura.interacao')}:** {s4.interacao_dinamica}\n")
    linhas += [formatar_tabela_d20(s4.teste_d20, tc("md.aventura.rotulo_sala", n=4)), "---\n"]

    s5 = adv.sala5
    linhas.append(tc("md.aventura.sala5", titulo=s5.titulo_sala))
    _narracao(linhas, s5.narracao)
    linhas.append(f"\n- **{tc('md.aventura.tesouros')}:**")
    linhas += [f"  - {tesouro}" for tesouro in s5.tesouros]
    linhas.append(f"- **{tc('md.aventura.fuga')}:** {s5.complicacao_fuga}")
    linhas.append(f"- **{tc('md.aventura.evolucao')}:** {s5.evolucao_mundo}")
    linhas.append(f"- **{tc('md.aventura.gancho')}:** {s5.gancho_futuro}\n")
    return "\n".join(linhas)
