"""
Testes automáticos do Silent Multiverse Nexus.

Rodar (na pasta do projeto, com o venv):
    venv\\Scripts\\python.exe -m unittest discover -s tests -v

Tudo roda isolado: dados em uma pasta temporária (SILENT_DATA_DIR) e projetos
de exemplo temporários. Nenhuma chamada real de IA ou Discord é feita.
"""
import os
import sys
import tempfile
from pathlib import Path

RAIZ_REPO = Path(__file__).resolve().parent.parent
if str(RAIZ_REPO) not in sys.path:
    sys.path.insert(0, str(RAIZ_REPO))

# Precisa acontecer ANTES de qualquer import de engine/core (que cria .silent_data)
_TEMP = Path(tempfile.mkdtemp(prefix="silent_tests_"))
os.environ["SILENT_DATA_DIR"] = str(_TEMP / "dados")
os.environ["PASTA_PROJETO"] = str(_TEMP / "projeto_inicial")
for _chave in ("GOOGLE_API_KEY", "CLAUDE_TOKEN", "PRO_API_KEY", "DISCORD_TOKEN", "MESTRE_DISCORD_ID", "AI_PROVIDER"):
    os.environ.pop(_chave, None)

PASTA_TEMP = _TEMP
