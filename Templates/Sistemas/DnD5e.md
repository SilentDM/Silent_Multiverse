# REGRAMENTO DE FICHA: D&D 5E

Você deve gerar a ficha no formato de Bloco de Estatísticas (Stat Block) oficial do D&D 5e usando o HTML fornecido abaixo.

### REGRAS MATEMÁTICAS DE D&D 5E:
- Modificador de Atributo = (Valor - 10) / 2 arredondado para baixo.
- Bônus de Proficiência por ND: ND 0-4 (+2), ND 5-8 (+3), ND 9-12 (+4), ND 13-16 (+5), ND 17-20 (+6).
- CD de Resistência de Magia = 8 + Bônus de Proficiência + Modificador do Atributo de Conjuração.
- Percepção Passiva = 10 + Modificador de Sabedoria (ou Perícia Percepção).

### ESTRUTURA OBRIGATÓRIA DA FICHA (Use exatamente este HTML):

<div class="stat-block">
  <h2>[Nome da Criatura/NPC]</h2>
  <p><em>[Tamanho] [Tipo], [Tendência]</em></p>
  <hr>
  <p><strong>Classe de Armadura:</strong> [Valor] ([Tipo de Armadura])</p>
  <p><strong>Pontos de Vida:</strong> [Valor] ([Dados de Vida])</p>
  <p><strong>Deslocamento:</strong> [Ex: 9m, voo 18m]</p>
  <hr>
  <div class="atributos">
    <p><strong>FOR:</strong> [Val] ([Mod]) | <strong>DES:</strong> [Val] ([Mod]) | <strong>CON:</strong> [Val] ([Mod])</p>
    <p><strong>INT:</strong> [Val] ([Mod]) | <strong>SAB:</strong> [Val] ([Mod]) | <strong>CAR:</strong> [Val] ([Mod])</p>
  </div>
  <hr>
  <p><strong>Testes de Resistência:</strong> [Ex: Con +5, Wis +4]</p>
  <p><strong>Perícias:</strong> [Ex: Percepção +4, Furtividade +6]</p>
  <p><strong>Sentidos:</strong> Visão no Escuro 18m, Percepção Passiva [Val]</p>
  <p><strong>Idiomas:</strong> [Idiomas]</p>
  <p><strong>Nível de Desafio:</strong> [Val] ([XP]) | <strong>Proficiência:</strong> +[Val]</p>
  <hr>
  <h3>Habilidades Passivas</h3>
  <p><strong>[Nome da Habilidade].</strong> [Descrição detalhada].</p>
  
  <h3>Ações</h3>
  <p><strong>[Nome do Ataque].</strong> <em>Ataque Corpo a Corpo com Arma:</em> +[Bônus] para acertar, alcance 1,5m, um alvo. <em>Acerto:</em> [Dano] ([Dados]) de dano [Tipo].</p>
</div>