"""Operações de arquivo (engine.arquivos) e estado do editor (engine.editor_session)."""
import time
from pathlib import Path
import unittest

from tests.util import novo_projeto, apagar, usar_idioma

import engine.arquivos as arq
import engine.editor_session as es
import engine.expander as ex


class TesteArquivos(unittest.TestCase):
    def setUp(self):
        usar_idioma("pt_br")
        self.raiz = novo_projeto({"NPCs/Aldric.md": "# Aldric\nVer [[Valia]].", "Valia.md": "# Valia",
                                  "NPCs/Phaethon_v04.md": "# Phaethon"})

    def tearDown(self):
        apagar(self.raiz)

    def test_arvore_e_busca(self):
        arvore = arq.montar_arvore()
        self.assertEqual({n.nome for n in arvore.filhos}, {"NPCs", "Valia"})
        encontrados = arq.buscar("valia")
        self.assertIn(str((self.raiz / "Valia.md").resolve()), encontrados)

    def test_criar_com_ponto_no_nome_e_impedir_duplicado(self):
        caminho = arq.criar_arquivo(str(self.raiz / "NPCs"), "St. Gregor")
        self.assertTrue(caminho.endswith("St. Gregor.md"))
        self.assertIn("<-- TODO", Path(caminho).read_text(encoding="utf-8"))
        with self.assertRaises(arq.ErroOperacao):
            arq.criar_arquivo(str(self.raiz / "NPCs"), "St. Gregor")

    def test_wikilinks(self):
        self.assertTrue(arq.resolver_wikilink("valia").endswith("Valia.md"))
        self.assertTrue(arq.resolver_wikilink("Phaethon").endswith("Phaethon_v04.md"))   # ignora _vNN
        self.assertTrue(arq.resolver_wikilink("Valia#História").endswith("Valia.md"))     # ignora #seção
        self.assertTrue(arq.resolver_wikilink("Valia|o reino").endswith("Valia.md"))       # ignora |apelido
        self.assertTrue(arq.resolver_wikilink("Reinos/Valia").endswith("Valia.md"))       # ignora pasta
        self.assertIsNone(arq.resolver_wikilink("Inexistente"))
        apelido = arq.criar_por_wikilink("Porto Sul|o porto", str(self.raiz), "Valia.md")
        self.assertTrue(apelido.endswith("Porto Sul.md"))
        novo = arq.criar_por_wikilink("Torre Negra", str(self.raiz), "Valia.md")
        self.assertIn("[[Valia.md]]", Path(novo).read_text(encoding="utf-8"))

    def test_mover_colar_duplicar_renomear(self):
        movido = arq.mover_para(str(self.raiz / "Valia.md"), str(self.raiz / "NPCs"))
        self.assertTrue(arq.eh_arquivo(movido))
        with self.assertRaises(arq.ErroOperacao):
            arq.mover_para(str(self.raiz / "NPCs"), str(self.raiz / "NPCs" / "Aldric.md"))  # pasta para dentro de si
        copia = arq.duplicar(movido)
        self.assertTrue(copia.endswith("_copia.md"))
        nova_pasta = arq.renomear(str(self.raiz / "NPCs"), "Personagens")
        self.assertTrue(arq.eh_pasta(nova_pasta))
        colado = arq.colar(str(self.raiz / "Personagens" / "Aldric.md"), str(self.raiz), recortar=True)
        self.assertTrue(arq.eh_arquivo(colado))


class TesteSessaoEditor(unittest.TestCase):
    def setUp(self):
        self.raiz = novo_projeto({"A.md": "# A\ntexto", "Pasta/B.md": "# B"})
        self.sessao = es.SessaoEditor()

    def tearDown(self):
        apagar(self.raiz)

    def test_nunca_sobrescreve_alteracao_da_ia(self):
        a = str(self.raiz / "A.md")
        texto = self.sessao.abrir(a)
        self.assertEqual(self.sessao.salvar(texto + "\nmais"), es.SALVO)
        self.assertEqual(self.sessao.salvar(texto + "\nde novo"), es.SALVO)    # salvar 2x seguidas não é "externo"
        time.sleep(0.02)
        (self.raiz / "A.md").write_text("VERSAO DA IA", encoding="utf-8")
        self.assertEqual(self.sessao.salvar("texto velho do editor"), es.ALTERADO_EXTERNAMENTE)
        self.assertEqual((self.raiz / "A.md").read_text(encoding="utf-8"), "VERSAO DA IA")
        self.assertTrue(self.sessao.precisa_recarregar())
        self.assertEqual(self.sessao.recarregar(), "VERSAO DA IA")

    def test_nao_salva_durante_processamento(self):
        a = str(self.raiz / "A.md")
        self.sessao.abrir(a)
        ex.marcar_processamento(a, True)
        try:
            self.assertEqual(self.sessao.salvar("NAO"), es.EM_PROCESSAMENTO)
        finally:
            ex.marcar_processamento(a, False)
        self.assertNotIn("NAO", (self.raiz / "A.md").read_text(encoding="utf-8"))

    def test_acompanha_pasta_renomeada_e_historico(self):
        b = str(self.raiz / "Pasta" / "B.md")
        self.sessao.abrir(str(self.raiz / "A.md"))
        self.sessao.abrir(b)
        nova = arq.renomear(str(self.raiz / "Pasta"), "Outra")
        self.assertTrue(self.sessao.acompanhar_movimento(str(self.raiz / "Pasta"), nova))
        self.assertTrue(self.sessao.arquivo_atual.endswith("B.md") and "Outra" in self.sessao.arquivo_atual)
        self.assertEqual(self.sessao.salvar("# B novo"), es.SALVO)
        self.assertTrue(self.sessao.voltar().endswith("A.md"))
        self.assertIn("Outra", self.sessao.avancar())


if __name__ == "__main__":
    unittest.main()
