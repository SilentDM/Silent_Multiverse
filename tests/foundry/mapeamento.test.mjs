// Testes da conversão ficha/loja do Silent -> dados do dnd5e 5.3.x. Rodar: node --test tests/foundry
import { test } from "node:test";
import assert from "node:assert/strict";
import { fichaParaAtor, itemDeAtaque, itemDeHabilidade, idiomas, itemProprioDeLoja, ajustarItemDoCompendio }
  from "../../foundry/silent-nexus/scripts/mapeamento.js";

let contador = 0;
const gerarId = () => `id${String(++contador).padStart(14, "0")}`;

const FICHA = {
  nome: "Borin Pé-de-Ferro", tamanho: "med", tipo_criatura: "humanoid", subtipo: "anão", alinhamento: "Neutro e Bom",
  classe_armadura: 13, pontos_de_vida: 22, formula_pv: "4d8 + 4", deslocamento_pes: 25, voo_pes: 0, natacao_pes: 0,
  escalada_pes: 0, forca: 14, destreza: 10, constituicao: 13, inteligencia: 10, sabedoria: 12, carisma: 15,
  testes_resistencia: ["con"], pericias: ["prc", "itm"], nivel_desafio: 0.5, visao_escuro_pes: 60,
  idiomas: ["Comum", "Anão", "Língua dos Túneis"], resistencias: ["poison"], imunidades: [], imunidades_condicao: [],
  ataques: [
    { nome: "Martelo de Guerra", alcance: "melee", classificacao: "weapon", alcance_pes: 5, alcance_longo_pes: 0,
      dados_quantidade: 1, dados_faces: 8, tipo_dano: "bludgeoning", descricao: "", descricao_html: "" },
    { nome: "Besta Leve", alcance: "ranged", classificacao: "weapon", alcance_pes: 80, alcance_longo_pes: 320,
      dados_quantidade: 1, dados_faces: 8, tipo_dano: "piercing", descricao: "", descricao_html: "" }
  ],
  habilidades: [
    { nome: "Resiliência Anã", ativacao: "passive", descricao: "Vantagem contra veneno.", descricao_html: "<p>Vantagem contra veneno.</p>" },
    { nome: "Grito de Taverna", ativacao: "bonus", descricao: "Aliados ganham 1d4.", descricao_html: "<p>Aliados ganham 1d4.</p>" }
  ],
  biografia_publica_html: "<p>Taverneiro caolho.</p>", biografia_mestre_html: "<p>Deve um favor ao grupo.</p>",
  fonte: "NPCs/Borin Pé-de-Ferro.md"
};

test("ficha completa vira um NPC do dnd5e", () => {
  const ator = fichaParaAtor(FICHA, { img: "silent-nexus/phaeton/borin.webp", pasta: "pasta1", gerarId });
  assert.equal(ator.type, "npc");
  assert.equal(ator.folder, "pasta1");
  assert.equal(ator.img, "silent-nexus/phaeton/borin.webp");
  assert.equal(ator.prototypeToken.texture.src, "silent-nexus/phaeton/borin.webp");
  const s = ator.system;
  assert.deepEqual([s.abilities.str.value, s.abilities.cha.value], [14, 15]);
  assert.equal(s.abilities.con.proficient, 1);
  assert.equal(s.abilities.str.proficient, 0);
  assert.deepEqual(s.skills, { prc: { value: 1 }, itm: { value: 1 } });
  assert.deepEqual(s.attributes.ac, { calc: "flat", flat: 13 });
  assert.deepEqual(s.attributes.hp, { value: 22, max: 22, formula: "4d8 + 4" });
  assert.equal(s.attributes.movement.walk, "25");              // o dnd5e guarda o deslocamento como texto
  assert.equal(s.attributes.movement.fly, null);
  assert.equal(s.attributes.senses.ranges.darkvision, 60);
  assert.equal(s.attributes.spellcasting, "cha");              // maior entre Int, Sab e Car
  assert.equal(s.details.cr, 0.5);
  assert.deepEqual(s.details.type, { value: "humanoid", subtype: "anão" });
  assert.equal(s.details.biography.public, "<p>Taverneiro caolho.</p>");   // jogadores
  assert.equal(s.details.biography.value, "<p>Deve um favor ao grupo.</p>"); // só o Mestre
  assert.deepEqual(s.traits.languages, { value: ["common", "dwarvish"], custom: "Língua dos Túneis" });
  assert.deepEqual(s.traits.dr, { value: ["poison"] });
  assert.equal(ator.items.length, 4);
  assert.equal(ator.flags["silent-nexus"].fonte, "NPCs/Borin Pé-de-Ferro.md");
});

test("ataques seguem o formato de arma com atividade de ataque (como o Bandido do dnd5e 5.3.3)", () => {
  const corpo = itemDeAtaque(FICHA.ataques[0], gerarId);
  assert.equal(corpo.type, "weapon");
  assert.equal(corpo.system.type.value, "natural");
  assert.deepEqual(corpo.system.damage.base, { number: 1, denomination: 8, types: ["bludgeoning"] });
  const [id, atividade] = Object.entries(corpo.system.activities)[0];
  assert.equal(atividade._id, id);
  assert.equal(atividade.type, "attack");
  assert.deepEqual(atividade.activation, { type: "action", value: 1 });
  assert.deepEqual(atividade.attack.type, { value: "melee", classification: "weapon" });
  assert.equal(atividade.damage.includeBase, true);

  const distancia = itemDeAtaque(FICHA.ataques[1], gerarId);
  assert.deepEqual(distancia.system.range, { value: 80, long: 320, units: "ft" });
  assert.equal(Object.values(distancia.system.activities)[0].attack.type.value, "ranged");

  const alcance = itemDeAtaque({ ...FICHA.ataques[0], alcance_pes: 10 }, gerarId);
  assert.deepEqual(alcance.system.properties, ["rch"]);
  const magia = itemDeAtaque({ ...FICHA.ataques[1], classificacao: "spell" }, gerarId);
  assert.equal(Object.values(magia.system.activities)[0].attack.type.classification, "spell");
});

test("traços passivos não têm atividade; ações especiais têm", () => {
  const passivo = itemDeHabilidade(FICHA.habilidades[0], gerarId);
  assert.equal(passivo.type, "feat");
  assert.equal(passivo.system.type.value, "monster");
  assert.deepEqual(passivo.system.activities, {});
  const bonus = itemDeHabilidade(FICHA.habilidades[1], gerarId);
  assert.equal(Object.values(bonus.system.activities)[0].activation.type, "bonus");
  assert.equal(Object.values(bonus.system.activities)[0].type, "utility");
});

test("idiomas em português e inglês viram códigos; o resto vai para custom", () => {
  assert.deepEqual(idiomas(["Élfico", "Thieves' Cant", "Dracônico", "Comum", "comum"]),
    { value: ["elvish", "cant", "draconic", "common"], custom: "" });
});

test("itens da loja: próprio do mundo e do compêndio ajustado", () => {
  const proprio = itemProprioDeLoja({ nome: "Tônico de Cinzas", tipo: "consumable", preco_po: 7.5, quantidade: 3, descricao_html: "<p>x</p>" });
  assert.deepEqual(proprio.system.price, { value: 7.5, denomination: "gp" });
  assert.equal(proprio.system.quantity, 3);
  assert.equal(proprio.type, "consumable");
  const doCompendio = { _id: "abc", folder: "f", name: "Longsword", type: "weapon", system: { price: { value: 15, denomination: "gp" }, description: { value: "<p>SRD</p>" } } };
  const ajustado = ajustarItemDoCompendio(doCompendio, { nome: "Espada Longa", preco_po: 18, quantidade: 2, descricao_html: "<p>Forjada em Brasaforte.</p>" });
  assert.equal(ajustado._id, undefined);
  assert.equal(ajustado.name, "Espada Longa");
  assert.deepEqual(ajustado.system.price, { value: 18, denomination: "gp" });
  assert.equal(ajustado.system.quantity, 2);
  assert.equal(ajustado.system.description.value, "<p>Forjada em Brasaforte.</p><p>SRD</p>");
  assert.equal(doCompendio.name, "Longsword");                   // o original do compêndio não muda
});
