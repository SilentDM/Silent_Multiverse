"""Toda chamada de IA e todo conteúdo gerado seguem o idioma escolhido (com IA falsa, sem rede)."""
import json
import unittest

from tests.util import novo_projeto, apagar, usar_idioma, ia_falsa

import core.ai_utils as au
import core.silent_persona as silent
import engine.dnd_schemas as dnd
import engine.expander as ex
import engine.knowledge_schemas as ks
import engine.persona_engine as pe
import engine.wbuilder as wb

T20 = dict(cd_base=12, pericia_ou_atributo="x", ate_5_falha_critica="a", de_6_a_10_falha_parcial="b",
           de_11_a_15_sucesso="c", de_16_a_20_excelente="d", acima_21_critico="e")


def aventura():
    return dnd.ModuloAventura5Rooms(
        titulo_aventura="T", nivel_recomendado="1", premissa_e_gancho="p", localizacao_mundo="l",
        tom_e_atmosfera="t", relogio_de_eventos="r",
        oponente_principal=dnd.StatblockDND(nome="Boss", tipo_e_alinhamento="x", ca=15, pv="10", nd_e_xp="1", ataque_principal="a"),
        sala1=dnd.Sala1Guardiao(titulo_sala="1", narracao="n", ameaca_inicial="a", teste_d20=T20),
        sala2=dnd.Sala2Enigma(titulo_sala="2", narracao="n", natureza_desafio="d", teste_d20=T20, recompensa_de_sucesso="r"),
        sala3=dnd.Sala3Reviravolta(titulo_sala="3", narracao="n", a_reviravolta="r", dilema_moral="d", teste_d20=T20),
        sala4=dnd.Sala4Climax(titulo_sala="4", narracao="n", efeito_ambiental_covil="e", interacao_dinamica="i", teste_d20=T20),
        sala5=dnd.Sala5Consequencias(titulo_sala="5", narracao="n", tesouros=["ouro"], complicacao_fuga="c",
                                     evolucao_mundo="e", gancho_futuro="g"))


class TesteIdiomaDaIA(unittest.TestCase):
    CASOS = {
        "pt_br": {"linha": "Responda SEMPRE em português do Brasil", "chat": "Você é Silent",
                  "sala": "## SALA 1:", "lore": "Verificações de Conhecimento", "desc": "True se"},
        "en_us": {"linha": "Always answer in American English", "chat": "You are Silent",
                  "sala": "## ROOM 1:", "lore": "## 🎲 Lore Checks", "desc": "True if"},
    }

    def setUp(self):
        self.raiz = novo_projeto({"Valia.md": "# Valia\n<-- TODO: descrever"})

    def tearDown(self):
        apagar(self.raiz)
        usar_idioma("pt_br")

    def test_linha_de_idioma_e_prompts(self):
        for idioma, esperado in self.CASOS.items():
            with self.subTest(idioma=idioma):
                usar_idioma(idioma)
                with ia_falsa("Resposta.") as ia:
                    silent.conversar("Quem é Valia?")
                    self.assertIn(esperado["chat"], ia.ultima["system_instruction"])
                    self.assertIn(esperado["linha"], ia.ultima["system_instruction"])
                    au.ask_ai(contents="x")   # mesmo sem instrução própria, o idioma é garantido
                    self.assertIn(esperado["linha"], ia.ultima["system_instruction"])

    def test_schema_com_descricoes_traduzidas(self):
        for idioma, esperado in self.CASOS.items():
            with self.subTest(idioma=idioma):
                usar_idioma(idioma)
                with ia_falsa(lambda k: json.dumps({"aprovado": True, "critica": "ok", "texto_final": "# Valia\n" + "x " * 40})
                              if k.get("response_schema") else "# Valia\nexpandido") as ia:
                    (self.raiz / "Valia.md").write_text("# Valia\n<-- TODO: descrever", encoding="utf-8")
                    ex.processar_arquivo_unico(self.raiz / "Valia.md")
                    schema = next(c["response_schema"] for c in ia.chamadas if c.get("response_schema"))
                    descricao = schema.model_json_schema()["properties"]["aprovado"]["description"]
                    self.assertTrue(descricao.startswith(esperado["desc"]), descricao)
                    self.assertIsNot(schema, ex.RevisaoLore)

    def test_markdown_gerado(self):
        for idioma, esperado in self.CASOS.items():
            with self.subTest(idioma=idioma):
                usar_idioma(idioma)
                self.assertIn(esperado["sala"], dnd.aventura_5rooms_para_markdown(aventura()))
                comp = ks.CompendioConhecimento(tema_entidade="G", resumo_mestre="r", testes=[])
                self.assertIn(esperado["lore"], ks.compendio_para_markdown(comp))

    def test_persona_guarda_marcador_interno(self):
        usar_idioma("en_us")
        pe.salvar_persona("Varis", {"nome": "Varis", "instrucoes_de_atuacao": ["x"]},
                          [{"autor": pe.AUTOR_INTERLOCUTOR, "texto": "oi"}])
        with ia_falsa("Hello.") as ia:
            pe.dialogar_com_persona("Varis", "hi")
            self.assertIn("Speaker: oi", ia.ultima["contents"])
        self.assertEqual(pe.carregar_persona("Varis")[1][-2]["autor"], "Interlocutor")

    def test_planejador_respeita_permissoes(self):
        import core.config as cfg
        usar_idioma("en_us")
        cfg.atualizar_configuracoes({"wb_allow_create_folder": False})
        try:
            canon = {"titulo": "T", "premissa": "p", "visao_geral_publica": "v", "entidades": []}
            with ia_falsa(lambda k: json.dumps(canon if k["response_schema"].__name__ == "CanonCampanha" else {"actions": []})) as ia:
                wb.gerar_canon("goal X")
                wb.gerar_plano()
                self.assertIn("goal X", ia.chamadas[0]["contents"])
                instrucao = ia.chamadas[1]["system_instruction"]
                self.assertIn("FORBIDDEN", instrucao)
                self.assertNotIn("CreateFolder", instrucao.split("ALLOWED TOOLS")[1].split("WHAT EACH TOOL")[0])
                self.assertIn("goal X", ia.chamadas[1]["contents"])
        finally:
            cfg.atualizar_configuracoes({"wb_allow_create_folder": True})


if __name__ == "__main__":
    unittest.main()
