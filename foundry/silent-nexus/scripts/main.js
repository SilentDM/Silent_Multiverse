/**
 * Silent Nexus para o Foundry VTT (dnd5e): importa NPCs (com retrato) e lojas (mercadores do Item Piles)
 * do projeto aberto no Silent Multiverse Nexus, neste mesmo PC. Só o Mestre vê o botão.
 */
import { MODULO, PASTA_ATORES, PASTA_IMAGENS } from "./constantes.js";
import { silent } from "./cliente.js";
import { fichaParaAtor, itemProprioDeLoja, ajustarItemDoCompendio, ICONES } from "./mapeamento.js";

const COMPENDIOS_DE_ITENS = ["dnd5e.equipment24", "dnd5e.items"];
const L = (chave, dados) => (dados ? game.i18n.format(`SILENTNEXUS.${chave}`, dados) : game.i18n.localize(`SILENTNEXUS.${chave}`));
const escapar = texto => foundry.utils.escapeHTML ? foundry.utils.escapeHTML(String(texto ?? ""))
  : String(texto ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

/* ------------------------------------------------------------------ */
/* CONFIGURAÇÕES E BOTÃO                                               */
/* ------------------------------------------------------------------ */
Hooks.once("init", () => {
  game.settings.register(MODULO, "url", {
    name: "SILENTNEXUS.ConfigUrl", hint: "SILENTNEXUS.ConfigUrlDica",
    scope: "world", config: true, type: String, default: "http://127.0.0.1:30111"
  });
  game.settings.register(MODULO, "token", {
    name: "SILENTNEXUS.ConfigToken", hint: "SILENTNEXUS.ConfigTokenDica",
    scope: "world", config: true, type: String, default: ""
  });
});

Hooks.on("renderActorDirectory", (app, html) => {
  if (!game.user.isGM) return;
  const raiz = html instanceof HTMLElement ? html : html?.[0];
  const acoes = raiz?.querySelector(".header-actions");
  if (!acoes || acoes.querySelector(".silent-nexus-abrir")) return;
  const botao = document.createElement("button");
  botao.type = "button";
  botao.className = "silent-nexus-abrir";
  botao.innerHTML = `<i class="fa-solid fa-book-skull"></i> ${L("Botao")}`;
  botao.addEventListener("click", () => new JanelaSilent().render({ force: true }));
  acoes.append(botao);
});

/* ------------------------------------------------------------------ */
/* CRIAÇÃO NO FOUNDRY                                                  */
/* ------------------------------------------------------------------ */
async function pastaDeAtores() {
  const existente = game.folders.find(f => f.type === "Actor" && f.name === PASTA_ATORES);
  return existente ?? CONFIG.Folder.documentClass.create({ name: PASTA_ATORES, type: "Actor" });
}

function slug(texto) {
  return String(texto ?? "").normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^A-Za-z0-9._-]+/g, "-").replace(/^-+|-+$/g, "") || "projeto";
}

async function garantirPasta(caminho) {
  const FP = CONFIG.ux?.FilePicker ?? foundry.applications.apps.FilePicker;
  let atual = "";
  for (const parte of caminho.split("/")) {
    atual = atual ? `${atual}/${parte}` : parte;
    try { await FP.createDirectory("data", atual); } catch (_) { /* já existe */ }
  }
  return FP;
}

/** Copia a imagem do projeto para Data/silent-nexus/<projeto>/ e devolve o caminho para usar no Foundry. */
async function enviarImagem(arquivoImagem, projeto) {
  if (!arquivoImagem) return null;
  const blob = await silent.imagem(arquivoImagem);
  const nome = slug(arquivoImagem.split("/").pop().replace(/\.[^.]+$/, "")) + "." + arquivoImagem.split(".").pop().toLowerCase();
  const destino = `${PASTA_IMAGENS}/${slug(projeto)}`;
  const FP = await garantirPasta(destino);
  const resposta = await FP.upload("data", destino, new File([blob], nome, { type: blob.type }), {}, { notify: false });
  return resposta?.path ?? null;
}

function atorDoArquivo(arquivo) {
  return game.actors.find(a => a.getFlag(MODULO, "fonte") === arquivo);
}

async function criarFichaDeNpc(entrada, projeto, forcar) {
  const ficha = await silent.ficha(entrada.arquivo, forcar);
  const img = await enviarImagem(entrada.imagem, projeto).catch(erro => {
    console.warn(`${MODULO} | imagem`, erro);
    return null;
  });
  const pasta = await pastaDeAtores();
  const dados = fichaParaAtor(ficha, { img, pasta: pasta.id, gerarId: () => foundry.utils.randomID() });
  const existente = atorDoArquivo(entrada.arquivo);
  if (existente) {                         // importar de novo atualiza o mesmo ator, sem duplicar
    const { items, ...resto } = dados;
    await existente.deleteEmbeddedDocuments("Item", existente.items.map(i => i.id));
    await existente.update(resto);
    await existente.createEmbeddedDocuments("Item", items);
    return existente;
  }
  return CONFIG.Actor.documentClass.create(dados);
}

let indicesDeItens = null;
async function itemDoSrd(nome) {
  if (!nome) return null;
  if (!indicesDeItens) {
    indicesDeItens = [];
    for (const id of COMPENDIOS_DE_ITENS) {
      const pacote = game.packs.get(id);
      if (pacote) indicesDeItens.push({ pacote, indice: await pacote.getIndex() });
    }
  }
  const alvo = nome.trim().toLowerCase();
  for (const { pacote, indice } of indicesDeItens) {
    const achado = indice.find(e => e.name?.toLowerCase() === alvo);
    if (achado) return (await pacote.getDocument(achado._id))?.toObject();
  }
  return null;
}

async function itensDaLoja(loja) {
  const itens = [];
  for (const item of loja.itens || []) {
    const doSrd = await itemDoSrd(item.nome_srd);
    itens.push(doSrd ? ajustarItemDoCompendio(doSrd, item) : itemProprioDeLoja(item));
  }
  return itens;
}

async function criarLoja(entrada, projeto, forcar) {
  const loja = await silent.loja(entrada.arquivo, forcar);
  const img = await enviarImagem(entrada.imagem, projeto).catch(() => null);
  const itens = await itensDaLoja(loja);
  const existente = atorDoArquivo(entrada.arquivo);
  if (existente) {
    await existente.deleteEmbeddedDocuments("Item", existente.items.map(i => i.id));
    await existente.createEmbeddedDocuments("Item", itens);
    await existente.update({ name: loja.nome, "system.details.biography.value": loja.descricao_html || "" });
    return existente;
  }
  const extras = { "system.details.biography.value": loja.descricao_html || "", [`flags.${MODULO}.fonte`]: entrada.arquivo };
  if (img) Object.assign(extras, { img, "prototypeToken.texture.src": img });
  const itemPiles = game.modules.get("item-piles")?.active ? game.itempiles?.API : null;
  if (itemPiles) {
    await itemPiles.createItemPile({
      createActor: true, actor: loja.nome, items: itens, folders: [PASTA_ATORES],
      itemPileFlags: { type: "merchant" }, actorOverrides: extras
    });
    return atorDoArquivo(entrada.arquivo);
  }
  // Sem Item Piles: um NPC com o estoque no inventário e a descrição na biografia
  const pasta = await pastaDeAtores();
  const ator = await CONFIG.Actor.documentClass.create({
    name: loja.nome, type: "npc", img: img || ICONES.loja, folder: pasta.id, items: itens,
    flags: { [MODULO]: { fonte: entrada.arquivo } }
  });
  await ator.update({ "system.details.biography.value": loja.descricao_html || "" });
  return ator;
}

/* ------------------------------------------------------------------ */
/* JANELA                                                              */
/* ------------------------------------------------------------------ */
class JanelaSilent extends foundry.applications.api.ApplicationV2 {
  static DEFAULT_OPTIONS = {
    id: "silent-nexus-janela",
    classes: ["silent-nexus"],
    window: { title: "SILENTNEXUS.Titulo", icon: "fa-solid fa-book-skull", resizable: true },
    position: { width: 560, height: 640 },
    actions: {
      recarregar: JanelaSilent.#recarregar,
      fichas: JanelaSilent.#criarFichas,
      lojas: JanelaSilent.#criarLojas
    }
  };

  #estado = { carregando: true, erro: null, projeto: "", arquivos: [], filtro: "npc", busca: "", marcados: new Set(), trabalhando: "" };

  async _prepareContext() {
    if (this.#estado.carregando) {
      try {
        const status = await silent.status();
        this.#estado.projeto = status.projeto;
        this.#estado.arquivos = await silent.arquivos();
        this.#estado.erro = null;
      } catch (erro) {
        this.#estado.erro = erro.message;
      }
      this.#estado.carregando = false;
    }
    return {};
  }

  #visiveis() {
    const { arquivos, filtro, busca } = this.#estado;
    const termo = busca.trim().toLowerCase();
    return arquivos.filter(a => (filtro === "todos" || (filtro === "npc" ? a.npc : a.loja))
      && (!termo || a.nome.toLowerCase().includes(termo) || a.pasta.toLowerCase().includes(termo)));
  }

  async _renderHTML() {
    const e = this.#estado;
    if (e.erro) {
      return `<div class="sn-erro"><p><i class="fa-solid fa-plug-circle-xmark"></i> ${escapar(e.erro)}</p>
        <p class="sn-dica">${L("DicaConexao")}</p>
        <button type="button" data-action="recarregar">${L("TentarDeNovo")}</button></div>`;
    }
    const linhas = this.#visiveis().map(a => `
      <li><label>
        <input type="checkbox" data-arquivo="${escapar(a.arquivo)}" ${e.marcados.has(a.arquivo) ? "checked" : ""}>
        <span class="sn-nome">${escapar(a.nome)}</span>
        ${a.imagem ? `<i class="fa-solid fa-image" title="${L("TemImagem")}"></i>` : ""}
        ${a.segredo ? `<i class="fa-solid fa-user-secret" title="${L("Segredo")}"></i>` : ""}
        ${atorDoArquivo(a.arquivo) ? `<i class="fa-solid fa-check" title="${L("JaImportado")}"></i>` : ""}
        <span class="sn-pasta">${escapar(a.pasta)}</span>
      </label></li>`).join("");
    const opcao = (valor, rotulo) => `<option value="${valor}" ${e.filtro === valor ? "selected" : ""}>${L(rotulo)}</option>`;
    return `
      <p class="sn-projeto"><i class="fa-solid fa-book-open"></i> ${L("Projeto", { projeto: escapar(e.projeto) })}
        <button type="button" data-action="recarregar" title="${L("Recarregar")}"><i class="fa-solid fa-rotate"></i></button></p>
      <div class="sn-filtros">
        <select name="filtro">${opcao("npc", "FiltroNpc")}${opcao("loja", "FiltroLoja")}${opcao("todos", "FiltroTodos")}</select>
        <input type="search" name="busca" value="${escapar(e.busca)}" placeholder="${L("Buscar")}">
        <label class="sn-todos"><input type="checkbox" name="todos"> ${L("MarcarTodos")}</label>
      </div>
      <ul class="sn-lista">${linhas || `<li class="sn-vazio">${L("Vazio")}</li>`}</ul>
      <label class="sn-forcar"><input type="checkbox" name="forcar"> ${L("Forcar")}</label>
      <p class="sn-trabalhando">${escapar(e.trabalhando)}</p>
      <footer class="sn-botoes">
        <button type="button" data-action="fichas"><i class="fa-solid fa-user-plus"></i> ${L("CriarFichas")}</button>
        <button type="button" data-action="lojas"><i class="fa-solid fa-store"></i> ${L("CriarLojas")}</button>
      </footer>`;
  }

  _replaceHTML(resultado, conteudo) {
    conteudo.innerHTML = resultado;
    conteudo.querySelectorAll("input[data-arquivo]").forEach(caixa => caixa.addEventListener("change", () => {
      if (caixa.checked) this.#estado.marcados.add(caixa.dataset.arquivo);
      else this.#estado.marcados.delete(caixa.dataset.arquivo);
    }));
    conteudo.querySelector("select[name=filtro]")?.addEventListener("change", evento => {
      this.#estado.filtro = evento.target.value;
      this.render();
    });
    const busca = conteudo.querySelector("input[name=busca]");
    busca?.addEventListener("input", foundry.utils.debounce(evento => {
      this.#estado.busca = evento.target.value;
      this.render().then(() => {
        const campo = this.element.querySelector("input[name=busca]");
        campo?.focus();
        campo?.setSelectionRange(campo.value.length, campo.value.length);
      });
    }, 250));
    conteudo.querySelector("input[name=todos]")?.addEventListener("change", evento => {
      for (const a of this.#visiveis()) {
        if (evento.target.checked) this.#estado.marcados.add(a.arquivo);
        else this.#estado.marcados.delete(a.arquivo);
      }
      this.render();
    });
  }

  static async #recarregar() {
    this.#estado.carregando = true;
    this.render();
  }

  async #executar(criar, rotulo) {
    const selecionados = this.#estado.arquivos.filter(a => this.#estado.marcados.has(a.arquivo));
    if (!selecionados.length) return ui.notifications.warn(L("NadaMarcado"));
    if (this.#estado.trabalhando) return;
    const forcar = !!this.element.querySelector("input[name=forcar]")?.checked;
    let feitos = 0;
    for (const [i, entrada] of selecionados.entries()) {
      this.#estado.trabalhando = L("Trabalhando", { atual: i + 1, total: selecionados.length, nome: entrada.nome });
      await this.render();
      try {
        await criar(entrada, this.#estado.projeto, forcar);
        feitos++;
      } catch (erro) {
        console.error(`${MODULO} |`, erro);
        ui.notifications.error(L("ErroItem", { nome: entrada.nome, erro: erro.message }));
      }
    }
    this.#estado.trabalhando = "";
    this.#estado.marcados.clear();
    await this.render();
    ui.notifications.info(L(rotulo, { total: feitos }));
  }

  static async #criarFichas() {
    await this.#executar(criarFichaDeNpc, "FichasProntas");
  }

  static async #criarLojas() {
    await this.#executar(criarLoja, "LojasProntas");
  }
}
