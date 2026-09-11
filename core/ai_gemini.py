import os, threading, time, json, concurrent.futures
import engine.project_utils as pu
import ui.settings as st
from typing import Any, Optional, Type
from pydantic import BaseModel
from google import genai
from google.genai import types, errors
import core.cache_gemini as cg

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

def _criterio_ordenacao_eficiencia(m: dict):
    """
    Ordena os modelos priorizando a eficiência real observada:
    1. Maior taxa de sucesso (menos falhas e timeouts)
    2. Menor tempo médio de resposta (mais veloz)
    3. Maior score de capacidade/contexto (inteligência do modelo)
    """
    tentativas = max(1, m.get("attempts", 1))
    sucessos = m.get("success", 0)
    taxa_sucesso = sucessos / tentativas

    tempo_resposta = m.get("responsetime", 9999.0)
    score_qualidade = m.get("quality_score", 0)

    # Ordenamos por:
    # -taxa_sucesso -> decrescente (ex: 1.0 antes de 0.8)
    # tempo_resposta -> crescente (ex: 1.2s antes de 4.5s)
    # -score_qualidade -> decrescente (desempate pela capacidade do modelo)
    return (-taxa_sucesso, tempo_resposta, -score_qualidade)

def _modelo_eh_invalido_para_lore(model_name: str, max_input: int, supported_methods: list = None) -> bool:
    """Verifica se o modelo deve ser imediatamente ignorado."""
    name = model_name.lower()

    # 1. Filtros de tarefas que não geram texto narrativo
    termos_proibidos = [
        "embedding", "robotics", "aqa", "realtime", "tts", "stt",
        "vision", "imagen", "audio", "medlm", "imagen", "veo", "transcribe"
    ]
    if any(t in name for t in termos_proibidos):
        return True

    # 2. Ignora modelos de geração puramente ultraleves ou subdimensionados para lore densa
    if "8b" in name or "nano" in name:
        return True

    # 3. Descarta modelos que não têm contexto mínimo para carregar um compêndio (mínimo 64k tokens)
    if max_input > 0 and max_input < 64_000:
        return True

    # 4. Checagem de métodos suportados (se fornecido pela API)
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

def findmodel(file_path=pu.log_path("models.json")):
    # Timeout mais tolerante para a descoberta
    client_fast = get_gemini_client(timeout_seconds=20)
    
    if not client_fast:
        print("Nenhuma GOOGLE_API_KEY configurada. Pulando ranqueamento de modelos.")
        return

    print("Verificando e ranqueando modelos disponíveis para Worldbuilding...")
    
    data = pu.ler_json_seguro(file_path, pu.LOCK_MODELS, padrao=None)
    is_empty = not data

    is_older_than_7_days = False
    if file_path.exists():
        is_older_than_7_days = (time.time() - os.path.getmtime(file_path)) > (7 * 24 * 60 * 60)

    if not is_older_than_7_days and not is_empty:
        print("Lista de modelos disponíveis OK!")
        return

    print("Atualizando compêndio de modelos da API...")
    try:
        all_models = client_fast.models.list()
    except Exception as e:
        print(f"Erro ao listar modelos da API: {e}")
        return

    working_models = []
    
    # Prompt rápido para avaliar se o modelo entende instruções de escrita
    teste_criativo = "Escreva uma frase de fantasia sombria sobre o [[Reino de Valia]]. Responda apenas a frase."

    for model in all_models:
        model_name = model.name
        max_input = getattr(model, 'input_token_limit', 0) or 0
        max_output = getattr(model, 'output_token_limit', 0) or 0
        supported_actions = getattr(model, 'supported_actions', []) or getattr(model, 'supported_generation_methods', [])

        # 1. Filtro estrito de descarte
        if _modelo_eh_invalido_para_lore(model_name, max_input, supported_actions):
            continue

        # 2. Benchmark de latência e execução
        start_time = time.time()
        try:
            resp = client_fast.models.generate_content(
                model=model_name, 
                contents=teste_criativo
            )
            response_time = round(time.time() - start_time, 4)
            texto_resp = resp.text or ""
            
            # Se a resposta foi vazia, descarta
            if not texto_resp.strip():
                continue

        except Exception as e:
            # Modelo instável, sem cota ou com erro de acesso
            continue

        # Bônus se respeitou o formato de wikilink [[...]] no mini-teste
        bonus_instrucao = 500 if "[[" in texto_resp and "]]" in texto_resp else 0

        quality_score = _calcular_score_modelo(model_name, max_input, max_output) + bonus_instrucao

        working_models.append({
            "name": model_name,
            "display_name": getattr(model, "display_name", model_name),
            "maxinputtokens": max_input,
            "maxoutputtokens": max_output,
            "responsetime": response_time,
            "quality_score": quality_score,
            "attempts": 1,
            "success": 1
        })
        time.sleep(0.3)

    if not working_models:
        print("⚠️ Nenhum modelo compatível respondeu com sucesso ao benchmark.")
        return

    # Ordena combinando taxa de sucesso inicial, qualidade arquitetural e velocidade
    working_models.sort(key=_criterio_ordenacao_eficiencia)

    pu.salvar_json_seguro(file_path, working_models, pu.LOCK_MODELS)
    print(f"✅ {len(working_models)} modelos válidos ranqueados com sucesso para Worldbuilding!")

def improvemodel(model, success, response_time=None):
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
            if response_time is not None and success:
                tempo_anterior = m.get("responsetime", response_time)
                m["responsetime"] = round((tempo_anterior * 0.7) + (response_time * 0.3), 4)
                
            m["attempts"] = m.get("attempts", 0) + 1
            m["success"] = m.get("success", 0) + (1 if success else 0)
            m["quality_score"] = _calcular_score_modelo(m["name"], m.get("maxinputtokens", 0))
            
            if not modo_manual:
                data.sort(key=_criterio_ordenacao_eficiencia)
            
            pu.salvar_json_seguro(file_path, data, pu.LOCK_MODELS)
            return

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

    for model in data:
        model_name = model["name"]
        config_to_use = config.model_copy(deep=True)

        if config_to_use.cached_content and cache_model and cache_model != model_name:
            config_to_use.cached_content = None

        if model.get("supports_tools", False):
            config_to_use.tools = [types.Tool(google_search=types.GoogleSearch())]
        else:
            config_to_use.tools = []

        start_time = time.time()
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=contents,
                config=config_to_use
            )
            response_time = round(time.time() - start_time, 4)
            improvemodel(model_name, True, response_time)
            if response and response.text:
                return response

        except Exception as e:
            response_time = round(time.time() - start_time, 4)
            improvemodel(model_name, False, response_time)
            
            err_msg = str(e).lower()
            if _is_rate_limit_error(e):
                print(f"Rate Limit atingido no modelo {model_name}. Pulando para o próximo...")
            elif "timeout" in err_msg or "timed out" in err_msg or "deadline" in err_msg:
                print(f"⏱️ Timeout no modelo {model_name} após {response_time}s. Pulando para o próximo...")
            else:
                print(f"Erro no modelo {model_name}: {e}")

    raise RuntimeError("Todos os modelos de fallback falharam em gerar conteúdo.")

def ask_ai(
    contents: Any = None, 
    system_instruction: Optional[str] = None, 
    temperature: Optional[float] = None,
    response_schema: Optional[Type[BaseModel]] = None,
    use_world_context: Optional[bool] = True,
    is_dm: Optional[bool] = True
) -> str:
    if not os.getenv("GOOGLE_API_KEY", "").strip():
        return "❌ Nenhuma chave de API da IA (GOOGLE_API_KEY) foi configurada. Acesse a aba 'Opções' para cadastrar sua chave."

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
                    contents_to_send = [uploaded_file, contents]
                elif world_context.get("type") == "cache":
                    config.cached_content = world_context["id"]
                    cache_model = world_context.get("model")
        except Exception as e:
            print(f"⚠️ World Context não disponível: {e}")
        
    with _api_lock:
        response = generate_content_with_fallback(contents_to_send, config, cache_model=cache_model)
        
    return response.text