/** Conversa com a ponte local do Silent (127.0.0.1), sempre com o token configurado no módulo. */
import { MODULO } from "./constantes.js";

function configuracao() {
  return {
    url: String(game.settings.get(MODULO, "url") || "http://127.0.0.1:30111").replace(/\/+$/, ""),
    token: String(game.settings.get(MODULO, "token") || "")
  };
}

async function pedir(caminho, { metodo = "GET", corpo = null, binario = false } = {}) {
  const { url, token } = configuracao();
  const opcoes = { method: metodo, headers: { "X-Silent-Token": token } };
  if (corpo) {
    opcoes.headers["Content-Type"] = "application/json";
    opcoes.body = JSON.stringify(corpo);
  }
  let resposta;
  try {
    resposta = await fetch(url + caminho, opcoes);
  } catch (erro) {
    throw new Error(game.i18n.format("SILENTNEXUS.ErroConexao", { url }));
  }
  if (!resposta.ok) {
    let mensagem = `${resposta.status}`;
    try { mensagem = (await resposta.json()).erro || mensagem; } catch (_) { /* resposta sem JSON */ }
    throw new Error(mensagem);
  }
  return binario ? resposta.blob() : resposta.json();
}

export const silent = {
  status: () => pedir("/status"),
  arquivos: async () => (await pedir("/arquivos")).arquivos,
  ficha: (arquivo, forcar = false) => pedir("/ficha", { metodo: "POST", corpo: { arquivo, forcar } }),
  loja: (arquivo, forcar = false) => pedir("/loja", { metodo: "POST", corpo: { arquivo, forcar } }),
  imagem: arquivo => pedir(`/imagem?arquivo=${encodeURIComponent(arquivo)}`, { binario: true })
};
