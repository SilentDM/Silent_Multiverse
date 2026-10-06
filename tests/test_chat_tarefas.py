"""
Chat do Silent (anexos, imagens, atalhos, Markdown) e a barra de tarefas (parar uma tarefa só).
IA falsa, sem rede.
"""
import io
import threading
import time
import unittest
import unittest.mock

from PIL import Image

from tests.util import novo_projeto, apagar, usar_idioma, ia_falsa

import core.atalhos_chat as atalhos
import core.markdown_simples as md
import core.silent_persona as silent
import engine.acoes as acoes
import engine.documento as documento
import engine.project_utils as pu


class TestePararUmaTarefa(unittest.TestCase):
    def tearDown(self):
        pu.reset_cancellation()

    def _tarefa(self, nome, inicio, resultado):
        def laco():
            inicio.set()
            for _ in range(200):
                if pu.is_cancelled():
                    resultado[nome] = "parou"
                    return
                time.sleep(0.01)
            resultado[nome] = "terminou"
        return laco

    def test_parar_so_uma(self):
        resultado, prontas = {}, [threading.Event(), threading.Event()]
        terminou = threading.Event()
        with unittest.mock.patch("core.tarefas.na_interface", side_effect=lambda f, *a: f(*a)):
            acoes._iniciar("teste_a", self._tarefa("a", prontas[0], resultado))
            acoes._iniciar("teste_b", self._tarefa("b", prontas[1], resultado),
                           ao_concluir=lambda _: terminou.set())
            for evento in prontas:
                evento.wait(2)
            self.assertEqual(acoes.em_andamento(), ["teste_a", "teste_b"])
            acoes.parar("teste_a")
            terminou.wait(5)
        self.assertEqual(resultado, {"a": "parou", "b": "terminou"})
        self.assertFalse(pu.is_cancelled())                     # fora das tarefas, nada foi cancelado

    def test_parada_antiga_nao_vale_para_a_proxima(self):
        pu.request_cancellation("teste_c")
        resultado, pronta, fim = {}, threading.Event(), threading.Event()
        with unittest.mock.patch("core.tarefas.na_interface", side_effect=lambda f, *a: f(*a)):
            acoes._iniciar("teste_c", lambda: resultado.setdefault("c", pu.is_cancelled()), ao_concluir=lambda _: fim.set())
            fim.wait(2)
        self.assertEqual(resultado, {"c": False})


class TesteChatSilent(unittest.TestCase):
    def setUp(self):
        usar_idioma("pt_br")
        self.raiz = novo_projeto({"Valia.md": "# Valia\nCidade portuária.", "Cronologia.md": "# Cronologia\nAno 1."})

    def tearDown(self):
        apagar(self.raiz)
        try:
            (pu.PASTA_LOGS / "atalhos_chat.json").unlink()
        except OSError:
            pass

    def _imagem(self, nome, lado):
        caminho = self.raiz / nome
        Image.new("RGB", (lado, lado // 2), (200, 30, 30)).save(caminho)
        return caminho

    def test_texto_e_imagem_vao_para_a_ia(self):
        anexos = [silent.preparar_anexo(self.raiz / "Valia.md"), silent.preparar_anexo(self._imagem("mapa.png", 64))]
        self.assertEqual([a["tipo"] for a in anexos], ["texto", "imagem"])
        with ia_falsa("Valia fica no litoral.") as ia:
            resposta = silent.conversar("O que é isso?", anexos)
        self.assertEqual(resposta, "Valia fica no litoral.")
        chamada = ia.ultima
        self.assertIn("Cidade portuária.", chamada["contents"])
        self.assertIn("mapa.png", chamada["contents"])
        self.assertEqual(chamada["imagens"][0]["mime"], "image/png")
        self.assertEqual(Image.open(io.BytesIO(chamada["imagens"][0]["dados"])).size, (64, 32))
        papel, texto = silent.historico_chat()[-2]
        self.assertEqual(papel, "usuario")
        self.assertIn("mapa.png", texto)                        # a memória registra o que foi anexado

    def test_sem_imagem_nao_manda_o_parametro(self):
        with ia_falsa("ok") as ia:
            silent.conversar("Oi")
        self.assertNotIn("imagens", ia.ultima)                  # Claude/OpenAI continuam recebendo o mesmo de antes

    def test_imagem_grande_e_reduzida(self):
        anexo = silent.preparar_anexo(self._imagem("grande.bmp", 3000))
        self.assertEqual(anexo["mime"], "image/jpeg")
        self.assertLessEqual(max(Image.open(io.BytesIO(anexo["dados"])).size), silent.LADO_MAXIMO_IMAGEM)

    def test_atalhos(self):
        padroes = atalhos.listar()
        self.assertGreaterEqual(len(padroes), 5)
        self.assertEqual(len(padroes), len(atalhos.padroes("en_us")))
        salvos = atalhos.salvar([{"nome": "Nomes", "texto": "Nomes para [o quê]"}, {"nome": "", "texto": "x"}])
        self.assertEqual(salvos, [{"nome": "Nomes", "texto": "Nomes para [o quê]"}])   # inválidos ficam de fora
        self.assertEqual(atalhos.listar(), salvos)
        self.assertEqual(atalhos.restaurar_padroes(), padroes)
        self.assertEqual(atalhos.primeiro_campo("Nomes para [o quê] já"), (11, 18))
        self.assertIsNone(atalhos.primeiro_campo("Fale de [[Valia]]"))

    def test_markdown_e_links(self):
        trechos = md.segmentos("# Título\nTexto **forte** e [[Valia]].\n- item\n```\ncódigo *cru*\n```")
        self.assertIn(("Título", ("h1",)), trechos)
        self.assertIn(("forte", ("negrito",)), trechos)
        self.assertIn(("Valia", ("link",)), trechos)
        self.assertIn(("  • ", ("lista",)), trechos)
        self.assertIn(("código *cru*\n", ("bloco_codigo",)), trechos)   # nada é formatado dentro do código
        self.assertEqual(md.segmentos("2 * 3 * 4"), [("2 * 3 * 4", ())])
        self.assertEqual(documento.resolver_link("Valia|a cidade"), str(self.raiz / "Valia.md"))
        self.assertIsNone(documento.resolver_link("Não Existe"))


if __name__ == "__main__":
    unittest.main()
