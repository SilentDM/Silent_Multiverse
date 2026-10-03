"""
Expander: encontra tags <-- TODO nos arquivos e usa a IA para preencher o trecho,
seguido de uma revisão de consistência. Prompts em locale/<idioma>/prompts/expander_*.md.
"""
import re
import shutil
from pathlib import Path

from pydantic import BaseModel, Field

import core.ai_utils as au
import core.eventos as ev
import engine.project_utils as pu
from core.i18n import t
from core.prompts import carregar_prompt

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
    return str(Path(caminho).resolve()) in ARQUIVOS_EM_PROCESSAMENTO


def marcar_processamento(caminho, ativo: bool):
    caminho_abs = str(Path(caminho).resolve())
    if ativo:
        ARQUIVOS_EM_PROCESSAMENTO.add(caminho_abs)
    else:
        ARQUIVOS_EM_PROCESSAMENTO.discard(caminho_abs)


# ----------------------------------------------------------------------
# HISTÓRICO DE VERSÕES
# ----------------------------------------------------------------------
def obter_proximo_caminho_historico(caminho_original):
    """
    Descobre o próximo nome versionado para arquivar dentro de logs/history/,
    preservando a hierarquia de subpastas do projeto.
    Exemplo: logs/history/Reinos/reinado_phaeton_v01.md
    """
    caminho_obj = Path(caminho_original).resolve()
    pasta_historico = pu.PASTA_LOGS / "history"
    try:
        destino_dir = pasta_historico / caminho_obj.relative_to(pu.CAMINHO_PROJETO).parent
    except ValueError:
        destino_dir = pasta_historico
    destino_dir.mkdir(parents=True, exist_ok=True)

    nome_base_limpo = re.sub(r'_v\d+$', '', caminho_obj.stem)
    extensao = caminho_obj.suffix or ".md"
    maior_versao = 0
    for arq in destino_dir.glob(f"{nome_base_limpo}_v*{extensao}"):
        match = re.search(r'_v(\d+)$', arq.stem, flags=re.IGNORECASE)
        if match:
            maior_versao = max(maior_versao, int(match.group(1)))
    return destino_dir / f"{nome_base_limpo}_v{maior_versao + 1:02d}{extensao}"


def arquivar_versao_para_historico(caminho_original):
    """
    Copia a versão atual do arquivo para a pasta de histórico com sufixo de versão.
    Usamos cópia (não mover) para que, se a escrita da nova versão falhar, o original fique intacto.
    """
    caminho_original = Path(caminho_original)
    try:
        if not caminho_original.exists():
            return None
        destino = obter_proximo_caminho_historico(caminho_original)
        shutil.copy2(str(caminho_original), str(destino))
        ev.log(t("expander.log_backup", nome=destino.name))
        return destino
    except Exception as e:
        ev.log(t("expander.log_erro_backup", nome=caminho_original.name, erro=e))
        return None


# ----------------------------------------------------------------------
# CONTEXTO DA EXPANSÃO
# ----------------------------------------------------------------------
def obter_arquivos_relacionados(titulo):
    """Até 10 arquivos que mais citam o título, para dar contexto à expansão."""
    titulo_original = titulo.lower()
    termo = re.sub(r'_', ' ', re.sub(r'_v\d+$', '', titulo_original))
    relacionados = []
    for arquivo in Path(pu.CAMINHO_PROJETO).rglob("*.md"):
        if pu.arquivo_em_pasta_ignorada(arquivo):
            continue
        conteudo = pu.ler_markdown(arquivo)
        if conteudo is None:
            continue
        if (arquivo.stem.lower() == titulo_original
                or any(tag in conteudo for tag in pu.TAG_ALVO)
                or any(ignore in conteudo for ignore in pu.IGNORELIST)):
            continue
        score = conteudo.lower().count(termo)
        if score > 0:
            relacionados.append((arquivo.name, conteudo, score))

    relacionados.sort(key=lambda x: x[2], reverse=True)
    relacionados = relacionados[:10]
    if relacionados:
        ev.log(t("expander.log_relacionados"))
        for nome, _, score in relacionados:
            ev.log(t("expander.log_relacionado", nome=nome, total=score))
    return "\n\n".join(conteudo for _, conteudo, _ in relacionados)


def carregar_diretrizes_estilo():
    """Carrega e unifica as diretrizes de estilo contidas na pasta Style."""
    pasta_estilo = pu.CAMINHO_ESTILO
    conteudo_estilo = []
    if pasta_estilo.is_dir():
        for arquivo in sorted(pasta_estilo.glob("*.md")):
            try:
                titulo = arquivo.stem.replace(" ", "_").replace("-", "_").lower()
                texto = arquivo.read_text(encoding="utf-8").strip()
                conteudo_estilo.append(f"\n<{titulo}>\n{texto}\n</{titulo}>\n")
            except Exception as e:
                ev.log(t("expander.log_erro_estilo", nome=arquivo.name, erro=e))
    return "".join(conteudo_estilo)


def nome_base(path):
    return re.sub(r'_v\d+$', '', path.stem.lower())


def remover_markdown_fences(texto: str) -> str:
    linhas = texto.strip().splitlines()
    if not linhas:
        return texto
    if linhas[0].strip().startswith("```"):
        linhas.pop(0)
    if linhas and linhas[-1].strip().startswith("```"):
        linhas.pop()
    return "\n".join(linhas).strip()


def _contexto_local(arquivo: Path) -> str:
    """Arquivos vizinhos (mesma pasta) que não são rascunho nem têm TODO."""
    blocos = []
    for vizinho in arquivo.parent.glob("*.md"):
        if vizinho.resolve() == arquivo.resolve():
            continue
        conteudo = pu.ler_markdown(vizinho)
        if conteudo and not any(tag in conteudo for tag in pu.TAG_ALVO) and not pu.eh_rascunho(conteudo):
            blocos.append(f"--- {vizinho.name} ---\n{conteudo}\n")
    return "\n".join(blocos)


# ----------------------------------------------------------------------
# EXPANSÃO
# ----------------------------------------------------------------------
def processar_arquivo_unico(path):
    caminho_abs = str(Path(path).resolve())
    ARQUIVOS_EM_PROCESSAMENTO.add(caminho_abs)
    try:
        arquivo = Path(path)
        conteudo = arquivo.read_text(encoding="utf-8")
        tag_encontrada = next((tag for tag in pu.TAG_ALVO if tag in conteudo), None)
        if not tag_encontrada:
            return
        ev.log(t("expander.log_tag", nome=arquivo.name))

        titulo = re.sub(r'_v\d+$', '', arquivo.stem.lower())
        instrucoes = carregar_prompt("expander_sistema", projeto=pu.PASTA_PROJETO, estilo=carregar_diretrizes_estilo())
        prompt = carregar_prompt(
            "expander_usuario", contexto_local=_contexto_local(arquivo), relacionados=obter_arquivos_relacionados(titulo),
            arquivo=arquivo.name, conteudo=conteudo, tag=tag_encontrada)

        try:
            with open(pu.log_path("Prompts.txt"), "w", encoding="utf-8") as f:
                f.write(f"{arquivo.name}\n{prompt}\n")

            # --- ETAPA 1: GERAÇÃO CRIATIVA (ESCRITOR) ---
            ev.log(t("expander.log_gerando", nome=arquivo.name))
            texto_bruto = au.ask_ai(contents=prompt, system_instruction=instrucoes, temperature=0.7)
            if not texto_bruto or not str(texto_bruto).strip():
                ev.log(t("expander.log_vazio", nome=arquivo.name))
                return
            texto_bruto_limpo = remover_markdown_fences(str(texto_bruto))

            # --- ETAPA 2: REVISÃO ESTRUTURADA (EDITOR) ---
            ev.log(t("expander.log_revisando", nome=arquivo.name))
            try:
                revisao = au.ask_ai(
                    contents=carregar_prompt("expander_revisao_usuario", projeto=pu.PASTA_PROJETO, texto=texto_bruto_limpo),
                    system_instruction=carregar_prompt("expander_revisao_sistema"),
                    temperature=0.1, response_schema=RevisaoLore, use_world_context=True)
                revisao_obj = RevisaoLore.model_validate_json(remover_markdown_fences(str(revisao)))
                ev.log(t("expander.log_parecer", nome=arquivo.name,
                         status=t("expander.aprovado") if revisao_obj.aprovado else t("expander.corrigido"),
                         critica=revisao_obj.critica))
                if revisao_obj.texto_final and len(revisao_obj.texto_final.strip()) > 50:
                    conteudo_salvar = remover_markdown_fences(revisao_obj.texto_final)
                else:
                    ev.log(t("expander.log_revisao_vazia"))
                    conteudo_salvar = texto_bruto_limpo
            except Exception as e:
                ev.log(t("expander.log_revisao_falhou", erro=e))
                conteudo_salvar = texto_bruto_limpo

            # --- ETAPA 3: GRAVAÇÃO (nome estável, versão anterior no histórico) ---
            if conteudo_salvar:
                arquivar_versao_para_historico(arquivo)
                arquivo.write_text(conteudo_salvar, encoding="utf-8")
                ev.log(t("expander.log_atualizado", nome=arquivo.name))
        except Exception as e:
            ev.log(t("expander.log_erro", nome=arquivo.name, erro=e))
    finally:
        ARQUIVOS_EM_PROCESSAMENTO.discard(caminho_abs)


def processar_arquivos():
    encontrou_tag = False
    for arquivo in Path(pu.CAMINHO_PROJETO).rglob("*.md"):
        if pu.is_cancelled():
            ev.log(t("expander.log_interrompido"))
            return
        if pu.arquivo_em_pasta_ignorada(arquivo):
            continue
        conteudo = pu.ler_markdown(arquivo) or ""
        if any(tag in conteudo for tag in pu.TAG_ALVO):
            encontrou_tag = True
            if esta_em_processamento(arquivo):
                ev.log(t("expander.log_ja_processando", nome=arquivo.name))
                continue
            processar_arquivo_unico(arquivo)
    if not encontrou_tag:
        ev.log(t("expander.log_nenhuma_tag"))
