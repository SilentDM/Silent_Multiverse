# ui/setup_env.py
import os, sys
from pathlib import Path
import keyring
from keyring.errors import KeyringError, PasswordDeleteError

# 🛡️ Garante o backend nativo do Windows quando rodar congelado pelo PyInstaller
if sys.platform == "win32":
    try:
        import keyring.backends.Windows
        keyring.set_keyring(keyring.backends.Windows.WinVaultKeyring())
    except Exception as e:
        print(f"Aviso ao inicializar WinVaultKeyring: {e}")

SERVICO_NOME = "SilentMultiverseNexus"

CHAVES_SENSIVEIS = [
    "GOOGLE_API_KEY",
    "CLAUDE_TOKEN",
    "PRO_API_KEY",
    "DISCORD_TOKEN",
    "MESTRE_DISCORD_ID",
    "AI_PROVIDER"
]

def obter_credencial(nome_chave: str, valor_padrao: str = "") -> str:
    """
    Busca a credencial com a seguinte prioridade:
    1. os.environ (se já foi carregada na memória)
    2. Cofre nativo do Windows (keyring)
    3. Fallback: Arquivo .env antigo (se existir, migra e deleta)
    """
    # 1. Se já está na memória do processo
    val_env = os.environ.get(nome_chave)
    if val_env and str(val_env).strip():
        return str(val_env).strip()

    # 2. Busca no cofre do sistema operacional
    try:
        val_cofre = keyring.get_password(SERVICO_NOME, nome_chave)
        if val_cofre and str(val_cofre).strip():
            val_limpo = str(val_cofre).strip()
            os.environ[nome_chave] = val_limpo
            return val_limpo
    except Exception as e:
        print(f"Erro ao ler {nome_chave} do cofre: {e}")

    # 3. Fallback de migração suave caso ainda exista um .env antigo na pasta
    base_dir = Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent.parent
    env_antigo = base_dir / ".env"
    if env_antigo.exists():
        try:
            with open(env_antigo, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        if k.strip() == nome_chave and v.strip():
                            val_str = v.strip()
                            salvar_credencial(nome_chave, val_str)
                            return val_str
        except Exception:
            pass

    return valor_padrao

def salvar_credencial(nome_chave: str, valor: str):
    """Grava diretamente no cofre seguro do Windows e atualiza a memória ativa."""
    if not valor or not str(valor).strip():
        remover_credencial(nome_chave)
        return

    valor_limpo = str(valor).strip()
    try:
        keyring.set_password(SERVICO_NOME, nome_chave, valor_limpo)
        os.environ[nome_chave] = valor_limpo
    except KeyringError as e:
        print(f"Erro ao salvar {nome_chave} no cofre do Windows: {e}")
        os.environ[nome_chave] = valor_limpo

def remover_credencial(nome_chave: str):
    """Remove a credencial do cofre do Windows e do os.environ."""
    try:
        keyring.delete_password(SERVICO_NOME, nome_chave)
    except Exception:
        pass
    os.environ.pop(nome_chave, None)

def carregar_todas_credenciais():
    """Injeta todas as chaves do cofre do Windows no ambiente ativo do Python."""
    for chave in CHAVES_SENSIVEIS:
        val = obter_credencial(chave)
        if val:
            os.environ[chave] = val

def atualizar_credenciais_em_lote(novos_valores: dict):
    """Recebe um dicionário com novas credenciais e persiste todas no cofre."""
    for k, v in novos_valores.items():
        if v is not None:
            salvar_credencial(k, str(v))