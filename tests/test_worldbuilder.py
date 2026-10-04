"""
WorldBuilder (nível alto) com a ideia de Vog'Mur e uma IA falsa:
Cânone → Plano validado → Execução por fases, segredos protegidos e retomada.
"""
import json
import unittest
from unittest import mock

from tests.util import novo_projeto, apagar, usar_idioma, ia_falsa
from tests.test_ia_idioma import aventura

import core.config as cfg
import engine.project_utils as pu
import engine.wbuilder as wb

IDEIA = ("Um elemental de fogo se instalou num vulcão e causa terremotos. Três cidades do reino de Vog'Mur "
         "contratam heróis. O rei trama na capital. Segredo: um lich tem um laboratório dentro do vulcão.")

CANON = {
    "titulo": "A Fúria de Vog'Mur", "premissa": "p", "visao_geral_publica": "O vulcão acordou.",
    "entidades": [
        {"nome": "Vog'Mur", "categoria": "reino", "resumo_publico": "Reino vulcânico.", "relacoes": ["Rei Thorvald"]},
        {"nome": "Rei Thorvald", "categoria": "npc", "resumo_publico": "O rei.", "segredo_do_mestre": "Quer lucrar."},
        {"nome": "Lich Morvath", "categoria": "npc", "resumo_publico": "", "segredo_do_mestre": "Laboratório no vulcão.",
         "eh_segredo": True},
    ],
    "segredos_principais": ["O lich atrai o elemental."], "linha_do_tempo": ["Ano 1: o lich chega."],
}


def plano():
    return {"actions": [
        {"type": "GenerateAdventure", "path": f"{pu.PASTA_PROJETO}/Aventuras/Coracao do Vulcao", "priority": 5,
         "objective": "Aventura no vulcão", "segredo": True, "fase": 5},
        {"type": "CreateFile", "path": "Reinos/Vog'Mur", "priority": 9, "objective": "O reino", "template": "reinado", "fase": 1},
        {"type": "CreateFolder", "path": "Reinos", "priority": 10, "objective": "pasta", "fase": 1},
        {"type": "CreateFile", "path": "NPCs/Lich Morvath.md", "priority": 5, "objective": "O lich", "template": "npc",
         "segredo": True, "fase": 3},
        {"type": "CreateFile", "path": "NPCs/Rei Thorvald.md", "priority": 6, "objective": "O rei", "template": "npc", "fase": 3},
        {"type": "CreateFile", "path": "Ideia.md", "priority": 1, "objective": "Reescrever", "fase": 1},
        {"type": "CreateFile", "path": "../fora.md", "priority": 1, "objective": "x", "fase": 2},
        {"type": "CreateFile", "path": "NPCs/Rei Thorvald.md", "priority": 1, "objective": "repetido", "fase": 3},
        {"type": "ImproveFile", "path": "Nao Existe.md", "priority": 1, "objective": "x", "fase": 2},
        {"type": "GenerateLoreChecks", "path": "Reinos/Vog'Mur.md", "priority": 1, "objective": "x", "fase": 5},
    ]}


def resposta_falsa(chamada):
    schema = chamada.get("response_schema")
    nome = getattr(schema, "__name__", "")
    if nome == "CanonCampanha":
        return json.dumps(CANON)
    if nome == "ActionPlan":
        return json.dumps(plano())
    if nome == "ModuloAventura5Rooms":
        return aventura().model_dump_json()
    if nome == "CompendioConhecimento":
        return json.dumps({"tema_entidade": "Vog'Mur", "resumo_mestre": "r", "testes": []})
    instrucao = chamada.get("system_instruction", "")
    if "Lich Morvath" in instrucao:
        return "# Lich Morvath\nstatus: rascunho\nMorvath esconde o laboratório."
    if "Rei Thorvald" in instrucao:
        return "# Rei Thorvald\nGoverna [[Vog'Mur]] com o conselheiro [[Conselheira Ilsa]]."
    return "# Arquivo\nConteúdo público sobre [[Vog'Mur]]."


class TesteWorldBuilder(unittest.TestCase):
    def setUp(self):
        usar_idioma("pt_br")
        self.raiz = novo_projeto({"Ideia.md": "# Ideia\n" + IDEIA})
        wb.nova_sessao()
        self.reconstrucoes = mock.patch.object(wb.cg, "force_rebuild_world_context").start()
        self.expander = mock.patch.object(wb.ex, "processar_arquivos").start()
        mock.patch.object(wb.geradores.aimg, "gerar_battlemap_boss", return_value=None).start()
        cfg.atualizar_configuracoes({"wb_max_acoes": 25})

    def tearDown(self):
        mock.patch.stopall()
        pu.reset_cancellation()
        for chave in ("wb_allow_create_folder", "wb_allow_generators"):
            cfg.atualizar_configuracoes({chave: True})
        apagar(self.raiz)

    def _canon_e_plano(self):
        with ia_falsa(resposta_falsa):
            caminho = wb.gerar_canon(IDEIA)
            itens = wb.gerar_plano()
        return caminho, itens

    def _item(self, itens, caminho, tipo=None):
        return next(i for i in itens if i["path"] == caminho and (tipo is None or i["type"] == tipo))

    def test_canon_e_secreto_e_as_edicoes_do_mestre_valem(self):
        with ia_falsa(resposta_falsa) as ia:
            caminho = wb.gerar_canon(IDEIA)
        texto = open(caminho, encoding="utf-8").read()
        self.assertIn("status: segredo", texto)
        self.assertIn("[[Lich Morvath]]", texto)
        self.assertIn(IDEIA, ia.ultima["contents"])
        self.assertNotIn("Morvath", pu.montar_contexto_mundo(is_dm=False))      # jogadores nunca veem o cânone

        with open(caminho, "a", encoding="utf-8") as f:
            f.write("\nEDITADO PELO MESTRE\n")
        with ia_falsa(resposta_falsa) as ia:
            wb.gerar_plano()
        self.assertIn("EDITADO PELO MESTRE", ia.ultima["contents"])
        self.assertEqual(wb.carregar_sessao()["etapa"], wb.ETAPA_PLANO)

    def test_validacao_do_plano(self):
        _, itens = self._canon_e_plano()
        self.assertEqual([i["fase"] for i in itens], sorted(i["fase"] for i in itens))       # ordem por fase
        self.assertEqual(itens[0]["type"], "CreateFolder")                                  # maior prioridade da fase 1
        self.assertTrue(self._item(itens, "Reinos/Vog'Mur.md")["ativo"])                   # .md acrescentado
        self.assertTrue(self._item(itens, "Aventuras/Coracao do Vulcao.md")["ativo"])      # prefixo do projeto removido
        ideia = self._item(itens, "Ideia.md")
        self.assertEqual((ideia["type"], ideia["ativo"]), ("ImproveFile", True))            # já existe: vira melhoria
        fora = next(i for i in itens if "fora" in i["path"])
        self.assertFalse(fora["ativo"])
        repetidos = [i for i in itens if i["path"] == "NPCs/Rei Thorvald.md"]
        self.assertEqual(sorted(i["ativo"] for i in repetidos), [False, True])
        self.assertFalse(self._item(itens, "Nao Existe.md")["ativo"])
        self.assertTrue(self._item(itens, "Reinos/Vog'Mur.md", "GenerateLoreChecks")["ativo"])  # criado antes no plano

    def test_limite_de_acoes(self):
        cfg.atualizar_configuracoes({"wb_max_acoes": 3})
        _, itens = self._canon_e_plano()
        self.assertEqual(sum(i["ativo"] for i in itens), 3)
        self.assertIn("3", next(i for i in itens if not i["ativo"] and "limite" in i["aviso"])["aviso"])

    def test_permissoes(self):
        cfg.atualizar_configuracoes({"wb_allow_generators": False, "wb_allow_create_folder": False})
        _, itens = self._canon_e_plano()
        self.assertFalse(self._item(itens, "Aventuras/Coracao do Vulcao.md")["ativo"])     # geradores desligados
        self.assertFalse(self._item(itens, "Reinos/Vog'Mur.md", "CreateFile")["ativo"])     # pasta não existe
        self.assertFalse(self._item(itens, "Reinos", "CreateFolder")["ativo"])
        self.assertTrue(self._item(itens, "Ideia.md")["ativo"])                            # na raiz: permitido

    def test_execucao_completa(self):
        self._canon_e_plano()
        with ia_falsa(resposta_falsa):
            resumo = wb.executar_plano()

        lich = (self.raiz / "NPCs" / "Lich Morvath.md").read_text(encoding="utf-8")
        self.assertIn("status: segredo", lich)
        self.assertNotIn("status: rascunho", lich)                    # arquivos do WorldBuilder entram no contexto
        rei = (self.raiz / "NPCs" / "Rei Thorvald.md").read_text(encoding="utf-8")
        self.assertNotIn("status: segredo", rei)
        aventura_md = (self.raiz / "Aventuras" / "Coracao do Vulcao.md").read_text(encoding="utf-8")
        self.assertIn("## SALA 1:", aventura_md)                       # gerador estruturado, não texto livre
        self.assertIn("status: segredo", aventura_md)
        self.assertIn("Vog'Mur", (self.raiz / "Reinos" / "Vog'Mur.md").read_text(encoding="utf-8"))

        jogadores = pu.montar_contexto_mundo(is_dm=False)
        self.assertNotIn("Morvath", jogadores)
        self.assertIn("Thorvald", jogadores)

        fases = sorted({i["fase"] for i in wb.carregar_sessao()["plano"] if i["ativo"]})
        self.assertEqual(self.reconstrucoes.call_count, len(fases) + 1)   # uma por fase + uma no fim
        self.expander.assert_not_called()                                 # o Expander do projeto inteiro não roda
        self.assertEqual(resumo["falhas"], 0)
        self.assertIn("Conselheira Ilsa", resumo["links_sem_arquivo"])
        self.assertNotIn("Vog'Mur", resumo["links_sem_arquivo"])
        self.assertEqual(wb.carregar_sessao()["etapa"], wb.ETAPA_CONCLUIDA)

    def test_interromper_e_retomar(self):
        self._canon_e_plano()
        chamadas = []

        def melhorar_que_para(caminho, objetivo=None, canon=None):
            chamadas.append(str(caminho))
            pu.request_cancellation()          # o Mestre clica em Parar durante a primeira ação de arquivo
            return True

        with mock.patch.object(wb.melhorar, "melhorar_arquivo", side_effect=melhorar_que_para), ia_falsa(resposta_falsa):
            resumo = wb.executar_plano()
            self.assertTrue(resumo["interrompido"])
            self.assertEqual(wb.carregar_sessao()["etapa"], wb.ETAPA_PLANO)
            feitos = [i["path"] for i in wb.carregar_sessao()["plano"] if i["estado"] == "concluida"]
            pu.reset_cancellation()
            chamadas.clear()
            mock.patch.object(wb.melhorar, "melhorar_arquivo", return_value=True).start()
            wb.executar_plano()
        refeitos = [i["path"] for i in wb.carregar_sessao()["plano"] if i["estado"] == "concluida"]
        self.assertTrue(set(feitos) < set(refeitos))
        self.assertEqual(chamadas, [])

    def test_edicao_do_mestre_no_plano(self):
        _, itens = self._canon_e_plano()
        indice = next(n for n, i in enumerate(itens) if i["path"] == "NPCs/Rei Thorvald.md" and i["ativo"])
        item = wb.atualizar_item(indice, path="NPCs/Rei Thorvald II", segredo=True, ativo=False)
        self.assertEqual((item["path"], item["segredo"], item["ativo"]), ("NPCs/Rei Thorvald II.md", True, False))
        item = wb.atualizar_item(indice, ativo=True)
        self.assertTrue(item["ativo"])
        item = wb.atualizar_item(indice, path="../../fora")
        self.assertFalse(item["ativo"])
        self.assertTrue(wb.carregar_sessao()["plano"][indice]["aviso"])

    def test_sem_canon(self):
        with self.assertRaises(wb.ErroWorldBuilder):
            wb.gerar_plano()


if __name__ == "__main__":
    unittest.main()
