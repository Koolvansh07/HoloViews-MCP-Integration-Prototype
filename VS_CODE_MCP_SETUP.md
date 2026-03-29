## VS Code MCP Setup

Use a workspace MCP config that launches this server with Python:

```json
{
  "servers": {
    "holoviz-panel-mcp": {
      "type": "stdio",
      "command": "python",
      "args": ["server.py"],
      "cwd": "${workspaceFolder}"
    }
  }
}
```

## Expected Flow

1. Start the MCP server from VS Code using the config above.
2. Ask the chat agent for a structured chart such as `create_plot`.
3. Ask for an interactive app such as `interactive_sine_wave`.
4. The tool should return an MCP App payload that VS Code can render inline in chat.

## Notes

- `create_plot` and `update_plot` are for safe typed plotting from tabular data.
- `show` is for custom Panel or HoloViews code.
- `interactive_sine_wave` is the reference interactive plot demo with sliders.
- If inline rendering is blocked by the host, open the returned `/view?...` URL in a browser.
