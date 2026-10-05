"""Configurações por projeto (.silent_projeto.json) com fallback nas globais."""
import json
import unittest

from tests.util import novo_projeto, apagar

import core.config as cfg
import engine.project_utils as pu


class TesteConfigPorProjeto(unittest.TestCase):
    def setUp(self):
        self.a = novo_projeto({"A.md": "# A"})
        self.b = novo_projeto({"B.md": "# B"})

    def tearDown(self):
        for raiz in (self.a, self.b):
            apagar(raiz)

    def _global(self):
        return json.loads(cfg.SETTINGS_FILE.read_text(encoding="utf-8"))

    def test_cada_projeto_tem_as_suas(self):
        pu.definir_projeto_ativo(self.a)
        global_antes = self._global().get("termos_secretos", "")
        cfg.atualizar_configuracoes({"termos_secretos": "Hastur", "estilo_genero": "horror_cosmico",
                                     "verificar_atualizacoes": False})
        self.assertTrue((self.a / cfg.ARQUIVO_PROJETO).exists())
        self.assertEqual(self._global().get("termos_secretos", ""), global_antes)   # global intocado
        self.assertFalse(self._global()["verificar_atualizacoes"])                  # chave do programa: global

        pu.definir_projeto_ativo(self.b)
        self.assertEqual(cfg.obter("termos_secretos"), global_antes)                # B herda o global
        cfg.atualizar_configuracoes({"termos_secretos": "Kor"})
        self.assertEqual(cfg.obter("termos_secretos"), "Kor")

        pu.definir_projeto_ativo(self.a)
        self.assertEqual(cfg.obter("termos_secretos"), "Hastur")
        self.assertEqual(cfg.obter("estilo_genero"), "horror_cosmico")
        self.assertFalse(cfg.obter("verificar_atualizacoes"))
        cfg.atualizar_configuracoes({"verificar_atualizacoes": True})

    def test_pasta_do_projeto_apagada_usa_o_global(self):
        pu.definir_projeto_ativo(self.a)
        apagar(self.a)
        cfg.atualizar_configuracoes({"termos_secretos": "X"})                       # não quebra
        self.assertEqual(self._global()["termos_secretos"], "X")
        cfg.atualizar_configuracoes({"termos_secretos": ""})


if __name__ == "__main__":
    unittest.main()
