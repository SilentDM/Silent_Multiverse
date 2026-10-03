"""
Prompts de IA e schemas no idioma ativo.

- carregar_prompt(nome, **vars): lê locale/<idioma>/prompts/<nome>.md e troca
  cada {{variavel}} pelo valor informado. (Usamos {{ }} para não colidir com as
  chaves { } de exemplos JSON dentro dos prompts.)
- schema_localizado(Modelo): devolve uma cópia do modelo Pydantic com as
  descrições dos campos traduzidas (chaves "schema.<Modelo>.<campo>" nos .json
  do idioma). Essas descrições vão para a IA junto do response_schema, então
  também precisam estar no idioma escolhido.
"""
import copy
import re
import typing

from pydantic import BaseModel, create_model

import core.i18n as i18n

_PADRAO_VARIAVEL = re.compile(r"\{\{\s*(\w+)\s*\}\}")
_cache_schemas: dict = {}


def caminho_prompt(nome: str, idioma: str = None):
    idioma = i18n.normalizar_idioma(idioma or i18n.idioma_ativo())
    return i18n.pasta_locale() / idioma / "prompts" / f"{nome}.md"


def variaveis_do_prompt(texto: str) -> set:
    return set(_PADRAO_VARIAVEL.findall(texto))


def carregar_prompt(nome: str, idioma: str = None, **variaveis) -> str:
    """Prompt pronto no idioma ativo. Falta de variável é erro (evita enviar '{{x}}' para a IA)."""
    caminho = caminho_prompt(nome, idioma)
    if not caminho.exists():
        caminho = caminho_prompt(nome, i18n.IDIOMA_PADRAO)
    texto = caminho.read_text(encoding="utf-8")

    faltando = variaveis_do_prompt(texto) - set(variaveis)
    if faltando:
        raise KeyError(f"Prompt '{nome}' sem valor para: {', '.join(sorted(faltando))}")

    return _PADRAO_VARIAVEL.sub(lambda m: str(variaveis[m.group(1)]), texto).strip()


def _localizar_tipo(tipo, idioma):
    """Troca, dentro de uma anotação de tipo, os modelos Pydantic pelas versões traduzidas."""
    if isinstance(tipo, type) and issubclass(tipo, BaseModel):
        return schema_localizado(tipo, idioma)
    origem = typing.get_origin(tipo)
    argumentos = typing.get_args(tipo)
    if origem is None or not argumentos:
        return tipo
    novos = tuple(_localizar_tipo(a, idioma) for a in argumentos)
    if novos == argumentos:
        return tipo
    if origem is typing.Union:
        return typing.Union[novos]
    if origem is list:
        return typing.List[novos[0]]
    if origem is dict:
        return typing.Dict[novos[0], novos[1]]
    return tipo


def schema_localizado(modelo, idioma: str = None):
    """Cópia do modelo com descrições no idioma (cacheada). Os nomes dos campos não mudam."""
    idioma = i18n.normalizar_idioma(idioma or i18n.idioma_ativo())
    chave = (modelo, idioma)
    if chave in _cache_schemas:
        return _cache_schemas[chave]

    campos = {}
    for nome, info in modelo.model_fields.items():
        novo_info = copy.copy(info)
        novo_info.description = i18n.traduzir(
            f"schema.{modelo.__name__}.{nome}", idioma, padrao=info.description
        )
        campos[nome] = (_localizar_tipo(info.annotation, idioma), novo_info)

    traduzido = create_model(modelo.__name__, __doc__=modelo.__doc__, **campos)
    _cache_schemas[chave] = traduzido
    return traduzido


def instrucao_idioma(idioma: str = None) -> str:
    """Frase curta reforçando o idioma de resposta (vai ao final das instruções de sistema)."""
    return i18n.traduzir("ia.responder_no_idioma", i18n.normalizar_idioma(idioma or i18n.idioma_ativo()),
                         idioma=i18n.nome_idioma_ia(idioma))
