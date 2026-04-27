# Knowledge Base

## Structure
- `knowledge_base/`
  - `background/`: organization background
  - `user_context/`: user profiles
  - `domain_knowledge/`: domain knowledge
  - `knowledge_config.json`: category and scan config
  - `.state/`: index and version state (auto-generated)

## Usage
1. Add or update `.md` files under `knowledge_base`.
2. Call `/knowledge/refresh` or wait for the scheduled refresh.
3. Knowledge snippets are injected before each chat or retrieved via `/knowledge/search`.

## Configuration
Example `knowledge_config.json`:

```json
{
  "root_dir": "knowledge_base",
  "refresh_minutes": 30,
  "max_excerpt_chars": 1200,
  "cache_ttl_seconds": 1800,
  "source_type": "file",
  "categories": [
    {"name": "background", "description": "Organization background", "enabled": true, "file_glob": "**/*.md"},
    {"name": "user_context", "description": "User profiles", "enabled": true, "file_glob": "**/*.md"},
    {"name": "domain_knowledge", "description": "Domain knowledge", "enabled": true, "file_glob": "**/*.md"}
  ]
}
```
