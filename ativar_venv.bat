@echo off
rem Abre um terminal ja com o venv do projeto ativado.
rem Uso: de dois cliques neste arquivo, ou digite "ativar_venv" no terminal dentro desta pasta.
rem Procura a pasta "venv" aqui e nas pastas acima (funciona tambem dentro de worktrees).
rem Para sair do venv depois, digite: deactivate

setlocal
set "PASTA=%~dp0"

:procurar
if exist "%PASTA%venv\Scripts\activate.bat" goto achou
for %%I in ("%PASTA%..") do set "ACIMA=%%~fI\"
if /i "%ACIMA%"=="%PASTA%" goto nao_achou
set "PASTA=%ACIMA%"
goto procurar

:nao_achou
echo Venv nao encontrado nesta pasta nem nas pastas acima.
echo Crie um com: python -m venv venv
pause
exit /b 1

:achou
cd /d "%~dp0"
endlocal & cmd /k ""%PASTA%venv\Scripts\activate.bat" && echo Venv ativado (%PASTA%venv). Rode: python main.py"
