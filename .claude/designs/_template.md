---
type: feature | model | service | tool | refactor
name: descriptive-kebab-case-name
step: 1
status: draft | in-progress | done | abandoned
depends_on: []   # list names from other design docs, e.g. [wiki-entry-model]
---

# [Name]

## Purpose
One sentence. What does this module/feature do and why does it exist?

## Problem
What gap does this fill? What breaks or is missing without it?

## Public API
List every public function, class, and method with full type signatures.
No implementation — signatures and intent only.
All paths are repo-relative.

```python
# Example
def fetch_entry(title: str, max_tokens: int = 512) -> WikiEntry: ...
```

## Data Models
Pydantic models or dataclasses that this module owns or introduces.

```python
# Example
class WikiEntry(BaseModel):
    title: str
    body: str
    updated_at: datetime
```

## Data Flow
How data moves through this module. Input → processing → output.

## Dependencies
- **Internal**: other modules in this repo (repo-relative paths)
- **External**: third-party libraries

## Test Scenarios
Real-world scenarios only. Format: [ID] Given / When / Then

- **T1** — Given ..., when ..., then ...
- **T2** — Given ..., when ..., then ...

## Error Cases
| Error | Trigger | Handling |
|---|---|---|

## Out of Scope
What this module does NOT do.

## Open Questions
- [ ] Unresolved decisions go here.
