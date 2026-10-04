# 🜂 Silent Multiverse Nexus

[English](README.md) | **Português (Brasil)**

> **Uma oficina desktop de worldbuilding para Mestres de RPG de mesa: gestão de lore em Markdown, escrita assistida por IA, um conselho de múltiplos agentes e um bot de Discord integrado.**

![Windows](https://img.shields.io/badge/Windows-10%2F11-0078D6?style=for-the-badge&logo=windows)
![Python](https://img.shields.io/badge/Python-3.14-blue?style=for-the-badge&logo=python)
![Gemini API](https://img.shields.io/badge/Google%20Gemini-API-orange?style=for-the-badge&logo=google)
![Discord.py](https://img.shields.io/badge/Discord-Bot-5865F2?style=for-the-badge&logo=discord)
![Obsidian Compatible](https://img.shields.io/badge/Obsidian-Compat%C3%ADvel-7A3EE8?style=for-the-badge&logo=obsidian)
![License](https://img.shields.io/badge/Licen%C3%A7a-MIT-green?style=for-the-badge)

O **Silent Multiverse Nexus** é um conjunto de ferramentas para Mestres, escritores e criadores de cenários. Você escreve o seu mundo em arquivos Markdown comuns (totalmente compatíveis com o **Obsidian**), e o programa ajuda a expandir, organizar, auditar e compartilhar esse mundo, com o Google Gemini fazendo o trabalho pesado e um bot de Discord que responde aos jogadores **sem revelar os seus segredos**.

Disponível em **português do Brasil** e **inglês**: a interface e tudo o que a IA escreve seguem o idioma escolhido.

> Ferramenta independente e não oficial, feita por fãs, sem afiliação com a Wizards of the Coast. Veja o [Aviso legal](#aviso-legal).

---

## ✨ Funcionalidades

### Editor feito para lore
* Funciona em qualquer pasta de arquivos `.md`, inclusive um **cofre do Obsidian** já existente. Os nomes de arquivo ficam limpos, então os **`[[Wikilinks]]` nunca quebram**.
* Árvore de arquivos com busca, arrastar e soltar, templates e renomear/copiar/colar/duplicar.
* **Visualização** instantânea em tema escuro com callouts do Obsidian (`> [!quote]`, `> [!danger]`...), propriedades YAML, tabelas e imagens.
* Clique em um wikilink para abri-lo, ou crie o arquivo que falta com um clique.
* Salvamento automático, histórico de voltar/avançar e uma proteção que **nunca sobrescreve um arquivo que a IA acabou de alterar**.

### Ferramentas de IA (Google Gemini)
* **Expander**: escreva `<-- TODO: o que você quer` em qualquer lugar e a IA preenche a lacuna usando o mundo inteiro como contexto; depois, um revisor confere a consistência antes de salvar.
* **Três níveis de pedidos à IA**: uma tag `<-- TODO:` para uma mudança pequena dentro do arquivo, **Melhorar com IA** para reescrever um arquivo inteiro e o **WorldBuilder** para montar uma campanha inteira.
* **WorldBuilder**: escreva a sua ideia em poucos parágrafos e ele trabalha em três etapas, com a sua revisão entre elas: uma ficha de **Cânone** só do Mestre com os nomes, fatos e segredos oficiais (você edita), uma **lista do plano** (você marca, desmarca e edita os itens) e a **execução por fases** (mundo, lugares, pessoas, monstros, aventuras). Arquivos secretos ficam escondidos dos jogadores, e uma execução interrompida continua de onde parou.
* **Conselho**: quatro agentes especialistas (Arquiteto, Cronista, a Voz dos NPCs, Tática & Caos) discutem um arquivo; você edita as visões deles e um Juiz Supremo escreve a versão final.
* **Auditoria de Lore**: encontra contradições, buracos na linha do tempo e inconsistências geográficas.
* **Melhorar com IA**, **aventuras 5-Room Dungeon** (com ficha do oponente e mapa de batalha da sala final) e **Testes de Conhecimento** (tabelas com faixas de CD), tudo com o botão direito em um arquivo.
* **Converse com Silent**: converse com o guardião do Nexus, que conhece o seu mundo inteiro, para brainstorming e dúvidas.
* **Roleplay (Teatro da Mente)**: crie personas para os seus NPCs a partir do contexto do mundo e converse com eles em personagem, com retratos gerados.
* Todo arquivo que a IA altera é arquivado antes (`_v01`, `_v02`...). Botão direito → **Histórico de Versões** mostra todas as versões e restaura qualquer uma com um clique.
* **Aba Requisições**: antes de qualquer pedido sobre um arquivo inteiro, ajuste os detalhes: estilo em quatro eixos (**Gênero, Tom, Clima, Estilo de escrita**), diretrizes extras, arquivos de referência, reescrever ou só acrescentar, profundidade, texto para jogadores, nível do grupo, criatividade e presets. Ela abre com os padrões do projeto.
* **Fichas de combate** de NPCs e monstros no seu sistema de regras; no 5e o programa confere a matemática do SRD (modificadores, proficiência, XP).
* **Notas do Mestre**: guarde ideias do Silent e depoimentos do Roleplay numa seção secreta de qualquer arquivo. Todas as ferramentas de IA as levam em conta, e o **Conselho** usa os depoimentos como a voz real dos NPCs.

### Bot do Discord
* Os jogadores perguntam sobre a lore com um prefixo (ex.: `!silent O que é a Catedral de Prata?`) e recebem respostas só da lore **pública**.
* **Filtro anti-spoiler determinístico**: arquivos secretos, seções secretas e uma lista de palavras secretas são removidos antes de a IA sequer ver o contexto dos jogadores.
* Cargos e IDs de Mestre recebem respostas com a lore completa.
* Rolador de dados: `!r 1d20+5`, `2d20kh1+3`, `4d6kh3`, `3#1d8+2`, rolagens compostas como `2d12+24+3d8`.
* Lê os canais de regras e avisos do servidor e cita o link de volta (`🔗 Ver no Discord`).
* Configuração por servidor: prefixo, cargos de Mestre, canais permitidos e bloqueados, cooldown.

### E mais
* **Livro do Cenário**: o projeto inteiro em um único HTML com índice e links (imprima como PDF).
* **Relatório de tamanho do projeto**: tokens por pasta e arquivo, nos contextos do Mestre e dos jogadores.
* **Backups** em `.zip`, **verificação de atualizações** ao abrir, perfis de tom e clima e escolha do sistema de regras (5e, Tormenta20, Pathfinder 2e ou genérico).
* Credenciais guardadas no **Gerenciador de Credenciais do Windows**, nunca em arquivos de texto.
* Minimiza para a bandeja do sistema com pouco uso de memória enquanto o bot continua rodando.

---

## 📋 Marcadores que você pode usar nos arquivos

| Marcador | Onde | O que faz |
| :--- | :--- | :--- |
| `<-- TODO: motivo` | Em qualquer `.md` | O **Expander** preenche essa lacuna com a IA. |
| `[segredo]` ou `[secret]` | Em um título | Esconde a seção inteira dos jogadores. |
| `status: segredo` ou `status: secret` | No cabeçalho YAML | Esconde o arquivo inteiro dos jogadores. |
| `<!-- segredo -->` ou `🤫` | Em um parágrafo | Esconde esse parágrafo dos jogadores. |
| `status: rascunho` ou `status: draft` | No cabeçalho YAML | A IA ignora o arquivo até você terminá-lo. |
| Palavras secretas | Página Opções (ex.: `Hastur`) | Remove qualquer menção a esses nomes da visão dos jogadores. |
| `[[Nota]]`, `![[imagem.png]]` | Em qualquer lugar | Links e imagens, exibidos na visualização e no livro. |

Os marcadores funcionam nos dois idiomas, então projetos existentes continuam funcionando ao trocar o idioma.

---

## 🚀 Como começar

1. Baixe o `SilentMultiverse-<versão>-windows.zip` mais recente em [**Releases**](../../releases).
2. Descompacte em qualquer pasta (ou na raiz do seu cofre do Obsidian) e execute o `SilentMultiverse.exe`.
   * Se o Windows mostrar "O Windows protegeu o computador", clique em **Mais informações → Executar assim mesmo**. Isso acontece com programas novos que ainda não têm assinatura digital.
3. Consiga uma chave gratuita do Gemini no [Google AI Studio](https://aistudio.google.com) ("Get API key").
4. No programa, vá em **Opções → Credenciais Seguras**, cole a chave e salve.
5. Escolha o idioma em **Opções → Idioma** e abra a pasta do seu projeto pelo botão 📁 no topo da barra lateral.

A página **📖 Manual & Guia** dentro do programa explica todas as funções, inclusive como configurar o bot do Discord.

**Atualizando:** quando sair uma versão nova, aparece um aviso na barra de status. Baixe a nova versão e substitua o `SilentMultiverse.exe` na mesma pasta. Seus projetos, configurações e a pasta `.silent_data` continuam como estão.

---

## 🔒 Privacidade e custos

* Seus arquivos ficam no seu computador. Para responder, a IA recebe o texto do seu projeto e o seu pedido, enviados à **API do Gemini do Google** com a **sua própria chave**. O programa não tem servidor e não coleta nada.
* No **nível gratuito** do Gemini, o Google pode usar o conteúdo enviado para melhorar seus produtos. Se o seu cenário for confidencial, use uma chave paga e confira os termos atuais do Google.
* Qualquer custo de uso é entre você e o Google.
* As imagens usam o modelo de imagem do Gemini ou, como alternativa, o serviço gratuito [Pollinations](https://pollinations.ai) (só a descrição da imagem é enviada).

---

## 🌐 Idiomas (PT-BR / EN-US)

Em **Opções → Idioma**:

* **A IA e o conteúdo gerado** mudam na hora: prompts, descrições de campos enviadas ao Gemini, Markdown gerado (aventuras, testes de conhecimento, fichas de persona, livro do cenário) e respostas do bot do Discord.
* **A interface** muda ao reiniciar.
* Seus arquivos de lore nunca são traduzidos. Os templates e guias de estilo iniciais mudam para o novo idioma só se você não os editou; arquivos seus ou editados são sempre mantidos.

Todos os textos ficam em `locale/`:

```
locale/
  pt_br/  e  en_us/
    ui.json          textos da interface
    mensagens.json   mensagens de log e avisos
    conteudo.json    títulos e rótulos do conteúdo gerado
    schemas.json     descrições dos campos dos schemas da IA
    manual.md        o manual exibido no programa
    prompts/*.md     um arquivo por chamada de IA (variáveis no formato {{nome}})
    modelos/         Templates/ e Style/ iniciais, copiados para a .silent_data no primeiro uso
```

Para alterar um texto ou prompt, edite nos **dois** idiomas (os testes conferem se as chaves e variáveis batem).

---

## 🛠️ Executando pelo código-fonte

Requer Windows e Python 3.14 (a versão com que o projeto é testado).

```bash
git clone https://github.com/SilentDM/Silent_Multiverse.git
cd Silent_Multiverse
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Dica: dê dois cliques no `ativar_venv.bat` para abrir um terminal com o venv já ativado.

**Testes** (sem rede e sem chaves reais; usam uma pasta temporária):

```bash
python -m unittest discover -s tests -t .
```

### Organização do código
* `ui/`: só monta as telas. Cada botão chama uma função de `core/`, `engine/` ou `bot/`. Nada de acesso a arquivos, chamadas de IA, threads ou regras de negócio na interface (um teste garante isso).
* `core/`: configurações, cofre de credenciais, idioma, prompts, eventos de log, tarefas em segundo plano, atualizações.
* `engine/`: operações de arquivo, sessão do editor, ações (Expander, WorldBuilder, auditoria, livro, backup), schemas e contexto do mundo.
* `bot/`: bot do Discord.

---

## 📦 Gerando o executável e publicando

```bash
pip install -r requirements-build.txt
python build.py
```

Isso cria `dist/SilentMultiverse.exe` e `dist/SilentMultiverse-<versão>-windows.zip`. O executável embute `locale/` (que inclui os templates e guias de estilo iniciais de cada idioma, em `locale/<idioma>/modelos/`) e o ícone.

**Publicando uma versão:**
1. Atualize `VERSAO` em `core/versao.py` (ex.: `2.1.0`) e faça o commit.
2. Crie e envie a tag correspondente: `git tag v2.1.0` e depois `git push origin v2.1.0`.
3. O GitHub Actions (`.github/workflows/release.yml`) roda os testes, gera o `.zip` no Windows e cria uma release em **rascunho**.
4. Revise o rascunho no GitHub e clique em **Publish release**. A verificação de atualizações do programa passa a mostrar a nova versão aos usuários.

---

## Aviso legal

O Silent Multiverse Nexus é uma ferramenta independente e não oficial, feita por fãs. **Não é afiliada, endossada, patrocinada nem aprovada pela Wizards of the Coast LLC**.

*Dungeons & Dragons* e *D&D* são marcas da Wizards of the Coast LLC. *Tormenta20* é marca da Jambô Editora. *Pathfinder* é marca da Paizo Inc. Esses nomes são usados apenas para indicar compatibilidade de regras. O programa não contém textos de regras nem conteúdo desses jogos.

As referências às regras da quinta edição (5e) seguem o System Reference Document 5.1:

> This work includes material taken from the System Reference Document 5.1 ("SRD 5.1") by Wizards of the Coast LLC and available at https://dnd.wizards.com/resources/systems-reference-document. The SRD 5.1 is licensed under the Creative Commons Attribution 4.0 International License available at https://creativecommons.org/licenses/by/4.0/legalcode.

(Tradução: esta obra inclui material do System Reference Document 5.1 da Wizards of the Coast LLC, licenciado sob a Creative Commons Atribuição 4.0 Internacional.)

O conteúdo gerado pela IA é responsabilidade do usuário. Silent é um personagem original deste programa.

## 📄 Licença

O código-fonte é distribuído sob a [Licença MIT](LICENSE).
