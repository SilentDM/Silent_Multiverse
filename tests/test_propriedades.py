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
        # O esboço traz as propriedades do template (type, tags, campos vazios) e o rascunho
        self.assertTrue(texto.startswith("---\ntype: local\ntags: [local]\naliases: []\nlocation:\nowner:\nstatus: rascunho\n---\n# Taverna"))
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


class TesteEsquemaDosTemplates(unittest.TestCase):
    """Hierarquia: o que está no arquivo > o que a IA preencheu nas chaves vazias > o padrão do template."""

    def setUp(self):
        usar_idioma("pt_br")
        self.raiz = novo_projeto({
            "Capital Zephyrus.md": "---\ntipo: cidade\nstatus: rascunho\n---\n# Capital Zephyrus\nTexto.",
            "Sem Tipo.md": "# Mercador Osmund\nVende peles.",
            "Tags Minhas.md": "---\ntype: cidade\ntags: [capital, zephyr]\n---\n# Outra",
        })

    def tearDown(self):
        apagar(self.raiz)

    def test_catalogo_dos_templates(self):
        import engine.esquemas as esquemas
        catalogo = esquemas.catalogo()
        self.assertEqual([c for c, _ in catalogo["cidade"]][:6], ["type", "tags", "aliases", "kingdom", "ruler", "population"])
        self.assertIn("npc", catalogo)
        # Um template na pasta Templates do cofre tem prioridade sobre os do programa
        (self.raiz / "Templates").mkdir()
        (self.raiz / "Templates" / "cidade.md").write_text("---\ntype: cidade\nmayor:\n---\n# C", encoding="utf-8")
        chaves = [c for c, _ in esquemas.catalogo()["cidade"]]
        self.assertIn("mayor", chaves)
        self.assertNotIn("population", chaves)

    def test_caso_da_capital(self):
        resposta = ("---\ntype: city\nstatus: completo\nkingdom: \"[[Reinado de Zephyr]]\"\nruler: \"[[Rei Zephyr Aventus]]\"\n"
                    "aliases: [Zephyrus]\ninventado: x\n---\n# Capital Zephyrus\nTexto novo.")
        alvo = self.raiz / "Capital Zephyrus.md"
        with ia_falsa(resposta) as ia:
            melhorar.melhorar_arquivo(alvo, "reescrever")
        self.assertIn("PROPRIEDADES DO OBSIDIAN", ia.ultima["contents"])
        self.assertIn("- kingdom", ia.ultima["contents"])
        p = props.ler(alvo.read_text(encoding="utf-8"))
        self.assertEqual(p["tipo"], "cidade")                       # do arquivo: fica (e vale como type)
        self.assertNotIn("type", p)
        self.assertEqual(p["status"], "rascunho")                   # status nunca vem da IA
        self.assertEqual(p["kingdom"], "[[Reinado de Zephyr]]")     # chaves vazias: preenchidas pela IA
        self.assertEqual(p["aliases"], ["Zephyrus"])
        self.assertEqual(p["tags"], ["cidade"])                     # sem valor da IA: padrão do template
        self.assertEqual(p["population"], "")                       # campo do template, ainda vazio
        self.assertNotIn("inventado", p)                            # fora do esquema: descartado
        self.assertIn("Texto novo.", alvo.read_text(encoding="utf-8"))

    def test_valores_do_arquivo_vencem_o_template(self):
        alvo = self.raiz / "Tags Minhas.md"
        with ia_falsa("---\ntags: [cidade]\nruler: \"[[Alguém]]\"\n---\n# Outra\nnovo") as ia:
            melhorar.melhorar_arquivo(alvo, "x")
        p = props.ler(alvo.read_text(encoding="utf-8"))
        self.assertEqual(p["tags"], ["capital", "zephyr"])
        self.assertEqual(p["ruler"], "[[Alguém]]")

    def test_sem_tipo_a_ia_escolhe_e_o_esquema_segue(self):
        alvo = self.raiz / "Sem Tipo.md"
        with ia_falsa("---\ntype: npc\noccupation: Mercador\nlocation: \"[[Mercado Aberto]]\"\ncor: azul\n---\n# Mercador Osmund\nVende peles raras.") as ia:
            melhorar.melhorar_arquivo(alvo, "x")
        self.assertIn("- npc: location, faction, occupation", ia.ultima["contents"])   # catálogo de tipos no pedido
        p = props.ler(alvo.read_text(encoding="utf-8"))
        self.assertEqual((p["type"], p["occupation"], p["location"]), ("npc", "Mercador", "[[Mercado Aberto]]"))
        self.assertEqual(p["faction"], "")
        self.assertNotIn("cor", p)

    def test_tirar_do_rascunho_ao_terminar(self):
        import engine.requisicao as requisicao
        alvo = self.raiz / "Capital Zephyrus.md"
        req = requisicao.nova("melhorar", alvo, "reescrever")
        self.assertTrue(req.eh_rascunho and req.tirar_rascunho)          # arquivo em rascunho: vem marcada
        req.tirar_rascunho = False
        with ia_falsa("# Capital Zephyrus\nTexto."):
            melhorar.melhorar_arquivo(alvo, requisicao=req)
        self.assertTrue(props.eh_rascunho(alvo.read_text(encoding="utf-8")))   # desmarcada: continua rascunho
        req.tirar_rascunho = True
        with ia_falsa("# Capital Zephyrus\nTexto."):
            melhorar.melhorar_arquivo(alvo, requisicao=req)
        texto = alvo.read_text(encoding="utf-8")
        self.assertFalse(props.eh_rascunho(texto))
        self.assertEqual(props.ler(texto)["tipo"], "cidade")             # o resto do bloco fica
        self.assertFalse(requisicao.nova("melhorar", self.raiz / "Sem Tipo.md").eh_rascunho)

    def test_sem_nada_para_preencher_nao_cria_bloco(self):
        alvo = self.raiz / "Sem Tipo.md"
        with ia_falsa("# Mercador Osmund\nVende peles raras."):
            melhorar.melhorar_arquivo(alvo, "x")
        self.assertTrue(alvo.read_text(encoding="utf-8").startswith("# Mercador Osmund"))


if __name__ == "__main__":
    unittest.main()
