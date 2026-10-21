import os, re, threading, time, json, datetime, concurrent.futures
import engine.project_utils as pu
import core.config as st
from typing import Any, Optional, Type
from pydantic import BaseModel
from google import genai
from google.genai import types, errors
import core.cache_gemini as cg
from core.i18n import t

_api_lock = threading.Lock()

DEFAULT_SYSTEM_INSTRUCTION = "You are a helpful assistant that explains things and creates what is requested."
DEFAULT_TEMPERATURE = 0.6
DEFAULT_CONTENTS = "Please repeat: I did not receive a correct prompt, your coding has failed somewhere."
MAX_TOKENS = 20480


def get_gemini_client(timeout_seconds: Optional[int] = 90):
    """
    Obtém o cliente Gemini atualizado dinamicamente.
    Se timeout_seconds for None, utiliza o tempo nativo da Google/HTTPX.
    Caso contrário, converte segundos para milissegundos.
    """
    api_key = os.getenv("GOOGLE_API_KEY", "").strip()
    if not api_key:
        return None

    if timeout_seconds is not None:
        # 90 segundos = 90_000 milissegundos
        http_opts = types.HttpOptions(timeout=timeout_seconds * 1000)
    else:
        # Padrão nativo do SDK / Google
        http_opts = types.HttpOptions()

    return genai.Client(api_key=api_key, http_options=http_opts)

def _is_rate_limit_error(e: Exception) -> bool:
    err_str = str(e).lower()
    if isinstance(e, errors.APIError):
        if getattr(e, "code", None) == 429:
            return True
    return any(
        kw in err_str
        for kw in ["429", "resource_exhausted", "quota", "rate limit", "too many requests"]
    )

def _segundos_do_erro(e: Exception) -> Optional[float]:
    """O retryDelay que a API manda junto com o 429 (ex.: 'retryDelay': '37s'), ou None."""
    achado = re.search(r"retry_?delay['\"]?\s*[:=]\s*['\"]?(\d+(?:\.\d+)?)s", str(e), re.IGNORECASE)
    return float(achado.group(1)) if achado else None


def _domingo(ano: int, mes: int, ordem: int) -> datetime.date:
    """O n-ésimo domingo do mês."""
    primeiro = datetime.date(ano, mes, 1)
    return primeiro + datetime.timedelta(days=(6 - primeiro.weekday()) % 7 + 7 * (ordem - 1))


def proxima_renovacao_diaria(agora: Optional[float] = None) -> float:
    """
    Quando a cota diária do Gemini renova: meia-noite no horário do Pacífico (regra de horário de verão dos EUA:
    do 2º domingo de março ao 1º domingo de novembro). Calculado à mão porque o Windows não traz o banco de fusos.
    """
    agora_utc = datetime.datetime.fromtimestamp(agora if agora is not None else time.time(), datetime.timezone.utc)
    ano = agora_utc.year
    inicio_verao = datetime.datetime.combine(_domingo(ano, 3, 2), datetime.time(10), datetime.timezone.utc)  # 2h PST
    fim_verao = datetime.datetime.combine(_domingo(ano, 11, 1), datetime.time(9), datetime.timezone.utc)     # 2h PDT
    deslocamento = datetime.timedelta(hours=-7 if inicio_verao <= agora_utc < fim_verao else -8)
    local = agora_utc + deslocamento
    meia_noite = datetime.datetime.combine(local.date() + datetime.timedelta(days=1), datetime.time(0))
    # A virada de horário nunca cai à meia-noite, então o deslocamento de agora também vale para a meia-noite seguinte
    return (meia_noite - deslocamento).replace(tzinfo=datetime.timezone.utc).timestamp()


def descanso_do_erro(e: Exception, agora: Optional[float] = None) -> float:
    """Até quando um modelo sem cota deve ser pulado: a cota diária volta na virada do dia do Google;
    a por minuto, no tempo que a API pedir (ou em 1 minuto)."""
    agora = agora if agora is not None else time.time()
    if "perday" in str(e).lower().replace("_", ""):
        return proxima_renovacao_diaria(agora)
    return agora + (_segundos_do_erro(e) or 60)


def modelo_descansando(m: dict, agora: Optional[float] = None) -> bool:
    return float(m.get("resting_until") or 0) > (agora if agora is not None else time.time())


def _taxa_sucesso(m: dict) -> float:
    """Taxa suavizada: um modelo ainda sem uso fica no meio (50%), e cada pedido real a move aos poucos."""
    return (int(m.get("success") or 0) + 1) / (int(m.get("attempts") or 0) + 2)


def _criterio_ordenacao_eficiencia(m: dict):
    """
    Ordena os modelos priorizando a eficiência real observada:
    1. Maior taxa de sucesso (menos falhas e timeouts)
    2. Menor tempo médio de resposta (mais veloz)
    3. Maior score de capacidade/contexto (inteligência do modelo)
    """
    taxa_sucesso = round(_taxa_sucesso(m), 2)

    tempo_resposta = m.get("responsetime") or 9999.0
    score_qualidade = m.get("quality_score", 0)

    # Ordenamos por:
    # -taxa_sucesso -> decrescente (ex: 1.0 antes de 0.8)
    # tempo_resposta -> crescente (ex: 1.2s antes de 4.5s)
    # -score_qualidade -> decrescente (desempate pela capacidade do modelo)
    return (-taxa_sucesso, tempo_resposta, -score_qualidade)

def _modelo_eh_invalido_para_lore(model_name: str, max_input: int, supported_methods: list = None) -> bool:
    """Verifica se o modelo deve ser imediatamente ignorado."""
    name = model_name.lower()
    termos_proibidos = [
        "embedding", "robotics", "aqa", "realtime", "tts", "stt",
        "vision", "imagen", "audio", "medlm", "imagen", "veo", "transcribe"
    ]
    if any(t in name for t in termos_proibidos):
        return True

    if "8b" in name or "nano" in name:
        return True

    if max_input > 0 and max_input < 64_000:
        return True

    if supported_methods and "generateContent" not in supported_methods:
        return True

    return False

def _calcular_score_modelo(model_name: str, max_input_tokens: int, max_output_tokens: int = 0) -> int:
    """
    Pontuação técnica baseada nas necessidades reais de Worldbuilding:
    Profundidade narrativa, coerência lógica e capacidade de contexto.
    """
    name = model_name.lower()
    score = 0

    # --- 1. CAPACIDADE DE CONTEXTO (MUNDO GIGANTE) ---
    if max_input_tokens >= 1_000_000:
        score += 6000   # Consegue absorver dezenas de livros de lore sem perda de atenção
    elif max_input_tokens >= 500_000:
        score += 3500
    elif max_input_tokens >= 128_000:
        score += 2000
    else:
        score -= 2000

    # --- 2. CAPACIDADE DE SAÍDA (CAPÍTULOS LONGOS) ---
    if max_output_tokens >= 8192:
        score += 1500
    elif max_output_tokens >= 4096:
        score += 800

    # --- 3. INTELIGÊNCIA E FAMÍLIA DO MODELO ---
    # Modelos "Pro" entendem sutileza, subtexto e motivações psicológicas de NPCs
    if "pro" in name:
        score += 5000

    # Modelos "Thinking" ou com raciocínio dedicado são perfeitos para auditar consistência
    if "thinking" in name or "reasoning" in name:
        score += 4500

    # Modelos Flash normais são excelentes para tarefas rápidas de preenchimento
    elif "flash" in name:
        score += 2500

    # Versões geracionais mais novas (prioriza 2.5 > 2.0 > 1.5)
    if "2.5" in name:
        score += 2000
    elif "2.0" in name:
        score += 1200
    elif "1.5" in name:
        score += 600

    # Preferência por versões estáveis e oficiais sobre previews instáveis
    if "preview" in name or "exp" in name:
        score -= 400

    return score

def findmodel(file_path=pu.log_path("models.json"), forcar: bool = False):
    """
    Monta a lista de modelos a partir do catálogo da API, sem mandar nenhuma mensagem (listar não gasta cota).
    A ordem começa pela pontuação de cada modelo e depois é ajustada pelo uso real (improvemodel).
    Modelos que continuam no catálogo mantêm o histórico; os novos entram sem uso.
    """
    client_fast = get_gemini_client(timeout_seconds=20)

    if not client_fast:
        print(t("gemini.log_sem_chave_ranking"))
        return

    print(t("gemini.log_verificando_modelos"))

    data = pu.ler_json_seguro(file_path, pu.LOCK_MODELS, padrao=None)
    is_empty = not data

    is_older_than_7_days = False
    if file_path.exists():
        is_older_than_7_days = (time.time() - os.path.getmtime(file_path)) > (7 * 24 * 60 * 60)

    if not forcar and not is_older_than_7_days and not is_empty:
        print(t("gemini.log_modelos_ok"))
        return

    print(t("gemini.log_atualizando_modelos"))
    try:
        all_models = list(client_fast.models.list())
    except Exception as e:
        print(t("gemini.log_erro_listar", erro=e))
        return

    anteriores = {m.get("name"): m for m in (data or [])}
    modelos = []
    for model in all_models:
        model_name = model.name
        max_input = getattr(model, 'input_token_limit', 0) or 0
        max_output = getattr(model, 'output_token_limit', 0) or 0
        supported_actions = getattr(model, 'supported_actions', []) or getattr(model, 'supported_generation_methods', [])

        if _modelo_eh_invalido_para_lore(model_name, max_input, supported_actions):
            continue

        entrada = {
            "name": model_name,
            "display_name": getattr(model, "display_name", None) or model_name,
            "maxinputtokens": max_input,
            "maxoutputtokens": max_output,
            "quality_score": _calcular_score_modelo(model_name, max_input, max_output),
            "responsetime": None,
            "attempts": 0,
            "success": 0,
        }
        antigo = anteriores.get(model_name)
        if antigo:
            for campo in ("responsetime", "attempts", "success", "resting_until"):
                if antigo.get(campo) is not None:
                    entrada[campo] = antigo[campo]
        modelos.append(entrada)

    if not modelos:
        print(t("gemini.log_nenhum_modelo"))
        return

    if st.carregar_configuracoes().get("modelos_modo_ordenacao", "automatico") == "manual" and data:
        # No modo manual, a ordem escolhida pelo usuário continua; os modelos novos vão para o fim
        posicao = {m.get("name"): i for i, m in enumerate(data)}
        modelos.sort(key=lambda m: posicao.get(m["name"], len(posicao)))
    else:
        modelos.sort(key=_criterio_ordenacao_eficiencia)

    pu.salvar_json_seguro(file_path, modelos, pu.LOCK_MODELS)
    print(t("gemini.log_ranking_ok", total=len(modelos)))


def improvemodel(model, success, response_time=None, descanso_ate=None):
    """
    Registra o resultado de um pedido real. Sem cota (descanso_ate) não é falha do modelo: ele só é pulado até
    a cota voltar, sem mexer na taxa de sucesso. Um sucesso encerra qualquer descanso.
    """
    file_path = pu.log_path("models.json")
    if not file_path.exists():
        return

    data = pu.ler_json_seguro(file_path, pu.LOCK_MODELS, padrao=[])
    if not data:
        return

    cfg = st.carregar_configuracoes()
    modo_manual = (cfg.get("modelos_modo_ordenacao", "automatico") == "manual")

    for m in data:
        if m.get("name") == model:
            if descanso_ate is not None:
                m["resting_until"] = descanso_ate
            else:
                if response_time is not None and success:
                    tempo_anterior = m.get("responsetime") or response_time
                    m["responsetime"] = round((tempo_anterior * 0.7) + (response_time * 0.3), 4)
                m["attempts"] = int(m.get("attempts") or 0) + 1
                m["success"] = int(m.get("success") or 0) + (1 if success else 0)
                if success:
                    m.pop("resting_until", None)
            m["quality_score"] = _calcular_score_modelo(m["name"], m.get("maxinputtokens", 0), m.get("maxoutputtokens", 0))

            if not modo_manual:
                data.sort(key=_criterio_ordenacao_eficiencia)

            pu.salvar_json_seguro(file_path, data, pu.LOCK_MODELS)
            return


TESTE_MODELO = "Escreva uma frase de fantasia sombria sobre o [[Reino de Valia]]. Responda apenas a frase."


def testar_modelo(model_name: str) -> dict:
    """
    Manda uma única mensagem curta para um modelo (botão Testar do cartão) e registra o resultado como um uso real.
    Devolve {"ok", "tempo", "erro", "descanso_ate"}.
    """
    client = get_gemini_client(timeout_seconds=60)
    if not client:
        raise ValueError(t("gemini.log_sem_chave_ranking"))
    inicio = time.time()
    try:
        resposta = client.models.generate_content(model=model_name, contents=TESTE_MODELO)
        tempo = round(time.time() - inicio, 4)
        ok = bool((resposta.text or "").strip())
        improvemodel(model_name, ok, tempo)
        return {"ok": ok, "tempo": tempo, "erro": None if ok else t("gemini.teste_vazio"), "descanso_ate": None}
    except Exception as e:
        tempo = round(time.time() - inicio, 4)
        if _is_rate_limit_error(e):
            descanso = descanso_do_erro(e)
            improvemodel(model_name, False, descanso_ate=descanso)
            return {"ok": False, "tempo": tempo, "erro": str(e), "descanso_ate": descanso}
        improvemodel(model_name, False, tempo)
        return {"ok": False, "tempo": tempo, "erro": str(e), "descanso_ate": None}


def reordenar_modelos_manualmente(nova_ordem_nomes: list):
    """Reordena o models.json de acordo com a lista de nomes informada pelo usuário."""
    file_path = pu.log_path("models.json")
    data = pu.ler_json_seguro(file_path, pu.LOCK_MODELS, padrao=[])
    if not data:
        return

    mapa_modelos = {m["name"]: m for m in data}
    lista_reordenada = []

    # 1. Adiciona na ordem que o usuário escolheu
    for nome in nova_ordem_nomes:
        if nome in mapa_modelos:
            lista_reordenada.append(mapa_modelos.pop(nome))

    # 2. Se sobrou algum modelo novo não listado, adiciona ao final
    for m in mapa_modelos.values():
        lista_reordenada.append(m)

    pu.salvar_json_seguro(file_path, lista_reordenada, pu.LOCK_MODELS)

def generate_content_with_fallback(contents: Any, config: types.GenerateContentConfig, cache_model: Optional[str] = None) -> Any:
    # 🟢 Timeout estendido para 90 segundos nas gerações reais
    # Se preferir o tempo 100% nativo da Google, use: client = get_gemini_client(timeout_seconds=None)
    client = get_gemini_client(timeout_seconds=90)
    
    if not client:
        raise ValueError("Nenhuma GOOGLE_API_KEY configurada.")

    data = pu.ler_json_seguro(pu.log_path("models.json"), pu.LOCK_MODELS, padrao=[])
    if not data:
        findmodel()
        data = pu.ler_json_seguro(pu.log_path("models.json"), pu.LOCK_MODELS, padrao=[])

    if not data:
        raise ValueError("models.json está vazio ou indisponível")

    # Modelos sem cota ficam para o fim: só são tentados se todos os outros falharem
    agora = time.time()
    data = [m for m in data if not modelo_descansando(m, agora)] + [m for m in data if modelo_descansando(m, agora)]

    for model in data:
        model_name = model["name"]
        config_to_use = config.model_copy(deep=True)
        contents_to_use = contents

        if config_to_use.cached_content and cache_model and cache_model != model_name:
            config_to_use.cached_content = None

        if config_to_use.cached_content:
            # A API recusa system_instruction / tools junto com cached_content.
            # As instruções vão para o início do conteúdo da própria requisição.
            if config_to_use.system_instruction:
                bloco_instrucoes = f"[INSTRUÇÕES DO SISTEMA]\n{config_to_use.system_instruction}\n[FIM DAS INSTRUÇÕES]"
                if isinstance(contents, list):
                    contents_to_use = [bloco_instrucoes, *contents]
                else:
                    contents_to_use = [bloco_instrucoes, contents]
                config_to_use.system_instruction = None
            config_to_use.tools = None
        elif model.get("supports_tools", False):
            config_to_use.tools = [types.Tool(google_search=types.GoogleSearch())]
        else:
            config_to_use.tools = []

        start_time = time.time()
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=contents_to_use,
                config=config_to_use
            )
            response_time = round(time.time() - start_time, 4)
            improvemodel(model_name, True, response_time)
            if response and response.text:
                return response

        except Exception as e:
            response_time = round(time.time() - start_time, 4)
            err_msg = str(e).lower()
            if _is_rate_limit_error(e):
                descanso = descanso_do_erro(e)
                improvemodel(model_name, False, descanso_ate=descanso)
                print(t("gemini.log_rate_limit", modelo=model_name,
                        hora=time.strftime("%d/%m %H:%M", time.localtime(descanso))))
                continue
            improvemodel(model_name, False, response_time)

            if "timeout" in err_msg or "timed out" in err_msg or "deadline" in err_msg:
                print(t("gemini.log_timeout", modelo=model_name, segundos=response_time))
            else:
                print(t("gemini.log_erro_modelo", modelo=model_name, erro=e))

    raise RuntimeError("Todos os modelos de fallback falharam em gerar conteúdo.")

def ask_ai(
    contents: Any = None, 
    system_instruction: Optional[str] = None, 
    temperature: Optional[float] = None,
    response_schema: Optional[Type[BaseModel]] = None,
    use_world_context: Optional[bool] = True,
    is_dm: Optional[bool] = True,
    imagens: Optional[list] = None
) -> str:
    if not os.getenv("GOOGLE_API_KEY", "").strip():
        raise RuntimeError("Nenhuma chave de API da IA (GOOGLE_API_KEY) foi configurada. Acesse a aba 'Opções' para cadastrar sua chave.")

    if not system_instruction:
        system_instruction = DEFAULT_SYSTEM_INSTRUCTION
    if temperature is None:
        temperature = DEFAULT_TEMPERATURE
    if contents is None:
        contents = DEFAULT_CONTENTS
    
    config_args = {
        "system_instruction": system_instruction,
        "temperature": temperature,
        "max_output_tokens": MAX_TOKENS
    }

    if response_schema:
        config_args["response_mime_type"] = "application/json"
        config_args["response_schema"] = response_schema
        
    config = types.GenerateContentConfig(**config_args)
    if imagens:
        # Texto + imagens na mesma mensagem (os modelos Gemini atuais entendem imagens)
        partes = list(contents) if isinstance(contents, list) else [contents]
        partes += [types.Part.from_bytes(data=img["dados"], mime_type=img["mime"]) for img in imagens]
        contents = partes
    contents_to_send = contents
    cache_model = None

    if use_world_context:
        try:
            world_context = cg.prepare_world_context(is_dm=is_dm)
            client = get_gemini_client()
            if world_context and client:
                config = config.model_copy(deep=True)
                if world_context.get("type") == "file":
                    uploaded_file = client.files.get(name=world_context["id"])
                    contents_to_send = [uploaded_file, *contents] if isinstance(contents, list) else [uploaded_file, contents]
                elif world_context.get("type") == "cache":
                    config.cached_content = world_context["id"]
                    cache_model = world_context.get("model")
        except Exception as e:
            print(t("gemini.log_sem_contexto", erro=e))
        
    with _api_lock:
        response = generate_content_with_fallback(contents_to_send, config, cache_model=cache_model)
        
    return response.text