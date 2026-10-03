"""Verificador de atualizações (sem rede: a lista de releases é falsa)."""
import io
import unittest
import urllib.error
from unittest import mock

import tests  # noqa: F401  (isola a pasta de dados antes dos imports)

import core.atualizacoes as at
import core.config as cfg
import core.eventos as ev


def release(tag, draft=False, prerelease=False):
    return {"tag_name": tag, "name": tag, "draft": draft, "prerelease": prerelease,
            "html_url": f"https://github.com/x/y/releases/tag/{tag}", "body": f"notas {tag}"}


# Tags reais do repositório (nomes inconsistentes) + uma nova
RELEASES = [release("Release_V1.0.7"), release("Release_v1.1.2"), release("Release_V1.1.0"),
            release("Release_V1.0.5", draft=True), release("Release"), release("v2.1.0"),
            release("v3.0.0-beta", prerelease=True), release("v9.0.0", draft=True)]


class TesteVersoes(unittest.TestCase):
    def test_numero_versao(self):
        self.assertEqual(at.numero_versao("Release_V1.1.0"), (1, 1, 0))
        self.assertEqual(at.numero_versao("v2"), (2, 0, 0))
        self.assertEqual(at.numero_versao("Release_v1.0.2"), (1, 0, 2))
        self.assertIsNone(at.numero_versao("Release"))

    def test_escolhe_a_maior_publicada(self):
        nova = at.escolher_mais_nova(RELEASES, "2.0.0")
        self.assertEqual(nova.versao, "2.1.0")          # ignora rascunhos, pré-lançamentos e "Latest" antigo
        self.assertTrue(nova.url.endswith("v2.1.0"))
        self.assertIsNone(at.escolher_mais_nova(RELEASES, "2.1.0"))
        self.assertEqual(at.escolher_mais_nova(RELEASES, "1.0.7").versao, "2.1.0")
        self.assertIsNone(at.escolher_mais_nova([], "1.0.0"))


class TesteVerificacao(unittest.TestCase):
    def setUp(self):
        self.eventos = []
        ev.inscrever_evento("atualizacao.disponivel", self.eventos.append)

    def tearDown(self):
        ev.cancelar_inscricoes()
        cfg.atualizar_configuracoes({"verificar_atualizacoes": True})

    def test_avisa_quando_ha_versao_nova(self):
        with mock.patch.object(at, "_baixar_releases", return_value=RELEASES), mock.patch.object(at, "VERSAO", "2.0.0"):
            nova = at.verificar()
        self.assertEqual(nova.versao, "2.1.0")
        self.assertEqual([e.versao for e in self.eventos], ["2.1.0"])

    def test_repositorio_sem_releases(self):
        erro = urllib.error.HTTPError(at.URL_API, 404, "Not Found", {}, io.BytesIO())
        with mock.patch.object(at, "_baixar_releases", side_effect=erro):
            self.assertIsNone(at.verificar())

    def test_inicializacao_respeita_opcao_e_nao_quebra_sem_internet(self):
        cfg.atualizar_configuracoes({"verificar_atualizacoes": False})
        with mock.patch.object(at, "_baixar_releases") as baixar:
            self.assertIsNone(at.verificar_na_inicializacao())
            baixar.assert_not_called()
        cfg.atualizar_configuracoes({"verificar_atualizacoes": True})
        with mock.patch.object(at, "_baixar_releases", side_effect=OSError("sem rede")):
            self.assertIsNone(at.verificar_na_inicializacao())   # só registra no Log
        self.assertEqual(self.eventos, [])


if __name__ == "__main__":
    unittest.main()
