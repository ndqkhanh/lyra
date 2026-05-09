# Lyra — Reference papers (PDF mirror)

This directory holds 22 arxiv PDFs (~145 MB) that inform Lyra's
design — Waves 1–3 are mirrored locally; Wave 4 (PolyKV
[2604.24971](https://arxiv.org/abs/2604.24971), CALM
[2604.24026](https://arxiv.org/abs/2604.24026)) is referenced but
not yet mirrored as binary; pull them with the reproducer script in
[`docs/research/papers.md`](../docs/research/papers.md). The PDFs
are kept as binary assets here; the **annotated bibliography**,
**per-paper citations**, **suggested reading order**, and
**reproducer download script** all live with the rest of the
documentation:

> **→ [docs/research/papers.md](../docs/research/papers.md)**

Why the split:

- PDFs are large binary; they don't belong in the markdown source
  tree that MkDocs walks.
- The bibliography is prose — it's better served searchable, dark-
  mode-aware, and cross-linked from the rest of the docs site.

The files in this directory are intentionally listed there, not
duplicated here, so there's exactly **one** source of truth for
"which papers does Lyra read?".

If you only want a quick look at what's in this directory:

```bash
ls papers/*.pdf
```

For everything else (annotated bibliography, reading order, paper
analyses, reproducer download script, citation conventions),
follow [`docs/research/papers.md`](../docs/research/papers.md).
