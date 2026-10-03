"""Contexto do mundo enviado à IA: segredos, rascunhos (PT/EN) e relatório de tokens."""
import unittest

from tests.util import novo_projeto, apagar, usar_idioma

import core.config as cfg
import engine.project_utils as pu
import engine.token_counter as tc


class TesteContextoDoMundo(unittest.TestCase):
    def setUp(self):
        usar_idioma("pt_br")
        cfg.atualizar_configuracoes({"termos_secretos": "Hastur"})
        self.raiz = novo_projeto({
            "Raiz.md": "# Raiz\nNa raiz do projeto.",
            "Reinos/Valia.md": "# Valia\nPúblico.\n\n### O Culto [segredo]\nTEXTO SECRETO PT\n\n## Comércio\nvisível",
            "Reinos/Norte.md": "# Norte\nPúblico.\n\n### Hidden [secret]\nTEXTO SECRETO EN\n\n## Trade\nvisible",
            "NPCs/Varis.md": "# Varis\nstatus: segredo\nvilão",
            "NPCs/Mira.md": "# Mira\nstatus: secret\nspy",
            "NPCs/Culto de Hastur.md": "# Seita\ngrupo de mercadores",
            "NPCs/Rascunho.md": "# R\nstatus: rascunho\nx",
            "NPCs/Draft.md": "# D\nstatus: draft\nx",
            "NPCs/Pendente.md": "# P\n<-- TODO: algo",
            "NPCs/Vazio.md": "",
            ".obsidian/workspace.md": "x",
        })

    def tearDown(self):
        apagar(self.raiz)
        cfg.atualizar_configuracoes({"termos_secretos": ""})

    def test_mestre_ve_tudo_menos_rascunhos(self):
        dm = pu.montar_contexto_mundo(is_dm=True)
        for presente in ("TEXTO SECRETO PT", "TEXTO SECRETO EN", "==== Varis.md", "==== Mira.md", "Culto de Hastur"):
            self.assertIn(presente, dm)
        for ausente in ("==== Rascunho.md", "==== Draft.md", "==== Pendente.md", ".obsidian"):
            self.assertNotIn(ausente, dm)

    def test_jogadores_nao_veem_segredos_nem_nomes_secretos(self):
        pl = pu.montar_contexto_mundo(is_dm=False)
        for ausente in ("TEXTO SECRETO PT", "TEXTO SECRETO EN", "Varis", "Mira", "Hastur", ".obsidian"):
            self.assertNotIn(ausente, pl)
        self.assertIn("visível", pl)
        self.assertIn("visible", pl)

    def test_indice_inclui_arquivos_da_raiz(self):
        import json
        self.assertIn("Raiz.md", json.loads(pu.gerar_indice())["ROOT"])

    def test_relatorio_de_tokens(self):
        analise = tc.analisar_projeto()
        por_nome = {a.caminho_relativo.name: a for a in analise.arquivos}
        self.assertEqual(por_nome["Vazio.md"].estado, "vazio")
        self.assertEqual(por_nome["Pendente.md"].estado, "todo")
        self.assertEqual(por_nome["Draft.md"].estado, "rascunho")
        self.assertEqual(por_nome["Mira.md"].estado, "oculto")
        self.assertEqual(por_nome["Valia.md"].estado, "parcial")
        self.assertEqual(sum(a.chars_mestre for a in analise.arquivos) + analise.overhead_chars_mestre,
                         analise.chars_bundle_mestre)
        arvore = tc.montar_arvore_relatorio(analise, "tok_m", True)
        self.assertTrue(any(no.tipo == "pasta" and no.filhos for no in arvore))


if __name__ == "__main__":
    unittest.main()
