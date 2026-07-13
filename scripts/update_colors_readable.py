#!/usr/bin/env python3
"""
Update The American Express 2026 HTML to use a readable white background with black text.
Modern, clean design with green odds and color-coded historical results.
"""

html_file = "/Users/chrismiller/Documents/CosmosGolfBetting/american_express_2026.html"

with open(html_file, "r") as f:
    html_content = f.read()

# NEW COLOR SCHEME - Modern, Clean, Readable
new_css_variables = """        .cosmos-betting-preview {
            --cosmos-white: #ffffff;
            --cosmos-black: #1a1a1a;
            --cosmos-gray-light: #f5f5f5;
            --cosmos-gray-border: #e0e0e0;
            --cosmos-gray-text: #666666;
            --cosmos-green: #00a86b;
            --cosmos-green-light: #e8f5f0;
            --cosmos-green-dark: #008f5a;
            --cosmos-gold: #f4c430;
            --cosmos-red: #dc3545;
            --cosmos-blue: #0066cc;
            --cosmos-shadow: rgba(0, 0, 0, 0.1);
        }"""

# Replace old CSS variables
old_pattern = """        .cosmos-betting-preview {
            --nasa-blue: #0B3D91;
            --nasa-red: #FC3D21;
            --space-black: #0a0a0f;
            --cyber-cyan: #00d4ff;
            --grid-green: #00ff88;
            --warning-gold: #ffd700;
            --panel-bg: rgba(11, 61, 145, 0.15);
            --border-glow: rgba(0, 212, 255, 0.3);
        }"""

html_content = html_content.replace(old_pattern, new_css_variables)

# Update body/main background
html_content = html_content.replace(
    'background: var(--space-black);',
    'background: var(--cosmos-white);'
)
html_content = html_content.replace(
    'color: #e0e0e0;',
    'color: var(--cosmos-black);'
)

# Remove dark animated backgrounds
html_content = html_content.replace(
    """background:
                radial-gradient(ellipse at 20% 80%, rgba(11, 61, 145, 0.4) 0%, transparent 50%),
                radial-gradient(ellipse at 80% 20%, rgba(0, 212, 255, 0.15) 0%, transparent 40%),
                radial-gradient(ellipse at 50% 50%, rgba(252, 61, 33, 0.1) 0%, transparent 60%);""",
    'background: transparent;'
)

# Remove grid overlay (too dark on white)
html_content = html_content.replace(
    """background-image:
                linear-gradient(rgba(0, 212, 255, 0.03) 1px, transparent 1px),
                linear-gradient(90deg, rgba(0, 212, 255, 0.03) 1px, transparent 1px);
            background-size: 50px 50px;""",
    'background: transparent;'
)

# Update header
html_content = html_content.replace(
    'border-bottom: 1px solid var(--border-glow);',
    'border-bottom: 2px solid var(--cosmos-gray-border);'
)
html_content = html_content.replace(
    'background: linear-gradient(180deg, rgba(11, 61, 145, 0.2) 0%, transparent 100%);',
    'background: var(--cosmos-white);'
)

# Update h1 styling
html_content = html_content.replace(
    "color: #fff;",
    "color: var(--cosmos-black);"
)
html_content = html_content.replace(
    'text-shadow: 0 0 30px rgba(0, 212, 255, 0.5);',
    'text-shadow: none;'
)

# Update subtitle
html_content = html_content.replace(
    'color: var(--cyber-cyan);',
    'color: var(--cosmos-gray-text);'
)

# Update logo filter (remove dark mode invert)
html_content = html_content.replace(
    'filter: brightness(0) invert(1) drop-shadow(0 0 10px rgba(0, 212, 255, 0.3));',
    'filter: none;'
)

# Update event info panel
html_content = html_content.replace(
    'background: var(--panel-bg);',
    'background: var(--cosmos-gray-light);'
)
html_content = html_content.replace(
    'border: 1px solid var(--border-glow);',
    'border: 1px solid var(--cosmos-gray-border);'
)

# Update info labels
html_content = html_content.replace(
    """        .cosmos-betting-preview .info-label {
            font-family: 'Share Tech Mono', monospace;
            font-size: 11px;
            color: var(--cyber-cyan);""",
    """        .cosmos-betting-preview .info-label {
            font-family: 'Share Tech Mono', monospace;
            font-size: 11px;
            color: var(--cosmos-gray-text);"""
)

# Update info values
html_content = html_content.replace(
    """font-size: 18px;
            color: #fff;""",
    """font-size: 18px;
            color: var(--cosmos-black);"""
)

# Update crew picks
html_content = html_content.replace(
    'background: linear-gradient(135deg, rgba(11, 61, 145, 0.3) 0%, rgba(0, 212, 255, 0.15) 100%);',
    'background: var(--cosmos-gray-light);'
)
html_content = html_content.replace(
    'border: 2px solid var(--cyber-cyan);',
    'border: 2px solid var(--cosmos-green);'
)
html_content = html_content.replace(
    'box-shadow: 0 0 30px rgba(0, 212, 255, 0.4), inset 0 0 20px rgba(0, 212, 255, 0.1);',
    'box-shadow: 0 2px 8px var(--cosmos-shadow);'
)

# Update crew picks header
html_content = html_content.replace(
    """        .cosmos-betting-preview .section-header h2 {
            font-family: 'Orbitron', sans-serif;
            font-size: 20px;
            font-weight: 700;
            color: #fff;""",
    """        .cosmos-betting-preview .section-header h2 {
            font-family: 'Orbitron', sans-serif;
            font-size: 20px;
            font-weight: 700;
            color: var(--cosmos-black);"""
)

# Update section line
html_content = html_content.replace(
    'background: linear-gradient(90deg, var(--cyber-cyan) 0%, transparent 100%);',
    'background: linear-gradient(90deg, var(--cosmos-gray-border) 0%, transparent 100%);'
)

# Update crew cards
html_content = html_content.replace(
    'background: rgba(11, 61, 145, 0.15);',
    'background: var(--cosmos-white);'
)
html_content = html_content.replace(
    'border: 1px solid rgba(0, 212, 255, 0.3);',
    'border: 1px solid var(--cosmos-gray-border);'
)
html_content = html_content.replace(
    'box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);',
    'box-shadow: 0 2px 8px var(--cosmos-shadow);'
)

# Update crew name
html_content = html_content.replace(
    'text-shadow: 0 0 10px rgba(0, 212, 255, 0.5);',
    'text-shadow: none;'
)

# Update pick odds color to GREEN
html_content = html_content.replace(
    """        .cosmos-betting-preview .pick-odds {
            color: var(--grid-green);""",
    """        .cosmos-betting-preview .pick-odds {
            color: var(--cosmos-green);"""
)

# Update tabs
html_content = html_content.replace(
    'border-bottom: 2px solid rgba(0, 212, 255, 0.2);',
    'border-bottom: 2px solid var(--cosmos-gray-border);'
)

# Update tab button
html_content = html_content.replace(
    """background: rgba(11, 61, 145, 0.2);
            color: #888;
            border: 1px solid rgba(0, 212, 255, 0.2);""",
    """background: var(--cosmos-white);
            color: var(--cosmos-gray-text);
            border: 1px solid var(--cosmos-gray-border);"""
)

# Update active tab
html_content = html_content.replace(
    """background: var(--cyber-cyan);
            color: var(--space-black);""",
    """background: var(--cosmos-green);
            color: var(--cosmos-white);"""
)
html_content = html_content.replace(
    'box-shadow: 0 0 20px rgba(0, 212, 255, 0.6);',
    'box-shadow: 0 2px 8px var(--cosmos-shadow);'
)

# Update table
html_content = html_content.replace(
    'background: rgba(11, 61, 145, 0.05);',
    'background: var(--cosmos-white);'
)
html_content = html_content.replace(
    """border: 1px solid rgba(0, 212, 255, 0.2);
            border-radius: 4px;
            overflow: hidden;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);""",
    """border: 1px solid var(--cosmos-gray-border);
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 8px var(--cosmos-shadow);"""
)

# Update table header
html_content = html_content.replace(
    """background: linear-gradient(180deg, rgba(11, 61, 145, 0.4) 0%, rgba(11, 61, 145, 0.2) 100%);
            color: var(--cyber-cyan);
            border-bottom: 2px solid var(--cyber-cyan);""",
    """background: var(--cosmos-gray-light);
            color: var(--cosmos-black);
            border-bottom: 2px solid var(--cosmos-gray-border);"""
)

# Update table rows
html_content = html_content.replace(
    'border-bottom: 1px solid rgba(0, 212, 255, 0.1);',
    'border-bottom: 1px solid var(--cosmos-gray-border);'
)

# Update row hover
html_content = html_content.replace(
    'background: rgba(0, 212, 255, 0.1);',
    'background: var(--cosmos-green-light);'
)

# Update odds cells - make them GREEN
html_content = html_content.replace(
    """        .cosmos-betting-preview .odds-value {
            color: var(--grid-green);""",
    """        .cosmos-betting-preview .odds-value {
            color: var(--cosmos-green);"""
)

# Update tier badges
html_content = html_content.replace(
    'background: linear-gradient(135deg, var(--warning-gold) 0%, #ffa500 100%);',
    'background: var(--cosmos-gold);'
)
html_content = html_content.replace(
    'color: var(--space-black);',
    'color: var(--cosmos-white);'
)
html_content = html_content.replace(
    'background: linear-gradient(135deg, var(--cyber-cyan) 0%, #0099cc 100%);',
    'background: var(--cosmos-blue);'
)
html_content = html_content.replace(
    'background: linear-gradient(135deg, var(--grid-green) 0%, #00cc66 100%);',
    'background: var(--cosmos-green);'
)

# Keep historical results colors (green/yellow/red) - they're already good
# These don't need changing, they already pop

# Update legend
html_content = html_content.replace(
    """background: rgba(11, 61, 145, 0.1);
            border: 1px solid rgba(0, 212, 255, 0.2);""",
    """background: var(--cosmos-gray-light);
            border: 1px solid var(--cosmos-gray-border);"""
)

# Update footer
html_content = html_content.replace(
    """border-top: 1px solid rgba(0, 212, 255, 0.2);
            background: linear-gradient(180deg, transparent 0%, rgba(11, 61, 145, 0.2) 100%);""",
    """border-top: 2px solid var(--cosmos-gray-border);
            background: var(--cosmos-gray-light);"""
)

# Update disclaimer
html_content = html_content.replace(
    """font-size: 11px;
            color: #888;""",
    """font-size: 11px;
            color: var(--cosmos-gray-text);"""
)

# Remove scanlines effect (too dark for white background)
html_content = html_content.replace(
    '<div class="scanlines"></div>',
    ''
)

# Write updated HTML
with open(html_file, "w") as f:
    f.write(html_content)

print("✅ Updated American Express 2026 to Readable Color Scheme!")
print("")
print("NEW COLOR SCHEME:")
print("  - White background (#ffffff)")
print("  - Black text (#1a1a1a)")
print("  - Green for odds (#00a86b)")
print("  - Light gray panels (#f5f5f5)")
print("  - Clean borders (#e0e0e0)")
print("  - Historical results: kept green/yellow/red (pops!)")
print("")
print("Preview the updated page:")
print("  python3 scripts/preview_server.py")
print("  http://localhost:8000/american_express_2026.html")
