from jinja2 import Template

instructions: Template = Template("""You are assistant who evaluates how suitable each group is for obtaining document.
For each group, specify:
    - group_id
    - probability (0..1)
    - justification

Return a list of JSON objects by this schema:
```
{{ schema }}
```
""")

prompt: Template = Template("""# Document content:
```
{{ content }}
```

# Groups:
{% for group in groups %}
## Group {{ group.group_id }}
- **Verdict**: {{ group.estimation.verdict }}
- **Confidence Level**: {{ group.estimation.confidence_level }}
- **Explanation**: {{ group.estimation.explanation }}
{% endfor %}
""")
