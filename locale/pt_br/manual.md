# SILENT MULTIVERSE NEXUS
- Uma oficina de worldbuilding para Mestres de RPG de mesa, feita sobre arquivos Markdown (.md) comuns. Funciona muito bem com um cofre do Obsidian.
- Edite, organize e ligue todos os arquivos do seu cenário com rapidez e segurança.
- Use a IA (Google Gemini) para preencher lacunas, melhorar arquivos, planejar expansões, auditar a lore, gerar aventuras e testes de conhecimento e conversar com seus NPCs.
- Converse com Silent, o guardião do Nexus, para fazer brainstorming, tirar dúvidas e revisar ideias sobre o seu mundo.
- Rode um bot no Discord para os jogadores perguntarem sobre a lore pública (os segredos ficam escondidos) e rolarem dados.
- Compile o projeto inteiro em um livro de cenário HTML com índice e links clicáveis.
> Use a lista Conteúdo à esquerda para ir direto a qualquer seção.

## A tela
- O menu à esquerda tem quatro grupos: Escrever (Editor), Criar com IA (WorldBuilder, Conselho, Interpretação e Silent), Projeto (Ações) e, embaixo, Sistema (Opções, Log e Manual).
- Enquanto há uma Requisição aberta, ela aparece no menu logo abaixo do Editor (↳ Requisição: nome do arquivo).
- A barra de status mostra o projeto, as contagens do arquivo aberto e, à direita, as tarefas de IA em andamento. Cada tarefa tem o seu ✕ para parar só ela; com mais de uma rodando aparece também ⏹ Parar tudo.
- A− e A+, no canto direito da barra de status, mudam o tamanho do texto.
- Ícones de ajuda: o círculo com ? ao lado de uma opção explica o que ela faz. Passe o mouse por cima (ou clique). Para escondê-los, desmarque Opções → Geral → Mostrar os ícones de ajuda.

# 1. PRIMEIROS PASSOS
> Na primeira vez que o programa abre, um assistente guia estes passos: idioma, chave do Gemini e pasta do projeto. Para repeti-lo, use Opções → Geral → Abrir o assistente de início.
## 1) Consiga uma chave de API do Gemini
- Abra o Google AI Studio (https://aistudio.google.com), entre com uma conta Google e clique em "Get API key".
- Existe um nível gratuito. Os limites mudam com o tempo e aparecem no próprio AI Studio.
## 2) Salve a chave
- Vá em Opções → IA (Gemini) e cole a chave no campo da chave. Ela é salva sozinha.
- As chaves ficam no Gerenciador de Credenciais do Windows, nunca em arquivos de texto.
## 3) Escolha o idioma
- Opções → Idioma. A IA muda na hora; a interface muda ao reiniciar.
## 4) Abra o seu projeto
- No topo da barra lateral, clique no ícone 📁 e escolha a pasta com seus arquivos .md (uma pasta vazia começa um projeto novo). Um cofre do Obsidian funciona do jeito que está.
- Os projetos recentes ficam na lista para trocar rápido.
## 5) Teste os modelos
- Em Opções → IA (Gemini), clique em "Testar Modelos". O programa testa os modelos disponíveis e os ordena por velocidade e confiabilidade.
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
- A IA passa a usar o novo idioma na hora: Expander, WorldBuilder, Conselho, Interpretação, chat, auditoria, aventuras, testes de conhecimento e o bot do Discord.
- A interface muda ao reiniciar o programa.
- Seus arquivos de lore nunca são traduzidos. O conteúdo novo gerado pela IA segue o idioma escolhido.
- Os templates e guias de estilo iniciais que você não editou mudam para o novo idioma; os seus e os editados são mantidos.
- Os marcadores funcionam nos dois idiomas: status: segredo ou status: secret, [segredo] ou [secret], status: rascunho ou status: draft.
- Glossário: Silent, Nexus, WorldBuilder e Expander são nomes do programa e ficam iguais nos dois idiomas. Em português, Roleplay aparece como Interpretação, In-Character como Em Personagem, Benchmark como Testar Modelos e Preset como Predefinição. Lore, token e Markdown ficam como estão.

# 4. EDITOR
## Árvore de arquivos
- Busca: digite na caixa acima da árvore para filtrar os arquivos pelo nome ou conteúdo.
- A árvore se atualiza sozinha quando algo muda na pasta (outro programa, a IA, o Obsidian). O botão ⟳ força a atualização.
- Ícones ao lado do nome: 🤫 segredo · ✎ rascunho · ⏳ TODO pendente · 🗒 tem Notas do Mestre · ⚙ a IA está trabalhando no arquivo.
- Ao selecionar uma pasta, o Editor mostra uma visão geral dela: números (arquivos, subpastas, palavras e tokens), quantos arquivos são secretos, rascunhos, têm TODO ou Notas do Mestre, a árvore do conteúdo com as marcas de cada arquivo, os editados por último e os [[links]] citados ali que ainda não têm arquivo. Clique num nome para abrir.
- Arraste e solte arquivos e pastas para movê-los.
- Clique com o botão direito em um arquivo ou pasta: Novo Arquivo, Nova Pasta, Renomear (F2), Copiar, Recortar, Colar, Duplicar, Excluir e Mostrar no Windows Explorer.
- Novo Arquivo permite escolher um dos Templates.
## Escrevendo
- Abas: cada arquivo aberto ganha uma aba acima do texto. Clique para trocar, × (ou botão do meio) para fechar. A posição do cursor de cada aba é lembrada.
- Ao lado do nome do arquivo, "● Não salvo" ou "✓ Salvo". O programa salva sozinho logo depois que você para de digitar, e com Ctrl+S.
- Modos: Editar (só o texto), Visualizar (a página formatada) e Lado a lado (texto e visualização juntos, atualizada enquanto você digita). 🌐 abre a visualização no navegador.
- Barra de formatação: títulos (H1–H3), negrito, itálico, [[link]], lista, citação, linha separadora, tag TODO e seção secreta.
- [[Links]]: ao digitar [[ aparece uma lista com os arquivos do projeto (↑ ↓ e Enter para escolher). Links para arquivos que ainda não existem ficam em vermelho; clique para criar o arquivo.
- 🔎 Buscar (Ctrl+F) e Substituir (Ctrl+H) dentro do arquivo, com contagem de ocorrências.
- Ctrl+P abre qualquer arquivo do projeto pelo nome.
- Painel lateral (☰): Sumário do arquivo (clique para pular até o título), Citado por (arquivos que linkam este) e as Notas do Mestre do arquivo.
- Voltar / Avançar (◀ ▶, Alt+Esquerda / Alt+Direita ou os botões laterais do mouse) navega entre os documentos abertos.
- A barra de status mostra palavras, caracteres, linhas e uma estimativa de tokens do arquivo aberto.
## Ações de IA (botão ✨ IA ou botão direito no arquivo)
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
## Propriedades do Obsidian
- Silent guarda os marcadores do arquivo como propriedades do Obsidian, o bloco entre linhas --- no topo do arquivo:
```
---
status: segredo
aliases: [O Rei das Cinzas]
---
```
- O Obsidian mostra esse bloco como Propriedades. O resto do bloco (tags, tipo, campos seus) é mantido como você escreveu.
- Arquivos antigos com a linha solta "status: segredo" continuam funcionando. Quando Silent grava o arquivo (IA, WorldBuilder, notas), a linha vira propriedade. O que você salva no Editor não é convertido.
- aliases (apelidos): ao digitar [[ no Editor, um apelido aparece na lista e vira [[Arquivo|Apelido]], o mesmo link que o Obsidian usa.
- Templates com propriedades próprias funcionam: ao criar um arquivo, as propriedades do template vão para o topo.
## Segredos do Mestre vs jogadores
- Arquivo inteiro: a propriedade status: segredo (ou secret), ou tags: [segredo]. A linha antiga status: segredo no começo do texto também vale.
- Uma seção: adicione [segredo] (ou [secret]) ao título dela, ex.: ### O Culto Oculto [segredo].
- Um parágrafo: o parágrafo que contém <!-- segredo --> (ou <!-- secret -->) ou 🤫 fica oculto.
- Palavras secretas (Opções): qualquer arquivo, pasta, título ou parágrafo que contenha esses nomes é removido da visão dos jogadores.
- O Mestre (chat local e cargos/IDs de Mestre no Discord) vê tudo; os jogadores veem só a lore pública.
## Rascunhos
- A propriedade status: rascunho (ou draft) deixa o arquivo fora do contexto da IA até você terminá-lo. Arquivos vazios e com tags <-- TODO pendentes também ficam de fora.
## Imagens
- ![[imagem.png]] mostra retratos e mapas de batalha na visualização e no livro de cenário.
## Notas do Mestre
- A seção "🤫 Notas do Mestre" no fim de um arquivo guarda notas de Silent, depoimentos da Interpretação e anotações suas.
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
- Corrigir a auditoria: no relatório da Auditoria de Lore, 🌍 Corrigir com o WorldBuilder pula o Cânone e monta um plano de correção (arquivos a corrigir com o motivo apontado pelo Auditor e arquivos que faltam). Ver Relatório da Auditoria reabre o relatório; Gerar Plano refaz o plano a partir dele. Nada é alterado até você clicar em Executar Marcadas, e cada arquivo é corrigido com o relatório como referência.
## A aba Requisições
- Abre com os padrões do projeto e mostra o arquivo inteiro. Tudo o que você trocar vale só para este pedido.
- Enquanto o pedido está aberto, ele fica no menu abaixo do Editor; dá para voltar ao Editor e retomar o pedido depois.
- Estilo em quatro eixos: Gênero, Tom, Clima e Estilo de escrita (ex.: numa aventura de Mistério, a caverna lovecraftiana pode usar Horror Cósmico).
- Diretrizes extras, arquivos de referência (os ligados por [[links]] aparecem sugeridos), modo (reescrever tudo ou só acrescentar), profundidade, público (Mestre ou texto para jogadores), nível do grupo, número de jogadores, criatividade e a marca 🤫 de segredo.
- Predefinições guardam combinações que você usa sempre; o tamanho estimado mostra quantos tokens o pedido vai usar.

# 7. AÇÕES
As ferramentas estão em quatro grupos: Gerar (escrevem ou montam algo novo), Analisar (só leem o projeto e mostram um relatório), Manutenção (deixam o projeto em ordem sem mudar a lore) e Zona de perigo (apagam o que não volta, sempre com confirmação).
- Expander: procura tags <-- TODO: em todos os arquivos e as preenche com a IA. Um revisor confere o resultado contra a sua lore antes de salvar.
- Reconstruir Contexto do Mundo: atualiza o que a IA sabe sobre o projeto (também é reconstruído automaticamente a cada 12 horas).
- Auditar Lore do Mundo: procura contradições, buracos na linha do tempo e inconsistências geográficas e mostra um relatório que você pode salvar ou mandar ao WorldBuilder (🌍 Corrigir com o WorldBuilder). Marque Montar o plano de correção no WorldBuilder ao terminar para isso acontecer sozinho; o plano sempre espera a sua revisão.
- Livro do Cenário: compila todos os arquivos em um HTML com índice e links e o abre no navegador (imprima como PDF se quiser).
- Analisar Tamanho do Projeto: mostra, por pasta e arquivo, quantos tokens o projeto ocupa no contexto da IA (Mestre e jogadores) e quanto isso representa do limite do provedor.
- Backup: cria um .zip com o projeto e a pasta de dados na raiz do disco do programa (ou na pasta do programa, se não houver permissão).
- Excluir Todas as Memórias: apaga o histórico do chat local e das conversas do Discord.
- Abrir Pasta de Dados: abre a .silent_data.
- Para parar uma tarefa, clique no ✕ dela na barra de status; ⏹ Parar tudo interrompe todas.

# 8. CONVERSE COM SILENT
- Silent é a entidade que guarda o Nexus: conhece o seu mundo inteiro (inclusive os segredos) e ajuda a fazer brainstorming, tirar dúvidas e revisar ideias.
- A conversa é lembrada por projeto e resumida automaticamente quando fica longa.
- A caixa de mensagem tem várias linhas: Enter envia, Ctrl+Enter (ou Shift+Enter) quebra a linha.
- Atalhos: botões com pedidos prontos (Resumir, Checar consistência, Nomes, Ganchos, Encontros, NPC rápido, Rumores, Descrever imagem, O que falta). O pedido vai para a caixa com o [trecho a completar] já selecionado: é só digitar por cima. O ✎ ao lado edita a lista (criar, apagar, reordenar ou restaurar os padrões).
- 📎 Anexar: arquivos do projeto (busca pelo nome), arquivos do computador e imagens (mapas, retratos, rascunhos). Dá para anexar vários de uma vez; o ✕ de cada um remove. Imagens grandes são reduzidas antes do envio.
- Para discutir um arquivo específico, clique nele com o botão direito no Editor e escolha "Perguntar a Silent sobre este arquivo": ele já entra como anexo.
- As respostas aparecem formatadas (títulos, listas, negrito, citações). Clique num [[link]] da resposta para abrir o arquivo no Editor.
- Botão direito numa mensagem: salvar como nota ou copiar de volta para a caixa de mensagem.
- 📝 Nota (ou botão direito numa mensagem): guarda a resposta nas Notas do Mestre do arquivo escolhido. "Salvar e aplicar agora" já abre a aba Requisições para incorporar a nota ao texto.
- 🌍 Levar ao WorldBuilder: a conversa vira a ideia do WorldBuilder.

# 9. INTERPRETAÇÃO (TEATRO DA MENTE)
- Clique em ➕ Nova Persona, digite o nome do personagem e descreva o papel, a motivação ou o mistério dele. A IA monta a persona completa a partir do contexto do seu mundo.
- Converse em personagem no lado direito. Cada persona lembra a própria conversa.
- A ficha da esquerda é editável: corrija o que a IA errou ou acrescente detalhes. Ela salva sozinha no arquivo da persona ("✓ Salvo") e a próxima fala já usa o texto novo.
- A seção 🎨 da ficha, logo depois da aparência, é o pedido do retrato (em inglês). Mude ali e gere um retrato novo. A seção termina na primeira linha em branco.
- ↺ Ficha original descarta as suas edições e volta à ficha que a IA gerou.
- 📝 Depoimento (ou botão direito numa fala): guarda a fala nas Notas do Mestre, de preferência no arquivo do próprio personagem. É a versão dele: pode mentir ou estar enganado.
- 🎨 Gerar Retrato do NPC cria uma imagem do personagem. Clique com o botão direito na imagem para abri-la, salvá-la ou mostrá-la na pasta de dados.
> As imagens (retratos e mapas de batalha das aventuras) usam o modelo de imagem do Gemini. Se ele não estiver disponível para a sua chave ou a cota acabar, o programa usa o serviço gratuito Pollinations (só a descrição da imagem é enviada).

# 10. CONSELHO (CRIAÇÃO E CONSOLIDAÇÃO)
- Escolha um arquivo (ou use Consolidar com o Conselho no Editor) e escreva uma diretriz.
- Passo 1: quatro especialistas dão sua visão: o Arquiteto (expansão), o Cronista (fatos e continuidade), a Voz dos NPCs (em primeira pessoa) e Tática & Caos (mecânicas e dilemas). Você pode editar os textos deles.
- Passo 2: o Juiz Supremo une os painéis na versão final do arquivo. A versão anterior é arquivada.
- O Conselho usa o que as outras perspectivas já disseram sobre o arquivo: os depoimentos da Interpretação viram a voz real dos NPCs, as notas de Silent e as suas orientam o Arquiteto e o Cronista, e conversas recentes de Roleplay com personagens citados também entram. A linha "O Conselho usou" mostra as fontes.

# 11. OPÇÕES
As Opções têm quatro abas. Tudo salva sozinho; um "✓ Salvo" no topo confirma.
- Geral: idioma, abrir a aba Requisições antes de cada pedido, ícones de ajuda (?), o assistente de início, versão, atualizações e o aviso legal.
- IA (Gemini): a chave do Gemini, o status do cache e a ordem de uso dos modelos (veja a seção 12).
- Projeto: Estilo (Gênero, Tom, Clima e Estilo de escrita), Sistema de Regras, palavras secretas e o Expander automático. Estas valem só para o projeto aberto e ficam salvas na pasta dele (.silent_projeto.json); um projeto novo começa com os valores atuais.
- Discord: token do bot, IDs de Mestre e as regras por servidor (veja a seção 13).
- Cache do Gemini: em contas sem faturamento o programa para de tentar o cache e usa o envio do bundle; "Tentar cache de novo" volta a tentar (trocar a chave também).

# 12. MODELOS DO GEMINI (Opções → IA)
- Testar Modelos testa todos os modelos Gemini disponíveis e os ordena por tempo de resposta e taxa de sucesso.
- O modo Automático usa essa ordem; o modo Manual deixa você definir a sua.
- Se um modelo falhar ou atingir o limite, o programa tenta o próximo automaticamente.

# 13. BOT DO DISCORD
## Criando o bot (uma vez)
- Abra o Discord Developer Portal (https://discord.com/developers/applications) → New Application.
- Em Bot: clique em Reset Token e copie o token. Ative "Message Content Intent".
- Em OAuth2 → URL Generator: marque "bot"; permissões: View Channels, Send Messages, Embed Links, Read Message History. Abra o link gerado para convidar o bot ao seu servidor.
- No programa: Opções → Discord → cole o token em "Token do Bot do Discord" (é salvo sozinho). Reinicie o programa para conectar.
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
- A IA não responde: confira a chave em Opções → IA, use Testar Modelos e veja o Log de Atividades. Um erro "429" ou "quota" significa que o limite da chave foi atingido; espere ou use outro modelo.
- O bot fica offline: confira o token, o Message Content Intent e o Log de Atividades; reinicie o programa depois de salvar o token.
- Um arquivo está travado: a IA está trabalhando nele. Espere a tarefa terminar ou clique no ✕ dela na barra de status.
- A visualização não aparece: falta o componente de visualização (tkinterweb); a versão publicada já o inclui.

# 18. ATALHOS
- [Ctrl + S]: salvar (e rodar o Auto Expander, se ativado).
- [Ctrl + F] buscar no arquivo · [Ctrl + H] substituir · [F3 / Shift + F3] próxima / anterior.
- [Ctrl + P]: abrir arquivo pelo nome.
- [Ctrl + W]: fechar a aba · [Ctrl + Tab / Ctrl + Shift + Tab]: próxima / aba anterior.
- [Ctrl + B] negrito · [Ctrl + I] itálico · [Ctrl + K] [[link]].
- [F2]: renomear o item selecionado na árvore de arquivos.
- [Ctrl + Roda do Mouse] ou [Ctrl + / Ctrl -]: zoom (ou A− / A+ na barra de status).
- [Alt + Esquerda / Direita] ou botões laterais do mouse: voltar / avançar entre documentos.
- [Ctrl + Z]: desfazer.
- Chat do Silent: [Enter] envia · [Ctrl + Enter] ou [Shift + Enter] quebra a linha.

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
