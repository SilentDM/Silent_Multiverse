<local_context>
{{contexto_local}}
</local_context>

<related_files>
{{relacionados}}
</related_files>

<target_file name="{{arquivo}}">
{{conteudo}}
</target_file>

<task_instruction>
Find the tag '{{tag}}' inside <target_file>.
Replace that tag with the expanded content, keeping full cohesion with <local_context> and <related_files>.
</task_instruction>

<response_rules>
1. Return ONLY the final content of the edited file, in Markdown.
2. Do not include comments, notes or XML tags in your answer.
3. FORMATTING AND WIKILINKS:
    - Organize the text with headings (#, ##, ###).
    - Use quotes (> text) for lore boxes, rumors, manuscripts or diaries.
    - Use bold (**word**) for key terms and items.
    - CREATE WIKILINKS [[Concept Name]]: whenever you mention characters, cities, places, factions, gods or relics of the universe, wrap the name in double brackets.
</response_rules>
