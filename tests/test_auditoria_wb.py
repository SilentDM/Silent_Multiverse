"""
Auditoria de Lore → WorldBuilder: o relatório vira um plano de correção revisável,
sem cânone, e cada arquivo corrigido recebe o relatório como motivo.
"""
import json
import unittest
from unittest import mock

from tests.util import novo_projeto, apagar, usar_idioma, ia_falsa

import core.config as cfg
import engine.acoes as acoes
import engine.project_utils as pu
import engine.wbuilder as wb

RELATORIO = ("## Inconsistência 1\nEm [[Rei Thorvald]] o rei tem 40 anos; em [[Cronologia]] ele nasceu há 90 anos.\n"
             "**Solução:** ajustar a idade em Rei Thorvald.md para 90.\n"
             "## Inconsistência 2\nA [[Ordem da Brasa]] é citada mas não tem arquivo.")


def plano_correcao():
    return {"actions": [
        {"type": "ImproveFile", "path": "Rei Thorvald.md", "priority": 9, "fase": 3,
         "objective": "Idade contradiz a Cronologia (90 anos): ajustar para 90."},
        {"type": "CreateFile", "path": "Ordem da Brasa.md", "priority": 5, "fase": 3, "template": "npc",
         "objective": "Facção citada sem arquivo."},
    ]}


def resposta(chamada):
    if getattr(chamada.get("response_schema"), "__name__", "") == "ActionPlan":
        return json.dumps(plano_correcao())
    return "# Corrigido\nConteúdo corrigido."


class TesteAuditoriaWorldBuilder(unittest.TestCase):
    def setUp(self):
        usar_idioma("pt_br")
        self.raiz = novo_projeto({"Rei Thorvald.md": "# Rei Thorvald\nTem 40 anos.",
                                  "Cronologia.md": "# Cronologia\nO rei nasceu há 90 anos."})
        wb.nova_sessao()
        mock.patch.object(wb.cg, "force_rebuild_world_context").start()
        mock.patch.object(wb.ex, "processar_arquivos").start()
        cfg.atualizar_configuracoes({"wb_max_acoes": 25})

    def tearDown(self):
        mock.patch.stopall()
        pu.reset_cancellation()
        apagar(self.raiz)

    def test_plano_a_partir_do_relatorio_sem_canon(self):
        self.assertFalse(wb.tem_plano_pendente())
        with ia_falsa(resposta) as ia:
            itens = wb.gerar_plano_da_auditoria(RELATORIO)
        self.assertIn(RELATORIO, ia.ultima["contents"])
        sessao = wb.carregar_sessao()
        self.assertEqual(sessao["origem"], wb.ORIGEM_AUDITORIA)
        self.assertEqual(sessao["auditoria"], RELATORIO)
        self.assertIsNone(sessao.get("canon"))
        self.assertEqual(sessao["etapa"], wb.ETAPA_PLANO)
        self.assertTrue(all(i["ativo"] for i in itens))
        self.assertTrue(wb.tem_plano_pendente())

        with ia_falsa(resposta) as ia:          # "Gerar plano" de novo refaz a partir do mesmo relatório
            wb.gerar_plano()
        self.assertIn(RELATORIO, ia.ultima["contents"])

    def test_execucao_leva_o_relatorio_a_cada_arquivo(self):
        with ia_falsa(resposta):
            wb.gerar_plano_da_auditoria(RELATORIO)
        with ia_falsa(resposta) as ia:
            resumo = wb.executar_plano()
        self.assertEqual(resumo["falhas"], 0)
        textos = [c.get("system_instruction", "") + c.get("contents", "") for c in ia.chamadas]
        self.assertTrue(textos)
        self.assertTrue(all("RELATÓRIO DA AUDITORIA" in x and "Ordem da Brasa" in x for x in textos))
        self.assertIn("Corrigido", (self.raiz / "Rei Thorvald.md").read_text(encoding="utf-8"))
        self.assertTrue((self.raiz / "Ordem da Brasa.md").exists())
        self.assertFalse(wb.tem_plano_pendente())

    def test_relatorio_vazio(self):
        with self.assertRaises(wb.ErroWorldBuilder):
            wb.gerar_plano_da_auditoria("   ")

    def test_opcao_de_enviar_automaticamente(self):
        original = acoes.auditoria_vai_ao_worldbuilder()
        try:
            acoes.definir_auditoria_vai_ao_worldbuilder(True)
            self.assertTrue(acoes.auditoria_vai_ao_worldbuilder())
            acoes.definir_auditoria_vai_ao_worldbuilder(False)
            self.assertFalse(acoes.auditoria_vai_ao_worldbuilder())
        finally:
            acoes.definir_auditoria_vai_ao_worldbuilder(original)


if __name__ == "__main__":
    unittest.main()
