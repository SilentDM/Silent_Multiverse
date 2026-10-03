import os, time, re, glob
import core.ai_utils as au
from core.i18n import t
from core.prompts import carregar_prompt
import engine.project_utils as pu
from pathlib import Path

MEMORIES_DIR = pu.PASTA_MEMORIES
os.makedirs(MEMORIES_DIR, exist_ok=True)

def sanitize_name(name):
    """Substitui caracteres inválidos de nomes por sublinhados para segurança do arquivo."""
    if not name:
        return "unknown"
    # Remove qualquer caractere que não seja alfanumérico, hífen ou sublinhado
    sanitized = re.sub(r'[^a-zA-Z0-9_\-]', '_', name)
    # Remove repetições de sublinhados e limpa as pontas
    sanitized = re.sub(r'_+', '_', sanitized).strip('_')
    return sanitized or "unknown"

def _buscar_arquivo_existente(guild_id, userid):
    """Procura na pasta se existe um arquivo que termine com o ID do servidor e do usuário."""
    g_id = guild_id if guild_id else "dm"
    # Padrão de busca: memoria_*_IDSERVIDOR_*_IDUSUARIO.txt
    pattern = os.path.join(MEMORIES_DIR, f"memoria_*_{g_id}_*_{userid}.txt")
    arquivos = glob.glob(pattern)
    if arquivos:
        return arquivos[0]
    return None

def _obter_caminho_alvo(guild_id, guild_name, userid, user_name):
    """Gera o caminho ideal com os nomes e IDs atuais."""
    g_id = guild_id if guild_id else "dm"
    g_name = sanitize_name(guild_name) if guild_id else "DM"
    u_name = sanitize_name(user_name)
    return os.path.join(MEMORIES_DIR, f"memoria_{g_name}_{g_id}_{u_name}_{userid}.txt")

def trim_incomplete_sentences(texto):
    """
    Remove apenas uma frase final que pareça cortada no meio (resposta truncada).
    Preserva quebras de linha/Markdown e nunca remove links, listas ou finais
    como ')', '**' ou emojis, que não indicam truncamento.
    """
    if not texto:
        return ""
    texto = texto.strip()
    if texto.endswith((".", "!", "?")):
        return texto

    ultima_linha = texto.splitlines()[-1].strip()
    # Itens de lista, títulos, citações e tabelas normalmente não terminam com pontuação
    if ultima_linha.startswith(("-", "*", "+", "#", ">", "|")) or re.match(r'\d+[.)]\s', ultima_linha):
        return texto
    # Só consideramos "cortado" se terminar em letra/número/vírgula etc. e não for um link
    if re.search(r'https?://', ultima_linha) or not re.search(r'[\w,;:\-]$', texto):
        return texto

    # Corta logo após o último fim de frase, mantendo a formatação original
    fins = list(re.finditer(r'[.!?](?=\s)', texto))
    if not fins:
        return texto

    return texto[:fins[-1].end()].rstrip()

def criar_resumo(memorias: str) -> str:
    """Condensa o histórico em um resumo no idioma ativo (temperatura baixa: só fatos, sem invenções)."""
    try:
        resumo_texto = au.ask_ai(
            contents=carregar_prompt("memoria_resumo_usuario", memorias=memorias),
            system_instruction=carregar_prompt("memoria_resumo_sistema"),
            temperature=0.3,
            use_world_context=False,
        )
        return trim_incomplete_sentences(resumo_texto) if resumo_texto else ""
    except Exception as e:
        print(t("memoria.erro_resumo", tipo=type(e).__name__, erro=e))
        return ""

def carregar_memorias(guild_id, guild_name, userid, user_name):
    """
    Busca o arquivo de memórias. Se encontrar um correspondente por ID, mas com nomes antigos,
    o arquivo é renomeado automaticamente para os nomes atualizados.
    """
    arquivo_existente = _buscar_arquivo_existente(guild_id, userid)
    caminho_ideal = _obter_caminho_alvo(guild_id, guild_name, userid, user_name)
    
    if arquivo_existente:
        # Se o arquivo físico encontrado tem um nome diferente do ideal (servidor/user mudou de nome)
        if os.path.abspath(arquivo_existente) != os.path.abspath(caminho_ideal):
            try:
                os.rename(arquivo_existente, caminho_ideal)
                print(t("memoria.renomeando", antigo=arquivo_existente, novo=caminho_ideal))
            except OSError:
                pass
            arquivo_final = caminho_ideal
        else:
            arquivo_final = arquivo_existente
    else:
        arquivo_final = caminho_ideal

    try:
        with open(arquivo_final, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return ""

def salvar_memoria(guild_id, guild_name, userid, user_name, prompt, resposta):    
    """Salva a interação atual, aplicando a expiração por idade e resumo por token."""
    arquivo_existente = _buscar_arquivo_existente(guild_id, userid)
    caminho_ideal = _obter_caminho_alvo(guild_id, guild_name, userid, user_name)
    
    if arquivo_existente:
        if os.path.abspath(arquivo_existente) != os.path.abspath(caminho_ideal):
            try:
                os.rename(arquivo_existente, caminho_ideal)
            except OSError:
                pass
            arquivo_final = caminho_ideal
        else:
            arquivo_final = arquivo_existente
    else:
        arquivo_final = caminho_ideal

    # Verifica tempo de validade do arquivo (7 dias)
    if os.path.exists(arquivo_final):
        ultima_mod = os.path.getmtime(arquivo_final)
        idade_horas = (time.time() - ultima_mod) / 3600
        if idade_horas > 168:
            print(t("memoria.expirou", nome=user_name, id=userid))
            try:
                os.remove(arquivo_final)
            except OSError:
                pass

    # Registra a nova mensagem
    with open(arquivo_final, "a", encoding="utf-8") as f:
        f.write(f"Prompt Usuário: {prompt}\nResposta: {resposta}\n")

    # Avaliação de tamanho do arquivo
    with open(arquivo_final, "r", encoding="utf-8") as f:
        conteudo = f.read()

    # 'enc' deve ser o seu codificador de tokens configurado previamente (ex: tiktoken)
    tamanho_estimado_tokens = len(conteudo) // 4
    if tamanho_estimado_tokens > 20480:
        print(t("memoria.resumindo", nome=user_name))
        
        # Chamada da função de resumo atualizada
        resumo = criar_resumo(conteudo)
        if resumo:
            with open(arquivo_final, "w", encoding="utf-8") as f:
                f.write(f"Resumo de Memórias: {resumo}\n")
                
def delete_all_memories():
    for arquivo in Path(MEMORIES_DIR).rglob("*"):
        if arquivo.is_file():
            arquivo.unlink()
            print(t("memoria.excluindo", nome=arquivo.name))
    