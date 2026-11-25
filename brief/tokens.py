"""DESIGN_SYSTEM.md tokens as one Python dict. Templates read from here, never raw hex.

Ported from build_reference.py (T, SANS, MONO, NUM, SECTION_GAP).
"""

SANS = "-apple-system,BlinkMacSystemFont,'SF Pro Text',system-ui,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"
MONO = "ui-monospace,'SF Mono',Menlo,Consolas,monospace"

COLORS = {
    "bg": "#F8F8F8",
    "primary": "#1D1D1F",      # apple.com text
    "secondary": "#6E6E73",
    "tertiary": "#424245",     # apple.com middle gray: icons
    "surface": "#F0F0F0",
    "subtle": "#EBEBEB",
    "theme": "#0079AF",
    "theme_tint": "#D3E5ED",
    "theme_line": "#7CB9D4",
    "up": "#1B7A5E",
    "down": "#C03A3A",
    "mta_45": "#00933C",
    "link": "#007AFF",      # Apple systemBlue: every external link, and the weather low
    "hi": "#FF3B30",        # Apple systemRed: the weather high
    "lo": "#007AFF",
}

# Icons are PNGs baked in this gray (templates/icons/make_icons.swift), so it has no dark variant.
ICON_GRAY = "#424245"   # = COLORS["tertiary"]

# Apple Mail dark mode (the @media (prefers-color-scheme: dark) block).
DARK = {
    "bg": "#0B0B0B",
    "primary": "#F2F2F2",
    "secondary": "#9A9A9A",
    "tertiary": "#C7C7CC",
    "surface": "#1A1A1A",
    "subtle": "#2A2A2A",
    "theme": "#4FB3E3",
    "theme_tint": "#0F2A38",
    "theme_line": "#1F5E7D",
    "up": "#3DD6A8",
    "down": "#FF6B6B",
    "mta_45": "#00933C",
    "link": "#0A84FF",
    "hi": "#FF453A",
    "lo": "#0A84FF",
}

SPACING = {"unit": 8, "xsmall": 16, "small": 24, "medium": 32, "xxlarge": 96}
SECTION_GAP = SPACING["xxlarge"]
SIDE_PADDING = 24
SIDE_PADDING_MOBILE = 16
RADIUS = {"sm": 4, "md": 8, "lg": 16}
CONTENT_WIDTH = 552   # 504px reading column + 24px padding each side

# Numbers style: meta + tabular figures.
NUM = (f"font-family:{SANS};font-size:14px;line-height:19px;letter-spacing:0.01em;"
       "font-variant-numeric:tabular-nums;")

TOKENS = {
    "sans": SANS, "mono": MONO, "colors": COLORS, "dark": DARK, "spacing": SPACING,
    "section_gap": SECTION_GAP, "radius": RADIUS, "content_width": CONTENT_WIDTH, "num": NUM,
}
