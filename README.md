# HoloViz Panel MCP

Minimal prototype for generating interactive HoloViews/Panel plots from structured data through an MCP server.

## Setup

```bash
pip install -r requirements.txt
```

## Run the MCP server

```bash
python server.py
```

## Run the local demo

```bash
python test_local.py
```

This writes an interactive plot to `output.html` and opens it in your browser.

## Supported plot types

- `scatter`
- `line`
- `bar`
