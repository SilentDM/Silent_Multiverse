"""
Estado do editor de texto, sem nada de interface.

Guarda o arquivo aberto, a "versão" do disco quando foi carregado (para nunca
gravar por cima de uma alteração feita pela IA), o histórico de navegação
Voltar/Avançar e acompanha o arquivo quando ele (ou sua pasta) é movido.
A interface só entrega o texto do widget e exibe o que a sessão devolve.
"""
import os

import engine.arquivos as arq
import engine.expander as ex
from core.i18n import t

# Resultados de salvar()
SALVO = "salvo"
ALTERADO_EXTERNAMENTE = "alterado_externamente"
EM_PROCESSAMENTO = "em_processamento"
SEM_ARQUIVO = None

MAX_HISTORICO = 50


class SessaoEditor:
    def __init__(self):
        self.arquivo_atual = None
        self._mtime_carregado = None
        self.historico = []
        self.indice_historico = -1

    # ------------------------------------------------------------------
    # ABRIR / FECHAR / RECARREGAR
    # ------------------------------------------------------------------
    @staticmethod
    def em_processamento(caminho) -> bool:
        return bool(caminho) and os.path.isfile(caminho) and ex.esta_em_processamento(caminho)

    def abrir(self, caminho: str, registrar_historico: bool = True) -> str:
        """Carrega o arquivo e o torna o atual. Devolve o texto."""
        texto = arq.ler_texto(caminho)
        self.arquivo_atual = os.path.abspath(caminho)
        self._registrar_versao()
        if registrar_historico:
            self._adicionar_ao_historico(self.arquivo_atual)
        return texto

    def fechar(self):
        self.arquivo_atual = None
        self._mtime_carregado = None

    def recarregar(self) -> str:
        return self.abrir(self.arquivo_atual, registrar_historico=False)

    def eh_atual(self, caminho) -> bool:
        return bool(self.arquivo_atual and caminho) and os.path.abspath(caminho) == self.arquivo_atual

    @property
    def nome_atual(self) -> str:
        return os.path.basename(self.arquivo_atual) if self.arquivo_atual else ""

    # ------------------------------------------------------------------
    # SALVAR (com proteção contra sobrescrever a IA)
    # ------------------------------------------------------------------
    def _registrar_versao(self):
        try:
            self._mtime_carregado = os.stat(self.arquivo_atual).st_mtime_ns
        except (OSError, TypeError):
            self._mtime_carregado = None

    def alterado_externamente(self) -> bool:
        if not self.arquivo_atual or self._mtime_carregado is None:
            return False
        try:
            return os.stat(self.arquivo_atual).st_mtime_ns != self._mtime_carregado
        except OSError:
            return False

    def salvar(self, texto: str):
        """
        Grava o texto no arquivo atual. Nunca sobrescreve um arquivo que a IA está
        processando ou que mudou no disco desde que foi carregado.
        """
        if not self.arquivo_atual or not os.path.isfile(self.arquivo_atual):
            return SEM_ARQUIVO
        if ex.esta_em_processamento(self.arquivo_atual):
            return EM_PROCESSAMENTO
        if self.alterado_externamente():
            return ALTERADO_EXTERNAMENTE
        if texto.endswith("\n"):
            texto = texto[:-1]
        with open(self.arquivo_atual, "w", encoding="utf-8") as f:
            f.write(texto)
        self._registrar_versao()
        return SALVO

    def precisa_recarregar(self) -> bool:
        """True se o arquivo aberto foi alterado por fora e não está mais sendo processado."""
        return bool(self.arquivo_atual) and os.path.isfile(self.arquivo_atual) \
            and not ex.esta_em_processamento(self.arquivo_atual) and self.alterado_externamente()

    # ------------------------------------------------------------------
    # MOVER / RENOMEAR
    # ------------------------------------------------------------------
    def acompanhar_movimento(self, origem: str, destino: str) -> bool:
        """Atualiza o arquivo atual e o histórico após 'origem' ser movido para 'destino'. True se o atual mudou."""
        novo = arq.remapear_caminho(self.arquivo_atual, origem, destino)
        mudou = novo != self.arquivo_atual
        if mudou:
            self.arquivo_atual = os.path.abspath(novo)
            self._registrar_versao()
        self.historico = [arq.remapear_caminho(h, origem, destino) for h in self.historico]
        return mudou

    # ------------------------------------------------------------------
    # HISTÓRICO VOLTAR / AVANÇAR
    # ------------------------------------------------------------------
    def _adicionar_ao_historico(self, caminho):
        if 0 <= self.indice_historico < len(self.historico) and self.historico[self.indice_historico] == caminho:
            return
        self.historico = self.historico[: self.indice_historico + 1]
        self.historico.append(caminho)
        if len(self.historico) > MAX_HISTORICO:
            self.historico.pop(0)
        self.indice_historico = len(self.historico) - 1

    def voltar(self):
        """Caminho do arquivo anterior existente no histórico (ou None no início)."""
        alvo = self.indice_historico - 1
        while alvo >= 0 and not os.path.isfile(self.historico[alvo]):
            self.historico.pop(alvo)
            alvo -= 1
        if alvo < 0:
            self.indice_historico = min(self.indice_historico, len(self.historico) - 1)
            return None
        self.indice_historico = alvo
        return self.historico[alvo]

    def avancar(self):
        """Caminho do próximo arquivo existente no histórico (ou None no fim)."""
        alvo = self.indice_historico + 1
        while alvo < len(self.historico) and not os.path.isfile(self.historico[alvo]):
            self.historico.pop(alvo)
        if alvo >= len(self.historico):
            return None
        self.indice_historico = alvo
        return self.historico[alvo]


def mensagem_salvamento(resultado, nome: str) -> str:
    """Texto de log para o resultado de salvar()."""
    if resultado == SALVO:
        return t("editor.log_auto_salvo", nome=nome)
    if resultado == EM_PROCESSAMENTO:
        return t("editor.log_save_ignorado_ia", nome=nome)
    if resultado == ALTERADO_EXTERNAMENTE:
        return t("editor.log_alterado_fora", nome=nome)
    return ""
