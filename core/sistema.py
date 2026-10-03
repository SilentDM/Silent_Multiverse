"""Integração com o sistema operacional (abrir arquivos/pastas, liberar memória)."""
import os
import subprocess
import sys
from pathlib import Path


def abrir_no_sistema(caminho):
    """Abre arquivo ou pasta no programa padrão do sistema (Explorer, navegador, visualizador...)."""
    caminho = str(Path(caminho))
    if os.name == "nt":
        os.startfile(caminho)
    elif sys.platform == "darwin":
        subprocess.call(["open", caminho])
    else:
        subprocess.call(["xdg-open", caminho])


def revelar_no_explorer(caminho):
    """Abre o gerenciador de arquivos com o item selecionado (ou a pasta, se for diretório)."""
    caminho = os.path.normpath(str(caminho))
    if os.name == "nt":
        if os.path.isfile(caminho):
            subprocess.run(["explorer", "/select,", caminho])
        else:
            os.startfile(caminho)
    elif sys.platform == "darwin":
        subprocess.call(["open", "-R", caminho] if os.path.isfile(caminho) else ["open", caminho])
    else:
        subprocess.call(["xdg-open", os.path.dirname(caminho) if os.path.isfile(caminho) else caminho])


def liberar_memoria():
    """No Windows, pede ao sistema para devolver a memória de trabalho inativa do processo."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        handle = ctypes.windll.kernel32.GetCurrentProcess()
        ctypes.windll.psapi.EmptyWorkingSet(handle)
    except Exception as e:
        print(f"Erro ao otimizar RAM: {e}")
