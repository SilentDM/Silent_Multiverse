import re, random

def rolar_dados(expressao: str) -> str:
    """Processa expressões de dados (1d20+5, 2d6+3, 1d100 ou 2d20kh1+3) com rastreamento de log."""
    if not expressao or not expressao.strip():
        return "🎲 *Por favor, informe a expressão do dado. Exemplo: `!r 1d20+5` ou `!r 2d6+3`*"

    try:
        expr = expressao.lower().replace(" ", "")
        match = re.match(r'^(\d+)d(\d+)(?:kh1)?([+-]\d+)?$', expr)
        if not match:
            return "🎲 *Formato inválido! Use por exemplo: 1d20+5, 2d6, 1d100 ou 2d20kh1+3*"

        qtd = min(100, int(match.group(1)))
        lados = int(match.group(2))
        mod_str = match.group(3)
        mod = int(mod_str) if mod_str else 0
        kh1 = "kh1" in expr

        if lados <= 0 or qtd <= 0:
            return "🎲 *A quantidade de dados e lados deve ser maior que zero!*"

        dados = [random.randint(1, lados) for _ in range(qtd)]

        if kh1 and qtd > 1:
            escolhido = max(dados)
            total = escolhido + mod
            detalhes = f"Dados: {dados} ➔ Maior: [{escolhido}]"
        else:
            soma = sum(dados)
            total = soma + mod
            detalhes = f"Dados: {dados}"

        mod_txt = f" {mod:+d}" if mod != 0 else ""
        resultado_txt = f"🎲 **Resultado:** `{total}` ({detalhes}{mod_txt})"
        
        print(f"✅ [DISCORD-TRACE] Rolagem: '{expr}' ➔ {total}")
        return resultado_txt

    except Exception as e:
        print(f"❌ [DISCORD-TRACE] Erro ao rolar dados: {e}")
        return f"🎲 *Erro ao rolar dados: {e}*"