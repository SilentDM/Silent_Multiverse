"""
Ponte local entre o Silent e o SilentModule do Foundry VTT (funcionalidade Silent Nexus).

Um servidor HTTP pequeno que só escuta no próprio PC (127.0.0.1) e exige o token que o Mestre copia
das Opções para as configurações do módulo. Sem o token, nenhuma página do navegador consegue ler
o projeto pelo endereço local. As chaves da IA nunca saem do Silent: o módulo só recebe respostas prontas.

Rotas (todas exigem o cabeçalho X-Silent-Token):
  GET  /status                  projeto aberto e versão
  GET  /arquivos                arquivos .md do projeto (marcando NPCs, lojas e a imagem de mesmo nome)
  GET  /imagem?arquivo=...      bytes de uma imagem do projeto
  POST /ficha {arquivo, forcar} ficha de NPC no formato do módulo (gerada pela IA, com cache)
  POST /loja  {arquivo, forcar} estoque de loja no formato do módulo
"""
import hmac
import json
import mimetypes
import re
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import core.config as cfg
import core.eventos as ev
import engine.foundry as foundry
import engine.project_utils as pu
from core.i18n import t
from core.versao import VERSAO

PORTA_PADRAO = 30111
ORIGEM_LOCAL = re.compile(r"^https?://(localhost|127\.0\.0\.1|\[::1\])(:\d+)?$")
TAMANHO_MAXIMO_PEDIDO = 64 * 1024

_estado = {"servidor": None, "thread": None, "gerando": 0}
_trava = threading.Lock()


def token() -> str:
    """O token da ponte (criado na primeira vez)."""
    atual = cfg.obter("foundry_token", "")
    if not atual:
        atual = secrets.token_urlsafe(18)
        cfg.atualizar_configuracoes({"foundry_token": atual})
    return atual


def novo_token() -> str:
    novo = secrets.token_urlsafe(18)
    cfg.atualizar_configuracoes({"foundry_token": novo})
    return novo


def porta() -> int:
    try:
        return int(cfg.obter("foundry_porta", PORTA_PADRAO))
    except (TypeError, ValueError):
        return PORTA_PADRAO


def ativa() -> bool:
    return _estado["servidor"] is not None


def _marcar_geracao(inicio: bool):
    """Mostra a tarefa "Foundry" na barra de status enquanto a IA gera algo para o módulo."""
    with _trava:
        antes = _estado["gerando"]
        _estado["gerando"] = max(0, antes + (1 if inicio else -1))
        depois = _estado["gerando"]
    if (antes == 0) != (depois == 0):
        ev.emitir("acao.estado", {"acao": "foundry", "rodando": depois > 0})


class _Pedido(BaseHTTPRequestHandler):
    server_version = "SilentNexusPonte/1"

    def log_message(self, formato, *args):        # sem barulho no console; o Log do Silent recebe o essencial
        pass

    # --- cabeçalhos ---
    def _cors(self):
        origem = self.headers.get("Origin", "")
        if ORIGEM_LOCAL.match(origem):
            self.send_header("Access-Control-Allow-Origin", origem)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Silent-Token")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Private-Network", "true")

    def _json(self, status: int, dados):
        corpo = json.dumps(dados, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self._cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def _autorizado(self) -> bool:
        recebido = self.headers.get("X-Silent-Token", "")
        if recebido and hmac.compare_digest(recebido, token()):
            return True
        self._json(401, {"erro": t("foundry.erro_token")})
        return False

    def _corpo(self) -> dict:
        tamanho = min(int(self.headers.get("Content-Length") or 0), TAMANHO_MAXIMO_PEDIDO)
        try:
            return json.loads(self.rfile.read(tamanho) or b"{}")
        except ValueError:
            return {}

    # --- métodos ---
    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        if not self._autorizado():
            return
        url = urlparse(self.path)
        try:
            if url.path == "/status":
                self._json(200, {"ok": True, "projeto": pu.PASTA_PROJETO, "versao": VERSAO})
            elif url.path == "/arquivos":
                self._json(200, {"arquivos": foundry.listar_arquivos()})
            elif url.path == "/imagem":
                self._imagem(parse_qs(url.query).get("arquivo", [""])[0])
            else:
                self._json(404, {"erro": "?"})
        except foundry.ErroFoundry as e:
            self._json(404, {"erro": str(e)})
        except Exception as e:
            ev.log(t("foundry.log_erro", erro=e))
            self._json(500, {"erro": str(e)})

    def do_POST(self):
        if not self._autorizado():
            return
        rota = urlparse(self.path).path
        gerar = {"/ficha": foundry.gerar_ficha, "/loja": foundry.gerar_loja}.get(rota)
        if gerar is None:
            self._json(404, {"erro": "?"})
            return
        pedido = self._corpo()
        arquivo = str(pedido.get("arquivo", ""))
        ev.log(t("foundry.log_pedido", tipo=t(f"foundry.tipo{rota.replace('/', '.')}"), nome=Path(arquivo).stem))
        _marcar_geracao(True)
        try:
            self._json(200, gerar(arquivo, forcar=bool(pedido.get("forcar"))))
        except foundry.ErroFoundry as e:
            self._json(404, {"erro": str(e)})
        except Exception as e:
            ev.log(t("foundry.log_erro", erro=e))
            self._json(500, {"erro": str(e)})
        finally:
            _marcar_geracao(False)

    def _imagem(self, relativo: str):
        caminho = foundry.caminho_do_arquivo(relativo)
        if caminho.suffix.lower() not in foundry.EXTENSOES_IMAGEM:
            raise foundry.ErroFoundry(t("foundry.erro_arquivo", nome=relativo))
        dados = caminho.read_bytes()
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", mimetypes.guess_type(caminho.name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(dados)))
        self.end_headers()
        self.wfile.write(dados)


def iniciar(porta_escolhida: int = None) -> bool:
    """Liga a ponte (se ainda não estiver ligada). Devolve False se a porta estiver ocupada."""
    if ativa():
        return True
    porta_escolhida = porta_escolhida or porta()
    try:
        servidor = ThreadingHTTPServer(("127.0.0.1", porta_escolhida), _Pedido)
    except OSError as e:
        ev.log(t("foundry.log_porta_ocupada", porta=porta_escolhida, erro=e))
        return False
    servidor.daemon_threads = True
    thread = threading.Thread(target=servidor.serve_forever, daemon=True, name="ponte-foundry")
    thread.start()
    _estado.update(servidor=servidor, thread=thread)
    token()
    ev.log(t("foundry.log_ligada", porta=servidor.server_address[1]))
    return True


def parar():
    servidor = _estado.get("servidor")
    if servidor is not None:
        servidor.shutdown()
        servidor.server_close()
        _estado.update(servidor=None, thread=None)
        ev.log(t("foundry.log_desligada"))


def porta_em_uso() -> int:
    servidor = _estado.get("servidor")
    return servidor.server_address[1] if servidor else 0
