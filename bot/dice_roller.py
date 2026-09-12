import re
import random
from typing import Optional, Tuple, List

REGEX_TOKEN_DADO = r'^(\d+)?d(\d+)(?:(kh|kl|dh|dl)(\d+))?$'

REGEX_REPETICAO = r'^(\d+)#(.+)$'


def eh_comando_dado(texto: str) -> bool:
    if not texto:
        return False

    primeira_palavra = texto.strip().split()[0].lower()

    match_rep = re.match(REGEX_REPETICAO, primeira_palavra)
    if match_rep:
        primeira_palavra = match_rep.group(2)

    if not re.search(r'\d*d\d+', primeira_palavra):
        return False

    return bool(re.match(r'^[0-9dkhl\+\-\*\/\(\)\.]+$', primeira_palavra))


def _rolar_dado_unitario(qtd: int, lados: int, op_filtro: Optional[str], qtd_filtro: Optional[int]) -> Tuple[int, str]:
    if lados <= 0 or qtd <= 0:
        return 0, "[0]"
    qtd = max(1, min(50, qtd))
    lados = max(1, min(1000, lados))

    rolagens = [random.randint(1, lados) for _ in range(qtd)]

    if op_filtro and qtd_filtro:
        qtd_filtro = min(qtd, max(1, qtd_filtro))
        indices_ordenados = sorted(range(len(rolagens)), key=lambda i: rolagens[i])

        if op_filtro == "kh":
            indices_mantidos = set(indices_ordenados[-qtd_filtro:])
        elif op_filtro == "kl":
            indices_mantidos = set(indices_ordenados[:qtd_filtro])
        elif op_filtro == "dh":
            indices_mantidos = set(indices_ordenados[:-qtd_filtro])
        elif op_filtro == "dl":
            indices_mantidos = set(indices_ordenados[qtd_filtro:])
        else:
            indices_mantidos = set(range(len(rolagens)))

        dados_usados = [rolagens[i] for i in indices_mantidos]
        str_dados = ", ".join(
            f"**{val}**" if i in indices_mantidos else f"~~{val}~~"
            for i, val in enumerate(rolagens)
        )
    else:
        dados_usados = rolagens
        str_dados = ", ".join(str(v) for v in rolagens)

    subtotal = sum(dados_usados)
    detalhes = f"[{str_dados}]"
    return subtotal, detalhes


def avaliar_expressao_composta(expr: str) -> Tuple[int, str]:
    tokens = re.split(r'([\+\-\*\/])', expr.replace(" ", "").lower())
    tokens = [t for t in tokens if t]

    expressao_matematica = []
    detalhes_visual = []

    for token in tokens:
        if token in ["+", "-", "*", "/"]:
            expressao_matematica.append(token)
            detalhes_visual.append(f" {token} ")
            continue

        match_dado = re.match(REGEX_TOKEN_DADO, token)
        if match_dado:
            qtd = int(match_dado.group(1)) if match_dado.group(1) else 1
            lados = int(match_dado.group(2))
            op_filtro = match_dado.group(3)
            qtd_filtro = int(match_dado.group(4)) if match_dado.group(4) else None

            subtotal, str_rolagens = _rolar_dado_unitario(qtd, lados, op_filtro, qtd_filtro)
            expressao_matematica.append(str(subtotal))
            detalhes_visual.append(f"{token}{str_rolagens}")
            continue

        if re.match(r'^\d+(\.\d+)?$', token):
            expressao_matematica.append(token)
            detalhes_visual.append(token)
            continue

        expressao_matematica.append("0")
        detalhes_visual.append(f"?({token})")

    try:
        resultado_bruto = _calcular_aritmetica_segura(tokens_aritmeticos=expressao_matematica)
        resultado_final = int(round(resultado_bruto))
    except Exception:
        resultado_final = 0

    detalhes_formatados = "".join(detalhes_visual)
    return resultado_final, detalhes_formatados


def _calcular_aritmetica_segura(tokens_aritmeticos: List[str]) -> float:
    valores = []
    operadores = []
    i = 0
    while i < len(tokens_aritmeticos):
        token = tokens_aritmeticos[i]
        if token in ["*", "/"]:
            op = token
            prox_num = float(tokens_aritmeticos[i + 1])
            ant_num = valores.pop()
            if op == "*":
                valores.append(ant_num * prox_num)
            elif op == "/":
                valores.append(ant_num / prox_num if prox_num != 0 else 0)
            i += 2
        elif token in ["+", "-"]:
            operadores.append(token)
            i += 1
        else:
            valores.append(float(token))
            i += 1

    total = valores[0] if valores else 0.0
    for idx, op in enumerate(operadores):
        prox = valores[idx + 1]
        if op == "+":
            total += prox
        elif op == "-":
            total -= prox

    return total


def processar_rolagem(texto: str) -> Optional[str]:
    if not texto:
        return None

    partes = texto.strip().split(maxsplit=1)
    comando = partes[0].lower()
    motivo = f" ({partes[1].strip()})" if len(partes) > 1 else ""

    try:
        # CENÁRIO 1: Múltiplas Linhas com '#' (ex: 3#2d12+24+1d6)
        match_rep = re.match(REGEX_REPETICAO, comando)
        if match_rep:
            repeticoes = min(20, int(match_rep.group(1)))
            sub_expr = match_rep.group(2)

            linhas = [f"`{comando}`{motivo}"]
            soma_geral = 0

            for i in range(1, repeticoes + 1):
                total_linha, detalhes_linha = avaliar_expressao_composta(sub_expr)
                soma_geral += total_linha
                linhas.append(f"- {detalhes_linha} = **{total_linha}**")

            linhas.append(f"\n`{soma_geral}`")
            return "\n".join(linhas)

        # CENÁRIO 2: Rolagem Composta Única Inline (ex: 2d12+24+3d8+2d10+1d6)
        total, detalhes = avaliar_expressao_composta(comando)
        return f"`{total}` <—— {motivo}{detalhes}"

    except Exception as e:
        print(f"[DICE] Erro ao processar rolagem: {e}")
        return None