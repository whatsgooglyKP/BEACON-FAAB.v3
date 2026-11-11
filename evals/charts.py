"""Tiny dependency-free SVG bar charts for the report."""
from __future__ import annotations

from html import escape


def bars(path, title, items, fmt="{:.2f}", vmax=None, width=640):
    """items: list of (label, value). Writes a horizontal bar chart SVG."""
    vmax = vmax or max([v for _, v in items if v is not None] + [1e-9])
    row, left, top = 26, 230, 40
    h = top + row * len(items) + 20
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{h}" font-family="Avenir,Segoe UI,sans-serif" font-size="12">',
           f'<rect width="100%" height="100%" fill="white"/><text x="10" y="22" font-size="15" font-weight="600" fill="#1E343F">{escape(title)}</text>']
    for i, (label, v) in enumerate(items):
        y = top + i * row
        w = 0 if v is None else (width - left - 70) * v / vmax
        out.append(f'<text x="{left - 8}" y="{y + 15}" text-anchor="end" fill="#1E343F">{escape(label)}</text>')
        out.append(f'<rect x="{left}" y="{y + 3}" width="{w:.1f}" height="17" fill="#F79122" rx="3"/>')
        out.append(f'<text x="{left + w + 6:.1f}" y="{y + 15}" fill="#61747f">{"n/a" if v is None else fmt.format(v)}</text>')
    out.append("</svg>")
    path.write_text("\n".join(out))
