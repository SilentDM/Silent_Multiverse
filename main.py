"""
Silent Multiverse Nexus - Ponto de Entrada Principal
"""
import sys
import ui.setup_env as se
import engine.project_utils as pu

se.carregar_todas_credenciais()
pu.inicializar_estrutura_silent_data()
pu.sincronizar_templates_e_estilo_iniciais()

from ui.gui import main as start_gui

def main():
    try:
        start_gui()
    except Exception as e:
        print(f"❌ Erro fatal na execução do aplicativo: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
    