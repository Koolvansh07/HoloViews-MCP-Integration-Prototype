## Setup

```bash
pip install -r requirements.txt
```

## VS Code MCP Setup

If you want the true inline chat experience in VS Code, follow:

[VS_CODE_MCP_SETUP.md](c:/Users/koolv/GSOC/Holoviz%20Panel%20MCP/VS_CODE_MCP_SETUP.md)

## Run As An MCP Server

```bash
python server.py
```

This server now builds on `panel-live-server`, so compatible MCP clients can render
`create_plot` and `update_plot` inline in the chat pane instead of only returning a URL.
For reliability, the structured tools use a lightweight HoloViews rendering path for single plots.

## Run The Local Demo

```bash
python test_local.py
```

This simulates MCP tool calls locally, prints the returned payload, and opens the fallback
browser URLs. Inline rendering only happens inside a compatible MCP client UI.
Keep the terminal open while viewing the demo. The `/feed` endpoint is not the visualization;
open the returned `/view?id=...` URL instead.

## Testing Example

Example `create_plot` input:

```json
{
  "data": [
    {"week": 1, "sales": 120},
    {"week": 2, "sales": 135},
    {"week": 3, "sales": 128},
    {"week": 4, "sales": 150},
    {"week": 5, "sales": 162}
  ],
  "plot_type": "scatter",
  "x": "week",
  "y": "sales"
}
```

Example `update_plot` input:

```json
{
  "plot_id": "<returned plot_id>",
  "data": [
    {"week": 1, "sales": 120},
    {"week": 2, "sales": 135},
    {"week": 3, "sales": 128},
    {"week": 4, "sales": 150},
    {"week": 5, "sales": 162},
    {"week": 6, "sales": 174},
    {"week": 7, "sales": 181}
  ],
  "plot_type": "line"
}
```

When you run `python test_local.py`, it uses this exact scenario and prints the MCP payloads
returned by both tools.

## Structured Plot Tools

- `create_plot`
- `update_plot`
- `list_plot_types`

## Inherited panel-live-server Tools

- `show`
- `validate`
- `list_packages`

## Supported Plot Types

- `scatter`
- `line`
- `bar`
