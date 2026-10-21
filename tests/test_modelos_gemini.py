"""
Lista de modelos sem gastar cota: buscar o catálogo não manda mensagens, o histórico de uso continua,
um 429 deixa o modelo descansando (sem contar como falha) e o botão Testar manda um pedido só. Sem rede.
"""
import calendar
import os
import time
import unittest
from types import SimpleNamespace
from unittest import mock

import tests  # noqa: F401  (isola a pasta de dados)

import core.ai_gemini as ag
import core.modelos_gemini as modelos
import engine.project_utils as pu

ERRO_DIARIO = Exception("429 RESOURCE_EXHAUSTED. Quota exceeded for metric: generativelanguage.googleapis.com/"
                        "generate_content_free_tier_requests, quotaId: GenerateRequestsPerDayPerProjectPerModel-FreeTier. "
                        "{'@type': 'type.googleapis.com/google.rpc.RetryInfo', 'retryDelay': '21s'}")
ERRO_MINUTO = Exception("429 RESOURCE_EXHAUSTED. quotaId: GenerateRequestsPerMinutePerProjectPerModel-FreeTier. "
                        "{'@type': 'type.googleapis.com/google.rpc.RetryInfo', 'retryDelay': '37s'}")


def modelo_api(nome, entrada=1_048_576, saida=65_536):
    return SimpleNamespace(name=nome, display_name=nome.split("/")[-1], input_token_limit=entrada,
                           output_token_limit=saida, supported_actions=["generateContent"])


CATALOGO = [modelo_api("models/gemini-2.5-pro"), modelo_api("models/gemini-2.5-flash"),
            modelo_api("models/text-embedding-004"), modelo_api("models/gemini-2.0-flash")]


class ClienteFalso:
    def __init__(self, catalogo=CATALOGO, respostas=None):
        self.pedidos = []
        self.respostas = respostas or {}
        self.models = SimpleNamespace(list=lambda: list(catalogo), generate_content=self._gerar)

    def _gerar(self, model, contents, config=None):
        self.pedidos.append(model)
        resposta = self.respostas.get(model, "Uma frase sombria.")
        if isinstance(resposta, Exception):
            raise resposta
        return SimpleNamespace(text=resposta)


class TesteListaDeModelos(unittest.TestCase):
    def setUp(self):
        self.chave = os.environ.get("GOOGLE_API_KEY")
        os.environ["GOOGLE_API_KEY"] = "chave-teste"
        self.arquivo = pu.log_path("models.json")
        if self.arquivo.exists():
            self.arquivo.unlink()

    def tearDown(self):
        mock.patch.stopall()
        if self.chave is None:
            os.environ.pop("GOOGLE_API_KEY", None)
        else:
            os.environ["GOOGLE_API_KEY"] = self.chave

    def _cliente(self, cliente):
        mock.patch.object(ag, "get_gemini_client", return_value=cliente).start()
        return cliente

    def _lista(self):
        return {m["name"]: m for m in modelos.listar()}

    def test_buscar_lista_nao_manda_mensagens(self):
        cliente = self._cliente(ClienteFalso())
        lista = modelos.atualizar_lista()
        self.assertEqual(cliente.pedidos, [])                              # nenhuma cota gasta
        nomes = [m["name"] for m in lista]
        self.assertNotIn("models/text-embedding-004", nomes)
        self.assertEqual(nomes[0], "models/gemini-2.5-pro")                # sem uso: vale a pontuação
        self.assertTrue(all(m["attempts"] == 0 and m["responsetime"] is None for m in lista))
        self.assertIsNone(modelos.metricas(lista[0])["taxa"])

    def test_buscar_de_novo_mantem_historico_e_tira_quem_saiu(self):
        self._cliente(ClienteFalso())
        modelos.atualizar_lista()
        ag.improvemodel("models/gemini-2.5-flash", True, 2.0)
        ag.improvemodel("models/gemini-2.5-flash", True, 2.0)
        self._cliente(ClienteFalso(catalogo=CATALOGO[1:]))                 # o Pro saiu do catálogo
        modelos.atualizar_lista()
        lista = self._lista()
        self.assertNotIn("models/gemini-2.5-pro", lista)
        self.assertEqual(lista["models/gemini-2.5-flash"]["attempts"], 2)
        self.assertEqual(lista["models/gemini-2.5-flash"]["success"], 2)

    def test_sem_cota_descansa_sem_contar_falha_e_e_pulado(self):
        cliente = self._cliente(ClienteFalso(respostas={"models/gemini-2.5-pro": ERRO_DIARIO}))
        modelos.atualizar_lista()
        config = ag.types.GenerateContentConfig()
        resposta = ag.generate_content_with_fallback("oi", config)
        self.assertEqual(resposta.text, "Uma frase sombria.")
        self.assertEqual(cliente.pedidos, ["models/gemini-2.5-pro", "models/gemini-2.5-flash"])
        pro = self._lista()["models/gemini-2.5-pro"]
        self.assertEqual(pro["attempts"], 0)                               # 429 não é falha
        self.assertTrue(ag.modelo_descansando(pro))
        self.assertIsNotNone(modelos.metricas(pro)["descanso_ate"])

        cliente.pedidos.clear()
        ag.generate_content_with_fallback("oi de novo", config)
        self.assertNotIn("models/gemini-2.5-pro", cliente.pedidos)         # pulado enquanto descansa

        depois = pro["resting_until"] + 1
        self.assertFalse(ag.modelo_descansando(pro, depois))               # volta sozinho

    def test_modelo_descansando_e_ultimo_recurso(self):
        cliente = self._cliente(ClienteFalso(respostas={"models/gemini-2.5-flash": ERRO_MINUTO,
                                                        "models/gemini-2.0-flash": ERRO_MINUTO}))
        modelos.atualizar_lista()
        ag.improvemodel("models/gemini-2.5-pro", False, descanso_ate=time.time() + 3600)
        resposta = ag.generate_content_with_fallback("oi", ag.types.GenerateContentConfig())
        self.assertEqual(resposta.text, "Uma frase sombria.")
        self.assertEqual(cliente.pedidos[-1], "models/gemini-2.5-pro")     # tentado só depois dos outros
        self.assertFalse(ag.modelo_descansando(self._lista()["models/gemini-2.5-pro"]))  # o sucesso encerra o descanso

    def test_testar_um_modelo(self):
        cliente = self._cliente(ClienteFalso(respostas={"models/gemini-2.0-flash": ERRO_MINUTO}))
        modelos.atualizar_lista()
        resultado = modelos.testar("models/gemini-2.5-flash")
        self.assertTrue(resultado["ok"])
        self.assertEqual(cliente.pedidos, ["models/gemini-2.5-flash"])     # um pedido só
        flash = self._lista()["models/gemini-2.5-flash"]
        self.assertEqual((flash["attempts"], flash["success"]), (1, 1))
        self.assertIsNotNone(flash["responsetime"])

        antes = time.time()
        resultado = modelos.testar("models/gemini-2.0-flash")
        self.assertFalse(resultado["ok"])
        self.assertAlmostEqual(resultado["descanso_ate"], antes + 37, delta=5)
        self.assertEqual(self._lista()["models/gemini-2.0-flash"]["attempts"], 0)


class TesteHorarioDaCota(unittest.TestCase):
    def _utc(self, *data):
        return calendar.timegm(data + (0,) * (6 - len(data)))

    def test_meia_noite_do_pacifico(self):
        # Outubro (horário de verão, UTC-7): meia-noite do Pacífico = 07:00 UTC
        self.assertEqual(ag.proxima_renovacao_diaria(self._utc(2026, 10, 20, 15)), self._utc(2026, 10, 21, 7))
        # 03:00 UTC ainda é o dia anterior no Pacífico
        self.assertEqual(ag.proxima_renovacao_diaria(self._utc(2026, 10, 21, 3)), self._utc(2026, 10, 21, 7))
        # Janeiro (horário padrão, UTC-8): 08:00 UTC
        self.assertEqual(ag.proxima_renovacao_diaria(self._utc(2026, 1, 10, 12)), self._utc(2026, 1, 11, 8))

    def test_descanso_pelo_tipo_de_cota(self):
        agora = self._utc(2026, 10, 20, 15)
        self.assertEqual(ag.descanso_do_erro(ERRO_DIARIO, agora), self._utc(2026, 10, 21, 7))  # ignora o retryDelay curto
        self.assertEqual(ag.descanso_do_erro(ERRO_MINUTO, agora), agora + 37)
        self.assertEqual(ag.descanso_do_erro(Exception("429 Too Many Requests"), agora), agora + 60)


if __name__ == "__main__":
    unittest.main()
