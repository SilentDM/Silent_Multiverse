"""
Silent Multiverse Nexus - Ponto de Entrada Principal
"""
import sys, traceback
import core.credentials as se
import engine.project_utils as pu

se.carregar_todas_credenciais()
pu.inicializar_estrutura_silent_data()
pu.instalar_modelos_iniciais()

from ui.app import main as start_gui

def main():
    try:
        start_gui()
    except Exception as e:
        print(f"❌ Erro fatal na execução do aplicativo: {e}")
        print("\n--- DETALHES DO ERRO (TRACEBACK) ---")
        traceback.print_exc()  # <== ISSO VAI MOSTRAR O ARQUIVO E A LINHA EXATA!
        print("------------------------------------\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
    