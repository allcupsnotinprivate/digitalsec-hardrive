from jinja2 import Template

instructions: str = Template("""Make a short, fact-rich summary of text below for next RAG stage.
Remove common phrases and introductory ones. Leave only unique semantic constructions, facts, key names, terms,
identifiers, numerical parameters, time and  structural features.

Your goal is to keep the text as small as possible, containing only the information that can be useful for 
searching or accurately identifying the document.

Requirements:
- Do not retell the content.
- Do not generalize.
- Do not add introductory words.
- Do not distort the wording from the text.
- Use the terminology from the original.
- Maximum length is 512 tokens.

Output format: flat text, without points and lists.
""").render()

prompt: Template = Template("""Text for summarizing:
```
{{ text }}
```
""")
