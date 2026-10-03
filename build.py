"""
Gera o executável do Silent Multiverse Nexus e o pacote .zip da release.

Uso (com o venv ativo e requirements-build.txt instalado):
    python build.py               -> dist/SilentMultiverse.exe + dist/SilentMultiverse-<versão>-windows.zip
    python build.py --tag v2.0.0  -> também confere se a tag bate com core/versao.py (usado no GitHub Actions)

Inclui no executável: locale/ (textos, prompts e os modelos iniciais de Templates/Style
de cada idioma, copiados para a .silent_data no primeiro uso) e icon.ico.
"""
import argparse
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
DIST = RAIZ / "dist"
NOME = "SilentMultiverse"


def versao_do_codigo() -> str:
    texto = (RAIZ / "core" / "versao.py").read_text(encoding="utf-8")
    return re.search(r'VERSAO\s*=\s*"([^"]+)"', texto).group(1)


def conferir_tag(tag: str, versao: str):
    if tag.lstrip("vV") != versao:
        sys.exit(f"A tag '{tag}' não bate com VERSAO = \"{versao}\" em core/versao.py. Atualize um dos dois.")


def dados_embutidos() -> list:
    # locale/ já traz os modelos iniciais (locale/<idioma>/modelos/Templates e Style)
    return [("locale", "locale"), ("icon.ico", ".")]


def gerar_executavel():
    comando = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onefile", "--windowed",
               "--name", NOME, "--icon", str(RAIZ / "icon.ico"),
               "--hidden-import", "keyring.backends.Windows",
               "--collect-all", "tkinterweb"]
    for origem, destino in dados_embutidos():
        comando += ["--add-data", f"{RAIZ / origem}{';' if sys.platform == 'win32' else ':'}{destino}"]
    comando.append(str(RAIZ / "main.py"))
    subprocess.run(comando, cwd=RAIZ, check=True)


def empacotar(versao: str) -> Path:
    exe = DIST / f"{NOME}.exe"
    pacote = DIST / f"{NOME}-{versao}-windows.zip"
    with zipfile.ZipFile(pacote, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(exe, exe.name)
        for extra in ("LICENSE", "README.md", "README.pt-BR.md"):
            if (RAIZ / extra).exists():
                z.write(RAIZ / extra, extra)
    return pacote


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--tag", help="tag da release (ex.: v2.0.0), conferida contra core/versao.py")
    args = parser.parse_args()

    versao = versao_do_codigo()
    if args.tag:
        conferir_tag(args.tag, versao)
    for pasta in (DIST, RAIZ / "build"):
        shutil.rmtree(pasta, ignore_errors=True)

    print(f"Gerando {NOME} {versao}...")
    gerar_executavel()
    pacote = empacotar(versao)
    print(f"\nPronto: {DIST / (NOME + '.exe')}\nPacote: {pacote}")


if __name__ == "__main__":
    main()
