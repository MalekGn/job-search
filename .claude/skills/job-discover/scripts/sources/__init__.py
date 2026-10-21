"""
sources — one module per job source queried by script (API or public pages).

Each module defines:
    search(r: common.SearchParams) -> dict
        {"roles": [postings in common.posting() format], "warnings": [str], ...source-specific fields}

"Web" sources (plain search queries) have no module: they are described in config/sources.json
and run by Claude.

Adding an API source: create sources/<name>.py with search(), then add an entry
{"id": "<name>", "type": "script", ...} to config/sources.json.
"""
