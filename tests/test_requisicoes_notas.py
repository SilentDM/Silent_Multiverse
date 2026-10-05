"""Estilos em 4 eixos, Requisição, Notas do Mestre, Fichas de Combate e o Conselho com insumos (IA falsa)."""
import json
import unittest
from unittest import mock

from tests.util import novo_projeto, apagar, usar_idioma, ia_falsa

import core.config as cfg
import core.i18n as i18n
import engine.council_engine as ce
import engine.expander as ex
import engine.fichas as fichas
import engine.geradores as geradores
import engine.melhorar as melhorar
import engine.notas as notas
import engine.persona_engine as pe
import engine.project_utils as pu
import engine.requisicao as requisicao
import engine.style_manager as estilo


def ficha_5e(**extra):
    dados = {"nome": "Ignarax", "tamanho_tipo_alinhamento": "Elemental Grande, Neutro", "classe_armadura": 15,
             "pontos_de_vida": 102, "dados_de_vida": "12d10 + 36", "deslocamento": "12 m",
             "forca": 18, "destreza": 15, "constituicao": 16, "inteligencia": 6, "sabedoria": 10, "carisma": 7,
             "sentidos": "visão no escuro 18 m", "nivel_de_desafio": "ND 5 (1.800 XP)",
             "acoes": [{"nome": "Toque", "descricao": "+7 para acertar, 2d6 + 4 de dano de fogo."}]}
    dados.update(extra)
    return json.dumps(dados)


class TesteEstilos(unittest.TestCase):
    def setUp(self):
        usar_idioma("pt_br")

    def tearDown(self):
        for eixo in estilo.EIXOS:
            cfg.atualizar_configuracoes({f"estilo_{eixo}": estilo.PADROES[eixo]})

    def test_mesmas_opcoes_nos_dois_idiomas(self):
        for eixo in estilo.EIXOS:
            ids = {idioma: [i for i, _ in estilo.opcoes(eixo, idioma)] for idioma in i18n.IDIOMAS}
            self.assertEqual(ids["pt_br"], ids["en_us"], eixo)
            self.assertIn(estilo.PADROES[eixo], ids["pt_br"])
        self.assertIn(("horror_cosmico", "Horror Cósmico"), estilo.opcoes("genero", "pt_br"))

    def test_migra_o_perfil_antigo(self):
        config = cfg.carregar_configuracoes()
        for eixo in estilo.EIXOS:
            config.pop(f"estilo_{eixo}", None)
        config["tom_clima_perfil"] = "Mistério & Investigação"
        cfg.salvar_configuracoes(config)
        self.assertEqual(estilo.padroes(), {"genero": "misterio", "tom": "neutro", "clima": "misterioso",
                                            "escrita": "enciclopedico"})

    def test_bloco_e_diretrizes(self):
        estilo.definir_padrao("genero", "misterio")
        bloco = ex.carregar_diretrizes_estilo({"genero": "horror_cosmico"})
        self.assertIn("Horror Cósmico", bloco)                     # a escolha do pedido vence o padrão
        self.assertNotIn("Mistério e Investigação", bloco)
        self.assertIn("Mistério e Investigação", ex.carregar_diretrizes_estilo())
        pu.CAMINHO_ESTILO.mkdir(parents=True, exist_ok=True)
        antigo = pu.CAMINHO_ESTILO / estilo.ARQUIVO_TOM_ANTIGO
        antigo.write_text(i18n.traduzir("style.conteudo.dark_fantasy", "pt_br", ""), encoding="utf-8")
        verdades = pu.CAMINHO_ESTILO / "Verdades.md"
        verdades.write_text("# Verdades\nOs deuses são reais.", encoding="utf-8")
        try:
            bloco = ex.carregar_diretrizes_estilo()
            self.assertIn("Os deuses são reais.", bloco)
            self.assertNotIn("<tom_e_clima>", bloco)               # o arquivo gerado antigo foi substituído pelos eixos
        finally:
            antigo.unlink()
            verdades.unlink()

    def test_estilo_criado_pelo_mestre(self):
        pasta = pu.PASTA_DADOS_NEXUS / "Estilos" / "Genero"
        pasta.mkdir(parents=True, exist_ok=True)
        (pasta / "steampunk.md").write_text("# Steampunk\nEngrenagens.", encoding="utf-8")
        try:
            self.assertIn(("steampunk", "Steampunk"), estilo.opcoes("genero"))
            self.assertIn("Engrenagens.", estilo.bloco_estilos({"genero": "steampunk"}))
        finally:
            (pasta / "steampunk.md").unlink()


class TesteRequisicao(unittest.TestCase):
    def setUp(self):
        usar_idioma("pt_br")
        self.raiz = novo_projeto({"Valia.md": "# Valia\nGovernada por [[Rei Aldren]].",
                                  "NPCs/Rei Aldren.md": "# Rei Aldren\nO rei.",
                                  "Porto.md": "# Porto\nComércio com [[Valia]]."})
        self.alvo = self.raiz / "Valia.md"

    def tearDown(self):
        apagar(self.raiz)

    def test_bloco_do_pedido(self):
        req = requisicao.nova("melhorar", self.alvo, "x")
        self.assertEqual(req.bloco_prompt(), "")                    # tudo no padrão: nada extra
        req = requisicao.nova("melhorar", self.alvo, "x", diretrizes_extras="Clima de horror na caverna",
                              profundidade="curto", publico="jogadores", nivel_grupo=5, jogadores=4, segredo=True,
                              referencias=[str(self.raiz / "NPCs" / "Rei Aldren.md")])
        bloco = req.bloco_prompt()
        for trecho in ("Clima de horror na caverna", "breve", "JOGADORES", "nível 5", "4 jogador", "segredo", "O rei."):
            self.assertIn(trecho, bloco)
        self.assertEqual(requisicao.nova("melhorar", self.alvo, criatividade="ousado").temperatura(0.4), 0.9)
        self.assertEqual(requisicao.nova("melhorar", self.alvo).temperatura(0.4), 0.4)

    def test_referencias_sugeridas(self):
        nomes = {p.split("\\")[-1].split("/")[-1]: motivo for p, motivo in requisicao.sugerir_referencias(self.alvo)}
        self.assertIn("Rei Aldren.md", nomes)                       # citado por Valia
        self.assertIn("Porto.md", nomes)                            # cita Valia
        self.assertGreater(requisicao.estimar_tokens(requisicao.nova("melhorar", self.alvo)), 0)

    def test_presets(self):
        req = requisicao.nova("melhorar", self.alvo, genero="horror_cosmico", profundidade="detalhado")
        requisicao.salvar_preset("Caverna", req)
        outra = requisicao.aplicar_preset("Caverna", requisicao.nova("aventura", self.alvo))
        self.assertEqual((outra.genero, outra.profundidade, outra.tipo), ("horror_cosmico", "detalhado", "aventura"))
        requisicao.excluir_preset("Caverna")
        self.assertNotIn("Caverna", requisicao.listar_presets())

    def test_modo_acrescentar_e_estilo_no_pedido(self):
        req = requisicao.nova("melhorar", self.alvo, "acrescente rumores", modo="acrescentar", genero="horror_cosmico",
                              segredo=True)
        with ia_falsa("## Rumores\nDizem que o rei não dorme.") as ia:
            self.assertTrue(melhorar.melhorar_arquivo(self.alvo, requisicao=req))
        texto = self.alvo.read_text(encoding="utf-8")
        self.assertTrue(texto.startswith("# Valia\nstatus: segredo\nGovernada por"))   # texto original mantido
        self.assertIn("## Rumores", texto)
        self.assertIn("Horror Cósmico", ia.ultima["system_instruction"])
        self.assertIn("NÃO reescreva", ia.ultima["contents"])


class TesteNotas(unittest.TestCase):
    def setUp(self):
        usar_idioma("pt_br")
        self.raiz = novo_projeto({"Thorvald.md": "# Rei Thorvald\nGoverna Vog'Mur."})
        self.alvo = self.raiz / "Thorvald.md"

    def tearDown(self):
        apagar(self.raiz)
        usar_idioma("pt_br")

    def test_nota_secreta_e_lista(self):
        notas.adicionar_nota(self.alvo, "Ele lucra com a crise.", "silent")
        notas.adicionar_nota(self.alvo, "Eu nunca traí meu povo.", "roleplay", "Rei Thorvald")
        texto = self.alvo.read_text(encoding="utf-8")
        self.assertIn("## 🤫 Notas do Mestre [segredo]", texto)
        self.assertEqual(texto.count("Notas do Mestre"), 1)
        lista = notas.listar_notas(self.alvo)
        self.assertEqual([n["depoimento"] for n in lista], [False, True])
        self.assertEqual(lista[1]["texto"], "Eu nunca traí meu povo.")
        jogadores = pu.montar_contexto_mundo(is_dm=False)
        self.assertIn("Governa Vog'Mur", jogadores)
        self.assertNotIn("lucra com a crise", jogadores)            # escondida dos jogadores
        self.assertIn("lucra com a crise", pu.montar_contexto_mundo(is_dm=True))

    def test_secao_em_ingles_reconhecida_e_arquivo_travado(self):
        self.alvo.write_text("# King\ntext\n\n## 🤫 GM Notes [secret]\n### Note from Silent — x\n> keep\n", encoding="utf-8")
        corpo, secao = notas.separar(self.alvo.read_text(encoding="utf-8"))
        self.assertNotIn("GM Notes", corpo)
        self.assertIn("> keep", secao)
        ex.marcar_processamento(self.alvo, True)
        try:
            with self.assertRaises(notas.ErroNotas):
                notas.adicionar_nota(self.alvo, "x", "mestre")
        finally:
            ex.marcar_processamento(self.alvo, False)

    def test_ferramentas_preservam_e_consideram_as_notas(self):
        notas.adicionar_nota(self.alvo, "Ele lucra com a crise.", "silent")
        with ia_falsa("# Rei Thorvald\nTexto novo.\n\n## 🤫 Notas do Mestre [segredo]\nCÓPIA DA IA") as ia:
            melhorar.melhorar_arquivo(self.alvo, "melhore")
        texto = self.alvo.read_text(encoding="utf-8")
        self.assertIn("Texto novo.", texto)
        self.assertIn("Ele lucra com a crise.", texto)
        self.assertNotIn("CÓPIA DA IA", texto)                     # a seção original vence a cópia da IA
        self.assertIn("Ele lucra com a crise.", ia.ultima["contents"])
        self.alvo.write_text(texto.replace("Texto novo.", "Texto novo. <-- TODO: mais"), encoding="utf-8")
        with ia_falsa(lambda k: json.dumps({"aprovado": True, "critica": "ok", "texto_final": "# Rei Thorvald\n" + "y " * 40})
                      if k.get("response_schema") else "# Rei Thorvald\nexpandido"):
            ex.processar_arquivo_unico(self.alvo)
        self.assertIn("Ele lucra com a crise.", self.alvo.read_text(encoding="utf-8"))


class TesteFichas(unittest.TestCase):
    def setUp(self):
        usar_idioma("pt_br")
        self.raiz = novo_projeto({"Ignarax.md": "# Ignarax\nO elemental do vulcão."})
        self.alvo = self.raiz / "Ignarax.md"

    def tearDown(self):
        apagar(self.raiz)
        cfg.atualizar_configuracoes({"rpg_sistema_ativo": "dnd5e"})

    def test_matematica_do_srd(self):
        self.assertEqual(fichas.normalizar_nd("ND 5 (1.800 XP)"), "5")
        self.assertEqual(fichas.normalizar_nd("0.5"), "1/2")
        self.assertEqual([fichas.bonus_proficiencia(nd) for nd in ("1/4", "4", "5", "9", "17", "30")], [2, 2, 3, 4, 6, 9])
        self.assertEqual(fichas.formatar_mod(18), "18 (+4)")
        self.assertEqual(fichas.formatar_mod(7), "7 (-2)")

    def test_ficha_5e_e_regerar_sem_duplicar(self):
        notas.adicionar_nota(self.alvo, "Fraco contra água.", "mestre")
        with ia_falsa(lambda k: ficha_5e(forca=18, nivel_de_desafio="ND 5 (errado)")):
            self.assertTrue(geradores.gerar_ficha(self.alvo, tipo="monstro"))
            self.assertTrue(geradores.gerar_ficha(self.alvo, tipo="monstro"))
        texto = self.alvo.read_text(encoding="utf-8")
        self.assertEqual(texto.count("## ⚔️ Ficha de Combate"), 1)
        self.assertIn("18 (+4)", texto)
        self.assertIn("5 (1,800 XP)", texto)
        self.assertIn("Bônus de Proficiência +3", texto)
        self.assertTrue(texto.rstrip().endswith("> Fraco contra água."))   # notas continuam no fim
        self.assertIn("O elemental do vulcão.", texto)

    def test_outro_sistema_em_texto(self):
        cfg.atualizar_configuracoes({"rpg_sistema_ativo": "tormenta20"})
        with ia_falsa("Ignarax ND 5, PV 90, Defesa 20") as ia:
            self.assertTrue(geradores.gerar_ficha(self.alvo))
        self.assertIsNone(ia.ultima.get("response_schema"))
        self.assertIn("## ⚔️ Ficha de Combate\nIgnarax ND 5", self.alvo.read_text(encoding="utf-8"))


class TesteConselhoMor(unittest.TestCase):
    def setUp(self):
        usar_idioma("pt_br")
        self.raiz = novo_projeto({"Capital.md": "# Capital\nO Rei Thorvald trama com Conselheira Ilsa."})
        self.alvo = self.raiz / "Capital.md"
        pe.salvar_persona("Conselheira Ilsa", {"nome": "Conselheira Ilsa"},
                          [{"autor": pe.AUTOR_INTERLOCUTOR, "texto": "Você é leal?"},
                           {"autor": "Conselheira Ilsa", "texto": "Só ao ouro."}])

    def tearDown(self):
        apagar(self.raiz)

    def test_conselho_usa_depoimentos_notas_e_conversas(self):
        notas.adicionar_nota(self.alvo, "Eu salvarei Vog'Mur, custe o que custar.", "roleplay", "Rei Thorvald")
        notas.adicionar_nota(self.alvo, "O rei deveria ter um plano B.", "silent")
        resposta = {"arquiteto": "a", "cronista": "c", "falas_npcs": [], "tatico_e_caos": "t"}
        with ia_falsa(json.dumps(resposta)) as ia:
            resultado = ce.executar_deliberacao_paineis(self.alvo, "aprofundar")
        pedido = ia.ultima["contents"]
        for trecho in ("custe o que custar", "plano B", "Só ao ouro.", "DEPOIMENTOS DO ROLEPLAY"):
            self.assertIn(trecho, pedido)
        self.assertNotIn("## 🤫 Notas do Mestre", pedido.split("DEPOIMENTOS")[0])   # o arquivo vai sem a seção
        self.assertIn("1 depoimento", resultado["fontes"])
        self.assertIn("Conselheira Ilsa", resultado["fontes"])

        final = {"resumo_decisao_juiz": "ok", "conteudo_markdown": "# Capital\nVersão do Juiz."}
        with ia_falsa(json.dumps(final)):
            ce.sintetizar_e_salvar_arquivo_canonica(self.alvo, "a", "c", "n", "t", "d")
        texto = self.alvo.read_text(encoding="utf-8")
        self.assertIn("Versão do Juiz.", texto)
        self.assertIn("custe o que custar", texto)                  # notas preservadas

    def test_sem_insumos(self):
        resposta = {"arquiteto": "a", "cronista": "c", "falas_npcs": [], "tatico_e_caos": "t"}
        outro = novo_projeto({"Ermo.md": "# Ermo\nNinguém mora aqui."})
        try:
            with ia_falsa(json.dumps(resposta)):
                self.assertEqual(ce.executar_deliberacao_paineis(outro / "Ermo.md", "x")["fontes"], "")
        finally:
            apagar(outro)


if __name__ == "__main__":
    unittest.main()
