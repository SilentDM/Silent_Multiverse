"""Integração com o sistema operacional (abrir arquivos/pastas, liberar memória)."""
import os
import subprocess
import sys
import webbrowser
from pathlib import Path
from core.i18n import t


def abrir_no_sistema(caminho):
    """Abre arquivo ou pasta no programa padrão do sistema (Explorer, navegador, visualizador...)."""
    caminho = str(Path(caminho))
    if os.name == "nt":
        os.startfile(caminho)
    elif sys.platform == "darwin":
        subprocess.call(["open", caminho])
    else:
        subprocess.call(["xdg-open", caminho])


def abrir_link(url: str):
    """Abre um endereço da web no navegador padrão."""
    webbrowser.open(url)


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
        print(t("sistema.log_erro_ram", erro=e))


def caminho_icone():
    """icon.ico embutido pelo PyInstaller (_MEIPASS) ou ao lado do programa; None se não existir."""
    candidatos = []
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        candidatos.append(Path(sys._MEIPASS) / "icon.ico")
    import engine.project_utils as pu
    candidatos.append(pu.BASE_DIR / "icon.ico")
    return next((c for c in candidatos if c.exists()), None)


def comando_para_reiniciar() -> list:
    """Comando que abre o programa de novo (o .exe empacotado ou o python com o main.py)."""
    if getattr(sys, "frozen", False):
        return [sys.executable] + sys.argv[1:]
    return [sys.executable] + sys.argv


def abrir_nova_instancia():
    """Abre uma nova cópia do programa (quem chama encerra a atual em seguida)."""
    subprocess.Popen(comando_para_reiniciar(), cwd=os.getcwd())
