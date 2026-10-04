# SILENT MULTIVERSE NEXUS
- Uma oficina de worldbuilding para Mestres de RPG de mesa, feita sobre arquivos Markdown (.md) comuns. Funciona muito bem com um cofre do Obsidian.
- Edite, organize e ligue todos os arquivos do seu cenário com rapidez e segurança.
- Use a IA (Google Gemini) para preencher lacunas, melhorar arquivos, planejar expansões, auditar a lore, gerar aventuras e testes de conhecimento e conversar com seus NPCs.
- Converse com Silent, o guardião do Nexus, para fazer brainstorming, tirar dúvidas e revisar ideias sobre o seu mundo.
- Rode um bot no Discord para os jogadores perguntarem sobre a lore pública (os segredos ficam escondidos) e rolarem dados.
- Compile o projeto inteiro em um livro de cenário HTML com índice e links clicáveis.
> Use a lista Conteúdo à esquerda para ir direto a qualquer seção.

# 1. PRIMEIROS PASSOS
## 1) Consiga uma chave de API do Gemini
- Abra o Google AI Studio (https://aistudio.google.com), entre com uma conta Google e clique em "Get API key".
- Existe um nível gratuito. Os limites mudam com o tempo e aparecem no próprio AI Studio.
## 2) Salve a chave
- Vá em Opções → Credenciais Seguras, cole a chave em "Chave da API Gemini" e clique em "Salvar Credenciais no Cofre".
- As chaves ficam no Gerenciador de Credenciais do Windows, nunca em arquivos de texto.
## 3) Escolha o idioma
- Opções → Idioma. A IA muda na hora; a interface muda ao reiniciar.
## 4) Abra o seu projeto
- No topo da barra lateral, clique no ícone 📁 e escolha a pasta com seus arquivos .md (uma pasta vazia começa um projeto novo). Um cofre do Obsidian funciona do jeito que está.
- Os projetos recentes ficam na lista para trocar rápido.
## 5) Teste os modelos
- Vá em Performance Gemini e clique em "Benchmark de Modelos". O programa testa os modelos disponíveis e os ordena por velocidade e confiabilidade.
> Pronto! Abra um arquivo no Editor, escreva uma tag <-- TODO: e rode o Expander para ver a IA trabalhando.

# 2. PASTAS DO PROJETO E DE DADOS
- Pasta do projeto: suas pastas e arquivos Markdown. Tenha quantos projetos quiser.
- .silent_data (ao lado do programa): tudo o que o programa guarda para você:
- Templates/: modelos para arquivos novos (ex.: npc.md, cidade.md). Edite-os ou crie os seus; eles aparecem na janela Novo Arquivo.
- Style/: as verdades e regras do seu cenário (ex.: Estilo_Narrativa.md). Todo .md desta pasta é lido pela IA em todas as criações.
- Estilos/: estilos criados por você, em subpastas Genero, Tom, Clima e Escrita (um .md por opção). Eles aparecem nos seletores junto com os do programa.
- memories/: histórico recente do chat local e das conversas do Discord (resumido automaticamente quando cresce).
- exports/: livros de cenário HTML e relatórios.
- logs/: configurações (settings.json), o cache de contexto da IA e as versões anteriores dos arquivos alterados pela IA (histórico, com nomes _v01, _v02...).
- Discord_Knowledge/: canais de regras e avisos lidos dos seus servidores do Discord.
> Mantenha a .silent_data ao lado do programa. Ao atualizar ou mover o programa, leve essa pasta junto.

# 3. IDIOMA
- Opções → Idioma: Português (Brasil) ou English (US).
- A IA passa a usar o novo idioma na hora: Expander, WorldBuilder, Conselho, Roleplay, chat, auditoria, aventuras, testes de conhecimento e o bot do Discord.
- A interface muda ao reiniciar o programa.
- Seus arquivos de lore nunca são traduzidos. O conteúdo novo gerado pela IA segue o idioma escolhido.
- Os templates e guias de estilo iniciais que você não editou mudam para o novo idioma; os seus e os editados são mantidos.
- Os marcadores funcionam nos dois idiomas: status: segredo ou status: secret, [segredo] ou [secret], status: rascunho ou status: draft.

# 4. EDITOR
## Árvore de arquivos
- Busca: digite na caixa acima da árvore para filtrar os arquivos pelo nome.
- Arraste e solte arquivos e pastas para movê-los.
- Clique com o botão direito em um arquivo ou pasta: Novo Arquivo, Nova Pasta, Renomear (F2), Copiar, Recortar, Colar, Duplicar, Excluir e Mostrar no Windows Explorer.
- Novo Arquivo permite escolher um dos Templates.
## Escrevendo
- As alterações são salvas automaticamente logo depois que você para de digitar, e com Ctrl+S.
- Visualizar mostra a página formatada (imagens, links, tabelas); Editar volta ao texto; Navegador abre a visualização no seu navegador.
- Voltar / Avançar (ou Alt+Esquerda / Alt+Direita, ou os botões laterais do mouse) navega entre os documentos abertos.
- A barra de status mostra palavras, caracteres, linhas e uma estimativa de tokens do arquivo aberto.
## Ações de IA (botão direito no arquivo)
- ✨ Melhorar com IA: reescreve o arquivo com mais detalhe e coesão, seguindo uma instrução opcional.
- 🎲 Gerar Aventura 5e: cria uma masmorra de 5 salas a partir do arquivo (gancho, salas, testes, ficha do oponente, tesouro) e uma imagem de mapa de batalha da sala final.
- 📜 Gerar Testes de Conhecimento: cria testes com faixas de dificuldade baseados no arquivo.
- ⚔️ Gerar Ficha de Combate: cria (ou refaz) a ficha do NPC ou da criatura no sistema de regras do projeto. No 5e, o programa confere a matemática do SRD (modificadores, proficiência e XP).
- 🏛️ Consolidar com o Conselho: envia o arquivo para a página do Conselho.
- 💬 Perguntar a Silent sobre este arquivo: anexa o documento inteiro ao chat.
- 🕘 Histórico de Versões: mostra todas as versões anteriores do arquivo e restaura uma com um clique (a atual é guardada antes).
> Melhorar, Aventura, Testes, Ficha e Conselho abrem antes a aba Requisições (dá para desligar nas Opções). Veja a seção 6.
## Segurança
- Enquanto a IA trabalha em um arquivo, ele fica travado: não dá para editá-lo até a IA terminar.
- Se a IA (ou outro programa) alterar um arquivo que você está com aberto, o Editor o recarrega e nunca sobrescreve a versão nova com o texto antigo.
- Antes de a IA alterar um arquivo, a versão anterior é arquivada em .silent_data/logs (histórico).

# 5. REGRAS DE ESCRITA E MARCADORES
## Wikilinks [[Nome do Arquivo]]
- Ligue outras entidades com colchetes duplos: [[Reino de Lucius]]. Clique no link para abri-lo; se o arquivo não existir, o programa oferece criá-lo.
- Também funcionam: [[Nome#Seção]] e [[Nome|texto exibido]].
## Tags de expansão <-- TODO: motivo
- Clique com o botão direito no editor para inserir a tag, ou digite-a. Depois dos dois-pontos, escreva o que a IA deve fazer.
- O Expander encontra a tag e preenche aquele trecho, seguindo sua instrução e o contexto do mundo.
## Segredos do Mestre vs jogadores
- Arquivo inteiro: status: segredo (ou status: secret) no cabeçalho, ou tags: [segredo].
- Uma seção: adicione [segredo] (ou [secret]) ao título dela, ex.: ### O Culto Oculto [segredo].
- Um parágrafo: o parágrafo que contém <!-- segredo --> (ou <!-- secret -->) ou 🤫 fica oculto.
- Palavras secretas (Opções): qualquer arquivo, pasta, título ou parágrafo que contenha esses nomes é removido da visão dos jogadores.
- O Mestre (chat local e cargos/IDs de Mestre no Discord) vê tudo; os jogadores veem só a lore pública.
## Rascunhos
- status: rascunho (ou status: draft) deixa o arquivo fora do contexto da IA até você terminá-lo. Arquivos vazios e com tags <-- TODO pendentes também ficam de fora.
## Imagens
- ![[imagem.png]] mostra retratos e mapas de batalha na visualização e no livro de cenário.
## Notas do Mestre
- A seção "🤫 Notas do Mestre" no fim de um arquivo guarda notas de Silent, depoimentos do Roleplay e anotações suas.
- Ela é secreta (os jogadores nunca a veem) e toda ferramenta de IA a lê para orientar as próximas criações sobre o arquivo, sem reescrevê-la.
- Você também pode escrever nela à mão: cada nota começa com ### e um título.

# 6. WORLDBUILDER
## Três níveis de pedidos à IA
- Baixo: uma tag <-- TODO: dentro do arquivo (Expander) para uma mudança pequena e direta.
- Médio: botão direito → Melhorar com IA (ou Aventura, Testes, Ficha, Conselho) para trabalhar um arquivo inteiro, passando pela aba Requisições.
- Alto: o WorldBuilder transforma uma ideia em uma campanha completa.
## Como o WorldBuilder funciona
- 1 · Cânone: escreva a ideia (ou deixe em branco) e clique em Gerar Cânone. A IA escreve Canon/<título>.md com os nomes, fatos e segredos oficiais (só o Mestre vê). Edite à vontade.
- 2 · Plano: clique em Gerar Plano. Revise a lista: clique em ✔ para marcar/desmarcar, selecione um item para editar caminho, objetivo, modelo ou a marca 🤫 de segredo e clique em Salvar Item.
- 3 · Execução: Executar Marcadas roda o plano por fases (mundo, lugares, pessoas, monstros, aventuras). Arquivos secretos ficam escondidos dos jogadores.
- Se você parar, Executar Marcadas continua de onde parou. O resultado lista os [[links]] novos que ainda não têm arquivo.
- As permissões e o máximo de ações ficam na própria página.
- Além de criar arquivos, o WorldBuilder pode Criar NPC e Criar Monstro (texto + ficha de combate), gerar Aventuras e Testes de Conhecimento.
- Cada item do plano tem um gênero: o laboratório secreto pode ser Horror Cósmico enquanto a capital é Intriga Política. O gênero escolhe o template (ex.: Templates/misterio/local.md) e o estilo do texto.
- No chat do Silent, 🌍 Levar ao WorldBuilder transforma a conversa na ideia do WorldBuilder.
## A aba Requisições
- Abre com os padrões do projeto e mostra o arquivo inteiro. Tudo o que você trocar vale só para este pedido.
- Estilo em quatro eixos: Gênero, Tom, Clima e Estilo de escrita (ex.: numa aventura de Mistério, a caverna lovecraftiana pode usar Horror Cósmico).
- Diretrizes extras, arquivos de referência (os ligados por [[links]] aparecem sugeridos), modo (reescrever tudo ou só acrescentar), profundidade, público (Mestre ou texto para jogadores), nível do grupo, número de jogadores, criatividade e a marca 🤫 de segredo.
- Presets guardam combinações que você usa sempre; o tamanho estimado mostra quantos tokens o pedido vai usar.

# 7. AÇÕES
- Parar Qualquer Execução Atual: interrompe todas as tarefas de IA em andamento.
- Expander: procura tags <-- TODO: em todos os arquivos e as preenche com a IA. Um revisor confere o resultado contra a sua lore antes de salvar.
- Reconstruir Contexto do Mundo: atualiza o que a IA sabe sobre o projeto (também é reconstruído automaticamente a cada 12 horas).
- Auditar Lore do Mundo: procura contradições, buracos na linha do tempo e inconsistências geográficas e mostra um relatório que você pode salvar.
- Livro do Cenário: compila todos os arquivos em um HTML com índice e links e o abre no navegador (imprima como PDF se quiser).
- Analisar Tamanho do Projeto: mostra, por pasta e arquivo, quantos tokens o projeto ocupa no contexto da IA (Mestre e jogadores) e quanto isso representa do limite do provedor.
- Backup: cria um .zip com o projeto e a pasta de dados na raiz do disco do programa (ou na pasta do programa, se não houver permissão).
- Excluir Todas as Memórias: apaga o histórico do chat local e das conversas do Discord.
- Abrir Pasta de Dados: abre a .silent_data.

# 8. CONVERSE COM SILENT
- Silent é a entidade que guarda o Nexus: conhece o seu mundo inteiro (inclusive os segredos) e ajuda a fazer brainstorming, tirar dúvidas e revisar ideias.
- A conversa é lembrada por projeto e resumida automaticamente quando fica longa.
- Para discutir um arquivo específico, clique nele com o botão direito no Editor e escolha "Perguntar a Silent sobre este arquivo".
- 📝 Nota (ou botão direito numa mensagem): guarda a resposta nas Notas do Mestre do arquivo escolhido. "Salvar e aplicar agora" já abre a aba Requisições para incorporar a nota ao texto.
- 🌍 Levar ao WorldBuilder: a conversa vira a ideia do WorldBuilder.

# 9. ROLEPLAY (TEATRO DA MENTE)
- Clique em ➕ Nova Persona, digite o nome do personagem e descreva o papel, a motivação ou o mistério dele. A IA monta a persona completa a partir do contexto do seu mundo.
- Converse em personagem no lado direito. Cada persona lembra a própria conversa.
- 📝 Depoimento (ou botão direito numa fala): guarda a fala nas Notas do Mestre, de preferência no arquivo do próprio personagem. É a versão dele: pode mentir ou estar enganado.
- 🎨 Gerar Retrato do NPC cria uma imagem do personagem. Clique com o botão direito na imagem para abri-la, salvá-la ou mostrá-la na pasta de dados.
> As imagens (retratos e mapas de batalha das aventuras) usam o modelo de imagem do Gemini. Se ele não estiver disponível para a sua chave ou a cota acabar, o programa usa o serviço gratuito Pollinations (só a descrição da imagem é enviada).

# 10. CONSELHO (CRIAÇÃO E CONSOLIDAÇÃO)
- Escolha um arquivo (ou use Consolidar com o Conselho no Editor) e escreva uma diretriz.
- Passo 1: quatro especialistas dão sua visão: o Arquiteto (expansão), o Cronista (fatos e continuidade), a Voz dos NPCs (em primeira pessoa) e Tática & Caos (mecânicas e dilemas). Você pode editar os textos deles.
- Passo 2: o Juiz Supremo une os painéis na versão final do arquivo. A versão anterior é arquivada.
- O Conselho usa o que as outras perspectivas já disseram sobre o arquivo: os depoimentos do Roleplay viram a voz real dos NPCs, as notas de Silent e as suas orientam o Arquiteto e o Cronista, e conversas recentes de Roleplay com personagens citados também entram. A linha "O Conselho usou" mostra as fontes.

# 11. OPÇÕES
- Idioma: veja a seção 3.
- Credenciais Seguras: chave do Gemini, token do bot do Discord e IDs de Mestre no Discord. O Gemini é o provedor suportado; os campos de Claude e OpenAI existem, mas não recebem manutenção.
- Bot do Discord: regras por servidor (veja a seção 13).
- Filtro de Segredos: palavras e nomes escondidos dos jogadores.
- Estilo do Projeto: o padrão de Gênero, Tom, Clima e Estilo de escrita para todas as criações, e a opção de abrir a aba Requisições antes de cada pedido.
- Cache do Gemini: em contas sem faturamento o programa para de tentar o cache e usa o envio do bundle; "Tentar cache de novo" volta a tentar (trocar a chave também).
- Sistema de Regras: o sistema que a IA segue nas mecânicas (5e, Tormenta20, Pathfinder 2e ou genérico).
- Automação do Expander: roda o Expander quando você salva (Ctrl+S) ou sai de um arquivo editado que tenha uma tag <-- TODO.
- Sobre e Atualizações: versão, verificação de atualizações e o aviso legal.

# 12. PERFORMANCE GEMINI
- O Benchmark de Modelos testa todos os modelos Gemini disponíveis e os ordena por tempo de resposta e taxa de sucesso.
- O modo Automático usa essa ordem; o modo Manual deixa você definir a sua.
- Se um modelo falhar ou atingir o limite, o programa tenta o próximo automaticamente.

# 13. BOT DO DISCORD
## Criando o bot (uma vez)
- Abra o Discord Developer Portal (https://discord.com/developers/applications) → New Application.
- Em Bot: clique em Reset Token e copie o token. Ative "Message Content Intent".
- Em OAuth2 → URL Generator: marque "bot"; permissões: View Channels, Send Messages, Embed Links, Read Message History. Abra o link gerado para convidar o bot ao seu servidor.
- No programa: Opções → Credenciais Seguras → cole o token em "Token do Bot do Discord" e salve. Reinicie o programa para conectar.
- IDs de Mestre no Discord: no Discord, ative o Modo Desenvolvedor (Configurações → Avançado), clique com o botão direito no seu nome → Copiar ID do usuário. Quem estiver nessa lista sempre recebe respostas de Mestre.
## Configurando por servidor
- Escolha o servidor (ou o Padrão Geral) no topo da caixa do Discord. Os servidores aparecem depois que o bot conecta.
- Gatilho (Prefixo): como os jogadores chamam o bot, ex.: !silent.
- Cargos de Mestre: quem tiver esses cargos recebe respostas com o projeto inteiro, segredos incluídos.
- Canais Permitidos / Bloqueados: onde o bot pode ou não responder (vazio = todos).
- Canais de Conhecimento: canais de regras e avisos que o bot lê e memoriza. Sincronize com "Sincronizar Canais com o Discord Agora" ou com o comando de sincronização.
- Cooldown: tempo de espera por usuário, para evitar spam.
## Comandos
```
!silent O que é a Catedral de Prata?   (perguntar sobre a lore)
!silent ajuda                          (guia de comandos)
!silent sincronizar                    (Mestres: reler os canais de conhecimento)
!r 1d20+5   !rolar 2d6+3   !r 2d20kh1+3 (dados)
```
- Em mensagens diretas, o bot só responde "ajuda".
- Os jogadores veem só a lore pública; segredos, rascunhos e palavras secretas são sempre removidos.

# 14. LOG DE ATIVIDADES
- Mostra tudo o que acontece em segundo plano: chamadas de IA, arquivos salvos, backups, eventos do Discord e erros.
- Quando algo não funcionar, olhe aqui primeiro.

# 15. ATUALIZAÇÕES
- Ao abrir, o programa procura uma versão nova no GitHub (dá para desligar em Opções → Sobre e Atualizações, ou procurar manualmente ali).
- Quando houver uma, aparece um aviso na barra de status. Clique nele para abrir a página de download.
- Para atualizar: baixe a versão nova e substitua o SilentMultiverse.exe antigo na mesma pasta. Seus projetos, a .silent_data e as credenciais continuam como estão.

# 16. PRIVACIDADE E CUSTOS
- Seus arquivos ficam no seu computador. Para responder, a IA recebe o texto do seu projeto (o contexto do mundo) e o seu pedido, enviados à API do Gemini do Google.
- No nível gratuito do Gemini, o Google pode usar o conteúdo para melhorar seus produtos. Se o seu cenário for confidencial, use uma chave paga (confira os termos atuais do Google).
- Os custos de uso, se houver, são entre você e o Google, pela sua própria chave. O programa não tem servidor e não coleta nada.
- Discord: o bot só lê mensagens nos canais que você permitir e nos canais de conhecimento que você listar.
- As credenciais ficam no Gerenciador de Credenciais do Windows.

# 17. SOLUÇÃO DE PROBLEMAS
- "O Windows protegeu o computador" na primeira execução: clique em "Mais informações" → "Executar assim mesmo". Isso acontece com programas novos que ainda não têm assinatura digital.
- A IA não responde: confira a chave nas Opções, rode o Benchmark de Modelos e veja o Log de Atividades. Um erro "429" ou "quota" significa que o limite da chave foi atingido; espere ou use outro modelo.
- O bot fica offline: confira o token, o Message Content Intent e o Log de Atividades; reinicie o programa depois de salvar o token.
- Um arquivo está travado: a IA está trabalhando nele. Espere a tarefa terminar ou use Parar Qualquer Execução Atual na página Ações.
- A visualização não aparece: falta o componente de visualização (tkinterweb); a versão publicada já o inclui.

# 18. ATALHOS
- [Ctrl + S]: salvar (e rodar o Auto Expander, se ativado).
- [F2]: renomear o item selecionado na árvore de arquivos.
- [Ctrl + Roda do Mouse] ou [Ctrl + / Ctrl -]: zoom.
- [Alt + Esquerda / Direita] ou botões laterais do mouse: voltar / avançar entre documentos.
- [Ctrl + Z]: desfazer.

# 19. GUIA RÁPIDO DE MARKDOWN
> Guia completo: https://www.markdownguide.org/basic-syntax/
```
# Título 1
## Título 2
### Título 3

- Item de lista

**texto em negrito**
*texto em itálico*
~~texto riscado~~

--- (linha separadora)

> citação

[[Wikilink para outro arquivo]]
![[imagem.png]]
<-- TODO: o que a IA deve escrever aqui
```

# 20. AVISO LEGAL
- O Silent Multiverse Nexus é uma ferramenta independente e não oficial, feita por fãs. Não é afiliada, endossada, patrocinada nem aprovada pela Wizards of the Coast LLC.
- Dungeons & Dragons e D&D são marcas da Wizards of the Coast LLC. Tormenta20 é marca da Jambô Editora. Pathfinder é marca da Paizo Inc. Os nomes são usados apenas para indicar compatibilidade de regras.
- O programa não contém textos de regras nem conteúdo desses jogos. As referências às regras da quinta edição (5e) seguem o System Reference Document 5.1:
> This work includes material taken from the System Reference Document 5.1 ("SRD 5.1") by Wizards of the Coast LLC and available at https://dnd.wizards.com/resources/systems-reference-document. The SRD 5.1 is licensed under the Creative Commons Attribution 4.0 International License available at https://creativecommons.org/licenses/by/4.0/legalcode.
- (Tradução: esta obra inclui material do System Reference Document 5.1 da Wizards of the Coast LLC, licenciado sob a Creative Commons Atribuição 4.0 Internacional.)
- O conteúdo gerado pela IA é responsabilidade sua: revise antes de publicar e não peça à IA para reproduzir material protegido por direitos autorais.
- Silent é um personagem original deste programa.
- O código-fonte do programa é distribuído sob a Licença MIT.
