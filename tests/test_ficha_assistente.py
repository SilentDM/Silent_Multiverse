"""
Ficha editável da Interpretação (salva no JSON e usada na conversa) e o assistente de primeira execução.
IA falsa, sem rede.
"""
import os
import unittest
from unittest import mock

from tests.util import usar_idioma, ia_falsa, novo_projeto, apagar

import core.config as cfg
import engine.acoes as acoes
import engine.persona_engine as pe

try:
    import tkinter as tk
    tk.Tk().destroy()
    TEM_TELA = True
except Exception:
    TEM_TELA = False

DADOS = {
    "nome": "Morvath", "titulo_ou_alcunha": "O Lich das Cinzas", "alinhamento_moral": "Neutro e Mau",
    "ocupacao_ou_papel": "Arcanista", "genero": "Masculino", "raca": "Lich", "idade_aparente": "Ancião",
    "tom_de_pele": "Cinzenta", "cabelo": "Nenhum", "olhos": "Brasas", "vestimentas_e_acessorios": "Manto",
    "tracos_marcantes": "Coroa partida", "psicologia_e_temperamento": "Paciente", "tom_de_voz_e_estilo_fala": "Sussurrado",
    "motivacao_primaria": "Despertar o vulcão", "fraqueza_ou_medo_oculto": "O filactério na forja",
    "bordao_ou_frase_marcante": "Tudo queima.", "instrucoes_de_atuacao": ["Nunca revele o filactério."],
    "prompt_visual_ingles": "A gaunt lich with ember eyes",
}


class TesteFichaEditavel(unittest.TestCase):
    def setUp(self):
        usar_idioma("pt_br")
        pe.salvar_persona("Morvath", dict(DADOS), [{"autor": pe.AUTOR_INTERLOCUTOR, "texto": "Olá"}])

    def tearDown(self):
        (pe.PASTA_PERSONAS / "Morvath.json").unlink(missing_ok=True)

    def test_ficha_gerada_tem_o_retrato_e_nao_esta_editada(self):
        ficha = pe.ficha("Morvath")
        self.assertFalse(ficha["editada"])
        self.assertIn("# Morvath", ficha["markdown"])
        self.assertIn("## 🎨", ficha["markdown"])
        self.assertIn("A gaunt lich with ember eyes", ficha["markdown"])
        self.assertFalse(pe.salvar_ficha("Morvath", ficha["markdown"]))        # nada mudou: nada gravado

    def test_edicao_salva_no_json_e_vale_na_conversa(self):
        texto = pe.ficha("Morvath")["markdown"].replace("Sussurrado", "Gritado e impaciente")
        texto = texto.replace("A gaunt lich with ember eyes", "A towering lich wreathed in blue fire")
        self.assertTrue(pe.salvar_ficha("Morvath", texto))
        dados, historico = pe.carregar_persona("Morvath")
        self.assertEqual(dados[pe.CHAVE_FICHA], texto.rstrip())
        self.assertEqual(dados["prompt_visual_ingles"], "A towering lich wreathed in blue fire")   # retrato segue a ficha
        self.assertEqual(len(historico), 1)                                       # o histórico continua lá
        self.assertTrue(pe.ficha("Morvath")["editada"])

        with ia_falsa("Queimem!") as ia:
            pe.dialogar_com_persona("Morvath", "Quem é você?")
        instrucao = ia.ultima["system_instruction"]
        self.assertIn("Gritado e impaciente", instrucao)
        self.assertNotIn("A towering lich", instrucao)                            # o pedido do retrato não vai para a fala
        self.assertEqual(len(pe.carregar_persona("Morvath")[1]), 3)

    def test_linha_acrescentada_no_fim_nao_entra_no_retrato(self):
        texto = pe.ficha("Morvath")["markdown"] + "\n- Fala sempre olhando para o fogo."
        pe.salvar_ficha("Morvath", texto)
        self.assertEqual(pe.carregar_persona("Morvath")[0]["prompt_visual_ingles"], "A gaunt lich with ember eyes")
        with ia_falsa("...") as ia:
            pe.dialogar_com_persona("Morvath", "Oi")
        self.assertIn("olhando para o fogo", ia.ultima["system_instruction"])
        self.assertIn("Nunca revele o filactério", ia.ultima["system_instruction"])

    def test_edicao_durante_a_resposta_nao_se_perde(self):
        def responder(_chamada):
            pe.salvar_ficha("Morvath", "# Morvath\nEDITADO ENQUANTO A IA RESPONDIA")
            return "..."
        with ia_falsa(responder):
            pe.dialogar_com_persona("Morvath", "Oi")
        self.assertIn("EDITADO ENQUANTO", pe.carregar_persona("Morvath")[0][pe.CHAVE_FICHA])

    def test_restaurar_volta_a_ficha_gerada(self):
        pe.salvar_ficha("Morvath", "# Morvath\nqualquer coisa")
        texto = pe.restaurar_ficha("Morvath")
        self.assertIn("Tudo queima.", texto)
        self.assertNotIn(pe.CHAVE_FICHA, pe.carregar_persona("Morvath")[0])


class TesteAssistente(unittest.TestCase):
    def tearDown(self):
        cfg.atualizar_configuracoes({"assistente_concluido": True})

    def test_so_aparece_para_quem_nao_tem_chave(self):
        cfg.atualizar_configuracoes({"assistente_concluido": False})
        with mock.patch.dict(os.environ, {"GOOGLE_API_KEY": ""}):
            self.assertTrue(acoes.precisa_assistente())
        with mock.patch.dict(os.environ, {"GOOGLE_API_KEY": "abc"}):
            self.assertFalse(acoes.precisa_assistente())                         # quem já usa o programa não vê
        acoes.concluir_assistente()
        with mock.patch.dict(os.environ, {"GOOGLE_API_KEY": ""}):
            self.assertFalse(acoes.precisa_assistente())


@unittest.skipUnless(TEM_TELA, "sem ambiente gráfico")
class TesteTelas(unittest.TestCase):
    def setUp(self):
        self.raiz = novo_projeto({"Valia.md": "# Valia"})
        self.outro = novo_projeto({"Outro.md": "# Outro"})
        self.patches = [mock.patch("bot.runner.iniciar"), mock.patch("bot.runner.parar"),
                        mock.patch("core.modelos_gemini.atualizar_se_necessario"),
                        mock.patch("core.atualizacoes.verificar_na_inicializacao"),
                        mock.patch("ui.app.SilentApp._iniciar_bandeja")]
        for p in self.patches:
            p.start()
        cfg.atualizar_configuracoes({"assistente_concluido": True})
        pe.salvar_persona("Morvath", dict(DADOS), [])

    def tearDown(self):
        for p in self.patches:
            p.stop()
        (pe.PASTA_PERSONAS / "Morvath.json").unlink(missing_ok=True)
        cfg.atualizar_configuracoes({"assistente_concluido": True, "idioma": "pt_br"})
        apagar(self.raiz)
        apagar(self.outro)
        usar_idioma("pt_br")

    def _montar(self):
        import ui.app as app
        from tests.test_interface import fechar
        usar_idioma("pt_br")
        root = tk.Tk()
        root.withdraw()
        janela = app.SilentApp(root)
        root.update()
        return root, janela, fechar

    def test_assistente(self):
        from ui.dialogs.first_run import AssistenteInicial
        root, janela, fechar = self._montar()
        try:
            assistente = AssistenteInicial(janela)
            self.assertEqual(assistente.lbl_titulo.cget("text"), "Bem-vindo ao Silent Multiverse Nexus")
            assistente.var_idioma.set("en_us")
            assistente._idioma_escolhido()
            self.assertEqual(assistente.lbl_titulo.cget("text"), "Welcome to Silent Multiverse Nexus")  # na hora
            assistente._proximo()
            assistente.var_chave.set("chave-de-teste")
            assistente._proximo()
            assistente.pasta = str(self.outro)
            assistente._proximo()
            self.assertEqual(assistente.btn_proximo.cget("text"), "Start")
            with mock.patch("engine.acoes.salvar_chave_gemini") as salvar, \
                    mock.patch("engine.style_manager.aplicar_idioma") as modelos_no_idioma, \
                    mock.patch.object(janela, "reiniciar") as reiniciar:
                assistente._proximo()                                             # Começar
            salvar.assert_called_once_with("chave-de-teste")
            reiniciar.assert_called_once()                                        # idioma da interface mudou
            modelos_no_idioma.assert_called_once()                                # modelos iniciais no novo idioma
            self.assertEqual(acoes.projeto_ativo()[1], str(self.outro.resolve()))
            self.assertEqual(cfg.obter("idioma"), "en_us")
            self.assertTrue(cfg.obter("assistente_concluido"))
        finally:
            fechar(root)

    def test_ficha_editavel_salva_sozinha(self):
        root, janela, fechar = self._montar()
        try:
            pagina = janela.pagina("roleplay")
            pagina._atualizar_lista("Morvath")
            pagina.ficha.insert("end", "\nNOVO DETALHE DO MESTRE")
            pagina._ficha_editada()
            self.assertEqual(pagina.lbl_ficha.cget("text"), "● Salvando...")
            pagina._salvar_ficha_agora()
            self.assertIn("NOVO DETALHE DO MESTRE", pe.carregar_persona("Morvath")[0][pe.CHAVE_FICHA])
            self.assertEqual(pagina.lbl_ficha.cget("text"), "✓ Salvo")
        finally:
            fechar(root)

    def test_acoes_em_grupos(self):
        root, janela, fechar = self._montar()
        try:
            pagina = janela.pagina("actions")
            titulos = [c.cget("text") for c in pagina.grade.caixas]
            self.assertEqual(titulos, ["Gerar", "Analisar", "Manutenção", "Zona de perigo"])
            self.assertEqual(pagina.grade.caixas[-1].cget("style"), "Perigo.TLabelframe")
            self.assertEqual(str(pagina.botoes["memorias"].cget("style")), "Perigo.TButton")
        finally:
            fechar(root)


if __name__ == "__main__":
    unittest.main()
