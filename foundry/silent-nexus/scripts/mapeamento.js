/**
 * Converte as fichas e lojas que o Silent manda para os dados do dnd5e 5.3.x (Atores e Itens).
 * Sem nenhuma dependência do Foundry: dá para testar com o Node (tests/foundry/mapeamento.test.mjs).
 */

export const ATRIBUTOS = {
  forca: "str", destreza: "dex", constituicao: "con",
  inteligencia: "int", sabedoria: "wis", carisma: "cha"
};

export const ICONES = {
  melee: "icons/svg/sword.svg",
  ranged: "icons/svg/target.svg",
  spell: "icons/svg/fire.svg",
  feat: "icons/svg/aura.svg",
  loja: "icons/svg/item-bag.svg"
};

// Nomes de idiomas (português e inglês, sem acento) -> códigos do dnd5e
const IDIOMAS = {
  comum: "common", common: "common", anao: "dwarvish", anão: "dwarvish", dwarvish: "dwarvish",
  elfico: "elvish", elvish: "elvish", gigante: "giant", giant: "giant", gnomico: "gnomish", gnomish: "gnomish",
  goblin: "goblin", halfling: "halfling", pequenino: "halfling", orc: "orc", orquico: "orc",
  abissal: "abyssal", abyssal: "abyssal", celestial: "celestial", draconico: "draconic", draconic: "draconic",
  "fala profunda": "deep", "deep speech": "deep", infernal: "infernal", primordial: "primordial",
  silvestre: "sylvan", sylvan: "sylvan", subcomum: "undercommon", undercommon: "undercommon",
  "giria dos ladroes": "cant", "thieves' cant": "cant", "thieves cant": "cant", druidico: "druidic", druidic: "druidic"
};

const semAcento = texto => String(texto ?? "").normalize("NFD").replace(/[̀-ͯ]/g, "").trim().toLowerCase();

export function idiomas(lista = []) {
  const codigos = [], outros = [];
  for (const nome of lista) {
    const codigo = IDIOMAS[semAcento(nome)];
    if (codigo) { if (!codigos.includes(codigo)) codigos.push(codigo); }
    else if (String(nome).trim()) outros.push(String(nome).trim());
  }
  return { value: codigos, custom: outros.join("; ") };
}

const pes = valor => (Number(valor) > 0 ? String(Math.round(Number(valor))) : null);

/** Um ataque da ficha -> Item "weapon" (arma natural) com uma atividade de ataque. */
export function itemDeAtaque(ataque, gerarId) {
  const id = gerarId();
  const corpoACorpo = ataque.alcance !== "ranged";
  const propriedades = [];
  if (corpoACorpo && Number(ataque.alcance_pes) >= 10) propriedades.push("rch");
  const alcance = corpoACorpo
    ? { value: null, long: null, units: "ft" }
    : { value: Number(ataque.alcance_pes) || 30, long: Number(ataque.alcance_longo_pes) || null, units: "ft" };
  return {
    name: ataque.nome,
    type: "weapon",
    img: ataque.classificacao === "spell" ? ICONES.spell : (corpoACorpo ? ICONES.melee : ICONES.ranged),
    system: {
      description: { value: ataque.descricao_html || "" },
      type: { value: "natural" },
      quantity: 1,
      equipped: true,
      properties: propriedades,
      range: alcance,
      damage: {
        base: {
          number: Math.max(1, Number(ataque.dados_quantidade) || 1),
          denomination: Number(ataque.dados_faces) || 6,
          types: [ataque.tipo_dano || "bludgeoning"]
        }
      },
      activities: {
        [id]: {
          _id: id,
          type: "attack",
          activation: { type: "action", value: 1 },
          attack: { type: { value: corpoACorpo ? "melee" : "ranged", classification: ataque.classificacao === "spell" ? "spell" : "weapon" } },
          damage: { includeBase: true, parts: [] },
          sort: 0
        }
      }
    }
  };
}

/** Um traço ou ação especial -> Item "feat" de monstro (com atividade quando não é passivo). */
export function itemDeHabilidade(habilidade, gerarId) {
  const atividades = {};
  if (habilidade.ativacao && habilidade.ativacao !== "passive") {
    const id = gerarId();
    atividades[id] = { _id: id, type: "utility", activation: { type: habilidade.ativacao, value: 1 }, sort: 0 };
  }
  return {
    name: habilidade.nome,
    type: "feat",
    img: ICONES.feat,
    system: {
      description: { value: habilidade.descricao_html || habilidade.descricao || "" },
      type: { value: "monster" },
      activities: atividades
    }
  };
}

/** A ficha completa -> dados de criação de um Ator NPC do dnd5e. */
export function fichaParaAtor(ficha, { img = null, pasta = null, gerarId } = {}) {
  const resistencias = new Set(ficha.testes_resistencia || []);
  const abilities = {};
  for (const [campo, codigo] of Object.entries(ATRIBUTOS)) {
    abilities[codigo] = { value: Number(ficha[campo]) || 10, proficient: resistencias.has(codigo) ? 1 : 0 };
  }
  const skills = {};
  for (const codigo of ficha.pericias || []) skills[codigo] = { value: 1 };

  // Ataques mágicos usam o atributo de conjuração: o maior entre Int, Sab e Car
  const conjuracao = ["int", "wis", "cha"].reduce((melhor, a) => (abilities[a].value > abilities[melhor].value ? a : melhor), "int");

  const dados = {
    name: ficha.nome,
    type: "npc",
    system: {
      abilities,
      skills,
      attributes: {
        ac: { calc: "flat", flat: Number(ficha.classe_armadura) || 10 },
        hp: { value: Number(ficha.pontos_de_vida) || 1, max: Number(ficha.pontos_de_vida) || 1, formula: ficha.formula_pv || "" },
        movement: {
          walk: pes(ficha.deslocamento_pes) ?? "30", fly: pes(ficha.voo_pes), swim: pes(ficha.natacao_pes),
          climb: pes(ficha.escalada_pes), units: "ft"
        },
        senses: { ranges: { darkvision: Number(ficha.visao_escuro_pes) > 0 ? Number(ficha.visao_escuro_pes) : null }, units: "ft" },
        spellcasting: conjuracao
      },
      details: {
        biography: { value: ficha.biografia_mestre_html || "", public: ficha.biografia_publica_html || "" },
        alignment: ficha.alinhamento || "",
        type: { value: ficha.tipo_criatura || "humanoid", subtype: ficha.subtipo || "" },
        cr: Number(ficha.nivel_desafio) || 0
      },
      traits: {
        size: ficha.tamanho || "med",
        languages: idiomas(ficha.idiomas),
        dr: { value: ficha.resistencias || [] },
        di: { value: ficha.imunidades || [] },
        ci: { value: ficha.imunidades_condicao || [] }
      }
    },
    items: [
      ...(ficha.ataques || []).map(a => itemDeAtaque(a, gerarId)),
      ...(ficha.habilidades || []).map(h => itemDeHabilidade(h, gerarId))
    ],
    prototypeToken: { name: ficha.nome },
    flags: { "silent-nexus": { fonte: ficha.fonte || "" } }
  };
  if (img) {
    dados.img = img;
    dados.prototypeToken.texture = { src: img };
  }
  if (pasta) dados.folder = pasta;
  return dados;
}

/** Um item de loja sem equivalente no SRD -> Item próprio, com preço e quantidade. */
export function itemProprioDeLoja(item) {
  return {
    name: item.nome,
    type: item.tipo || "loot",
    img: ICONES.loja,
    system: {
      description: { value: item.descricao_html || "" },
      price: { value: Number(item.preco_po) || 0, denomination: "gp" },
      quantity: Math.max(1, Number(item.quantidade) || 1),
      identified: true
    }
  };
}

/** Item do compêndio (já como objeto) ajustado pela loja: nome do projeto, preço, quantidade e descrição. */
export function ajustarItemDoCompendio(objeto, item) {
  const copia = structuredClone(objeto);
  delete copia._id;
  delete copia.folder;
  copia.name = item.nome || copia.name;
  copia.system ??= {};
  if (Number(item.preco_po) > 0) copia.system.price = { value: Number(item.preco_po), denomination: "gp" };
  copia.system.quantity = Math.max(1, Number(item.quantidade) || 1);
  if (item.descricao_html) {
    copia.system.description ??= {};
    copia.system.description.value = item.descricao_html + (copia.system.description.value || "");
  }
  return copia;
}
