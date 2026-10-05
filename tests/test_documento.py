"""engine.documento: sumário, links quebrados, autocompletar, citado por, estado dos arquivos e abertura rápida."""
import os
import time
import unittest

from tests.util import novo_projeto, apagar, usar_idioma

import engine.documento as documento


class TesteDocumento(unittest.TestCase):
    def setUp(self):
        usar_idioma("pt_br")
        self.raiz = novo_projeto({
            "Reinos/Vog'Mur.md": "# Vog'Mur\nGovernado por [[Rei Thorvald]] e [[Fantasma]]. ![[mapa.png]]\n\n## Cidades\n```\n# não é título\n```\n### Brasaforte",
            "NPCs/Rei Thorvald.md": "# Rei Thorvald\nstatus: segredo\nVive em [[Vog'Mur|o reino]]. <-- TODO: idade",
            "NPCs/Rascunho.md": "# R\nstatus: rascunho\n\n## 🤫 Notas do Mestre [segredo]\n### Nota do Mestre — x\n> oi",
            "Locais/Torre_v02.md": "# Torre",
        })
        documento.invalidar()

    def tearDown(self):
        apagar(self.raiz)

    def test_sumario_ignora_codigo(self):
        self.assertEqual(documento.sumario((self.raiz / "Reinos/Vog'Mur.md").read_text(encoding="utf-8")),
                         [(1, "Vog'Mur", 1), (2, "Cidades", 4), (3, "Brasaforte", 8)])

    def test_links_quebrados_e_sugestoes(self):
        texto = (self.raiz / "Reinos/Vog'Mur.md").read_text(encoding="utf-8")
        quebrados = [texto[i:f] for i, f in documento.links_quebrados(texto)]
        self.assertEqual(quebrados, ["[[Fantasma]]"])               # imagens e arquivos existentes não contam
        self.assertEqual(documento.sugerir_links("rei"), ["Rei Thorvald"])
        self.assertIn("Torre", documento.sugerir_links("torr"))     # sem o sufixo _v02
        self.assertIn("Rei Thorvald", documento.sugerir_links("thor"))

    def test_citado_por_e_estado(self):
        citado = [os.path.basename(c) for c in documento.citado_por(self.raiz / "Reinos/Vog'Mur.md")]
        self.assertEqual(citado, ["Rei Thorvald.md"])                # aceita [[Vog'Mur|apelido]]
        rei = documento.estado(self.raiz / "NPCs/Rei Thorvald.md")
        self.assertEqual((rei["segredo"], rei["todo"], rei["rascunho"], rei["notas"]), (True, True, False, False))
        rascunho = documento.estado(self.raiz / "NPCs/Rascunho.md")
        self.assertEqual((rascunho["rascunho"], rascunho["notas"], rascunho["segredo"]), (True, True, False))

    def test_assinatura_e_indice_seguem_o_disco(self):
        antes = documento.assinatura_projeto()
        time.sleep(0.05)
        (self.raiz / "Fantasma.md").write_text("# Fantasma", encoding="utf-8")
        self.assertNotEqual(documento.assinatura_projeto(), antes)
        documento.invalidar()
        texto = (self.raiz / "Reinos/Vog'Mur.md").read_text(encoding="utf-8")
        self.assertEqual(documento.links_quebrados(texto), [])

    def test_abertura_rapida(self):
        nomes = [nome for nome, _, _ in documento.buscar_arquivos("t")]
        self.assertEqual(nomes, ["Torre_v02", "Rei Thorvald"])     # primeiro quem começa com "t", depois quem contém
        self.assertEqual(documento.buscar_arquivos("npcs/ra")[0][0], "Rascunho")   # também procura no caminho
        self.assertEqual(len(documento.buscar_arquivos("")), 4)


if __name__ == "__main__":
    unittest.main()
