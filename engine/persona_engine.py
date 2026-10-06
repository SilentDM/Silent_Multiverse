import json, re
from pathlib import Path
import engine.project_utils as pu
import core.ai_utils as au
from core.i18n import t, tc
from core.prompts import carregar_prompt
import engine.expander as ex
from engine.persona_schemas import PersonaRoleplay, persona_para_markdown

PASTA_PERSONAS = pu.PASTA_DADOS_NEXUS / "personas"
AUTOR_INTERLOCUTOR = "Interlocutor"  # marcador interno do histórico salvo (não traduzir)
PASTA_PERSONAS.mkdir(parents=True, exist_ok=True)

def nome_arquivo_seguro(nome: str) -> str:
    """Remove caracteres proibidos em nomes de arquivo no Windows (barras, : * ? " < > |) e pontas inválidas."""
    limpo = re.sub(r'[\\/:*?"<>|\x00-\x1f]', '', str(nome or "")).strip().strip(".")
    return limpo or "persona"

def listar_personas_disponiveis() -> list[str]:
    """Retorna os nomes de todos os personagens salvos."""
    PASTA_PERSONAS.mkdir(parents=True, exist_ok=True)
    return sorted([f.stem for f in PASTA_PERSONAS.glob("*.json")])

def salvar_persona(nome: str, dados_dict: dict, historico_chat: list = None):
    """Salva os metadados e o histórico de chat do personagem."""
    caminho = PASTA_PERSONAS / f"{nome_arquivo_seguro(nome)}.json"
    registro = {
        "dados": dados_dict,
        "historico": historico_chat or []
    }
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(registro, f, ensure_ascii=False, indent=2)

def carregar_persona(nome: str) -> tuple[dict, list]:
    """Carrega os dados e o histórico do personagem."""
    caminho = PASTA_PERSONAS / f"{nome_arquivo_seguro(nome)}.json"
    if not caminho.exists():
        return {}, []
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            conteudo = json.load(f)
            return conteudo.get("dados", {}), conteudo.get("historico", [])
    except Exception as e:
        print(t("persona.erro_ler", nome=nome, erro=e))
        return {}, []

def forjar_nova_persona(nome_personagem: str, descricao_direta: str) -> str:
    """Usa o mundo inteiro como contexto para derivar a psicologia e a aparência do personagem."""
    resposta_raw = au.ask_ai(
        contents=carregar_prompt("persona_forja_usuario", nome=nome_personagem, diretrizes=descricao_direta),
        system_instruction=carregar_prompt("persona_forja_sistema"),
        temperature=0.65,
        response_schema=PersonaRoleplay,
        use_world_context=True,
    )
    persona_obj = PersonaRoleplay.model_validate_json(ex.remover_markdown_fences(str(resposta_raw)))
    # O nome do arquivo (e da persona na lista) é a versão segura do nome devolvido pela IA
    nome_salvo = nome_arquivo_seguro(persona_obj.nome)
    salvar_persona(nome_salvo, persona_obj.model_dump(), historico_chat=[])
    return nome_salvo


def _instrucoes_da_ficha_editada(dados: dict) -> str:
    """A ficha que o Mestre editou (sem a seção do retrato) vira a identidade do personagem."""
    return carregar_prompt("persona_dialogo_ficha_sistema", nome=dados.get("nome", ""),
                           ficha=_separar_retrato(dados[CHAVE_FICHA])[0])


def dialogar_com_persona(nome_persona: str, prompt_usuario: str) -> str:
    """Executa a chamada da IA assumindo estritamente a persona (relida do disco a cada fala)."""
    dados, historico = carregar_persona(nome_persona)
    if not dados:
        raise RuntimeError(t("persona.erro_carregar", nome=nome_persona))

    if (dados.get(CHAVE_FICHA) or "").strip():
        instrucoes = _instrucoes_da_ficha_editada(dados)
    else:
        instrucoes = _instrucoes_dos_campos(dados)

    # Histórico recente (as últimas 6 mensagens); o autor interno "Interlocutor" vira o rótulo do idioma
    rotulo_interlocutor = tc("persona.interlocutor")
    historico_txt = "\n".join(
        f"{rotulo_interlocutor if m['autor'] == AUTOR_INTERLOCUTOR else m['autor']}: {m['texto']}" for m in historico[-6:])

    resposta = au.ask_ai(
        contents=carregar_prompt("persona_dialogo_usuario", historico=historico_txt, interlocutor=rotulo_interlocutor,
                                 mensagem=prompt_usuario, nome=dados.get("nome")),
        system_instruction=instrucoes,
        temperature=0.75,
        use_world_context=True,
    )
    resposta = str(resposta).strip()
    # Relê antes de gravar: a ficha pode ter sido editada enquanto a IA respondia
    dados_atuais, _ = carregar_persona(nome_persona)
    historico.append({"autor": AUTOR_INTERLOCUTOR, "texto": prompt_usuario})
    historico.append({"autor": dados.get("nome"), "texto": resposta})
    salvar_persona(nome_persona, dados_atuais or dados, historico)
    return resposta


def _instrucoes_dos_campos(dados: dict) -> str:
    return carregar_prompt(
        "persona_dialogo_sistema", nome=dados.get("nome"), alcunha=dados.get("titulo_ou_alcunha"),
        ocupacao=dados.get("ocupacao_ou_papel"), alinhamento=dados.get("alinhamento_moral"),
        bordao=dados.get("bordao_ou_frase_marcante"), voz=dados.get("tom_de_voz_e_estilo_fala"),
        psicologia=dados.get("psicologia_e_temperamento"), motivacao=dados.get("motivacao_primaria"),
        fraqueza=dados.get("fraqueza_ou_medo_oculto"),
        instrucoes="\n".join(f"- {d}" for d in dados.get("instrucoes_de_atuacao", [])))


# ----------------------------------------------------------------------
# FICHA E RETRATO (usados pela página de Roleplay)
# ----------------------------------------------------------------------
# A ficha é exibida como texto editável. Quando o Mestre edita, o texto vai para o JSON
# (CHAVE_FICHA) e passa a ser a identidade usada nas conversas. A seção "## 🎨" guarda o
# prompt do retrato; ao salvar, ela atualiza o prompt usado pelo gerador de imagem.
CHAVE_FICHA = "ficha_texto"
MARCA_RETRATO = "## 🎨"


def _ficha_gerada(dados: dict) -> str:
    try:
        return persona_para_markdown(PersonaRoleplay(**dados))
    except Exception:
        return json.dumps({k: v for k, v in dados.items() if k != CHAVE_FICHA}, ensure_ascii=False, indent=2)


def _separar_retrato(texto: str) -> tuple:
    """(ficha sem a seção do retrato, prompt do retrato ou ""). A seção vai do título "## 🎨" até a primeira linha em branco."""
    linhas = (texto or "").splitlines()
    for i, linha in enumerate(linhas):
        if linha.strip().startswith(MARCA_RETRATO):
            fim = i + 1
            while fim < len(linhas) and linhas[fim].strip() and not linhas[fim].lstrip().startswith(("#", ">")):
                fim += 1
            corpo = linhas[:i] + linhas[fim:]
            return "\n".join(corpo).strip(), "\n".join(linhas[i + 1:fim]).strip()
    return (texto or "").strip(), ""


def ficha(nome_persona: str) -> dict:
    """Dados prontos para exibir: a ficha (editada pelo Mestre ou a gerada), histórico e retrato."""
    dados, historico = carregar_persona(nome_persona)
    if not dados:
        return {"markdown": "", "historico": historico, "retrato": None, "nome": nome_persona, "editada": False}
    editada = bool((dados.get(CHAVE_FICHA) or "").strip())
    markdown = dados[CHAVE_FICHA] if editada else _ficha_gerada(dados)
    retrato = dados.get("portrait_path")
    if retrato and not Path(retrato).exists():
        retrato = None
    return {"markdown": markdown, "historico": historico, "retrato": retrato, "nome": dados.get("nome", nome_persona),
            "editada": editada}


def salvar_ficha(nome_persona: str, texto: str) -> bool:
    """Grava a ficha editada no JSON da persona (mantendo o histórico). Devolve False se nada mudou."""
    dados, historico = carregar_persona(nome_persona)
    if not dados:
        raise RuntimeError(t("persona.erro_carregar", nome=nome_persona))
    texto = (texto or "").rstrip()
    atual = dados.get(CHAVE_FICHA) or _ficha_gerada(dados)
    if texto == atual.rstrip():
        return False
    dados[CHAVE_FICHA] = texto
    prompt_retrato = _separar_retrato(texto)[1]
    if prompt_retrato:
        dados["prompt_visual_ingles"] = prompt_retrato
    salvar_persona(nome_persona, dados, historico)
    return True


def restaurar_ficha(nome_persona: str) -> str:
    """Descarta as edições do Mestre e volta à ficha gerada pela IA. Devolve o texto dela."""
    dados, historico = carregar_persona(nome_persona)
    dados.pop(CHAVE_FICHA, None)
    salvar_persona(nome_persona, dados, historico)
    return _ficha_gerada(dados)


def gerar_retrato(nome_persona: str):
    """Gera o retrato e o grava na persona certa (relendo o histórico atual). Devolve o caminho ou None."""
    import core.ai_image as aimg
    dados, _ = carregar_persona(nome_persona)
    caminho = aimg.gerar_portrait_persona(dados.get("nome", nome_persona), dados)
    if not caminho:
        return None
    dados_atuais, historico_atual = carregar_persona(nome_persona)
    dados_atuais = dados_atuais or dados
    dados_atuais["portrait_path"] = str(caminho)
    salvar_persona(nome_persona, dados_atuais, historico_atual)
    return str(caminho)


def nome_sugerido_retrato(nome_persona: str) -> str:
    return f"portrait_{nome_arquivo_seguro(nome_persona).replace(' ', '_').lower()}.png"


def exportar_retrato(origem: str, destino: str):
    import shutil
    shutil.copy2(origem, destino)
