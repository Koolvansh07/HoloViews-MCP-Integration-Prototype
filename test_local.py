from __future__ import annotations

import asyncio
import json
import webbrowser

from fastmcp.client import Client

from server import mcp


initial_data = [
    {"week": 1, "sales": 120},
    {"week": 2, "sales": 135},
    {"week": 3, "sales": 128},
    {"week": 4, "sales": 150},
    {"week": 5, "sales": 162},
]

updated_data = [
    {"week": 1, "sales": 120},
    {"week": 2, "sales": 135},
    {"week": 3, "sales": 128},
    {"week": 4, "sales": 150},
    {"week": 5, "sales": 162},
    {"week": 6, "sales": 174},
    {"week": 7, "sales": 181},
]

create_example = {
    "data": initial_data,
    "plot_type": "scatter",
    "x": "week",
    "y": "sales",
}

update_example = {
    "data": updated_data,
    "plot_type": "line",
}

sine_wave_example = {
    "amplitude": 1.5,
    "frequency": 1.2,
    "phase": 0.4,
}


async def main() -> None:
    async with Client(mcp) as client:
        plot_types_result = await client.call_tool("list_plot_types", {})
        plot_types = json.loads(plot_types_result.content[0].text)
        print("Supported structured plot types:", ", ".join(plot_types))
        print()

        print("create_plot example input:")
        print(json.dumps(create_example, indent=2))
        print()

        create_result = await client.call_tool(
            "create_plot",
            create_example,
        )
        create_payload = json.loads(create_result.content[0].text)
        print("create_plot returned:")
        print(json.dumps(create_payload, indent=2))
        print(f"Fallback browser URL: {create_payload['url']}")
        webbrowser.open(create_payload["url"])

        await asyncio.sleep(5)

        print()
        print("update_plot example input:")
        print(
            json.dumps(
                {
                    "plot_id": create_payload["plot_id"],
                    **update_example,
                },
                indent=2,
            )
        )
        print()

        update_result = await client.call_tool(
            "update_plot",
            {
                "plot_id": create_payload["plot_id"],
                **update_example,
            },
        )
        update_payload = json.loads(update_result.content[0].text)
        print("update_plot returned:")
        print(json.dumps(update_payload, indent=2))
        print(f"Updated fallback browser URL: {update_payload['url']}")
        webbrowser.open(update_payload["url"])

        print()
        print("interactive_sine_wave example input:")
        print(json.dumps(sine_wave_example, indent=2))
        print()

        sine_result = await client.call_tool(
            "interactive_sine_wave",
            sine_wave_example,
        )
        sine_payload = json.loads(sine_result.content[0].text)
        print("interactive_sine_wave returned:")
        print(json.dumps(sine_payload, indent=2))
        print(f"Interactive app fallback browser URL: {sine_payload['url']}")
        webbrowser.open(sine_payload["url"])

        print()
        print("Keep this terminal open while viewing the browser demo.")
        print("Use the returned /view URL, not /feed.")
        await asyncio.to_thread(input, "Press Enter to stop the local demo...")


if __name__ == "__main__":
    asyncio.run(main())
