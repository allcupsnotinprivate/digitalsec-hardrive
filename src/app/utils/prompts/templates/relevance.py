from jinja2 import Template

instructions: Template = Template("""You are an expert assistant responsible for assessing how likely a specific person 
(potential recipient) is the actual intended recipient of a given document.

You are provided with:
- The **content of document**.
- The **description** of the potential recipient.
- A set of **recipient statistics**, which are derived from how frequently and strongly this person appeared 
  among documents that are semantically similar to the current one.

Each potential recipient is described by the following characteristics:
- `description`: textual description of the person, including position, expertise, or role.
- `frequency`: how many times this person appeared as a potential recipient in top-ranked similar documents.
- `weighted_score`: the sum of similarity scores of the documents in which this recipient appeared.
- `scores`: list of the individual similarity scores per document (can indicate consistency).
- `importance_index`: normalized score that combines frequency and average weighted_score relative to top values.
  The higher the importance index, the more likely this recipient was relevant in similar cases.

### Your task:
Based on the content of the document and these characteristics, determine **how likely** this person is 
to be the correct recipient. Be logical and concise.

### Confidence Level Guidelines:
- 0.75 – 1.00 → high confidence;
- 0.60 – 0.74 → medium confidence
- < 0.60 → low confidence.

### Output:
Respond strictly in following JSON format by this schema:
```
{{ schema }}
```
""")

prompt: Template = Template("""Document content:
```
{{ content }}
```

Potential recipient:
- Description: {{ recipient_description }}
- Frequency: {{ recipient_freq }}
- Weighted score: {{ recipient_wscore }}
- Scores: {{ recipient_scores }}
- Importance index: {{ recipient_importance_idx }}

### Your task:
Based on the content of the document and these characteristics, determine **how likely** this person is 
to be the correct recipient. Be logical and concise.

### Output:
Respond strictly in the following JSON format by schema:
```
{{ schema }}
```
""")
