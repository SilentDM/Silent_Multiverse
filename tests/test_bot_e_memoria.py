"""Bot do Discord (sem conexão real), dados e memória."""
import types
import unittest

from tests.util import usar_idioma

import bot.dice_roller as dados
import core.memory as me
import engine.project_utils as pu


class TesteDados(unittest.TestCase):
    def test_rolagens_e_uso(self):
        usar_idioma("pt_br")
        for expressao in ("1d20+5", "2d6+3 dano", "2d20kh1+3", "3#1d8+2"):
            self.assertNotIn("Uso", dados.rolar_dados(expressao), expressao)
        self.assertIn("Uso", dados.rolar_dados(""))
        usar_idioma("en_us")
        self.assertIn("Usage", dados.rolar_dados("bananas"))
        usar_idioma("pt_br")


class TesteRespostas(unittest.TestCase):
    def test_corte_de_frase_preserva_links_e_markdown(self):
        link = "A regra diz que não pode.\n🔗 [Ver no Discord](https://discord.com/x)"
        self.assertEqual(me.trim_incomplete_sentences(link), link)
        lista = "# Título\n\nParágrafo.\n\n- item um\n- item dois"
        self.assertEqual(me.trim_incomplete_sentences(lista), lista)
        cortado = "Frase um.\n\nFrase dois completa. E então o dragão"
        self.assertEqual(me.trim_incomplete_sentences(cortado), "Frase um.\n\nFrase dois completa.")

    def test_intencao_em_portugues_e_ingles(self):
        usar_idioma("pt_br")
        self.assertEqual(pu.detectar_intencao("Onde fica Valia?"), "Foque na localização")
        self.assertEqual(pu.detectar_intencao("Where is Valia?"), "Foque na localização")
        self.assertEqual(pu.detectar_intencao("cômodo antigo"), "")   # não confunde "como" dentro de palavras


class TestePermissaoMestre(unittest.TestCase):
    def test_ids_de_mestre(self):
        try:
            import bot.bot_actions as ba
        except ImportError:
            self.skipTest("discord.py não instalado")
        mensagem = types.SimpleNamespace(author=types.SimpleNamespace(id=123456789012345678, name="gm", roles=[]))
        self.assertTrue(ba.verificar_permissao_mestre(mensagem, {"discord_roles_dm": ""}, "111, 123456789012345678"))
        self.assertFalse(ba.verificar_permissao_mestre(mensagem, {"discord_roles_dm": ""}, "999"))
        cargo = types.SimpleNamespace(name="Mestre")
        mensagem.author.roles = [cargo]
        self.assertTrue(ba.verificar_permissao_mestre(mensagem, {"discord_roles_dm": "Mestre, DM"}, ""))


if __name__ == "__main__":
    unittest.main()
