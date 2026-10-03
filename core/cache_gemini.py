import engine.project_utils as pu
import core.ai_gemini as ag
from google.genai import types
import os, time
from core.i18n import t

def force_rebuild_world_context():
    arquivo = pu.log_path("Gemini_cache_id.json")
    try:
        if arquivo.exists():
            print(t("gemini.log_apagando_contexto"))
            arquivo.unlink()
    except Exception as e:
        print(t("gemini.log_erro_remover", erro=e))
    return prepare_world_context()

def prepare_world_context(is_dm: bool = True, ttl_hours=12):
    arquivo = pu.log_path("Gemini_cache_id.json")
    
    # 1. Check if an existing Cache or File Upload is still valid (< 24 hours old)
    if arquivo.exists():
        ultima_mod = os.path.getmtime(arquivo)
        idade_horas = (time.time() - ultima_mod) / 3600
        
        dados = pu.ler_json_seguro(arquivo, pu.LOCK_MODELS, padrao={})
        projeto_cache = dados.get("projeto_origem", "")
        
        if idade_horas <= 12 and projeto_cache == pu.PASTA_PROJETO:
            chave = "dm" if is_dm else "player"
            if chave in dados:
                return dados[chave]
            
        print(t("gemini.log_cache_expirado"))
        try:
            os.remove(arquivo)
        except OSError:
            pass

    print(t("gemini.log_criando_bundle"))
    client = ag.get_gemini_client(timeout_seconds=120)
    if not client:
        print(t("gemini.log_sem_chave_bundle"))
        return None

    context_dm = pu.montar_contexto_mundo(is_dm=True)
    context_player = pu.montar_contexto_mundo(is_dm=False)

    # 3. Attempt Explicit Context Caching (For Billing-Enabled Accounts)
    print(t("gemini.log_tentando_cache"))
    data = pu.ler_json_seguro(pu.log_path("models.json"), pu.LOCK_MODELS, padrao=[])
    if not data:
        print(t("gemini.log_recriando_modelos"))
        ag.findmodel()
        data = pu.ler_json_seguro(pu.log_path("models.json"), pu.LOCK_MODELS, padrao=[])

    # ÁREA DE CACHE PARA TOKEN PAGO
    for model in data:
        model_name = model["name"]
        try:
            print(t("gemini.log_cache_modelo", modelo=model_name))
            cache_dm_path = client.caches.create(
                model=model_name,
                config=types.CreateCachedContentConfig(
                    contents=[context_dm],
                    display_name=f"{pu.PASTA_PROJETO} Cache(DM)",
                    ttl=f"{ttl_hours * 3600}s"  
                )
            )
            cache_player_path = client.caches.create(
                            model=model_name,
                            config=types.CreateCachedContentConfig(
                                contents=[context_player],
                                display_name=f"{pu.PASTA_PROJETO} Cache(Player)",
                                ttl=f"{ttl_hours * 3600}s"  
                            )
                        )
            
            registro = {
                "projeto_origem": pu.PASTA_PROJETO,
                "dm": {"type": "cache","id": cache_dm_path.name,"model": model_name,"created": pu.currentdate()},
                "player":{"type": "cache","id": cache_player_path.name,"model": model_name,"created": pu.currentdate()}
            }
            pu.salvar_json_seguro(arquivo, registro, pu.LOCK_MODELS)
            print(t("gemini.log_cache_ok"))
            return registro["dm" if is_dm else "player"]

        except Exception as e:
            print(t("gemini.log_cache_nao_suportado", modelo=model_name, erro=e))


    # ÁREA FREE COM BUNDLE TXT
    print(t("gemini.log_upload"))
    bundle_dm_path = pu.log_path("world_bundle_dm.txt")
    bundle_player_path = pu.log_path("world_bundle_player.txt")

    with open(bundle_dm_path, "w", encoding="utf-8") as f:
        f.write(context_dm)

    with open(bundle_player_path, "w", encoding="utf-8") as f:
        f.write(context_player)

    try:
        uploaded_dm = client.files.upload(file=bundle_dm_path)
        uploaded_player = client.files.upload(file=bundle_player_path)
        # Aguarda o processamento dos DOIS arquivos (Mestre e Jogadores) no Gemini ficar ACTIVE
        while uploaded_dm.state.name == "PROCESSING":
            time.sleep(0.5)
            uploaded_dm = client.files.get(name=uploaded_dm.name)
        while uploaded_player.state.name == "PROCESSING":
            time.sleep(0.5)
            uploaded_player = client.files.get(name=uploaded_player.name)


        registro = {
            "projeto_origem": pu.PASTA_PROJETO,
            "dm": {"type": "file", "id": uploaded_dm.name, "created": pu.currentdate()},
            "player": {"type": "file", "id": uploaded_player.name, "created": pu.currentdate()}
        }

        pu.salvar_json_seguro(arquivo, registro, pu.LOCK_MODELS)
        print(t("gemini.log_bundle_ok"))
        return registro["dm" if is_dm else "player"]

    except Exception as e:
        print(t("gemini.log_erro_upload", erro=e))
        return None