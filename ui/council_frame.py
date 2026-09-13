import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
from pathlib import Path
import engine.council_engine as ce
import engine.expander as ex

class CouncilFrame(ttk.Frame):
    def __init__(self, parent, log_callback, toast_callback, page_header_callback, on_consolidation_finished=None):
        super().__init__(parent)
        self.log_callback = log_callback
        self.toast_callback = toast_callback
        self.on_consolidation_finished = on_consolidation_finished
        
        self.caminho_arquivo_ativo = None
        self.deliberando = False

        page_header_callback(
            self, 
            "Conselho de Criação & Consolidação", 
            "Delibere sobre qualquer arquivo com múltiplos agentes especializados antes de gravar o resultado canônico."
        )

        # ==========================================
        # BARRA DE CONTROLE SUPERIOR
        # ==========================================
        control_box = ttk.LabelFrame(self, text=" Controle de Consolidação do Arquivo ")
        control_box.pack(fill=tk.X, padx=15, pady=(0, 10))

        # Linha 1: Arquivo e Diretriz
        row1 = ttk.Frame(control_box)
        row1.pack(fill=tk.X, padx=10, pady=6)

        ttk.Label(row1, text="Arquivo Alvo:", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(0, 4))
        self.lbl_target_file = ttk.Label(row1, text="Nenhum arquivo selecionado", font=("Segoe UI", 9, "bold"), foreground="#10b981")
        self.lbl_target_file.pack(side=tk.LEFT, padx=(0, 15))

        ttk.Label(row1, text="Diretriz / Foco do Mestre:").pack(side=tk.LEFT, padx=(0, 4))
        self.entry_diretriz = ttk.Entry(row1, font=("Segoe UI", 10))
        self.entry_diretriz.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        # Linha 2: Botões dos 2 Passos
        row2 = ttk.Frame(control_box)
        row2.pack(fill=tk.X, padx=10, pady=(0, 8))

        self.btn_fase1 = ttk.Button(
            row2, 
            text="▶️ 1. Iniciar Deliberação (Ouvir Especialistas & NPCs)", 
            command=self.iniciar_deliberacao_fase1
        )
        self.btn_fase1.pack(side=tk.LEFT, padx=(0, 10))

        self.btn_fase2 = ttk.Button(
            row2, 
            text="⚖️ 2. Sintetizar & Consolidar no Arquivo Final", 
            command=self.sintetizar_fase2,
            state=tk.DISABLED
        )
        self.btn_fase2.pack(side=tk.LEFT)

        self.lbl_status = ttk.Label(row2, text="Pronto para iniciar.", font=("Segoe UI", 9, "italic"), foreground="#888888")
        self.lbl_status.pack(side=tk.RIGHT)

        # ==========================================
        # GRID DOS 4 PAINÉIS VISUAIS (2x2)
        # ==========================================
        self.grid_container = ttk.Frame(self)
        self.grid_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))
        self.grid_container.columnconfigure(0, weight=1)
        self.grid_container.columnconfigure(1, weight=1)
        self.grid_container.rowconfigure(0, weight=1)
        self.grid_container.rowconfigure(1, weight=1)

        # Painel 1: O Arquiteto
        p1_box = ttk.LabelFrame(self.grid_container, text=" 📐 Painel 1: O Arquiteto (Proposta de Expansão) ")
        p1_box.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        self.txt_p1 = scrolledtext.ScrolledText(p1_box, wrap=tk.WORD, font=("Consolas", 9), bg="#18181c", fg="#e3e3e3", insertbackground="white", bd=0)
        self.txt_p1.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        # Painel 2: O Cronista
        p2_box = ttk.LabelFrame(self.grid_container, text=" 📜 Painel 2: O Cronista (Auditoria de Fatos & Continuidade) ")
        p2_box.grid(row=0, column=1, sticky="nsew", padx=4, pady=4)
        self.txt_p2 = scrolledtext.ScrolledText(p2_box, wrap=tk.WORD, font=("Consolas", 9), bg="#18181c", fg="#e3e3e3", insertbackground="white", bd=0)
        self.txt_p2.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        # Painel 3: Voz dos NPCs
        p3_box = ttk.LabelFrame(self.grid_container, text=" 🎭 Painel 3: A Voz dos NPCs e Habitantes (1ª Pessoa) ")
        p3_box.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)
        self.txt_p3 = scrolledtext.ScrolledText(p3_box, wrap=tk.WORD, font=("Consolas", 9), bg="#18181c", fg="#f59e0b", insertbackground="white", bd=0)
        self.txt_p3.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        # Painel 4: Tático & Caos
        p4_box = ttk.LabelFrame(self.grid_container, text=" 🎲 Painel 4: Tático & Caos (Mecânicas D&D + Dilemas) ")
        p4_box.grid(row=1, column=1, sticky="nsew", padx=4, pady=4)
        self.txt_p4 = scrolledtext.ScrolledText(p4_box, wrap=tk.WORD, font=("Consolas", 9), bg="#18181c", fg="#38bdf8", insertbackground="white", bd=0)
        self.txt_p4.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

    def carregar_arquivo_para_conselho(self, caminho_arquivo: str):
        """Chamado pelo Explorer ao clicar com botão direito."""
        self.caminho_arquivo_ativo = Path(caminho_arquivo)
        nome = self.caminho_arquivo_ativo.name
        self.lbl_target_file.config(text=nome)
        
        # Sugestão de diretriz padrão
        self.entry_diretriz.delete(0, tk.END)
        self.entry_diretriz.insert(0, f"Aprofundar a intriga, detalhes operacionais e reações dos personagens de {nome}.")

        # Limpa os 4 painéis
        for txt in [self.txt_p1, self.txt_p2, self.txt_p3, self.txt_p4]:
            txt.delete("1.0", tk.END)

        self.btn_fase2.config(state=tk.DISABLED)
        self.lbl_status.config(text="Arquivo carregado. Clique no Botão 1 para ouvir os especialistas.", foreground="#e3e3e3")

    def iniciar_deliberacao_fase1(self):
        if not self.caminho_arquivo_ativo or not self.caminho_arquivo_ativo.is_file():
            self.toast_callback("⚠️ Selecione um arquivo válido primeiro!")
            return

        if self.deliberando:
            return

        diretriz = self.entry_diretriz.get().strip() or "Expandir e aprofundar o documento."
        self.deliberando = True
        self.btn_fase1.config(state=tk.DISABLED)
        self.btn_fase2.config(state=tk.DISABLED)
        self.lbl_status.config(text="⏳ Convocando especialistas e ouvindo os NPCs...", foreground="#60a5fa")
        self.toast_callback("🏛️ O Conselho iniciou a deliberação dos 4 painéis...")

        # Feedback visual nos painéis
        for txt in [self.txt_p1, self.txt_p2, self.txt_p3, self.txt_p4]:
            txt.delete("1.0", tk.END)
            txt.insert("1.0", "⏳ Consultando a IA...")

        def _worker():
            try:
                resultados = ce.executar_deliberacao_paineis(self.caminho_arquivo_ativo, diretriz)

                def _atualizar():
                    self.txt_p1.delete("1.0", tk.END)
                    self.txt_p1.insert("1.0", resultados["arquiteto"])

                    self.txt_p2.delete("1.0", tk.END)
                    self.txt_p2.insert("1.0", resultados["cronista"])

                    self.txt_p3.delete("1.0", tk.END)
                    self.txt_p3.insert("1.0", resultados["npcs"])

                    self.txt_p4.delete("1.0", tk.END)
                    self.txt_p4.insert("1.0", resultados["tatico_caos"])

                    self.btn_fase1.config(state=tk.NORMAL)
                    self.btn_fase2.config(state=tk.NORMAL)
                    self.lbl_status.config(text="✅ Painéis deliberados! Revise/edite os textos e clique no Botão 2.", foreground="#10b981")
                    self.toast_callback("✅ Especialistas concluíram! Você pode editar os painéis.")

                self.after(0, _atualizar)
            except Exception as e:
                self.log_callback(f"Erro na deliberação da Fase 1: {e}")
                self.after(0, lambda: self.lbl_status.config(text="❌ Erro na deliberação.", foreground="#ef4444"))
                self.after(0, lambda: self.btn_fase1.config(state=tk.NORMAL))
            finally:
                self.deliberando = False

        threading.Thread(target=_worker, daemon=True).start()

    def sintetizar_fase2(self):
        if not self.caminho_arquivo_ativo:
            return

        # Coleta o texto atual dos 4 painéis (incluindo edições manuais feitas pelo usuário!)
        t1 = self.txt_p1.get("1.0", tk.END).strip()
        t2 = self.txt_p2.get("1.0", tk.END).strip()
        t3 = self.txt_p3.get("1.0", tk.END).strip()
        t4 = self.txt_p4.get("1.0", tk.END).strip()
        diretriz = self.entry_diretriz.get().strip()

        self.btn_fase1.config(state=tk.DISABLED)
        self.btn_fase2.config(state=tk.DISABLED)
        self.lbl_status.config(text="⚖️ O Juiz Supremo está consolidando o documento final...", foreground="#f59e0b")
        self.toast_callback("⚖️ Juiz Supremo gerando versão canônica...")

        def _worker():
            try:
                sucesso = ce.sintetizar_e_salvar_arquivo_canonica(
                    self.caminho_arquivo_ativo,
                    texto_arquiteto=t1,
                    texto_cronista=t2,
                    texto_npcs=t3,
                    texto_tatico_caos=t4,
                    diretriz_original=diretriz
                )
                if sucesso:
                    self.toast_callback(f"🏆 '{self.caminho_arquivo_ativo.name}' consolidado e salvo com sucesso!")
                    self.log_callback(f"Conselho finalizou consolidação canônica em: {self.caminho_arquivo_ativo.name}")
                    def _concluir():
                        self.lbl_status.config(text="🏆 Documento canônico salvo e versão arquivada no histórico!", foreground="#10b981")
                        self.btn_fase1.config(state=tk.NORMAL)
                        self.btn_fase2.config(state=tk.NORMAL)
                        if self.on_consolidation_finished:
                            self.on_consolidation_finished(self.caminho_arquivo_ativo)
                    self.after(0, _concluir)
                else:
                    self.toast_callback("❌ Erro ao consolidar documento final.")
            except Exception as e:
                self.log_callback(f"Erro na síntese do Juiz: {e}")
                self.after(0, lambda: self.btn_fase1.config(state=tk.NORMAL))
                self.after(0, lambda: self.btn_fase2.config(state=tk.NORMAL))

        threading.Thread(target=_worker, daemon=True).start()