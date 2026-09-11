# core/ai_image.py
import os, time, base64, urllib.parse, urllib.request
from pathlib import Path
from PIL import Image
from io import BytesIO
from google import genai
from google.genai import types
import engine.project_utils as pu

PASTA_IMAGENS = pu.PASTA_DADOS_NEXUS / "images"
PASTA_IMAGENS.mkdir(parents=True, exist_ok=True)

# Modelo do Google para quem tiver faturamento/token pago ativo
MODELO_IMAGEM_GEMINI = "gemini-2.5-flash-image"

def obter_cliente_gemini():
    """Obtém o cliente GenAI com a chave armazenada no cofre."""
    api_key = os.getenv("GOOGLE_API_KEY", "").strip()
    if not api_key:
        return None
    return genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=60_000))


def _gerar_via_gemini(prompt: str) -> Path:
    """Tenta gerar via API oficial do Gemini (funciona se houver cota/plano pago)."""
    client = obter_cliente_gemini()
    if not client:
        return None

    config = types.GenerateContentConfig(
        response_modalities=["IMAGE"],
        temperature=0.7
    )

    print(f"🎨 [IMAGEM-GEMINI] Tentando gerar via {MODELO_IMAGEM_GEMINI}...")
    response = client.models.generate_content(
        model=MODELO_IMAGEM_GEMINI,
        contents=[prompt],
        config=config
    )

    if response and response.candidates:
        for part in response.candidates[0].content.parts:
            if getattr(part, "inline_data", None):
                raw_data = part.inline_data.data
                img_bytes = base64.b64decode(raw_data) if isinstance(raw_data, str) else raw_data

                img = Image.open(BytesIO(img_bytes))
                nome_arquivo = f"img_gemini_{int(time.time())}.png"
                caminho_saida = PASTA_IMAGENS / nome_arquivo
                img.save(caminho_saida, format="PNG")
                
                print(f"✅ [IMAGEM-GEMINI] Gerada com sucesso pelo Gemini: {caminho_saida.name}")
                return caminho_saida

    return None


def _gerar_via_pollinations(prompt: str, width: int = 768, height: int = 768) -> Path:
    """Fallback 100% gratuito e open-source via Pollinations (Flux / SDXL)."""
    print(f"🌐 [IMAGEM-FALLBACK] Acionando motor gráfico gratuito Pollinations...")
    prompt_encoded = urllib.parse.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{prompt_encoded}?width={width}&height={height}&nologo=true&seed={int(time.time())}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=45) as response:
        img_data = response.read()
        img = Image.open(BytesIO(img_data))

        nome_arquivo = f"img_free_{int(time.time())}.png"
        caminho_saida = PASTA_IMAGENS / nome_arquivo
        img.save(caminho_saida, format="PNG")

        print(f"✅ [IMAGEM-FALLBACK] Gerada com sucesso pelo Pollinations: {caminho_saida.name}")
        return caminho_saida


def gerar_imagem_com_fallback(prompt: str, width: int = 768, height: int = 768) -> Path:
    """
    1. Tenta a API do Gemini (caso o usuário tenha chave paga / cota).
    2. Se der erro 429, limit: 0 ou qualquer falha, chaveia automaticamente para o Pollinations.
    """
    # 1. Tentativa com o Gemini
    try:
        caminho_gemini = _gerar_via_gemini(prompt)
        if caminho_gemini:
            return caminho_gemini
    except Exception as e:
        err_str = str(e).lower()
        if "429" in err_str or "resource_exhausted" in err_str or "limit: 0" in err_str:
            print("ℹ️ [IMAGEM] Chave sem cota paga no Gemini (limit: 0). Chaveando para motor gratuito...")
        else:
            print(f"⚠️ [IMAGEM] Falha no Gemini ({e}). Tentando fallback...")

    # 2. Fallback garantido gratuito
    try:
        return _gerar_via_pollinations(prompt, width=width, height=height)
    except Exception as e:
        print(f"❌ [IMAGEM] Falha também no motor de fallback: {e}")
        return None


def gerar_portrait_persona(nome: str, psicologia: str, aparencia: str) -> Path:
    """Retrato quadrado (1:1) focado em busto/rosto."""
    prompt = (
        f"Fantasy RPG character portrait bust of {nome}, {aparencia}, "
        f"expression and mood: {psicologia}, highly detailed face, dark fantasy art, "
        "dramatic lighting, digital concept art, trending on artstation, 8k"
    )
    return gerar_imagem_com_fallback(prompt, width=768, height=768)


def gerar_battlemap_boss(nome_sala: str, descricao_ambiente: str) -> Path:
    """Battlemap retangular (16:9) top-down."""
    prompt = (
        f"Top-down D&D tactical battlemap of {nome_sala}, {descricao_ambiente}, "
        "orthogonal aerial view, tabletop RPG battle map, dungeon tiles, atmospheric lighting, 8k"
    )
    return gerar_imagem_com_fallback(prompt, width=1024, height=576)