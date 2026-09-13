# 🜂 Silent Multiverse Nexus

> **Plataforma Desktop de Worldbuilding, Gestão de Lore para RPG, Conselho Deliberativo com IA e Bot de Discord Integrado.**

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python)
![Gemini API](https://img.shields.io/badge/Google%20Gemini-Context%20Caching-orange?style=for-the-badge&logo=google)
![Discord.py](https://img.shields.io/badge/Discord.py-Bot-5865F2?style=for-the-badge&logo=discord)
![Obsidian Compatible](https://img.shields.io/badge/Obsidian-Native%20Vault%20Support-7A3EE8?style=for-the-badge&logo=obsidian)
![Security](https://img.shields.io/badge/Security-Windows%20Keyring-success?style=for-the-badge&logo=windows)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

O **Silent Multiverse Nexus** é uma suíte completa de ferramentas desktop para Mestres de RPG, Escritores e Criadores de Cenários. Ele combina a escrita nativa em Markdown compatível com o ecossistema do **Obsidian.md**, automação com modelos de ponta de Inteligência Artificial (Google Gemini, OpenAI, Claude), geração de arte integrada e um Bot de Discord com **filtro mecânico anti-spoiler** e rolador avançado de dados para mesas online.

---

## Principais Funcionalidades

### 1. Integração Nativa com Obsidian.md & Preview Embutido
* **Compatibilidade com Cofres (Vaults)**: Aponte o programa para qualquer pasta do Obsidian. O Nexus preserva nomes limpos de arquivos para **nunca quebrar Wikilinks (`[[Nota]]`)**.
* **Modo de Visualização (Preview Estilo Obsidian)**: Alterne instantaneamente entre o editor de texto bruto e a visualização renderizada no tema Dark, com suporte a **Callouts nativos (`> [!quote]`, `> [!danger]`, `> [!tip]`)**, painel visual de propriedades YAML, tabelas de combate e imagens embutidas.
* **Isolamento Total em `.nexus_data/`**: Todos os dados operacionais (logs, histórico, memórias, imagens e templates) são guardados em uma pasta oculta ao lado do executável, mantendo seu cofre limpo e sem poluição de arquivos de sistema.

---

### 2. Conselho de Criação & Consolidação (Multi-Agentes em 2 Etapas)
* **Deliberação Especializada em 4 Painéis**: Clique com o botão direito em qualquer documento para convocar o Conselho:
  * **Painel 1 (O Arquiteto):** Gera propostas ricas de expansão e novos fatos.
  * **Painel 2 (O Cronista):** Audita a continuidade contra o cache de 1 milhão de tokens (evita datas conflitantes e NPCs ressuscitados).
  * **Painel 3 (A Voz dos NPCs):** Identifica os personagens nomeados no texto e gera a reação de cada um em **1ª pessoa**.
  * **Painel 4 (Tático & Caos):** Define desafios de perícias graduais (D&D 5e) somados a dilemas dramáticos.
* **Human-in-the-Loop Total**: Você pode editar os textos diretamente dentro de qualquer painel antes da aprovação final.
* **Síntese Canônica**: O Juiz Supremo compila os painéis revisados no Markdown final, arquiva a versão anterior em `history/` (`_v01`, `_v02`) e grava a nova versão mantendo os links intactos.

---

### 3. Teatro da Mente (Roleplay com Habitantes do Universo)
* **Converse Diretamente com seus NPCs**: Crie ou forje personas imersivas que absorvem toda a geografia, facções e história do seu mundo.
* **Fichas Visuais Ricas**: Geração automática de traços físicos detalhados em Português (gênero, raça, olhos, cabelo, roupas e marcas) e mentalidade profunda (fraquezas ocultas, bordões e psicologia).
* **Diálogos In-Character**: O NPC responde mantendo estritamente sua voz, segredos e objetivos, com histórico de memória individual persistente.

---

### 4. Geração de Imagens com Fallback Gracioso
* **Retratos de Personagens (Portraits 1:1)**: Geração de arte para NPCs na aba de Roleplay com prompts técnicos otimizados em inglês. Menu de contexto interativo para **abrir no visualizador nativo**, **salvar como** ou **mostrar na pasta**.
* **Mapas Táticos de Combate (Battlemaps 16:9 Top-Down)**: Criação automática de mapas de batalha para masmorras, embutidos diretamente nas notas de aventura com visualização imediata.
* **Arquitetura Híbrida Inteligente**: Utiliza a infraestrutura oficial do Gemini se houver chave com faturamento ativo, com **chaveamento automático para o motor open-source Pollinations (Flux / SDXL)** caso a cota gratuita do Google esteja sem créditos.

---

### 5. Ferramentas Prontas para D&D 5e
* **Aventuras 5-Room Estruturadas**: Gera módulos completos de masmorra divididos em:
  1. *Guardião da Entrada*
  2. *Enigma / Desafio de Perícia*
  3. *Ponto de Tensão / Reviravolta*
  4. *O Clímax (com Statblock 5e e Ações de Covil)*
  5. *Recompensa e Fuga*
* **Testes de Conhecimento (Lore Checks)**: Transforma qualquer documento (cidade, guilda, item, monstro) em tabelas de consulta rápida para a mesa com faixas graduais de resultado d20:
  * `≤ 5` (Rumor popular) | `6-10` (Básico) | `11-15` (Operacional) | `16-20` (Especialista) | `21-25` (Segredo de Cúpula) | `26+` (Mistério Central).

---

### 6. Bot de Discord "Ao" & Central de Servidor
* **Sem Prefixo Obrigatório para Dados**: Reconhece rolagens automaticamente pelo formato padrão de RPG:
  * Rolagens compostas: `2d12+24+3d8+2d10+1d6`
  * Filtros de vantagem/desvantagem: `4d6kh3`, `2d20kl1`
  * Repetições em linhas separadas: `3#d6`, `2#1d20+5 Ataques Múltiplos`
* **Filtro Mecânico Anti-Spoiler (Segurança 100% Determinística)**:
  * **Blacklist de Palavras Secretas**: Cadastre termos e nomes proibidos (ex: `Hastur, Cthulhu`). O sistema omite automaticamente do bundle dos jogadores qualquer arquivo, cabeçalho ou parágrafo que mencione essas palavras.
  * Suporte a tags manuais: `[SEGREDO]`, `status: segredo` e emojis `🤫`.
* **Raspagem de Regras (Discord Scraper)**: Monitora canais de regras, anúncios e tópicos do Discord, gerando links de referência direta `🔗 [Ver no Discord](URL)` quando a IA cita normas do servidor.
* **Configuração Multisservidor**: Perfis de prefixos, cargos de Mestre e canais autorizados independentes para cada guilda do Discord.

---

### 7. Segurança Profissional & Performance
* **Cofre Nativo do Windows (`keyring`)**: Seus tokens de API e chaves do Discord são armazenados diretamente no *Windows Credential Manager* com criptografia de conta do SO. **Zero arquivos `.env` soltos em texto puro na raiz**.
* **Seletor de Modelos Gemini (Automático vs. Manual)**:
  * *Modo Automático:* Ranquear modelos por taxa de sucesso e menor tempo de resposta.
  * *Modo Manual:* Reordene os cartões de IA para priorizar modelos Pro para lore literária, mesmo que sejam mais lentos.
* **Otimização de RAM no System Tray**: Ao minimizar para a bandeja do relógio do Windows, o aplicativo esvazia o *working set*, reduzindo o consumo de **~120 MB para cerca de 15 MB de RAM** enquanto o bot opera em segundo plano.

---

## 📋 Sistema de Marcações do Projeto

| Marcador / Sintaxe | Onde usar | Comportamento |
| :--- | :--- | :--- |
| `<-- TO DO: motivo` | Em qualquer `.md` | O **Expander** preenche a lacuna com IA contextualizada. |
| `[SEGREDO]` | No título de uma seção | Oculta a seção inteira dos jogadores no Discord e no cache. |
| `status: segredo` | No Frontmatter YAML | Oculta o arquivo inteiro das consultas dos jogadores. |
| `status: rascunho` | No Frontmatter YAML | Ignorado pela IA até que você finalize o rascunho. |
| `Termos Secretos` | Aba Opções (ex: `Hastur`) | Elimina qualquer menção ao nome do conhecimento dos jogadores. |
| `![[imagem.png]]` | Em qualquer `.md` | Renderiza portraits e battlemaps nativamente no preview. |

---

## 🚀 Como Usar

### Opção A: Executável Portátil (Recomendado para Usuários)
1. Acesse a aba de [**Releases**](../../releases) deste repositório.
2. Baixe o pacote `SilentMultiverse.zip`.
3. Descompacte em qualquer pasta ou na raiz do seu cofre do Obsidian e execute `SilentMultiverse.exe`.
4. Abra a aba **Opções** e configure sua chave de API (salva de forma criptografada pelo sistema).

---

### Opção B: Execução via Código-Fonte (Desenvolvedores)

1. **Clone o repositório:**
   ```bash
   git clone https://github.com/SilentDM/Silent_Multiverse.git
   cd Silent_Multiverse
   ```

2. **Crie e ative um ambiente virtual:**
   ```bash
   python -m venv .venv
   ```
   * No Windows (CMD):
     ```cmd
     .venv\Scripts\activate.bat
     ```
   * No Windows (PowerShell):
     ```powershell
     .\.venv\Scripts\Activate.ps1
     ```

3. **Instale as dependências:**
   ```bash
   pip install google-genai discord.py pydantic openai anthropic pystray Pillow tkinterweb keyring
   ```

4. **Inicie o aplicativo:**
   ```bash
   python main.py
   ```

5. **Para compilar o `.exe` único:**
   Execute o script de automação:
   ```cmd
   build.bat
   ```
   O executável otimizado será gerado na pasta `dist/SilentMultiverse.exe`.

---

## 📄 Licença

Este projeto está licenciado sob a licença [MIT](LICENSE).
