import os
# AI_PROVIDER decide, em UM ÚNICO LUGAR, qual implementação de IA o programa
# inteiro vai usar. Valores esperados: "gemini" (padrão/gratuito), "pro" ou "claude".
# O provedor é lido A CADA CHAMADA (e não só no import), para que a troca feita
# na aba 'Opções' valha imediatamente, sem reiniciar o programa.

def obter_provedor_ativo() -> str:
    return os.getenv("AI_PROVIDER", "gemini").strip().lower()

def _obter_implementacao():
    # Importamos SÓ o módulo do provedor escolhido (import tardio), assim as
    # bibliotecas de um provedor não usado nunca são carregadas.
    provedor = obter_provedor_ativo()
    if provedor == "pro":
        from core.ai_pro import ask_ai as impl
    elif provedor == "claude":
        from core.ai_claude import ask_ai as impl
    else:
        from core.ai_gemini import ask_ai as impl
    return impl

def ask_ai(contents=None, system_instruction=None, temperature=None, response_schema=None, use_world_context=True,  is_dm=True):
    """
    Ponto único de entrada para QUALQUER parte do programa que precise
    perguntar algo para a IA (memory.py, wbuilder.py, expander.py, dbot.py, gui.py).

    Quem chama esta função não precisa saber (e não deveria precisar saber)
    qual provedor está ativo no momento — Gemini gratuito ou a IA "Pro".
    Se um dia você quiser trocar de provedor, ou adicionar um terceiro,
    a mudança acontece SÓ aqui em cima, em _obter_implementacao(). Nenhum
    outro arquivo do projeto precisa ser tocado.

    Também garante o IDIOMA de todas as chamadas, num lugar só:
    - acrescenta às instruções de sistema "responda sempre em <idioma ativo>";
    - troca o response_schema por uma cópia com as descrições dos campos traduzidas.
    """
    import core.prompts as prompts
    instrucao_idioma = prompts.instrucao_idioma()
    system_instruction = f"{system_instruction}\n\n{instrucao_idioma}" if system_instruction else instrucao_idioma
    if response_schema is not None:
        response_schema = prompts.schema_localizado(response_schema)

    return _obter_implementacao()(
        contents=contents,
        system_instruction=system_instruction,
        temperature=temperature,
        response_schema=response_schema,
        use_world_context=use_world_context,
        is_dm=is_dm
    )
