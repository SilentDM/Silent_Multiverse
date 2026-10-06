"""
Propriedades do Obsidian (YAML): Silent lê o formato antigo e o novo, grava sempre o novo
quando escreve um arquivo, preserva o que o Mestre escreveu no bloco e não mexe nas edições do Editor.
"""
import unittest

from tests.util import novo_projeto, apagar, usar_idioma, ia_falsa

import core.propriedades as props
import core.secret_filter as sf
import engine.arquivos as arq
import engine.compiler as comp
import engine.documento as documento
import engine.editor_session as es
import engine.melhorar as melhorar
import engine.notas as notas
import engine.project_utils as pu


class TestePropriedades(unittest.TestCase):
    def setUp(self):
        usar_idioma("pt_br")

    def test_leitura_dos_dois_formatos(self):
        self.assertTrue(props.eh_segredo("# Rei\nstatus: segredo\ntexto"))                 # linha antiga
        self.assertTrue(props.eh_segredo("---\nstatus: secret\n---\n# Rei"))
        self.assertTrue(props.eh_segredo("---\nstatus:\n  - publicado\n  - segredo\n---\n"))  # lista
        self.assertTrue(props.eh_segredo('---\nstatus: "secret"\n---\n'))
        self.assertTrue(props.eh_segredo("---\ntags: [npc, segredo]\n---\n"))
        self.assertTrue(props.eh_rascunho("---\nstatus: draft\n---\n"))
        self.assertFalse(props.eh_segredo("# Regra\n\n---\n\nstatus: segredo aparece aqui no meio da frase"))
        self.assertEqual(props.apelidos("---\naliases:\n  - O Rei das Cinzas\n  - Thor\n---\n"), ["O Rei das Cinzas", "Thor"])

    def test_normalizar_migra_e_preserva_o_resto(self):
        antigo = "---\ncor: azul\ntags: [npc]\n---\n# Rei\nstatus: rascunho\n\nTexto."
        novo = props.normalizar(antigo, segredo=True, rascunho=False)
        self.assertEqual(novo, "---\ncor: azul\ntags: [npc]\nstatus: segredo\n---\n# Rei\n\nTexto.")
        self.assertEqual(props.normalizar(novo), novo)                                       # estável
        self.assertEqual(props.normalizar("# Nada\ntexto"), "# Nada\ntexto")               # sem bloco vazio
        outro = props.normalizar("---\nstatus: publicado\n---\n# X", segredo=True)
        self.assertEqual(props.lista(outro, "status"), ["publicado", "segredo"])           # valor do Mestre fica
        self.assertEqual(props.normalizar(outro, segredo=False), "---\nstatus: publicado\n---\n# X")

    def test_mesclar_mantem_o_bloco_do_original(self):
        original = "---\nstatus: segredo\naliases: [Thor]\n---\n# Rei\nvelho"
        ia = "---\nstatus: draft\ntipo: npc\n---\n# Rei\nnovo"
        self.assertEqual(props.mesclar(original, ia),
                         "---\nstatus: segredo\naliases: [Thor]\ntipo: npc\n---\n# Rei\nnovo")
        self.assertEqual(props.mesclar(original, "# Rei\nsem bloco"),
                         "---\nstatus: segredo\naliases: [Thor]\n---\n# Rei\nsem bloco")


class TesteNoProjeto(unittest.TestCase):
    def setUp(self):
        usar_idioma("pt_br")
        self.raiz = novo_projeto({
            "Rei.md": "# Rei Thorvald\nstatus: segredo\nGoverna Vog'Mur.",
            "Thor.md": "---\naliases:\n  - O Rei das Cinzas\n---\n# Thor\nO rascunho.",
            "Lich.md": "---\nstatus:\n  - segredo\n---\n# Lich\nNo vulcão.",
            "Vila.md": "# Vila\nPública.",
        })
        documento.invalidar()

    def tearDown(self):
        apagar(self.raiz)

    def test_jogadores_nao_veem_segredos_nos_dois_formatos(self):
        jogadores = pu.montar_contexto_mundo(is_dm=False)
        self.assertNotIn("Governa Vog'Mur", jogadores)
        self.assertNotIn("No vulcão", jogadores)
        self.assertIn("Pública", jogadores)
        self.assertEqual(sf.filtrar_conteudo_por_permissao("---\nstatus: secret\n---\n# X\ny", is_dm=False), "")

    def test_ia_grava_no_formato_novo(self):
        rei = self.raiz / "Rei.md"
        with ia_falsa("# Rei Thorvald\nGoverna Vog'Mur com mão de ferro."):
            self.assertTrue(melhorar.melhorar_arquivo(rei, "detalhar"))
        texto = rei.read_text(encoding="utf-8")
        self.assertTrue(texto.startswith("---\nstatus: segredo\n---\n# Rei Thorvald"))      # a linha antiga virou propriedade
        self.assertEqual(texto.count("status:"), 1)

        lich = self.raiz / "Lich.md"
        with ia_falsa("---\nstatus: draft\n---\n# Lich\nReescrito."):
            melhorar.melhorar_arquivo(lich, "x")
        self.assertTrue(lich.read_text(encoding="utf-8").startswith("---\nstatus:\n  - segredo\n---\n# Lich\nReescrito."))

    def test_nota_e_esboco_de_template(self):
        notas.adicionar_nota(self.raiz / "Rei.md", "Ele mente.", "mestre")
        self.assertTrue((self.raiz / "Rei.md").read_text(encoding="utf-8").startswith("---\nstatus: segredo\n---\n"))
        caminho = arq.criar_arquivo(str(self.raiz), "Taverna", "local")
        texto = open(caminho, encoding="utf-8").read()
        self.assertTrue(texto.startswith("---\nstatus: rascunho\n---\n# Taverna"))
        self.assertTrue(documento.estado(caminho)["rascunho"])

    def test_template_com_propriedades_vai_para_o_topo(self):
        self.assertEqual(props.juntar_template("# Taverna\n\n<-- TODO: x", "---\ntype: local\n---\n## Descrição"),
                         "---\ntype: local\n---\n# Taverna\n\n<-- TODO: x\n## Descrição")
        texto = props.normalizar(props.juntar_template("# T", "---\ntype: local\n---\n## D"), rascunho=True)
        self.assertEqual(props.ler(texto), {"type": "local", "status": "rascunho"})
        self.assertEqual(props.juntar_template("# T", "## D"), "# T\n## D")

    def test_edicao_do_mestre_nao_e_convertida(self):
        sessao = es.SessaoEditor()
        rei = str(self.raiz / "Rei.md")
        texto = sessao.abrir(rei)
        sessao.salvar(texto + "\nMais uma linha.")
        self.assertTrue(open(rei, encoding="utf-8").read().startswith("# Rei Thorvald\nstatus: segredo"))

    def test_apelido_no_autocompletar_e_livro_sem_yaml(self):
        self.assertIn("Thor|O Rei das Cinzas", documento.sugerir_links("o rei"))
        self.assertIn("Thor", documento.sugerir_links("tho"))
        limpo = comp._limpar_conteudo_markdown((self.raiz / "Lich.md").read_text(encoding="utf-8"))
        self.assertEqual(limpo, "# Lich\nNo vulcão.")
        self.assertEqual(comp._limpar_conteudo_markdown("# Rei\nstatus: segredo\nTexto"), "# Rei\nTexto")


if __name__ == "__main__":
    unittest.main()
