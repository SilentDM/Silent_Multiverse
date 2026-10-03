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


@unittest.skipUnless(TEM_TELA, "sem ambiente gráfico")
class TesteInterface(unittest.TestCase):
    def setUp(self):
        self.raiz_projeto = novo_projeto({"Valia.md": "# Valia\ntexto"})
        self.patches = [mock.patch("bot.runner.iniciar"), mock.patch("bot.runner.parar"),
                        mock.patch("core.modelos_gemini.atualizar_se_necessario"),
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
                    root.destroy()

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
            root.destroy()


if __name__ == "__main__":
    unittest.main()
