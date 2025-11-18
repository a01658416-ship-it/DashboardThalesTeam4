def theme_css(mode: str) -> str:
    """
    Returns a <style> block that:
      - Defines light and dark color tokens with CSS variables.
      - Applies to Streamlit's main area and sidebar via stable `data-testid` hooks.
      - Supports 'auto' (prefers-color-scheme), 'light', and 'dark'.
    """
    return f"""
<style>
:root {{
  --bg: #c3ecff;
  --bg-alt: #8eccf7;
  --fg: #111111;
  --muted: #475569;
  --primary: #3b82f6;
  --border: #e5e7eb;
}}

@media (prefers-reduced-motion: no-preference) {{
  [data-testid="stAppViewContainer"],
  [data-testid="stSidebar"] {{
    transition: background-color .2s ease, color .2s ease, border-color .2s ease;
  }}
}}

{("""
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #242a75;
    --bg-alt: #27badc;
    --fg: #E6E9EF;
    --muted: #a0a3ad;
    --primary: #03b3cd;
    --border: #00365b;
  }
}
""" if mode == "auto" else "")}

{("""
:root {
  --bg: #c3ecff;
  --bg-alt: #8eccf7;
  --fg: #111111;
  --muted: #475569;
  --primary: #3b82f6;
  --border: #e5e7eb;
}
""" if mode == "light" else "")}

{("""
:root {
  --bg: #c3ecff;
  --bg-alt: #8eccf7;
  --fg: #111111;
  --muted: #475569;
  --primary: #3b82f6;
  --border: #e5e7eb;
}
""" if mode == "dark" else "")}

/* Main content area */
[data-testid="stAppViewContainer"],
.block-container {{
  background-color: var(--bg);
  color: var(--fg);
}}

a, .stMarkdown a {{
  color: var(--primary);
}}

div[data-baseweb="input"] input,
textarea, .stTextInput input, .stNumberInput input, .stTextArea textarea,
.stSelectbox div[role="combobox"], .stMultiSelect div[role="combobox"] {{
  background-color: var(--bg-alt) !important;
  color: var(--fg) !important;
  border: 1px solid var(--border) !important;
}}

.stButton > button, .stDownloadButton > button {{
  background-color: #bce4ff !important;
  color: #111111 !important;
  border: 1px solid #a5d9ff !important;
  border-radius: 5px;
  font-weight: bold;
}}

.stButton > button:hover,
[data-testid="stSidebar"] .stButton > button:hover {{
  background-color: #bce4ff !important;
  border-color: #a5d9ff  !important;
}}

hr {{
  border-color: var(--border);
}}

/* Sidebar styling */
[data-testid="stSidebar"] {{
  background-color: var(--bg-alt);
  border-right: 1px solid var(--border);
  color: var(--fg);
}}

[data-testid="stSidebar"] * {{
  color: var(--fg) !important;
}}

[data-testid="stSidebar"] a {{
  color: var(--primary) !important;
}}

[data-testid="stSidebar"] .stTextInput input,
[data-testid="stSidebar"] textarea,
[data-testid="stSidebar"] .stSelectbox div[role="combobox"],
[data-testid="stSidebar"] .stMultiSelect div[role="combobox"],
[data-testid="stSidebar"] .stNumberInput input {{
  background-color: var(--bg) !important;
  color: var(--fg) !important;
  border: 1px solid var(--border) !important;
}}

[data-testid="stSidebar"] .stButton > button,
[data-testid="stSidebar"] .stDownloadButton > button {{
  background-color: #8ac0ce !important;
  color: #111111 !important;
  border: 1px solid #03b3cd !important;
  border-radius: 5px;
  font-weight: bold;
}}

[data-testid="stSidebar"] label,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {{
  color: var(--fg) !important;
}}

[data-testid="stSidebar"] .stRadio [role="radiogroup"] > div[aria-checked="true"] label span {{
  font-weight: 600;
}}
</style>
"""