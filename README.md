# 🜂 Silent Multiverse Nexus

**English** | [Português (Brasil)](README.pt-BR.md)

> **A desktop worldbuilding workshop for tabletop RPG Game Masters: Markdown lore management, AI-assisted writing, a multi-agent council and an integrated Discord bot.**

![Windows](https://img.shields.io/badge/Windows-10%2F11-0078D6?style=for-the-badge&logo=windows)
![Python](https://img.shields.io/badge/Python-3.14-blue?style=for-the-badge&logo=python)
![Gemini API](https://img.shields.io/badge/Google%20Gemini-API-orange?style=for-the-badge&logo=google)
![Discord.py](https://img.shields.io/badge/Discord-Bot-5865F2?style=for-the-badge&logo=discord)
![Obsidian Compatible](https://img.shields.io/badge/Obsidian-Vault%20Compatible-7A3EE8?style=for-the-badge&logo=obsidian)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

**Silent Multiverse Nexus** is a toolkit for Game Masters, writers and setting creators. You write your world in plain Markdown files (fully compatible with **Obsidian**), and the program helps you expand, organize, audit and share it, with Google Gemini doing the heavy lifting and a Discord bot that answers your players **without spoiling your secrets**.

Available in **English** and **Brazilian Portuguese**: the interface and everything the AI writes follow the language you pick.

> Independent, unofficial fan tool, not affiliated with Wizards of the Coast. See the [Legal notice](#legal-notice).

---

## ✨ Features

### Editor built for lore
* Works on any folder of `.md` files, including an existing **Obsidian vault**. File names stay clean, so **`[[Wikilinks]]` never break**.
* File tree with search, drag and drop, templates, and rename/copy/paste/duplicate.
* Instant **preview** in a dark theme with Obsidian callouts (`> [!quote]`, `> [!danger]`...), YAML properties, tables and embedded images.
* Click a wikilink to jump to it, or create the missing file in one click.
* Auto-save, back/forward history, and protection that **never overwrites a file the AI just changed**.

### AI tools (Google Gemini)
* **Expander**: write `<-- TODO: what you want` anywhere and the AI fills the gap using your whole world as context, then a reviewer checks it for consistency before saving.
* **Three levels of AI requests**: a `<-- TODO:` tag for a small change inside a file, **Improve with AI** to rewrite a whole file, and the **WorldBuilder** to build a whole campaign.
* **WorldBuilder**: write your idea in a few paragraphs and it works in three steps, with your review in between: a GM-only **Canon** sheet with the official names, facts and secrets (you edit it), a **plan checklist** (you check, uncheck and edit items), then **execution by phases** (world, places, people, monsters, adventures). Secret files stay hidden from players, and an interrupted run continues where it stopped.
* **Council**: four specialist agents (Architect, Chronicler, the Voice of the NPCs, Tactics & Chaos) discuss a file; you edit their views, and a Supreme Judge writes the final version.
* **Lore Audit**: finds contradictions, timeline gaps and geographic inconsistencies.
* **Improve with AI**, **5-Room Dungeon adventures** (with a statblock and a battlemap of the final room) and **Lore Checks** (knowledge tables with DC ranges), all from a right-click on a file.
* **Talk to Silent**: chat with the keeper of the Nexus, who knows your whole world, for brainstorming and questions.
* **Roleplay (Theater of the Mind)**: forge personas for your NPCs from the world context and talk to them in character, with generated portraits.
* Every file the AI changes is archived first (`_v01`, `_v02`...). Right-click → **Version History** shows every version and restores one with a click.
* **Requests tab**: before any whole-file request, fine-tune it: style in four axes (**Genre, Tone, Mood, Writing style**), extra guidelines, reference files, rewrite or append, depth, player-facing text, party level, creativity, presets. It opens with the project defaults.
* **Combat statblocks** for NPCs and monsters in your rules system; in 5e the program checks the SRD math (modifiers, proficiency, XP).
* **GM Notes**: save Silent's ideas and Roleplay testimonies into a secret section of any file. Every AI tool takes them into account, and the **Council** uses testimonies as the NPCs' real voice.

### Discord bot
* Players ask about the lore with a prefix (e.g. `!silent What is the Silver Cathedral?`) and get answers from the **public** lore only.
* **Deterministic anti-spoiler filter**: secret files, secret sections and a blacklist of secret words are removed before the AI ever sees the players' context.
* GM roles and GM user IDs get answers with the full lore.
* Dice roller: `!r 1d20+5`, `2d20kh1+3`, `4d6kh3`, `3#1d8+2`, composite rolls like `2d12+24+3d8`.
* Reads your server's rules and announcement channels and links back to them (`🔗 View on Discord`).
* Per-server settings: prefix, GM roles, allowed and blocked channels, cooldown.

### And also
* **Sourcebook export**: the whole project as one HTML file with a table of contents and links (print it to PDF).
* **Project size report**: tokens per folder and file, for both the GM and player contexts.
* **Backups** to `.zip`, **update check** on startup, tone & mood profiles, and rules-system choice (5e, Tormenta20, Pathfinder 2e or generic).
* Credentials stored in the **Windows Credential Manager**, never in plain text files.
* Minimizes to the system tray with low memory use while the bot keeps running.

---

## 📋 Markers you can use in your files

| Marker | Where | What it does |
| :--- | :--- | :--- |
| `<-- TODO: reason` | Anywhere in a `.md` | The **Expander** fills this gap with the AI. |
| `[secret]` or `[segredo]` | In a heading | Hides the whole section from players. |
| `status: secret` or `status: segredo` | In the YAML header | Hides the whole file from players. |
| `<!-- secret -->` or `🤫` | In a paragraph | Hides that paragraph from players. |
| `status: draft` or `status: rascunho` | In the YAML header | The AI ignores the file until you finish it. |
| Secret words | Options page (e.g. `Hastur`) | Removes any mention of these names from the players' view. |
| `[[Note]]`, `![[image.png]]` | Anywhere | Links and images, rendered in the preview and the sourcebook. |

Markers work in both languages, so existing projects keep working when you switch.

---

## 🚀 Getting started

1. Download the latest `SilentMultiverse-<version>-windows.zip` from [**Releases**](../../releases).
2. Unzip it into any folder (or your Obsidian vault's root) and run `SilentMultiverse.exe`.
   * If Windows shows "Windows protected your PC", click **More info → Run anyway**. This happens with new programs that don't have a code signature yet.
3. Get a free Gemini API key at [Google AI Studio](https://aistudio.google.com) ("Get API key").
4. In the program, go to **Options → AI (Gemini)** and paste the key (it saves by itself).
5. Choose your language in **Options → Language**, then open your project folder with the 📁 button at the top of the sidebar.

The built-in **📖 Manual & Guide** page covers every feature, including how to set up the Discord bot.

**Updating:** when a new version is out, a notice appears in the status bar. Download it and replace `SilentMultiverse.exe` in the same folder. Your projects, settings and the `.silent_data` folder stay as they are.

---

## 🔒 Privacy and costs

* Your files stay on your computer. To answer, the AI receives your project's text and your request, sent to **Google's Gemini API** with **your own key**. The program has no server and collects nothing.
* On Gemini's **free tier**, Google may use submitted content to improve its products. If your setting is confidential, use a paid key, and check Google's current terms.
* Any usage cost is between you and Google.
* Images use Gemini's image model, or the free [Pollinations](https://pollinations.ai) service as a fallback (only the image description is sent).

---

## 🌐 Languages (EN-US / PT-BR)

In **Options → Language**:

* **The AI and generated content** switch immediately: prompts, the field descriptions sent to Gemini, generated Markdown (adventures, lore checks, persona sheets, sourcebook) and Discord bot replies.
* **The interface** switches after a restart.
* Your lore files are never translated. The starter templates and style guides switch to the new language only if you haven't edited them; your own and edited files are always kept.

All texts live in `locale/`:

```
locale/
  pt_br/  and  en_us/
    ui.json          interface texts
    mensagens.json   log messages and notices
    conteudo.json    headings and labels of generated content
    schemas.json     field descriptions of the AI schemas
    manual.md        the in-app manual
    prompts/*.md     one file per AI call (variables as {{name}})
    modelos/         starter Templates/ and Style/ copied to .silent_data on first use
```

To change a text or prompt, edit it in **both** languages (the tests check that keys and variables match).

---

## 🛠️ Running from source

Requires Windows and Python 3.14 (the version the project is tested with).

```bash
git clone https://github.com/SilentDM/Silent_Multiverse.git
cd Silent_Multiverse
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Tip: double-click `ativar_venv.bat` to open a terminal with the venv already active.

**Tests** (no network, no real keys; they work in a temporary folder):

```bash
python -m unittest discover -s tests -t .
```

### Code layout
* `ui/`: only builds the screens. Every button calls a function from `core/`, `engine/` or `bot/`. No file access, AI calls, threads or business rules in the interface (a test enforces this).
* `core/`: settings, credential vault, language, prompts, log events, background tasks, updates.
* `engine/`: file operations, editor session, actions (Expander, WorldBuilder, audit, sourcebook, backup), schemas and world context.
* `bot/`: Discord bot.

---

## 📦 Building and releasing

```bash
pip install -r requirements-build.txt
python build.py
```

This creates `dist/SilentMultiverse.exe` and `dist/SilentMultiverse-<version>-windows.zip`. The executable bundles `locale/` (which includes the starter templates and style guides of each language, in `locale/<language>/modelos/`) and the icon.

**Publishing a release:**
1. Update `VERSAO` in `core/versao.py` (e.g. `2.1.0`) and commit.
2. Create and push a matching tag: `git tag v2.1.0` then `git push origin v2.1.0`.
3. GitHub Actions (`.github/workflows/release.yml`) runs the tests, builds the `.zip` on Windows and creates a **draft** release.
4. Review the draft on GitHub and click **Publish release**. The program's update check then shows the new version to users.

---

## Legal notice

Silent Multiverse Nexus is an independent, unofficial fan tool. It is **not affiliated with, endorsed, sponsored or approved by Wizards of the Coast LLC**.

*Dungeons & Dragons* and *D&D* are trademarks of Wizards of the Coast LLC. *Tormenta20* is a trademark of Jambô Editora. *Pathfinder* is a trademark of Paizo Inc. These names are used only to describe rules compatibility. The program contains no rules text or content from these games.

References to fifth edition rules (5e) follow the System Reference Document 5.1:

> This work includes material taken from the System Reference Document 5.1 ("SRD 5.1") by Wizards of the Coast LLC and available at https://dnd.wizards.com/resources/systems-reference-document. The SRD 5.1 is licensed under the Creative Commons Attribution 4.0 International License available at https://creativecommons.org/licenses/by/4.0/legalcode.

Content generated by the AI is the user's responsibility. Silent is an original character of this program.

## 📄 License

The source code is licensed under the [MIT License](LICENSE).
