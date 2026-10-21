"""
Homebrew do 5etools: catálogo sem aventuras/livros/oficiais, download só das fontes escolhidas, conversão do
formato do 5etools, busca de opções para o NPC e crédito do autor na ficha. Sem rede (downloads falsos).
"""
import json
import unittest
from unittest import mock

import tests  # noqa: F401  (isola a pasta de dados)
from tests.util import novo_projeto, apagar, ia_falsa

import core.config as cfg
import engine.foundry as fvtt
import engine.homebrew as homebrew

INDICE = {
    "race": {"race/Benjamin Huffman; Beastfolk.json": "race", "race/D&D 4ed; Dark Sun Races.json": "race",
             "adventure/Someone; Big Adventure.json": "adventure"},
    "monster": {"creature/Dragonix; Monster Manual Expanded.json": "creature",
                "book/Ghostfire Gaming; Codex.json": "book"},
    "feat": {"race/Benjamin Huffman; Beastfolk.json": "race"},
}
BEASTFOLK = {
    "_meta": {"sources": [{"json": "BF", "full": "Beastfolk", "authors": ["Benjamin Huffman"]}]},
    "race": [{"name": "Beastfolk", "source": "BF", "entries": [
        {"type": "entries", "name": "Age", "entries": ["Beastfolk age as humans do."]},
        {"type": "entries", "name": "Keen Senses", "entries": ["You have proficiency in the {@skill Perception} skill."]},
    ]}],
    "feat": [{"name": "Beast Whisperer", "source": "BF", "prerequisite": [{"race": [{"name": "Beastfolk|BF"}]}],
              "entries": ["You can speak with beasts:", {"type": "list", "items": ["As the {@spell speak with animals} spell."]}]}],
}
DRAGONIX = {
    "_meta": {"sources": [{"json": "MME", "full": "Monster Manual Expanded", "authors": ["Dragonix"]}]},
    "monster": [{"name": "Abyssal Rotfiend", "source": "MME", "type": {"type": "undead", "tags": ["demon"]}, "cr": "16",
                 "trait": [{"name": "Abyssal Fields", "entries": ["No enemy can teleport within 25 ft."]}],
                 "action": [{"name": "Skullsplitter", "entries": [
                     "{@atk ms} {@hit 10} to hit, range 30 ft. {@h}23 ({@damage 3d8 + 10}) psychic damage. {@recharge 5}"]}]},
                {"name": "Dwarf Ghost Miner", "source": "MME", "type": "undead", "cr": {"cr": "3"},
                 "trait": [{"name": "Stonecunning Dead", "entries": ["Knows every tunnel ({@dc 13} to resist)."]}]}],
}
ARQUIVOS = {homebrew.INDICE: INDICE, "race/Benjamin Huffman; Beastfolk.json": BEASTFOLK,
            "creature/Dragonix; Monster Manual Expanded.json": DRAGONIX}


def baixar_falso(caminho):
    return json.dumps(ARQUIVOS[caminho]).encode("utf-8")


class TesteHomebrew(unittest.TestCase):
    def setUp(self):
        cfg.atualizar_configuracoes({"homebrew_fontes": []})
        homebrew._carregar.cache_clear()

    def tearDown(self):
        for fonte in homebrew.fontes_escolhidas():
            homebrew.desativar_fonte(fonte)

    def _ativar_tudo(self):
        homebrew.ativar_fonte("race/Benjamin Huffman; Beastfolk.json", baixar=baixar_falso)
        homebrew.ativar_fonte("creature/Dragonix; Monster Manual Expanded.json", baixar=baixar_falso)

    def test_catalogo_deixa_de_fora_aventuras_livros_e_oficiais(self):
        catalogo = homebrew.atualizar_catalogo(baixar=baixar_falso)
        arquivos = {f["arquivo"]: f for f in catalogo}
        self.assertEqual(set(arquivos), {"race/Benjamin Huffman; Beastfolk.json",
                                         "creature/Dragonix; Monster Manual Expanded.json"})
        beastfolk = arquivos["race/Benjamin Huffman; Beastfolk.json"]
        self.assertEqual((beastfolk["autor"], beastfolk["titulo"]), ("Benjamin Huffman", "Beastfolk"))
        self.assertEqual(beastfolk["tipos"], ["race", "feat"])
        self.assertEqual(homebrew.catalogo(), catalogo)                      # fica salvo

    def test_converter_formato_do_5etools(self):
        texto = homebrew.converter_texto("{@atk mw,rw} {@hit 5} to hit. {@h}7 ({@damage 2d6}) damage, "
                                         "{@dc 13} or {@condition prone|XPHB}. {@recharge 5} {@creature goblin|MM|the goblin}")
        self.assertEqual(texto, "Melee or Ranged Weapon Attack: +5 to hit. Hit: 7 (2d6) damage, DC 13 or prone. "
                                "(Recharge 5–6) the goblin")
        lista = homebrew.texto_das_entradas([{"type": "entries", "name": "Keen", "entries": ["One.", {"type": "list", "items": ["Two."]}]}])
        self.assertEqual(lista, "Keen. One.\n• Two.")

    def test_ativar_e_desativar_fonte(self):
        self._ativar_tudo()
        self.assertEqual(len(homebrew.fontes_escolhidas()), 2)
        assinatura = homebrew.assinatura()
        self.assertTrue(assinatura)
        homebrew.desativar_fonte("race/Benjamin Huffman; Beastfolk.json")
        self.assertEqual(homebrew.fontes_escolhidas(), ["creature/Dragonix; Monster Manual Expanded.json"])
        self.assertNotEqual(homebrew.assinatura(), assinatura)
        self.assertFalse(homebrew._arquivo_local("race/Benjamin Huffman; Beastfolk.json").exists())

    def test_candidatos_combinam_com_o_npc(self):
        self.assertEqual(homebrew.candidatos("Borin é um anão mineiro."), [])      # sem fontes, nada
        self._ativar_tudo()
        # "anão" e "fantasma" em português casam com dwarf e ghost em inglês
        nomes = [o["nome"] for o in homebrew.candidatos("Borin é o fantasma de um anão mineiro.")]
        self.assertEqual(nomes[0], "Stonecunning Dead")
        self.assertNotIn("Keen Senses", " ".join(nomes))
        nomes = [o["nome"] for o in homebrew.candidatos("Kara is a beastfolk ranger.")]
        self.assertEqual(nomes[:2], ["Beastfolk", "Beast Whisperer"])                # raça e o talento dela
        self.assertEqual(homebrew.candidatos("Um mercador humano comum."), [])

    def test_texto_para_a_ia_tem_credito_e_corta_textos_longos(self):
        self._ativar_tudo()
        opcoes = homebrew.candidatos("O fantasma de um anão.")
        texto = homebrew.texto_para_prompt(opcoes)
        self.assertIn("[fonte: Monster Manual Expanded — Dragonix]", texto)
        self.assertIn("habilidade de Dwarf Ghost Miner, ND 3", texto)
        longo = dict(opcoes[0], texto="palavra " * 200)
        self.assertLess(len(homebrew.texto_para_prompt([longo])), homebrew.LIMITE_TEXTO + 200)

    def test_ficha_leva_opcoes_para_a_ia_e_credito_na_descricao(self):
        self._ativar_tudo()
        raiz = novo_projeto({"NPCs/Borin.md": "# Borin\nO fantasma de um anão mineiro."})
        pedidos = []
        ficha = {"nome": "Borin", "tamanho": "med", "tipo_criatura": "undead", "subtipo": "anão", "alinhamento": "Neutro",
                 "classe_armadura": 12, "pontos_de_vida": 30, "formula_pv": "5d8 + 5", "deslocamento_pes": 25, "voo_pes": 0,
                 "natacao_pes": 0, "escalada_pes": 0, "forca": 10, "destreza": 12, "constituicao": 12, "inteligencia": 10,
                 "sabedoria": 12, "carisma": 8, "testes_resistencia": [], "pericias": [], "nivel_desafio": 2,
                 "visao_escuro_pes": 60, "idiomas": ["Anão"], "resistencias": [], "imunidades": [], "imunidades_condicao": [],
                 "ataques": [],
                 "habilidades": [{"nome": "Morto que Conhece a Pedra", "ativacao": "passive", "descricao": "Conhece os túneis.",
                                  "fonte": "Monster Manual Expanded — Dragonix"}],
                 "biografia_publica": "Um fantasma.", "biografia_mestre": "Guarda a mina."}

        def resposta(chamada):
            pedidos.append(str(chamada.get("contents")))
            return json.dumps(ficha)
        try:
            with ia_falsa(resposta):
                dados = fvtt.gerar_ficha("NPCs/Borin.md")
            self.assertIn("Stonecunning Dead", pedidos[0])
            self.assertIn("[fonte: Monster Manual Expanded — Dragonix]", pedidos[0])
            self.assertIn("Fonte: Monster Manual Expanded — Dragonix", dados["habilidades"][0]["descricao_html"])
            with ia_falsa(resposta):
                fvtt.gerar_ficha("NPCs/Borin.md")
            self.assertEqual(len(pedidos), 1)                                    # cache
            homebrew.desativar_fonte("race/Benjamin Huffman; Beastfolk.json")
            with ia_falsa(resposta):
                fvtt.gerar_ficha("NPCs/Borin.md")
            self.assertEqual(len(pedidos), 2)                                    # outras fontes: gera de novo
        finally:
            apagar(raiz)


if __name__ == "__main__":
    unittest.main()
