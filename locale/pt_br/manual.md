# SILENT MULTIVERSE NEXUS
- Maneje todos os arquivos .md dentro de um projeto de forma fácil, rápida e segura.
- Exporte seu projeto inteiro como um arquivo HTML com índice, hiperlinks navegáveis e na ordem que você configurar.
- Use IA como achar melhor, onde quiser, sob suas ordens, respondendo como você quiser.
- Converse com Ao para tirar dúvidas, pedir variações de ideias e brainstorming.
- Crie um bot no Discord para seus jogadores e amigos perguntarem qualquer coisa sobre o projeto.
- Faça arquivos com regras de servidor para o Bot também responder quaisquer dúvidas.

# 1. INÍCIO RÁPIDO & ESTRUTURA DO PROJETO
- Projeto Atual: o projeto ativo fica selecionado no topo do menu lateral. Você pode criar ou alternar entre projetos a qualquer momento clicando no ícone de pasta 📁.
- Pasta do Projeto: guarda as pastas e os arquivos em Markdown (.md). Pode ter quantos projetos quiser!
- Templates/: modelos de criação (ex: cidade.md, npc.md, reinado.md). Você pode editá-los e adicionar novos diretamente nesta pasta.
- Style/: diretrizes de escrita e clima (ex: Tom_e_Clima.md). O arquivo base muda conforme a opção escolhida em Opções; outros documentos que você colocar ali também são usados pela IA.
- memories/: histórico recente das conversas locais e do Discord. Só é apagado pelo botão Excluir Memórias na página Ações.
- exports/: livros do cenário em HTML e relatórios.

# 2. IDIOMA
- Em Opções → Idioma, escolha Português (Brasil) ou English (US).
- A IA passa a responder no novo idioma imediatamente (Expander, WorldBuilder, Conselho, Roleplay, chat e bot do Discord).
- A interface muda depois de reiniciar o programa.
- Seus arquivos de lore não são traduzidos; o conteúdo novo gerado pela IA segue o idioma escolhido.

# 3. SINTAXE DO EDITOR & REGRAS DE ESCRITA
## Wikilinks [[Nome Do Arquivo]]
- Sempre que quiser citar outra entidade do seu mundo, use colchetes duplos (ex: [[Reino de Lucius]]). Clique no link no editor para navegar até ele. Se o documento não existir, o programa pergunta se deseja criá-lo.
## Tags de Expansão (<-- TODO: Motivo)
- Clique com o botão direito no editor para inserir a tag <-- TODO:, ou digite manualmente. Depois dos dois pontos, escreva o que deve ser feito.
- O Expander detecta a tag e usa a IA para preencher o trecho seguindo suas instruções.
## Segredos do Mestre vs Jogadores
- Usado pelo Bot do Discord quando responde jogadores.
- Para ocultar um arquivo inteiro dos jogadores, coloque status: segredo (ou status: secret) ou tags: [segredo] no cabeçalho.
- Para ocultar uma seção, inclua [segredo] (ou [secret]) no título (ex: ### O Culto Oculto [segredo]).
- Arquivos ou pastas cujo NOME contém uma palavra secreta (cadastrada em Opções) também ficam ocultos.
- Rascunhos: status: rascunho (ou status: draft) deixa o arquivo fora do contexto da IA.

# 4. CONVERSA COM AO & BOT DO DISCORD
## Chat Local
- Ao, dentro do programa, simula o Bot do Discord: brainstorming, dúvidas e discussões sobre o projeto.
- Clique com o botão direito em um arquivo no Editor e escolha 'Perguntar sobre este arquivo ao Ao' para anexar o documento completo à conversa.
## Bot do Discord
- Gatilho (Prefixo): como os jogadores acionam o bot no servidor. Ex: !ao, $ao, &Supremo.
- Cargos de Mestre: quem tiver esses cargos recebe respostas com o projeto inteiro, incluindo segredos.
- Canais Permitidos/Proibidos: onde o bot pode ou não responder.
- Tempo de Espera: cooldown por usuário, para impedir spam.
- Dados: !r 1d20+5, !rolar 2d6+3 ou !r 2d20kh1+3.

# 5. PÁGINA WORLDBUILDER
- Escreva o objetivo e clique em Executar: o WorldBuilder planeja e executa ações (criar pastas, criar e melhorar arquivos).
- As ações planejadas aparecem na lista assim que o planejamento termina; o log mostra cada passo em tempo real.
- As permissões (criar pastas, criar arquivos, melhorar arquivos) ficam na própria página.

# 6. PÁGINA AÇÕES
- Expander: procura tags <-- TODO: em todos os arquivos e gera o conteúdo com a IA. A versão anterior vai para logs/history.
- Expander Automático (Opções): roda o Expander ao salvar com Ctrl+S ou ao sair de um arquivo editado que contenha a tag.
- Reconstruir Contexto: atualiza o que a IA sabe sobre o projeto. O contexto é recriado sozinho a cada 12h.
- Auditoria de Lore: procura incoerências históricas, furos de cronologia ou contradições geográficas.
- Livro do Cenário: compila todos os arquivos em um HTML com índice e links e o abre no navegador (pode ser salvo como PDF).
- Analisar Tamanho do Projeto: mostra, por pasta e arquivo, quantos tokens o projeto ocupa no contexto da IA (Mestre e Jogadores) e quanto isso representa do limite do provedor.
- Backup: gera um .zip com o projeto e a pasta de dados, na raiz do disco do programa (ou na pasta do programa, se não houver permissão).
- Excluir Memórias: apaga as conversas locais e do Discord.

# 7. ATALHOS
- [Ctrl + S]: salvar o arquivo (e acionar o Expander automático, se habilitado).
- [F2]: renomear o item selecionado no Editor.
- [Ctrl + Roda do Mouse]: zoom.
- [Alt + Seta Esquerda / Direita]: voltar / avançar entre documentos.
- [Ctrl + Z]: desfazer.

# 8. COMANDOS MARKDOWN (.md)
> Guia completo: https://github.com/mende1/guia-definitivo-de-markdown
```
# Título 1
## Título 2
### Título 3

- Item de lista

**texto em negrito**
*texto em itálico*
~~texto riscado~~

--- (linha separadora)

> texto de citação
```
