"""
Foundry VTT: listagem do projeto, geração (com cache), a ponte local (token, origem, rotas),
a instalação do módulo e os testes JavaScript da conversão para o dnd5e (com o Node, se houver).
IA falsa, sem rede: a ponte é testada em 127.0.0.1 numa porta livre.
"""
import http.client
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests import RAIZ_REPO, PASTA_TEMP
from tests.util import novo_projeto, apagar, usar_idioma, ia_falsa

import core.config as cfg
import engine.foundry as fvtt
import engine.ponte_foundry as ponte

FICHA = {
    "nome": "Borin", "tamanho": "med", "tipo_criatura": "humanoid", "subtipo": "anão", "alinhamento": "Neutro",
    "classe_armadura": 13, "pontos_de_vida": 22, "formula_pv": "4d8 + 4", "deslocamento_pes": 25, "voo_pes": 0,
    "natacao_pes": 0, "escalada_pes": 0, "forca": 14, "destreza": 10, "constituicao": 13, "inteligencia": 10,
    "sabedoria": 12, "carisma": 15, "testes_resistencia": ["con"], "pericias": ["prc"], "nivel_desafio": 0.5,
    "visao_escuro_pes": 60, "idiomas": ["Comum"], "resistencias": [], "imunidades": [], "imunidades_condicao": [],
    "ataques": [{"nome": "Martelo", "alcance": "melee", "classificacao": "weapon", "alcance_pes": 5,
                 "alcance_longo_pes": 0, "dados_quantidade": 1, "dados_faces": 8, "tipo_dano": "bludgeoning",
                 "descricao": ""}],
    "habilidades": [], "biografia_publica": "Taverneiro caolho.", "biografia_mestre": "Deve um favor.\n\nMente sobre o olho.",
}
LOJA = {"nome": "Forja de Brasa", "dono": "Borin", "descricao": "Cheira a carvão.",
        "itens": [{"nome": "Espada Longa", "nome_srd": "Longsword", "tipo": "weapon", "preco_po": 18, "quantidade": 2,
                   "descricao": "Forjada aqui."}]}


def resposta_ia(chamada):
    nome = getattr(chamada.get("response_schema"), "__name__", "")
    return json.dumps(FICHA if nome == "FichaFoundry" else LOJA)


class TesteConteudo(unittest.TestCase):
    def setUp(self):
        usar_idioma("pt_br")
        self.raiz = novo_projeto({
            "NPCs/Borin.md": "# Borin\nTaverneiro.",
            "Lojas/Forja de Brasa.md": "---\ntype: loja\n---\n# Forja\n![[fachada.webp]]",
            "Segredos/Lich.md": "---\nstatus: segredo\ntype: npc\n---\n# Lich",
            "Reino.md": "# Reino",
        })
        (self.raiz / "NPCs" / "Borin.png").write_bytes(b"\x89PNG imagem")
        (self.raiz / "Imagens").mkdir()
        (self.raiz / "Imagens" / "fachada.webp").write_bytes(b"RIFF webp")

    def tearDown(self):
        apagar(self.raiz)

    def test_listagem_marca_npcs_lojas_e_imagens(self):
        itens = {i["arquivo"]: i for i in fvtt.listar_arquivos()}
        self.assertTrue(itens["NPCs/Borin.md"]["npc"])                       # pela pasta
        self.assertEqual(itens["NPCs/Borin.md"]["imagem"], "NPCs/Borin.png")   # mesmo nome
        self.assertTrue(itens["Lojas/Forja de Brasa.md"]["loja"])            # pela propriedade type
        self.assertEqual(itens["Lojas/Forja de Brasa.md"]["imagem"], "Imagens/fachada.webp")   # ![[...]] do texto
        self.assertTrue(itens["Segredos/Lich.md"]["npc"] and itens["Segredos/Lich.md"]["segredo"])
        self.assertFalse(itens["Reino.md"]["npc"] or itens["Reino.md"]["loja"])

    def test_nao_sai_da_pasta_do_projeto(self):
        with self.assertRaises(fvtt.ErroFoundry):
            fvtt.caminho_do_arquivo("../fora.md")
        with self.assertRaises(fvtt.ErroFoundry):
            fvtt.caminho_do_arquivo("Nao Existe.md")

    def test_ficha_com_cache(self):
        with ia_falsa(resposta_ia) as ia:
            ficha = fvtt.gerar_ficha("NPCs/Borin.md")
            self.assertEqual(ficha["biografia_mestre_html"], "<p>Deve um favor.</p><p>Mente sobre o olho.</p>")
            self.assertEqual(ficha["fonte"], "NPCs/Borin.md")
            self.assertIn("Taverneiro.", ia.ultima["contents"])
            self.assertTrue(ia.ultima["use_world_context"])
            fvtt.gerar_ficha("NPCs/Borin.md")                                 # cache: a IA não é chamada de novo
            self.assertEqual(len(ia.chamadas), 1)
            fvtt.gerar_ficha("NPCs/Borin.md", forcar=True)
            self.assertEqual(len(ia.chamadas), 2)
            import os, time
            caminho = self.raiz / "NPCs" / "Borin.md"
            os.utime(caminho, (time.time() + 10, time.time() + 10))           # o arquivo mudou: gera de novo
            fvtt.gerar_ficha("NPCs/Borin.md")
            self.assertEqual(len(ia.chamadas), 3)

    def test_loja(self):
        with ia_falsa(resposta_ia):
            loja = fvtt.gerar_loja("Lojas/Forja de Brasa.md")
        self.assertEqual(loja["itens"][0]["nome_srd"], "Longsword")
        self.assertEqual(loja["descricao_html"], "<p>Cheira a carvão.</p>")


class TestePonte(unittest.TestCase):
    def setUp(self):
        usar_idioma("pt_br")
        self.raiz = novo_projeto({"NPCs/Borin.md": "# Borin\nTaverneiro."})
        (self.raiz / "NPCs" / "Borin.png").write_bytes(b"\x89PNG imagem")
        self.assertTrue(ponte.iniciar(porta_escolhida=0))                     # porta livre qualquer
        self.porta = ponte.porta_em_uso()
        self.token = ponte.token()

    def tearDown(self):
        ponte.parar()
        apagar(self.raiz)

    def _pedido(self, metodo, caminho, corpo=None, token=True, origem="http://localhost:30000"):
        conexao = http.client.HTTPConnection("127.0.0.1", self.porta, timeout=10)
        cabecalhos = {"Origin": origem}
        if token:
            cabecalhos["X-Silent-Token"] = self.token if token is True else token
        if corpo is not None:
            cabecalhos["Content-Type"] = "application/json"
        conexao.request(metodo, caminho, body=json.dumps(corpo) if corpo is not None else None, headers=cabecalhos)
        resposta = conexao.getresponse()
        dados = resposta.read()
        conexao.close()
        return resposta, dados

    def test_sem_token_nao_entra(self):
        resposta, dados = self._pedido("GET", "/status", token=False)
        self.assertEqual(resposta.status, 401)
        resposta, _ = self._pedido("GET", "/arquivos", token="errado")
        self.assertEqual(resposta.status, 401)

    def test_rotas_com_token(self):
        resposta, dados = self._pedido("GET", "/status")
        self.assertEqual(resposta.status, 200)
        self.assertEqual(json.loads(dados)["projeto"], self.raiz.name)
        self.assertEqual(resposta.getheader("Access-Control-Allow-Origin"), "http://localhost:30000")
        resposta, dados = self._pedido("GET", "/arquivos")
        self.assertEqual(json.loads(dados)["arquivos"][0]["imagem"], "NPCs/Borin.png")
        resposta, dados = self._pedido("GET", "/imagem?arquivo=NPCs/Borin.png")
        self.assertEqual((resposta.status, dados), (200, b"\x89PNG imagem"))
        self.assertEqual(resposta.getheader("Content-Type"), "image/png")
        resposta, _ = self._pedido("GET", "/imagem?arquivo=NPCs/Borin.md")   # só imagens
        self.assertEqual(resposta.status, 404)
        resposta, _ = self._pedido("GET", "/imagem?arquivo=../../x.png")
        self.assertEqual(resposta.status, 404)
        with ia_falsa(resposta_ia):
            resposta, dados = self._pedido("POST", "/ficha", {"arquivo": "NPCs/Borin.md"})
        self.assertEqual(resposta.status, 200)
        self.assertEqual(json.loads(dados)["nome"], "Borin")

    def test_origem_de_fora_nao_recebe_cors(self):
        resposta, _ = self._pedido("GET", "/status", origem="https://site-qualquer.com")
        self.assertIsNone(resposta.getheader("Access-Control-Allow-Origin"))
        resposta, _ = self._pedido("OPTIONS", "/ficha", token=False)
        self.assertEqual(resposta.status, 204)
        self.assertEqual(resposta.getheader("Access-Control-Allow-Private-Network"), "true")
        self.assertIn("X-Silent-Token", resposta.getheader("Access-Control-Allow-Headers"))


class TesteModulo(unittest.TestCase):
    def test_instalar_modulo(self):
        dados = Path(tempfile.mkdtemp(prefix="foundry_", dir=PASTA_TEMP))
        try:
            destino = fvtt.instalar_modulo(dados)
            self.assertTrue((destino / "module.json").is_file())
            self.assertTrue((destino / "scripts" / "main.js").is_file())
            self.assertEqual(fvtt.versao_modulo(destino), fvtt.versao_modulo(fvtt.pasta_modulo_no_programa()))
            fvtt.instalar_modulo(dados)                                         # atualizar por cima funciona
        finally:
            apagar(dados)

    def test_modulo_e_traducoes_coerentes(self):
        pasta = RAIZ_REPO / "foundry" / "silent-nexus"
        manifesto = json.loads((pasta / "module.json").read_text(encoding="utf-8"))
        self.assertEqual(manifesto["id"], "silent-nexus")
        for idioma in manifesto["languages"]:
            self.assertTrue((pasta / idioma["path"]).is_file(), idioma["path"])
        en = json.loads((pasta / "lang" / "en.json").read_text(encoding="utf-8"))["SILENTNEXUS"]
        pt = json.loads((pasta / "lang" / "pt-BR.json").read_text(encoding="utf-8"))["SILENTNEXUS"]
        self.assertEqual(set(en), set(pt))
        usadas = set()
        import re
        for js in (pasta / "scripts").glob("*.js"):
            texto = js.read_text(encoding="utf-8")
            usadas |= set(re.findall(r'L\("([A-Za-z]+)"', texto)) | set(re.findall(r'SILENTNEXUS\.([A-Za-z]+)', texto))
        self.assertEqual(usadas - set(en), set())

    @unittest.skipUnless(shutil.which("node"), "Node.js não instalado")
    def test_conversao_para_dnd5e_no_node(self):
        resultado = subprocess.run(["node", "--test", str(RAIZ_REPO / "tests" / "foundry" / "mapeamento.test.mjs")],
                                   capture_output=True, text=True, encoding="utf-8", cwd=RAIZ_REPO, timeout=120)
        self.assertEqual(resultado.returncode, 0, resultado.stdout + resultado.stderr)


if __name__ == "__main__":
    unittest.main()
