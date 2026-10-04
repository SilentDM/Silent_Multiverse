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
                    for chave in app.PAGINAS_TOPO + app.PAGINAS_RODAPE:
                        janela.mostrar_pagina(chave)
                        root.update()
                        self.assertEqual(janela.pagina_atual, chave)
                    self.assertEqual(janela.botoes_nav["actions"].cget("text").strip().split()[-1], palavra)
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
