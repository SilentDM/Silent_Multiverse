"""Sessões: anotações livres durante a mesa e o diário de Silent ao finalizar. IA falsa, sem rede."""
import json
import unittest
from unittest import mock

from tests.util import novo_projeto, apagar, usar_idioma, ia_falsa

import core.propriedades as props
import engine.project_utils as pu
import engine.sessoes as sessoes

NOTAS = ("[20:10] grupo chega em Brasaforte, fala com o Rei Thorvald\n"
         "rei diz que tem 30 anos (?)\n"
         "taverneiro novo: Borin Pé-de-Ferro, anão caolho, deve favor ao grupo\n"
         "Thalindra achou o símbolo do lich no porão!!\n"
         "prometeram voltar com o martelo em 3 dias")

DIARIO = {
    "titulo": "O Símbolo no Porão",
    "cenas": [{"titulo": "Audiência", "resumo": "O grupo encontra o [[Rei Thorvald]] em [[Brasaforte]]."}],
    "nascidos_na_mesa": [{"nome": "Borin Pé-de-Ferro", "tipo": "NPC", "descricao": "Taverneiro anão caolho."}],
    "contradicoes": [{"dito_na_mesa": "O rei tem 30 anos.", "escrito_no_mundo": "O rei tem 54 anos.",
                      "arquivo": "[[Rei Thorvald]]", "sugestao": "Manter 54 e corrigir na próxima sessão."}],
    "segredos_em_risco": [{"segredo": "O lich sob o vulcão", "arquivo": "[[Morvath]]",
                           "situacao": "Thalindra viu o símbolo do lich."}],
    "pontas_soltas": ["Voltar com o martelo em 3 dias."],
    "conclusoes": ["Prepare a reação do lich ao símbolo descoberto."],
}


class TesteSessoes(unittest.TestCase):
    def setUp(self):
        usar_idioma("pt_br")
        self.raiz = novo_projeto({"Rei Thorvald.md": "# Rei Thorvald\n**Idade:** 54", "Brasaforte.md": "# Brasaforte"})
        self.rebuild = mock.patch("core.cache_gemini.force_rebuild_world_context").start()

    def tearDown(self):
        mock.patch.stopall()
        sessoes.salvar_notas("")
        apagar(self.raiz)

    def test_anotacoes_salvam_e_voltam(self):
        self.assertEqual(sessoes.carregar_notas(), "")
        sessoes.salvar_notas(NOTAS)
        self.assertEqual(sessoes.carregar_notas(), NOTAS)
        self.assertFalse((self.raiz / "Sessões").exists())                 # anotações não vão para o cofre
        self.assertNotIn("Borin", pu.montar_contexto_mundo(is_dm=True))      # nem para o contexto da IA

    def test_numeracao(self):
        self.assertEqual(sessoes.proximo_numero(), 1)
        (self.raiz / "Sessões").mkdir()
        (self.raiz / "Sessões" / "Sessão 3.md").write_text("---\ntype: sessao\nsession: 3\n---\n# x", encoding="utf-8")
        (self.raiz / "Sessões" / "Sessão 7.md").write_text("# sem propriedades", encoding="utf-8")
        self.assertEqual(sessoes.proximo_numero(), 8)
        self.assertEqual([n for n, _ in sessoes.listar_diarios()], [7, 3])

    def test_finalizar_escreve_o_diario(self):
        sessoes.salvar_notas(NOTAS)
        with ia_falsa(json.dumps(DIARIO)) as ia:
            caminho = sessoes.finalizar_sessao(NOTAS, 12)
        self.assertIn("Borin Pé-de-Ferro", ia.ultima["contents"])          # as anotações vão para a IA
        self.assertTrue(ia.ultima["use_world_context"])
        self.rebuild.assert_called_once()
        self.assertTrue(caminho.endswith("Sessão 12.md"))
        texto = open(caminho, encoding="utf-8").read()
        p = props.ler(texto)
        self.assertEqual((p["type"], p["session"], p["status"]), ("sessao", "12", "segredo"))
        for trecho in ("# Sessão 12: O Símbolo no Porão", "## 🎬 O que aconteceu", "[[Rei Thorvald]]",
                       "## 🌱 O que nasceu na mesa", "**[[Borin Pé-de-Ferro]]** (NPC)", "## ⚠️ O que contradiz o mundo",
                       "## 🤫 Segredos em risco", "## 🧵 Pontas soltas", "## 🔮 Conclusões de Silent",
                       "## 📝 Anotações da mesa", "prometeram voltar com o martelo"):
            self.assertIn(trecho, texto)
        self.assertEqual(sessoes.carregar_notas(), "")                      # a próxima sessão começa em branco
        self.assertEqual(sessoes.proximo_numero(), 13)
        self.assertNotIn("Símbolo no Porão", pu.montar_contexto_mundo(is_dm=False))   # diário é segredo

    def test_erros_nao_perdem_as_anotacoes(self):
        with self.assertRaises(sessoes.ErroSessao):
            sessoes.finalizar_sessao("   ")
        with ia_falsa(json.dumps(DIARIO)):
            sessoes.finalizar_sessao(NOTAS, 1)
        with self.assertRaises(sessoes.ErroSessao):                         # número já usado
            sessoes.finalizar_sessao(NOTAS, 1)
        with ia_falsa("isto não é JSON"), self.assertRaises(Exception):
            sessoes.finalizar_sessao(NOTAS + "\nmais", 2)
        self.assertIn("mais", sessoes.carregar_notas())                     # a IA falhou: anotações ficam

    def test_relatorio_para_o_worldbuilder(self):
        with ia_falsa(json.dumps(DIARIO)):
            caminho = sessoes.finalizar_sessao(NOTAS, 4)
        relatorio = sessoes.relatorio_para_worldbuilder(caminho)
        self.assertIn("Borin Pé-de-Ferro", relatorio)
        self.assertIn("O rei tem 54 anos.", relatorio)
        self.assertNotIn("Prepare a reação do lich", relatorio)              # só nascidos e contradições
        self.assertNotIn("prometeram voltar", relatorio)


if __name__ == "__main__":
    unittest.main()
