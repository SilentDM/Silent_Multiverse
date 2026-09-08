import os, re, shutil
from pathlib import Path
import core.ai_utils as au
import engine.project_utils as pu
from pydantic import BaseModel, Field

ARQUIVOS_EM_PROCESSAMENTO = set()

class RevisaoLore(BaseModel):
    aprovado: bool = Field(
        description="True se o texto estiver 100% coerente com o lore; False se precisou de correções."
    )
    critica: str = Field(
        description="Breve explicação técnica das incoerências encontradas ou confirmação de conformidade."
    )
    texto_final: str = Field(
        description="O conteúdo Markdown COMPLETO do documento. Se aprovado, deve conter o texto revisado integralmente, sem comentários ou pareceres dentro dele."
    )

def esta_em_processamento(caminho) -> bool:
    caminho_abs = str(Path(caminho).resolve())
    return caminho_abs in ARQUIVOS_EM_PROCESSAMENTO

def marcar_processamento(caminho, ativo: bool):
    caminho_abs = str(Path(caminho).resolve())
    if ativo:
        ARQUIVOS_EM_PROCESSAMENTO.add(caminho_abs)
    else:
        ARQUIVOS_EM_PROCESSAMENTO.discard(caminho_abs)

def obter_proximo_caminho_historico(caminho_original):
    """
    Descobre o próximo nome versionado para arquivar dentro de logs/history/,
    preservando a hierarquia de subpastas do projeto.
    Exemplo: logs/history/Reinos/reinado_phaeton_v01.md
    """
    caminho_obj = Path(caminho_original).resolve()
    pasta_historico = pu.PASTA_LOGS / "history"

    try:
        relativo = caminho_obj.relative_to(pu.CAMINHO_PROJETO)
        destino_dir = pasta_historico / relativo.parent
    except ValueError:
        destino_dir = pasta_historico

    destino_dir.mkdir(parents=True, exist_ok=True)

    # Nome base sempre limpo sem sufixos
    nome_base = re.sub(r'_v\d+$', '', caminho_obj.stem)
    extensao = caminho_obj.suffix or ".md"
    maior_versao = 0

    # Varre a pasta de histórico procurando versões existentes
    for arq in destino_dir.glob(f"{nome_base}_v*{extensao}"):
        match = re.search(r'_v(\d+)$', arq.stem, flags=re.IGNORECASE)
        if match:
            maior_versao = max(maior_versao, int(match.group(1)))

    nova_versao = maior_versao + 1
    return destino_dir / f"{nome_base}_v{nova_versao:02d}{extensao}"

def arquivar_versao_para_historico(caminho_original):
    """
    Copia a versão atual do arquivo para a pasta de histórico com sufixo de versão.
    Usamos shutil.copy2 em vez de move para garantir que, se a escrita da nova versão
    falhar logo a seguir, o arquivo original permaneça intacto.
    """
    try:
        caminho_original = Path(caminho_original)
        if not caminho_original.exists():
            return None

        destino_arquivo = obter_proximo_caminho_historico(caminho_original)
        shutil.copy2(str(caminho_original), str(destino_arquivo))
        print(f"📦 Backup arquivado no histórico: {destino_arquivo.name}")
        return destino_arquivo
    except Exception as e:
        print(f"Erro ao arquivar versão no histórico ({caminho_original.name}): {e}")
        return None

def obter_arquivos_relacionados(titulo):
    relacionados = []
    for arquivo in Path(pu.PASTA_PROJETO).rglob("*.md"):
        if any(part in pu.IGNORELIST for part in arquivo.parts):
            continue
        try:
            with open(arquivo, encoding="utf-8", errors="ignore") as f:
                conteudo = f.read()
        except Exception:
            continue
        if (
            arquivo.stem.lower() == titulo
            or any(tag in conteudo for tag in pu.TAG_ALVO)
            or any(ignore in conteudo for ignore in pu.IGNORELIST)
        ):
            continue
        titulo = re.sub(r'_v\d+$', '', titulo.lower())
        titulo = re.sub(r'_',' ', titulo)
        score = conteudo.lower().count(titulo)
        if score > 0:
            relacionados.append((arquivo.name, conteudo, score))

    relacionados.sort(
        key=lambda x: x[2],
        reverse=True
    )
    
    relacionados = relacionados[:10]
    if relacionados:
        print("\n==== Arquivos relacionados encontrados:====")
        for name, _, score in relacionados:
            print(f"{name}: {score} ocorrências")
    
    return "\n\n".join(
        conteudo for _, conteudo, _ in relacionados
    )

def carregar_diretrizes_estilo():
    """Carrega e unifica as diretrizes de estilo contidas na pasta designada."""
    pasta_estilo = pu.CAMINHO_ESTILO
    conteudo_estilo = []
    if pasta_estilo.exists() and pasta_estilo.is_dir():
        for arquivo in sorted(pasta_estilo.glob("*.md")):
            try:
                with open(arquivo, "r", encoding="utf-8") as f:
                    titulo = arquivo.stem.replace(" ", "_").replace("-", "_").lower()
                    conteudo_estilo.append(f"\n<diretrizes_de_{titulo}>\n{f.read().strip()}\n</diretrizes_de_{titulo}>\n")
            except Exception as e:
                print(f"Erro ao carregar diretriz {arquivo.name}: {e}")
    return "".join(conteudo_estilo)

def nome_base(path):
    return re.sub(r'_v\d+$', '', path.stem.lower())

def remover_markdown_fences(texto: str) -> str:
    linhas = texto.strip().splitlines()
    if not linhas:
        return texto

    # Se a primeira linha começar com as crases, nós a removemos
    if linhas[0].strip().startswith("```"):
        linhas.pop(0)
        
    # Se a última linha terminar com as crases, nós a removemos
    if linhas and linhas[-1].strip().startswith("```"):
        linhas.pop()
        
    return "\n".join(linhas).strip()

def processar_arquivo_unico(path):
    caminho_abs = str(Path(path).resolve())
    
    # 🛡️ Trava de Segurança contra execução em duplicidade / loop
    if caminho_abs in ARQUIVOS_EM_PROCESSAMENTO:
        print(f"⚠️ Arquivo {Path(path).name} já está sendo processado pelo Expander. Pulando...")
        return

    ARQUIVOS_EM_PROCESSAMENTO.add(caminho_abs)

    try:
        estilo_contexto = carregar_diretrizes_estilo()
        instrucoes_globais = f"""
Você é um Mestre de Mesa (DM) de RPG experiente e escritor de fantasia.
Seu objetivo é preencher lacunas de desenvolvimento do cenário de {pu.PASTA_PROJETO}.
# Diretrizes e Regras Adicionais do Projeto:
{estilo_contexto}
"""
        arquivo = Path(path)
        with open(arquivo, 'r', encoding='utf-8') as f:
            linhas = f.readlines()
            conteudo = "".join(linhas)
            titulo = re.sub(r'_v\d+$', '', arquivo.stem.lower())

        tag_encontrada = next((tag for tag in pu.TAG_ALVO if tag in conteudo), None)
        if not tag_encontrada:
            return

        print(f"\n=====\nTag encontrada no arquivo:\n{arquivo.name}\n=====")
        
        # 1. Montagem do contexto local de arquivos vizinhos
        info_locais = ""
        for arq_p in arquivo.parent.glob("*.md"):
            if arq_p.resolve() != arquivo.resolve():
                try:
                    with open(arq_p, "r", encoding="utf-8") as f:
                        conteudo_local = f.read()
                        if not any(tag in conteudo_local for tag in pu.TAG_ALVO) and "status: rascunho" not in conteudo_local.lower():
                            info_locais += f"--- {arq_p.name} ---\n{conteudo_local}\n\n"
                except Exception:
                    pass

        info_importante = obter_arquivos_relacionados(titulo)

        prompt_conteudo = f"""
<contexto_local>
{info_locais}
</contexto_local>

<arquivos_relacionados>
{info_importante}
</arquivos_relacionados>

<arquivo_alvo nome="{arquivo.name}">
{conteudo}
</arquivo_alvo>

<instrucao_tarefa>
Identifique a tag '{tag_encontrada}' dentro de <arquivo_alvo>.
Substitua essa tag pelo conteúdo expandido, mantendo total coesão com <contexto_local> e <arquivos_relacionados>.
</instrucao_tarefa>

<regras_de_resposta>
1. Retorne APENAS o conteúdo final do arquivo editado em Markdown.
2. Não inclua comentários, notas ou tags XML na sua resposta.
3. FORMATAÇÃO E WIKILINKS:
    - Organize o texto com títulos (#, ##, ###).
    - Use citações (> texto) para caixas de lore, rumores, manuscritos ou diários.
    - Use negrito (**palavra**) em termos e itens de destaque.
    - CRIE WIKILINKS [[Nome do Conceito]]: Sempre que citar personagens, cidades, locais, facções, deuses ou relíquias do universo, envolva o nome em colchetes duplos.
</regras_de_resposta>
"""

        try:
            with open(pu.log_path("Prompts.txt"), 'w', encoding='utf-8') as f:
                f.write(f"Alterando Arquivo: {arquivo.name}\n")
                f.write(prompt_conteudo + '\n')
            
            # --- ETAPA 1: GERAÇÃO CRIATIVA (ESCRITOR) ---
            print(f"Gerando expansão para {arquivo.name}...")
            texto_bruto = au.ask_ai(
                contents=prompt_conteudo,
                system_instruction=instrucoes_globais,
                temperature=0.7
            )

            if not texto_bruto or not str(texto_bruto).strip():
                print(f"⚠️ O retorno do modelo para {arquivo.name} foi vazio.")
                return

            texto_bruto_limpo = remover_markdown_fences(str(texto_bruto))

            # --- ETAPA 2: VALIDAÇÃO E REVISÃO ESTRUTURADA (EDITOR) ---
            print(f"Revisando consistência de lore para {arquivo.name}...")
            prompt_revisao = f"""
Você é o Editor-Chefe de Lore de {pu.PASTA_PROJETO}.
Analise o texto gerado abaixo confrontando-o com o compêndio de lore fornecido no contexto de mundo.

DIRETRIZES DE REVISÃO:
- Avalie se há contradições com datas, personagens, locais ou tom já estabelecidos.
- Se houver inconsistências: corrija-as diretamente no campo 'texto_final'.
- Se o texto estiver coerente e aprovado: preencha o campo 'texto_final' integralmente com o texto recebido.
- IMPORTANTE: O campo 'texto_final' deve conter EXCLUSIVAMENTE o conteúdo Markdown do artigo. NUNCA coloque relatórios, justificativas, pareceres ou avisos como "Status: Aprovado" dentro de 'texto_final'. Use o campo 'critica' para suas observações técnicas.

TEXTO GERADO PARA REVISÃO:
{texto_bruto_limpo}
"""
            revisao_resultado = au.ask_ai(
                contents=prompt_revisao,
                system_instruction="Você é um validador rigoroso de consistência de universos fictícios. Responda estritamente através do schema JSON.",
                temperature=0.1,
                response_schema=RevisaoLore,
                use_world_context=True
            )

            conteudo_salvar = None
            try:
                json_str = remover_markdown_fences(str(revisao_resultado))
                revisao_obj = RevisaoLore.model_validate_json(json_str)

                print(f"\n📋 [Parecer do Editor para {arquivo.name}]:")
                print(f"   Status: {'APROVADO' if revisao_obj.aprovado else 'CORRIGIDO COM ALTERAÇÕES'}")
                print(f"   Observações: {revisao_obj.critica}")

                # Validação defensiva do texto final
                if revisao_obj.texto_final and len(revisao_obj.texto_final.strip()) > 50:
                    conteudo_salvar = remover_markdown_fences(revisao_obj.texto_final)
                else:
                    print("⚠️ Revisor retornou texto_final vazio ou inválido. Usando texto da primeira etapa como fallback.")
                    conteudo_salvar = texto_bruto_limpo

            except Exception as e:
                print(f"⚠️ Falha ao decodificar JSON de revisão ({e}). Usando texto original gerado como fallback seguro.")
                conteudo_salvar = texto_bruto_limpo

            # --- ETAPA 3: PERSISTÊNCIA COMPATÍVEL COM OBSIDIAN ---
            if conteudo_salvar:
                # 1. Arquiva versão anterior no histórico (_v01.md, _v02.md...)
                arquivar_versao_para_historico(arquivo)

                # 2. Mantém o nome limpo no cofre para não quebrar Wikilinks [[...]]
                with open(arquivo, 'w', encoding='utf-8') as f:
                    f.write(conteudo_salvar)
                print(f"✅ Arquivo atualizado com sucesso: {arquivo.name}")

        except Exception as e:
            print(f"❌ Erro ao processar {arquivo.name}: {e}")

    finally:
        ARQUIVOS_EM_PROCESSAMENTO.discard(caminho_abs)

def processar_arquivos():
    caminho_projeto = Path(pu.PASTA_PROJETO)
    encontrou_tag = False
    
    for arquivo in caminho_projeto.rglob("*.md"):
        if pu.is_cancelled():
            print("\n🛑 Processamento do Expander interrompido pelo usuário!")
            return
        with open(arquivo, 'r', encoding='utf-8') as f:
            conteudo = f.read()
            
        if any(tag in conteudo for tag in pu.TAG_ALVO):
            encontrou_tag = True
            processar_arquivo_unico(arquivo)
            
    if not encontrou_tag:
        print("Nenhuma tag encontrada.")

if __name__ == "__main__":
    processar_arquivos()
    print("\n✅ Processamento concluído!")