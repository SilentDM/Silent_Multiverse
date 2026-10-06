"""Monta a janela real (sem Discord, bandeja ou rede) e percorre as páginas nos dois idiomas."""
import time
import unittest
from unittest import mock

from tests.util import novo_projeto, apagar, usar_idioma

import engine.editor_session as es
import engine.expander as ex

try:
    import tkinter as tk
    _raiz_teste = tk.Tk()
    _raiz_teste.destroy()
    TEM_TELA = True
except Exception:
    TEM_TELA = False


def fechar(root):
    """Cancela os timers pendentes (toasts, autosave) antes de fechar: senão eles disparam na janela do próximo teste."""
    try:
        for timer in root.tk.splitlist(root.tk.call("after", "info")):
            root.tk.call("after", "cancel", timer)
    except Exception:
        pass
    import core.eventos as ev
    ev.cancelar_inscricoes()      # as páginas fechadas não devem receber eventos do próximo teste
    root.destroy()


@unittest.skipUnless(TEM_TELA, "sem ambiente gráfico")
class TesteInterface(unittest.TestCase):
    def setUp(self):
        self.raiz_projeto = novo_projeto({"Valia.md": "# Valia\ntexto"})
        self.patches = [mock.patch("bot.runner.iniciar"), mock.patch("bot.runner.parar"),
                        mock.patch("core.modelos_gemini.atualizar_se_necessario"),
                        mock.patch("core.atualizacoes.verificar_na_inicializacao"),
                        mock.patch("ui.app.SilentApp._iniciar_bandeja")]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        apagar(self.raiz_projeto)
        usar_idioma("pt_br")

    def _montar(self, idioma):
        import ui.app as app
        usar_idioma(idioma)
        root = tk.Tk()
        root.withdraw()
        janela = app.SilentApp(root)
        root.update()
        return root, janela

    def test_todas_as_paginas_nos_dois_idiomas(self):
        import ui.app as app
        for idioma, palavra in (("pt_br", "Ações"), ("en_us", "Actions")):
            with self.subTest(idioma=idioma):
                root, janela = self._montar(idioma)
                try:
                    for chave in app.CLASSES_PAGINAS:
                        janela.mostrar_pagina(chave)
                        root.update()
                        self.assertEqual(janela.pagina_atual, chave)
                    self.assertEqual(janela.botoes_nav["actions"].cget("text").strip().split()[-1], palavra)
                finally:
                    fechar(root)

    def test_menu_requisicao_e_barra_de_tarefas(self):
        import core.eventos as ev
        root, janela = self._montar("pt_br")
        try:
            sub = janela.botoes_nav["requisicoes"]
            self.assertEqual(sub.winfo_manager(), "")                         # sem pedido aberto: sem sub-item
            janela.abrir_requisicao("melhorar", str(self.raiz_projeto / "Valia.md"))
            root.update()
            self.assertEqual(sub.winfo_manager(), "pack")
            self.assertIn("Valia", sub.cget("text"))
            self.assertEqual(sub.cget("style"), "NavSubActive.TButton")
            janela.pagina("requisicoes")._cancelar()
            root.update()
            self.assertEqual(sub.winfo_manager(), "")
            self.assertEqual(janela.pagina_atual, "editor")

            ev.emitir("acao.estado", {"acao": "expander", "rodando": True})
            ev.emitir("acao.estado", {"acao": "auditoria", "rodando": True})
            root.update()
            self.assertEqual(set(janela._chips), {"expander", "auditoria"})
            self.assertEqual(janela.btn_parar_tudo.winfo_manager(), "pack")       # mais de uma tarefa: "Parar tudo"
            with mock.patch("engine.acoes.parar") as parar:
                janela._parar_tarefa("expander")
            parar.assert_called_once_with("expander")
            ev.emitir("acao.estado", {"acao": "expander", "rodando": False})
            ev.emitir("acao.estado", {"acao": "auditoria", "rodando": False})
            root.update()
            self.assertEqual(janela._chips, {})
            self.assertEqual(janela.lbl_status_tarefa.winfo_manager(), "pack")     # volta o "Pronto"
        finally:
            fechar(root)

    def test_chat_caixa_atalhos_e_anexos(self):
        root, janela = self._montar("pt_br")
        try:
            janela.mostrar_pagina("chat")
            chat = janela.pagina("chat")
            root.update()
            entrada = chat.entrada
            entrada.insert("1.0", "linha 1")
            chat._quebrar_linha(None)                                       # Ctrl+Enter
            entrada.insert("end-1c", "linha 2")
            self.assertEqual(entrada.get("1.0", "end-1c"), "linha 1\nlinha 2")
            entrada.delete("1.0", "end")

            chat._usar_atalho("Sugira nomes para [o quê] no mundo.")
            self.assertEqual(entrada.get("sel.first", "sel.last"), "[o quê]")  # o campo fica selecionado
            self.assertTrue(chat.quadro_atalhos.winfo_children())             # atalhos padrão na tela

            chat.anexar_arquivo(str(self.raiz_projeto / "Valia.md"))
            root.update()
            self.assertEqual([a["nome"] for a in chat._anexos], ["Valia.md"])
            self.assertEqual(chat.quadro_anexos.winfo_manager(), "pack")

            with mock.patch("engine.acoes.conversar_silent", return_value=True) as enviar:
                chat._tecla_enter(None)                                         # Enter envia
            mensagem, anexos = enviar.call_args.args
            self.assertIn("[o quê]", mensagem)
            self.assertEqual(anexos[0]["conteudo"], (self.raiz_projeto / "Valia.md").read_text(encoding="utf-8").strip())
            self.assertEqual(entrada.get("1.0", "end-1c"), "")
            self.assertEqual(chat._anexos, [])

            chat._resposta("## Ideias\n- **Brasaforte** fica perto de [[Valia]].")
            texto = chat.texto.get("1.0", "end")
            self.assertIn("Ideias", texto)
            self.assertNotIn("**", texto)
            self.assertTrue(chat.texto.tag_ranges("link"))
        finally:
            fechar(root)

    def test_janela_de_historico_restaura(self):
        import engine.historico as hist
        from ui.dialogs.history import JanelaHistorico
        root, janela = self._montar("en_us")
        try:
            alvo = self.raiz_projeto / "Valia.md"
            hist.arquivar_versao_para_historico(alvo)
            alvo.write_text("# Valia\nnova", encoding="utf-8")
            restaurados = []
            dialogo = JanelaHistorico(root, str(alvo), ao_restaurar=restaurados.append)
            root.update()
            self.assertEqual(len(dialogo.versoes), 1)
            with mock.patch("ui.dialogs.history.messagebox.askyesno", return_value=True):
                dialogo._restaurar()
            self.assertEqual(alvo.read_text(encoding="utf-8"), "# Valia\ntexto")
            self.assertEqual(restaurados, [str(alvo)])
            self.assertEqual(len(dialogo.versoes), 2)          # a versão substituída também foi guardada
            dialogo.destroy()
        finally:
            fechar(root)

    def test_visao_geral_da_pasta(self):
        pasta = self.raiz_projeto / "NPCs"
        pasta.mkdir()
        (pasta / "Thorvald.md").write_text("# Thorvald\nstatus: segredo\nRei de [[Valia]] e [[Fantasma]].", encoding="utf-8")
        root, janela = self._montar("pt_br")
        try:
            editor = janela.paginas["editor"]
            editor.atualizar_arvore()
            editor.ir_para(str(pasta))
            root.update()
            texto = editor._texto_editor()
            self.assertIn("📁 NPCs", texto)
            self.assertIn("└─ Thorvald 🤫", texto)
            self.assertIn("[[Fantasma]]", texto)                       # citado e ainda sem arquivo
            self.assertNotIn("[[Valia]]", texto)
            self.assertEqual(str(editor.editor.cget("state")), "disabled")

            inicio = editor.editor.search("Thorvald", "1.0")             # clicar no nome abre o arquivo
            caixa = editor.editor.bbox(inicio)
            evento = type("Evento", (), {"x": caixa[0] + 2, "y": caixa[1] + 2})()
            editor._clique_pasta(evento)
            self.assertEqual(editor.sessao.arquivo_atual, str(pasta / "Thorvald.md"))
        finally:
            fechar(root)

    def test_editor_abas_busca_autocompletar_e_painel(self):
        (self.raiz_projeto / "Thorvald.md").write_text("# Thorvald\nstatus: segredo\nRei. <-- TODO: x", encoding="utf-8")
        (self.raiz_projeto / "Valia.md").write_text("# Valia\n## Cidades\nGovernada por [[Thorvald]] e [[Fantasma]].",
                                                    encoding="utf-8")
        root, janela = self._montar("pt_br")
        try:
            editor = janela.paginas["editor"]
            editor.atualizar_arvore()
            textos = [editor.tree.item(i, "text") for i in editor._todos()]
            self.assertTrue(any("Thorvald" in tx and "🤫" in tx and "⏳" in tx for tx in textos))   # ícones de estado

            valia, thorvald = str(self.raiz_projeto / "Valia.md"), str(self.raiz_projeto / "Thorvald.md")
            editor.ir_para(valia)
            editor.ir_para(thorvald)
            self.assertEqual(editor._abas, [valia, thorvald])                       # abas
            editor.ir_para(valia)
            root.update()
            self.assertEqual(editor._dados_lateral["sumario"][1][1], "Cidades")      # painel lateral
            faixas = editor.editor.tag_ranges("md_link_quebrado")
            self.assertEqual(editor.editor.get(faixas[0], faixas[1]), "[[Fantasma]]")  # link quebrado em vermelho

            editor._abrir_busca(True)
            editor.var_procurar.set("Governada")
            editor.var_substituir.set("Regida")
            editor._substituir_tudo()
            self.assertIn("Regida por", editor._texto_editor())
            self.assertEqual(editor.lbl_estado.cget("text"), "● Não salvo")
            editor.salvar_agora()
            self.assertIn("Regida por", (self.raiz_projeto / "Valia.md").read_text(encoding="utf-8"))
            self.assertEqual(editor.lbl_estado.cget("text"), "✓ Salvo")

            editor.editor.mark_set("insert", tk.END)
            editor.editor.insert(tk.END, "\nVer [[Tho")
            editor._verificar_autocompletar()
            self.assertIsNotNone(editor._popup)
            editor._confirmar_autocompletar()
            self.assertTrue(editor._texto_editor().rstrip().endswith("Ver [[Thorvald]]"))

            editor._fechar_aba(valia)
            self.assertEqual(editor._abas, [thorvald])
            self.assertTrue(editor.sessao.eh_atual(thorvald))
            editor._definir_modo("lado")
            self.assertEqual(len(editor.area.panes()), 2 if editor.html is not None else 1)
            editor._definir_modo("editar")
            self.assertEqual(len(editor.area.panes()), 1)
        finally:
            fechar(root)

    def test_editor_preserva_alteracao_da_ia(self):
        root, janela = self._montar("pt_br")
        try:
            editor = janela.paginas["editor"]
            alvo = str(self.raiz_projeto / "Valia.md")
            editor._abrir(alvo)
            editor.editor.insert("end", "\nminha edição")
            time.sleep(0.02)
            (self.raiz_projeto / "Valia.md").write_text("# Valia\nVERSAO DA IA", encoding="utf-8")
            self.assertEqual(editor.salvar_agora(), es.ALTERADO_EXTERNAMENTE)
            self.assertIn("VERSAO DA IA", (self.raiz_projeto / "Valia.md").read_text(encoding="utf-8"))

            ex.marcar_processamento(alvo, True)
            try:
                editor._abrir(alvo)
                self.assertEqual(str(editor.editor.cget("state")), "disabled")
                self.assertIsNone(editor.salvar_agora())
            finally:
                ex.marcar_processamento(alvo, False)
        finally:
            fechar(root)


if __name__ == "__main__":
    unittest.main()
