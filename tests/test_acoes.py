"""Central de ações: trava do arquivo durante a IA, duplicidade, eventos e Expander automático."""
import threading
import time
import unittest

from tests.util import novo_projeto, apagar

import core.config as cfg
import core.eventos as ev
import engine.acoes as acoes


class TesteAcoes(unittest.TestCase):
    def setUp(self):
        self.raiz = novo_projeto({"A.md": "# A\ntexto"})
        self.alvo = str(self.raiz / "A.md")
        self.estados = []
        ev.inscrever_evento("acao.estado", self.estados.append)
        self._original = acoes.melhorar.melhorar_arquivo

    def tearDown(self):
        acoes.melhorar.melhorar_arquivo = self._original
        ev.cancelar_inscricoes()
        cfg.atualizar_configuracoes({"auto_expander": False})
        apagar(self.raiz)

    def test_trava_durante_a_ia_e_recusa_duplicada(self):
        durante = {}

        def melhorar_falso(caminho, objetivo="", canon=None):
            durante["travado"] = acoes.arquivo_em_processamento(caminho)
            time.sleep(0.2)
            return True

        acoes.melhorar.melhorar_arquivo = melhorar_falso
        fim, resultado = threading.Event(), {}
        self.assertTrue(acoes.executar_acao_arquivo("melhorar", self.alvo, "",
                                                    ao_concluir=lambda r: (resultado.setdefault("r", r), fim.set())))
        self.assertFalse(acoes.executar_acao_arquivo("melhorar", self.alvo, ""))
        self.assertTrue(fim.wait(5))
        self.assertTrue(resultado["r"] and durante["travado"])
        self.assertFalse(acoes.arquivo_em_processamento(self.alvo))
        self.assertEqual([e["rodando"] for e in self.estados if e["acao"].startswith("arquivo:")], [True, False])

    def test_expander_automatico(self):
        (self.raiz / "A.md").write_text("# A\n<-- TODO: x", encoding="utf-8")
        self.assertFalse(acoes.deve_auto_expandir(self.alvo))
        cfg.atualizar_configuracoes({"auto_expander": True})
        self.assertTrue(acoes.deve_auto_expandir(self.alvo))


if __name__ == "__main__":
    unittest.main()
