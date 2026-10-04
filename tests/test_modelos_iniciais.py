"""Modelos iniciais (Templates/ e Style/) por idioma: instalação, troca de idioma e instalações antigas."""
import tempfile
import typing
import unittest
from pathlib import Path

from tests import PASTA_TEMP
from tests.util import apagar

import core.i18n as i18n
import engine.project_utils as pu
import engine.wbuilder as wb

ESTILO = pu.PASTA_ESTILO_NOME


class TesteModelosIniciais(unittest.TestCase):
    def setUp(self):
        self.dados = Path(tempfile.mkdtemp(prefix="dados_", dir=PASTA_TEMP))

    def tearDown(self):
        apagar(self.dados)

    def _ler(self, relativo):
        return (self.dados / relativo).read_text(encoding="utf-8")

    def test_mesmos_arquivos_nos_dois_idiomas_e_nomes_do_worldbuilder(self):
        conjuntos = {}
        for idioma in i18n.IDIOMAS:
            base = pu.pasta_modelos_iniciais(idioma)
            conjuntos[idioma] = sorted(str(p.relative_to(base)) for p in base.rglob("*.md"))
        self.assertEqual(conjuntos["pt_br"], conjuntos["en_us"])
        nomes_wb = set(typing.get_args(typing.get_args(wb.Action.model_fields["template"].annotation)[0])) - {"nenhum"}
        templates = {Path(p).stem for p in conjuntos["pt_br"] if Path(p).parts[0] == "Templates"}
        self.assertEqual(templates, nomes_wb)

    def test_instala_e_troca_so_o_que_nao_foi_editado(self):
        copiados = pu.instalar_modelos_iniciais("pt_br", self.dados)
        self.assertEqual(len(copiados), 16)        # 8 genéricos + 8 por gênero
        self.assertIn("# Aventura:", self._ler("Templates/aventura.md"))
        self.assertEqual(pu.instalar_modelos_iniciais("pt_br", self.dados), [])   # nada a fazer

        (self.dados / "Templates/npc.md").write_text("# Meu NPC editado", encoding="utf-8")
        (self.dados / "Templates/faccao.md").write_text("# Modelo do usuário", encoding="utf-8")
        pu.instalar_modelos_iniciais("en_us", self.dados)
        self.assertIn("# Adventure:", self._ler("Templates/aventura.md"))
        self.assertIn("# Writing Style", self._ler(f"{ESTILO}/Estilo_Escrita.md"))
        self.assertEqual(self._ler("Templates/npc.md"), "# Meu NPC editado")      # editado: preservado
        self.assertEqual(self._ler("Templates/faccao.md"), "# Modelo do usuário")  # do usuário: preservado

        pu.instalar_modelos_iniciais("pt_br", self.dados)                            # volta ao português
        self.assertIn("# Aventura:", self._ler("Templates/aventura.md"))
        self.assertEqual(self._ler("Templates/npc.md"), "# Meu NPC editado")

    def test_modelo_novo_chega_uma_vez_em_instalacao_existente(self):
        import json
        pu.instalar_modelos_iniciais("pt_br", self.dados)
        registro = self.dados / "logs" / "modelos_iniciais.json"
        dados = json.loads(registro.read_text(encoding="utf-8"))
        dados["conhecidos"].remove("Templates/monstro.md")          # simula a versão anterior do programa
        registro.write_text(json.dumps(dados), encoding="utf-8")
        (self.dados / "Templates/monstro.md").unlink()
        (self.dados / "Templates/aventura.md").unlink()               # o usuário apagou um modelo antigo
        self.assertEqual([Path(c).name for c in pu.instalar_modelos_iniciais("pt_br", self.dados)], ["monstro.md"])
        (self.dados / "Templates/monstro.md").unlink()
        self.assertEqual(pu.instalar_modelos_iniciais("pt_br", self.dados), [])   # só uma vez

    def test_instalacao_antiga_fica_como_esta(self):
        (self.dados / "Templates").mkdir()
        (self.dados / "Templates/npc.md").write_text("# NPC antigo", encoding="utf-8")
        copiados = pu.instalar_modelos_iniciais("en_us", self.dados)
        self.assertTrue(all(ESTILO in c for c in copiados))           # só a pasta Style (vazia) recebeu modelos
        self.assertFalse((self.dados / "Templates/aventura.md").exists())
        self.assertEqual(self._ler("Templates/npc.md"), "# NPC antigo")
        pu.instalar_modelos_iniciais("pt_br", self.dados)
        self.assertEqual(self._ler("Templates/npc.md"), "# NPC antigo")


if __name__ == "__main__":
    unittest.main()
