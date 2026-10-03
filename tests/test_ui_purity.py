"""A interface (ui/) deve ser só visual: nada de arquivos, regex, JSON, threads, SO ou IA."""
import ast
import unittest
from pathlib import Path

from tests import RAIZ_REPO

MODULOS_PROIBIDOS = {"os", "re", "json", "shutil", "threading", "subprocess", "glob", "asyncio", "keyring"}
PREFIXOS_PROIBIDOS = ("core.ai_", "core.cache_gemini", "core.credentials")
CHAMADAS_PROIBIDAS = {"open", "ask_ai", "exec", "eval"}


class TestePurezaDaInterface(unittest.TestCase):
    def test_ui_sem_logica(self):
        problemas = []
        for arquivo in sorted((RAIZ_REPO / "ui").rglob("*.py")):
            arvore = ast.parse(arquivo.read_text(encoding="utf-8"))
            for no in ast.walk(arvore):
                modulos = []
                if isinstance(no, ast.Import):
                    modulos = [a.name for a in no.names]
                elif isinstance(no, ast.ImportFrom) and no.module:
                    modulos = [no.module]
                for modulo in modulos:
                    if modulo.split(".")[0] in MODULOS_PROIBIDOS or modulo.startswith(PREFIXOS_PROIBIDOS):
                        problemas.append(f"{arquivo.relative_to(RAIZ_REPO)}:{no.lineno} importa {modulo}")
                if isinstance(no, ast.Call):
                    nome = no.func.id if isinstance(no.func, ast.Name) else getattr(no.func, "attr", None)
                    # Image.open (PIL, só para exibir imagens) é permitido
                    eh_pil = isinstance(no.func, ast.Attribute) and getattr(no.func.value, "id", "") == "Image"
                    if nome in CHAMADAS_PROIBIDAS and not eh_pil:
                        problemas.append(f"{arquivo.relative_to(RAIZ_REPO)}:{no.lineno} chama {nome}()")
        self.assertEqual(problemas, [], "Lógica encontrada na interface:\n" + "\n".join(problemas))

    def test_ui_nao_e_importada_pela_logica(self):
        """engine/, core/ e bot/ nunca dependem da interface."""
        problemas = []
        for pasta in ("engine", "core", "bot"):
            for arquivo in (RAIZ_REPO / pasta).rglob("*.py"):
                texto = arquivo.read_text(encoding="utf-8")
                if "import ui." in texto or "from ui" in texto:
                    problemas.append(str(arquivo.relative_to(RAIZ_REPO)))
        self.assertEqual(problemas, [])


if __name__ == "__main__":
    unittest.main()
