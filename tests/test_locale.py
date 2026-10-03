"""Traduções completas: mesmas chaves nos dois idiomas, prompts e descrições de schema para tudo."""
import ast
import json
import re
import unittest

from tests import RAIZ_REPO

import core.i18n as i18n
import core.prompts as prompts

IDIOMAS = list(i18n.IDIOMAS)


def _textos(idioma):
    i18n.recarregar()
    return i18n.carregar_textos(idioma)


def _chaves_estaticas_usadas():
    """Chaves literais passadas a t(), tc(), traduzir() e aos helpers de status das páginas."""
    usadas = set()
    padrao = re.compile(r'\b(?:t|tc|traduzir|_status)\(\s*"([^"]+)"')
    for pasta in ("ui", "engine", "core", "bot"):
        for arquivo in (RAIZ_REPO / pasta).rglob("*.py"):
            usadas.update(padrao.findall(arquivo.read_text(encoding="utf-8")))
    return usadas


class TesteTraducoes(unittest.TestCase):
    def test_mesmas_chaves_nos_idiomas(self):
        base = set(_textos(IDIOMAS[0]))
        for idioma in IDIOMAS[1:]:
            outro = set(_textos(idioma))
            self.assertEqual(base - outro, set(), f"faltam em {idioma}")
            self.assertEqual(outro - base, set(), f"sobram em {idioma}")

    def test_sem_chaves_duplicadas_entre_arquivos(self):
        for idioma in IDIOMAS:
            vistos = {}
            for arquivo in (i18n.pasta_locale() / idioma).glob("*.json"):
                for chave in json.loads(arquivo.read_text(encoding="utf-8")):
                    self.assertNotIn(chave, vistos, f"{chave} em {arquivo.name} e {vistos.get(chave)}")
                    vistos[chave] = arquivo.name

    def test_chaves_usadas_existem(self):
        for idioma in IDIOMAS:
            textos = _textos(idioma)
            faltando = sorted(k for k in _chaves_estaticas_usadas() if k not in textos)
            self.assertEqual(faltando, [], f"chaves usadas no código sem tradução em {idioma}")

    def test_variaveis_iguais_nos_dois_idiomas(self):
        a, b = _textos(IDIOMAS[0]), _textos(IDIOMAS[1])
        variaveis = re.compile(r"\{(\w+)\}")
        for chave in a:
            self.assertEqual(set(variaveis.findall(a[chave])), set(variaveis.findall(b[chave])), chave)

    def test_prompts_existem_com_as_mesmas_variaveis(self):
        pastas = {idioma: i18n.pasta_locale() / idioma / "prompts" for idioma in IDIOMAS}
        nomes = {idioma: {p.name for p in pasta.glob("*.md")} for idioma, pasta in pastas.items()}
        self.assertEqual(nomes[IDIOMAS[0]], nomes[IDIOMAS[1]])
        for nome in nomes[IDIOMAS[0]]:
            v = [prompts.variaveis_do_prompt((pastas[i] / nome).read_text(encoding="utf-8")) for i in IDIOMAS]
            self.assertEqual(v[0], v[1], nome)

    def test_prompts_usados_existem(self):
        usados = set()
        for pasta in ("engine", "core", "bot"):
            for arquivo in (RAIZ_REPO / pasta).rglob("*.py"):
                usados.update(re.findall(r'carregar_prompt\(\s*"(\w+)"', arquivo.read_text(encoding="utf-8")))
        for idioma in IDIOMAS:
            for nome in usados:
                self.assertTrue(prompts.caminho_prompt(nome, idioma).exists(), f"{idioma}/prompts/{nome}.md")

    def test_todos_os_campos_de_schema_traduzidos(self):
        from pydantic import BaseModel
        import engine.council_engine, engine.dnd_schemas, engine.expander, engine.knowledge_schemas, engine.persona_schemas
        modulos = [engine.council_engine, engine.dnd_schemas, engine.expander, engine.knowledge_schemas, engine.persona_schemas]
        for idioma in IDIOMAS:
            textos = _textos(idioma)
            for modulo in modulos:
                for objeto in vars(modulo).values():
                    if isinstance(objeto, type) and issubclass(objeto, BaseModel) and objeto.__module__ == modulo.__name__:
                        for campo, info in objeto.model_fields.items():
                            if info.description:
                                self.assertIn(f"schema.{objeto.__name__}.{campo}", textos, idioma)

    def test_manual_nos_dois_idiomas(self):
        for idioma in IDIOMAS:
            self.assertTrue((i18n.pasta_locale() / idioma / "manual.md").exists())


if __name__ == "__main__":
    unittest.main()
