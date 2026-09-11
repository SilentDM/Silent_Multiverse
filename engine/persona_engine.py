import json
from pathlib import Path
import engine.project_utils as pu
import core.ai_utils as au
from engine.persona_schemas import PersonaRoleplay, persona_para_markdown

PASTA_PERSONAS = pu.PASTA_DADOS_NEXUS / "personas"
PASTA_PERSONAS.mkdir(parents=True, exist_ok=True)

def listar_personas_disponiveis() -> list[str]:
    """Retorna os nomes de todos os personagens salvos."""
    PASTA_PERSONAS.mkdir(parents=True, exist_ok=True)
    return sorted([f.stem for f in PASTA_PERSONAS.glob("*.json")])

def salvar_persona(nome: str, dados_dict: dict, historico_chat: list = None):
    """Salva os metadados e o histórico de chat do personagem."""
    caminho = PASTA_PERSONAS / f"{nome}.json"
    registro = {
        "dados": dados_dict,
        "historico": historico_chat or []
    }
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(registro, f, ensure_ascii=False, indent=2)

def carregar_persona(nome: str) -> tuple[dict, list]:
    """Carrega os dados e o histórico do personagem."""
    caminho = PASTA_PERSONAS / f"{nome}.json"
    if not caminho.exists():
        return {}, []
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            conteudo = json.load(f)
            return conteudo.get("dados", {}), conteudo.get("historico", [])
    except Exception as e:
        print(f"Erro ao carregar persona {nome}: {e}")
        return {}, []

def forjar_nova_persona(nome_personagem: str, descricao_direta: str) -> str:
    """
    Usa o bundle completo do mundo para derivar a psicologia profunda do personagem.
    """
    estilo_contexto = pu.CAMINHO_ESTILO
    prompt_usuario = f"""
Crie a mente completa para roleplay do seguinte personagem:
NOME: {nome_personagem}
DIRETRIZES DO ESCRITOR / MESTRE: {descricao_direta}

Analise todo o contexto do mundo para entender onde ele vive, quais deuses ele teme,
a quais facções ele se submete ou se opõe, e como seu tom de fala reflete sua história.
"""

    instrucoes_sistema = """
Você é um psicólogo de personagens e diretor teatral para ficção e RPG.
Sua missão é criar uma psique rica, cheia de nuances, manias de fala e motivações vivas.
Responda ESTRITAMENTE seguindo o schema JSON.
"""

    resposta_raw = au.ask_ai(
        contents=prompt_usuario,
        system_instruction=instrucoes_sistema,
        temperature=0.65,
        response_schema=PersonaRoleplay,
        use_world_context=True
    )

    # Valida e converte
    persona_obj = PersonaRoleplay.model_validate_json(str(resposta_raw))
    dados_dict = persona_obj.model_dump()
    
    # Salva no arquivo .json
    salvar_persona(persona_obj.nome, dados_dict, historico_chat=[])
    return persona_obj.nome

def dialogar_com_persona(nome_persona: str, prompt_usuario: str) -> str:
    """Executa a chamada da IA assumindo estritamente a persona."""
    dados, historico = carregar_persona(nome_persona)
    if not dados:
        return "⚠️ Erro: Não foi possível carregar as diretrizes deste personagem."

    # Monta a instrução de sistema da persona
    diretrizes_txt = "\n".join(f"- {d}" for d in dados.get("instrucoes_de_atuacao", []))
    
    persona_prompt = f"""
[ASSUMA ESTA IDENTIDADE AGORA]
Você é {dados.get('nome')}, conhecido como '{dados.get('titulo_ou_alcunha')}'.
Ocupação: {dados.get('ocupacao_ou_papel')} | Alinhamento: {dados.get('alinhamento_moral')}

SUA VISÃO DE MUNDO / FILOSOFIA:
"{dados.get('bordao_ou_frase_marcante')}"

COMO VOCÊ FALA:
{dados.get('tom_de_voz_e_estilo_fala')}

SUA MENTE E TEMPERAMENTO:
{dados.get('psicologia_e_temperamento')}

SUA MOTIVAÇÃO PRINCIPAL:
{dados.get('motivacao_primaria')}

SEU MEDO OU FRAQUEZA OCULTA (Nunca revele isso facilmente!):
{dados.get('fraqueza_ou_medo_oculto')}

REGRAS DE INTERPRETAÇÃO (ROLEPLAY):
{diretrizes_txt}
- Responda SEMPRE em primeira pessoa ("Eu acho...", "Você ousa me perguntar isso?").
- Mantenha total fidelidade ao clima do universo e às relações de poder do mundo.
- Jamais quebre o personagem. Você não é um modelo de linguagem; você é {dados.get('nome')}.
"""

    # Constrói o histórico recente do chat desse personagem
    contexto_conversa = ""
    for msg in historico[-6:]:  # Pega as últimas 6 mensagens
        contexto_conversa += f"{msg['autor']}: {msg['texto']}\n"

    input_final = f"--- HISTÓRICO DA NOSSA CONVERSA ---\n{contexto_conversa}\n\nInterlocutor: {prompt_usuario}\n{dados.get('nome')}:"

    resposta = au.ask_ai(
        contents=input_final,
        system_instruction=persona_prompt,
        temperature=0.75,
        use_world_context=True
    )

    # Salva no histórico
    historico.append({"autor": "Interlocutor", "texto": prompt_usuario})
    historico.append({"autor": dados.get("nome"), "texto": str(resposta).strip()})
    salvar_persona(nome_persona, dados, historico)

    return str(resposta).strip()