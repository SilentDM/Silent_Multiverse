"""Marca de 'conta sem cache explícito' do Gemini: para de tentar, zera ao trocar a chave (sem rede)."""
import os
import unittest
from unittest import mock

import tests  # noqa: F401  (isola a pasta de dados)

import core.cache_gemini as cg
import engine.project_utils as pu

ERRO_GRATUITO = Exception("429 RESOURCE_EXHAUSTED. Quota exceeded for metric: "
                          "generativelanguage.googleapis.com/TotalCachedContentStorageTokensPerModelFreeTier, limit: 0")
ERRO_PEQUENO = Exception("400 INVALID_ARGUMENT. Cached content is too small. total_token_count=300, min_total_token_count=1024")


class ClienteFalso:
    def __init__(self, erro):
        self.criacoes = 0
        self.erro = erro
        self.caches = mock.Mock(create=self._criar)
        arquivo = mock.Mock(state=mock.Mock(name="ACTIVE"))
        arquivo.name = "files/bundle"
        arquivo.state.name = "ACTIVE"
        self.files = mock.Mock(upload=mock.Mock(return_value=arquivo))

    def _criar(self, **kwargs):
        self.criacoes += 1
        raise self.erro


class TesteMarcaDeCache(unittest.TestCase):
    def setUp(self):
        self.chave_original = os.environ.get("GOOGLE_API_KEY")
        os.environ["GOOGLE_API_KEY"] = "chave-teste-1"
        cg.reativar_cache()
        pu.salvar_json_seguro(pu.log_path("models.json"), [{"name": "m1"}, {"name": "m2"}, {"name": "m3"}], pu.LOCK_MODELS)
        mock.patch.object(pu, "montar_contexto_mundo", return_value="mundo").start()

    def tearDown(self):
        mock.patch.stopall()
        cg.reativar_cache()
        if self.chave_original is None:
            os.environ.pop("GOOGLE_API_KEY", None)
        else:
            os.environ["GOOGLE_API_KEY"] = self.chave_original

    def _reconstruir(self, cliente):
        with mock.patch.object(cg.ag, "get_gemini_client", return_value=cliente):
            return cg.force_rebuild_world_context()

    def test_conta_gratuita_para_de_tentar(self):
        cliente = ClienteFalso(ERRO_GRATUITO)
        self.assertEqual(self._reconstruir(cliente)["type"], "file")
        self.assertEqual(cliente.criacoes, 1)                 # parou no primeiro modelo
        self.assertTrue(cg.status_cache()["sem_suporte"])
        self._reconstruir(cliente)
        self.assertEqual(cliente.criacoes, 1)                 # nem tentou de novo
        dados = pu.ler_json_seguro(pu.log_path(cg.ARQUIVO_STATUS_CACHE), pu.LOCK_MODELS, padrao={})
        self.assertNotIn("chave-teste-1", str(dados))          # a chave nunca é gravada

    def test_trocar_a_chave_ou_reativar_tenta_de_novo(self):
        cliente = ClienteFalso(ERRO_GRATUITO)
        self._reconstruir(cliente)
        os.environ["GOOGLE_API_KEY"] = "chave-teste-2"
        self.assertFalse(cg.status_cache()["sem_suporte"])
        self._reconstruir(cliente)
        self.assertEqual(cliente.criacoes, 2)
        cg.reativar_cache()
        self.assertFalse(cg.status_cache()["sem_suporte"])

    def test_outros_erros_nao_desativam(self):
        cliente = ClienteFalso(ERRO_PEQUENO)
        self._reconstruir(cliente)
        self.assertEqual(cliente.criacoes, 3)                 # tentou todos os modelos, como antes
        self.assertFalse(cg.status_cache()["sem_suporte"])
        self.assertFalse(cg.erro_sem_suporte_a_cache(TimeoutError("timed out")))


if __name__ == "__main__":
    unittest.main()
