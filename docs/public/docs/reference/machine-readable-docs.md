# Machine-readable docs (/docs/reference/machine-readable-docs)

# Machine-readable docs

## Files

| File | Contents |
| --- | --- |
| `/llms.txt` | Structured index by section |
| `/llms-full.txt` | Full authored corpus (the generated API reference is not repeated here; link to it) |
| `/docs/&lt;page&gt;.md` | Markdown/MDX content for an individual page |

```bash
# Fetch the compact section index.
curl -L https://qnbhd.github.io/agentsparty/llms.txt
# Fetch the full authored documentation corpus.
curl -L https://qnbhd.github.io/agentsparty/llms-full.txt
# Fetch one page as Markdown.
curl -L https://qnbhd.github.io/agentsparty/docs/start/quickstart.md
```

(Exact host depends on deployment `basePath`.)

## Cross-references

In authored MDX use `[[agentsparty.protocol]]` style xrefs. They resolve via
`docs/public/api-data.json`.

## Search

The site search index includes titles, headings, aliases, public symbols, error
names, glossary terms, and migration synonyms such as `handoff`, `checkpoint`,
`Crew`, and `state graph`.

