import tkinter as tk
from tkinter import ttk, simpledialog, scrolledtext, messagebox, filedialog
import threading, os, sys, shutil, subprocess
import engine.persona_engine as pe
import core.ai_image as aimg
from engine.persona_schemas import PersonaRoleplay, persona_para_markdown
from PIL import Image, ImageTk
from pathlib import Path

class RoleplayFrame(ttk.Frame):
    def __init__(self, parent, log_callback, toast_callback, page_header_callback):
        super().__init__(parent)
        self.log_callback = log_callback
        self.toast_callback = toast_callback
        self.current_persona = None

        page_header_callback(self, "Teatro da Mente - Roleplay de Personagens", "Converse diretamente com habitantes, vilões e entidades do seu universo.")

        # PanedWindow dividindo Esquerda (Ficha) e Direita (Chat)
        self.pane = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.pane.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))

        # ==========================================
        # COLUNA DA ESQUERDA: FICHA E SELEÇÃO
        # ==========================================
        self.left_frame = ttk.LabelFrame(self.pane, text=" Persona Ativa ")
        self.pane.add(self.left_frame, weight=1)

        # Barra superior do personagem
        top_bar = ttk.Frame(self.left_frame)
        top_bar.pack(fill=tk.X, padx=10, pady=8)

        self.combo_personas = ttk.Combobox(top_bar, state="readonly", font=("Segoe UI", 10))
        self.combo_personas.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        self.combo_personas.bind("<<ComboboxSelected>>", self._on_persona_selected)

        self.btn_nova_persona = ttk.Button(top_bar, text="➕ Nova Persona", command=self.modal_criar_persona)
        self.btn_nova_persona.pack(side=tk.RIGHT)

        self.portrait_container = tk.Frame(self.left_frame, bg="#18181c")
        self.portrait_container.pack(fill=tk.X, padx=10, pady=(6, 2))

        self.lbl_portrait = tk.Label(self.portrait_container, bg="#18181c", cursor="hand2")
        self.lbl_portrait.pack(anchor="center")

        # 🟢 MENU DE CONTEXTO DO RETRATO
        self.portrait_menu = tk.Menu(self, tearoff=0, bg="#1e1e1e", fg="#e3e3e3", activebackground="#0f766e", activeforeground="white")
        self.portrait_menu.add_command(label="Abrir Imagem no Sistema", command=self.abrir_portrait_no_sistema)
        self.portrait_menu.add_command(label="Salvar Imagem Como...", command=self.salvar_portrait_como)
        self.portrait_menu.add_separator()
        self.portrait_menu.add_command(label="Mostrar na Pasta de Dados", command=self.revelar_portrait_na_pasta)

        # 🟢 BINDINGS DE MOUSE NA IMAGEM
        self.lbl_portrait.bind("<Double-1>", lambda e: self.abrir_portrait_no_sistema())
        self.lbl_portrait.bind("<Button-3>", self._mostrar_menu_portrait)
        self.lbl_portrait.bind("<Button-2>", self._mostrar_menu_portrait)

        self.btn_gerar_portrait = ttk.Button(
            self.left_frame, 
            text="🎨 Gerar Retrato do NPC", 
            command=self.disparar_geracao_portrait
        )
        self.btn_gerar_portrait.pack(fill=tk.X, padx=10, pady=(2, 6))

        # Variáveis de controle da imagem atual
        self._foto_tk = None
        self._caminho_imagem_atual = None
        # Editor de Ficha / Características
        ttk.Label(self.left_frame, text="Características & Mentalidade:", font=("Segoe UI", 8, "bold"), foreground="#888888").pack(anchor=tk.W, padx=10, pady=(4, 2))
        
        self.txt_ficha = scrolledtext.ScrolledText(
            self.left_frame, wrap=tk.WORD, font=("Consolas", 10),
            bg="#18181c", fg="#e3e3e3", insertbackground="white",
            selectbackground="#0f766e", selectforeground="white", bd=0
        )
        self.txt_ficha.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 8))

        # ==========================================
        # COLUNA DA DIREITA: CHAT IN-CHARACTER
        # ==========================================
        self.right_frame = ttk.LabelFrame(self.pane, text=" Diálogo In-Character ")
        self.pane.add(self.right_frame, weight=2)

        # Display do Chat
        self.chat_display = scrolledtext.ScrolledText(
            self.right_frame, wrap=tk.WORD, state=tk.DISABLED, font=("Segoe UI", 10),
            bg="#1e1e1e", fg="#e3e3e3", insertbackground="white",
            selectbackground="#0f766e", selectforeground="white", bd=0
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)
        self.chat_display.tag_config("user", foreground="#60a5fa", font=("Segoe UI", 10, "bold"))
        self.chat_display.tag_config("npc", foreground="#f59e0b", font=("Segoe UI", 10, "bold"))
        self.chat_display.tag_config("system", foreground="#888888", font=("Segoe UI", 9, "italic"))

        # Input e Botão de Envio
        input_box = ttk.Frame(self.right_frame)
        input_box.pack(fill=tk.X, padx=10, pady=(0, 10))

        self.entry_msg = ttk.Entry(input_box, font=("Segoe UI", 10))
        self.entry_msg.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        self.entry_msg.bind("<Return>", lambda e: self.enviar_mensagem())

        self.btn_send = ttk.Button(input_box, text="Falar", command=self.enviar_mensagem)
        self.btn_send.pack(side=tk.RIGHT)

        self.atualizar_dropdown_personas()

    def toast(self, msg):
        if self.toast_callback:
            self.toast_callback(msg)

    def atualizar_dropdown_personas(self, selecionar_nome=None):
        nomes = pe.listar_personas_disponiveis()
        self.combo_personas["values"] = nomes
        if nomes:
            alvo = selecionar_nome if (selecionar_nome and selecionar_nome in nomes) else nomes[0]
            self.combo_personas.set(alvo)
            self._carregar_persona_na_ui(alvo)
        else:
            self.combo_personas.set("")
            self.txt_ficha.delete("1.0", tk.END)
            self.txt_ficha.insert("1.0", "Nenhum personagem criado ainda. Clique em '➕ Nova Persona'!")

    def _on_persona_selected(self, event=None):
        nome = self.combo_personas.get()
        if nome:
            self._carregar_persona_na_ui(nome)

    def _carregar_persona_na_ui(self, nome: str):
        self.current_persona = nome
        dados, historico = pe.carregar_persona(nome)
        
        # 1. Carrega a ficha no ScrolledText da esquerda
        self.txt_ficha.delete("1.0", tk.END)
        if dados:
            try:
                obj = PersonaRoleplay(**dados)
                self.txt_ficha.insert("1.0", persona_para_markdown(obj))
            except Exception:
                self.txt_ficha.insert("1.0", str(dados))

        # 2. Carrega o histórico no chat da direita
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.delete("1.0", tk.END)
        self.chat_display.insert(tk.END, "Narrador: ", "system")
        self.chat_display.insert(tk.END, f"Você está frente a frente com {nome}. Ele observa sua postura.\n\n")

        for h in historico:
            if h["autor"] == "Interlocutor":
                self.chat_display.insert(tk.END, "Você: ", "user")
            else:
                self.chat_display.insert(tk.END, f"{nome}: ", "npc")
            self.chat_display.insert(tk.END, f"{h['texto']}\n\n")

        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)
        caminho_salvo = dados.get("portrait_path")
        self._atualizar_foto_portrait(caminho_salvo)

    def modal_criar_persona(self):
        nome = simpledialog.askstring("Nova Persona", "Nome do Personagem ou Entidade:", parent=self)
        if not nome or not nome.strip():
            return
        
        descricao = simpledialog.askstring(
            "Diretrizes da Persona",
            f"Descreva o papel, motivação ou mistério de {nome}:\n(A IA usará o contexto do mundo para deduzir o restante):",
            parent=self
        )
        if descricao is None:
            return

        self.toast(f"🔮 Forjando a mente de {nome} com o bundle do mundo...")
        self.log_callback(f"Iniciando forja de persona para: {nome}")

        def _worker():
            try:
                nome_salvo = pe.forjar_nova_persona(nome.strip(), descricao.strip())
                self.log_callback(f"✅ Persona {nome_salvo} forjada com sucesso!")
                self.toast(f"🎭 Persona {nome_salvo} pronta para conversar!")
                self.after(0, lambda: self.atualizar_dropdown_personas(selecionar_nome=nome_salvo))
            except Exception as e:
                self.log_callback(f"❌ Erro ao criar persona: {e}")
                self.toast("Erro ao forjar personagem.")

        threading.Thread(target=_worker, daemon=True).start()

    def enviar_mensagem(self):
        if not self.current_persona:
            self.toast("⚠️ Selecione ou crie um personagem primeiro!")
            return

        msg = self.entry_msg.get().strip()
        if not msg:
            return

        self.entry_msg.delete(0, tk.END)

        # Mostra a mensagem do usuário na hora
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, "Você: ", "user")
        self.chat_display.insert(tk.END, f"{msg}\n\n")
        self.chat_display.insert(tk.END, f"{self.current_persona}: ", "npc")
        self.chat_display.insert(tk.END, "...\n\n", "system")
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)

        persona_alvo = self.current_persona

        def _worker():
            try:
                resposta = pe.dialogar_com_persona(persona_alvo, msg)
                def _atualizar():
                    self.chat_display.config(state=tk.NORMAL)
                    # Apaga o "..."
                    self.chat_display.delete("end-3l", "end")
                    self.chat_display.insert(tk.END, f"{persona_alvo}: ", "npc")
                    self.chat_display.insert(tk.END, f"{resposta}\n\n")
                    self.chat_display.see(tk.END)
                    self.chat_display.config(state=tk.DISABLED)
                self.after(0, _atualizar)
            except Exception as e:
                self.log_callback(f"Erro no diálogo de roleplay: {e}")

        threading.Thread(target=_worker, daemon=True).start()

    def _atualizar_foto_portrait(self, caminho_img):
        """Carrega e exibe o retrato na coluna esquerda."""
        if caminho_img and Path(caminho_img).exists():
            try:
                self._caminho_imagem_atual = Path(caminho_img).resolve()
                pil_img = Image.open(self._caminho_imagem_atual)
                pil_img = pil_img.resize((150, 150), Image.Resampling.LANCZOS)
                self._foto_tk = ImageTk.PhotoImage(pil_img)
                
                self.lbl_portrait.config(image=self._foto_tk)
                self.lbl_portrait.pack(anchor="center", pady=(4, 6))
                self.btn_gerar_portrait.config(text="🔄 Recriar Retrato")
                return
            except Exception as e:
                print(f"Erro ao carregar portrait: {e}")

        # Se não há imagem válida
        self._caminho_imagem_atual = None
        self._foto_tk = None
        self.lbl_portrait.config(image="")
        self.lbl_portrait.pack_forget()
        self.btn_gerar_portrait.config(text="🎨 Gerar Retrato do NPC")

    def _mostrar_menu_portrait(self, event):
        """Exibe o menu de contexto do botão direito sobre a foto."""
        if self._caminho_imagem_atual and Path(self._caminho_imagem_atual).exists():
            self.portrait_menu.post(event.x_root, event.y_root)

    def abrir_portrait_no_sistema(self):
        """Abre o arquivo da imagem no visualizador nativo de fotos do Windows."""
        if not self._caminho_imagem_atual or not Path(self._caminho_imagem_atual).exists():
            return
        
        caminho_str = os.path.normpath(str(self._caminho_imagem_atual))
        try:
            if os.name == 'nt':
                os.startfile(caminho_str)
            elif sys.platform == 'darwin':
                subprocess.call(('open', caminho_str))
            else:
                subprocess.call(('xdg-open', caminho_str))
            self.toast("🔍 Abrindo retrato no visualizador do sistema...")
        except Exception as e:
            self.log_callback(f"Erro ao abrir imagem: {e}")

    def salvar_portrait_como(self):
        """Permite que o usuário exporte e salve o retrato em qualquer pasta do computador."""
        if not self._caminho_imagem_atual or not Path(self._caminho_imagem_atual).exists():
            return

        nome_sugerido = f"portrait_{self.current_persona.replace(' ', '_').lower()}.png" if self.current_persona else "portrait.png"
        
        destino = filedialog.asksaveasfilename(
            title="Salvar Retrato do NPC Como...",
            initialfile=nome_sugerido,
            defaultextension=".png",
            filetypes=[("Imagem PNG", "*.png"), ("Todos os Arquivos", "*.*")],
            parent=self
        )

        if destino:
            try:
                shutil.copy2(str(self._caminho_imagem_atual), destino)
                self.toast(f"💾 Retrato exportado com sucesso!")
                self.log_callback(f"Retrato de {self.current_persona} salvo em: {destino}")
            except Exception as e:
                messagebox.showerror("Erro ao Salvar", f"Falha ao exportar imagem: {e}", parent=self)

    def revelar_portrait_na_pasta(self):
        """Abre a pasta .nexus_data/images selecionando o arquivo no Windows Explorer."""
        if not self._caminho_imagem_atual or not Path(self._caminho_imagem_atual).exists():
            return
            
        caminho_str = os.path.normpath(str(self._caminho_imagem_atual))
        try:
            if os.name == 'nt':
                subprocess.run(['explorer', '/select,', caminho_str])
            elif sys.platform == 'darwin':
                subprocess.call(['open', '-R', caminho_str])
            else:
                pasta = os.path.dirname(caminho_str)
                subprocess.call(['xdg-open', pasta])
            self.toast("📂 Revelando imagem na pasta de dados...")
        except Exception as e:
            self.log_callback(f"Erro ao revelar imagem no Explorer: {e}")

    def disparar_geracao_portrait(self):
        if not self.current_persona:
            self.toast("⚠️ Selecione ou crie um personagem primeiro!")
            return

        dados, historico = pe.carregar_persona(self.current_persona)
        nome_npc = dados.get("nome", self.current_persona)

        self.toast(f"🎨 Gerando retrato para '{nome_npc}'...")
        self.btn_gerar_portrait.config(state=tk.DISABLED)

        def _worker():
            try:
                # 🟢 Passa o dicionário completo com os atributos físicos e o prompt_visual_ingles
                caminho = aimg.gerar_portrait_persona(nome_npc, dados)
                if caminho:
                    dados["portrait_path"] = str(caminho)
                    pe.salvar_persona(self.current_persona, dados, historico)
                    self.after(0, lambda: self._atualizar_foto_portrait(caminho))
                    self.toast(f"🖼️ Retrato de '{nome_npc}' concluído!")
                else:
                    self.toast("⚠️ Não foi possível gerar a imagem no momento.")
            finally:
                self.after(0, lambda: self.btn_gerar_portrait.config(state=tk.NORMAL))

        threading.Thread(target=_worker, daemon=True).start()