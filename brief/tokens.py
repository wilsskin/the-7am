"""DESIGN_SYSTEM.md tokens. The email template and charts read colors from here, never raw hex."""

SANS = "-apple-system,BlinkMacSystemFont,'SF Pro Text',system-ui,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"
MONO = "ui-monospace,'SF Mono',Menlo,Consolas,monospace"

COLORS = {
    "bg": "#F8F8F8",
    "primary": "#1D1D1F",      # apple.com text
    "secondary": "#6E6E73",
    "tertiary": "#424245",     # apple.com middle gray: icons (PNGs baked in this gray by make_icons.swift)
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

SECTION_GAP = 96      # --spacing-xxlarge
CONTENT_WIDTH = 552   # 504px reading column + 24px padding each side

# Numbers style: meta + tabular figures.
NUM = (f"font-family:{SANS};font-size:14px;line-height:19px;letter-spacing:0.01em;"
       "font-variant-numeric:tabular-nums;")
