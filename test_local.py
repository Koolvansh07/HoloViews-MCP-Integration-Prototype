from __future__ import annotations

from pathlib import Path
import webbrowser

from viz import render_plot


sample_data = [
    {"student": 1, "score": 65},
    {"student": 2, "score": 72},
    {"student": 3, "score": 68},
    {"student": 4, "score": 80},
    {"student": 5, "score": 77},
]


def main() -> None:
    html = render_plot(
        data=sample_data,
        plot_type="scatter",
        x="student",
        y="score",
    )

    output_path = Path("output.html")
    output_path.write_text(html, encoding="utf-8")

    print(f"Saved plot to {output_path.resolve()}")
    webbrowser.open(output_path.resolve().as_uri())


if __name__ == "__main__":
    main()
