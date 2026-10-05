"""Nível médio (Melhorar Arquivo) e o Histórico de versões com restauração."""
import unittest

from tests.util import novo_projeto, apagar, usar_idioma, ia_falsa

import engine.expander as ex
import engine.historico as hist
import engine.melhorar as melhorar


class TesteHistorico(unittest.TestCase):
    def setUp(self):
        usar_idioma("pt_br")
        self.raiz = novo_projeto({"Reinos/Valia.md": "# Valia\nv1"})
        self.alvo = self.raiz / "Reinos" / "Valia.md"

    def tearDown(self):
        apagar(self.raiz)

    def _escrever_versao(self, texto):
        hist.arquivar_versao_para_historico(self.alvo)
        self.alvo.write_text(texto, encoding="utf-8")

    def test_lista_da_mais_nova_para_a_mais_antiga(self):
        self._escrever_versao("# Valia\nv2")
        self._escrever_versao("# Valia\nv3")
        versoes = hist.listar_versoes(self.alvo)
        self.assertEqual([v.numero for v in versoes], [2, 1])
        self.assertEqual(hist.ler_versao(versoes[-1]), "# Valia\nv1")
        self.assertIn("Reinos", str(versoes[0].caminho))            # mantém as subpastas do projeto

    def test_restaurar_guarda_a_atual_antes(self):
        self._escrever_versao("# Valia\nv2")
        primeira = hist.listar_versoes(self.alvo)[-1]
        hist.restaurar_versao(self.alvo, primeira)
        self.assertEqual(self.alvo.read_text(encoding="utf-8"), "# Valia\nv1")
        versoes = hist.listar_versoes(self.alvo)
        self.assertEqual(hist.ler_versao(versoes[0]), "# Valia\nv2")  # a restauração pode ser desfeita

    def test_nao_restaura_arquivo_travado_pela_ia(self):
        self._escrever_versao("# Valia\nv2")
        ex.marcar_processamento(self.alvo, True)
        try:
            with self.assertRaises(hist.ErroHistorico):
                hist.restaurar_versao(self.alvo, hist.listar_versoes(self.alvo)[0])
        finally:
            ex.marcar_processamento(self.alvo, False)
        self.assertEqual(self.alvo.read_text(encoding="utf-8"), "# Valia\nv2")

    def test_projetos_diferentes_nao_misturam_historico(self):
        self._escrever_versao("# Valia\nv2")
        outro = novo_projeto({"Reinos/Valia.md": "# Outra Valia"})
        try:
            self.assertEqual(hist.listar_versoes(outro / "Reinos" / "Valia.md"), [])
        finally:
            apagar(outro)

    def test_versoes_antigas_sem_pasta_do_projeto_continuam_visiveis(self):
        import engine.project_utils as pu
        legado = pu.PASTA_LOGS / "history" / "Reinos"
        legado.mkdir(parents=True, exist_ok=True)
        (legado / "Valia_v01.md").write_text("# Valia\nantiga", encoding="utf-8")
        self._escrever_versao("# Valia\nv2")
        self.assertEqual([v.numero for v in hist.listar_versoes(self.alvo)], [2, 1])
        (legado / "Valia_v01.md").unlink()

    def test_arquivo_sem_historico(self):
        self.assertEqual(hist.listar_versoes(self.raiz / "Outro.md"), [])


class TesteMelhorarArquivo(unittest.TestCase):
    def setUp(self):
        usar_idioma("en_us")
        self.raiz = novo_projeto({"Valia.md": "# Valia\nold"})
        self.alvo = self.raiz / "Valia.md"

    def tearDown(self):
        apagar(self.raiz)
        usar_idioma("pt_br")

    def test_reescreve_arquiva_e_usa_o_canon(self):
        with ia_falsa("```markdown\n# Valia\nnew\n```") as ia:
            self.assertTrue(melhorar.melhorar_arquivo(self.alvo, "more detail", canon="King Aldren rules Valia"))
        self.assertEqual(self.alvo.read_text(encoding="utf-8"), "# Valia\nnew\n")
        self.assertIn("King Aldren rules Valia", ia.ultima["contents"])
        self.assertIn("CAMPAIGN CANON", ia.ultima["contents"])
        self.assertEqual(hist.ler_versao(hist.listar_versoes(self.alvo)[0]), "# Valia\nold")
        self.assertFalse(ex.esta_em_processamento(self.alvo))

    def test_sem_canon_e_resposta_vazia(self):
        with ia_falsa("") as ia:
            self.assertFalse(melhorar.melhorar_arquivo(self.alvo, "x"))
        self.assertNotIn("CAMPAIGN CANON", ia.ultima["contents"])
        self.assertEqual(self.alvo.read_text(encoding="utf-8"), "# Valia\nold")


if __name__ == "__main__":
    unittest.main()
