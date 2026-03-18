SVG logo variants included:

- `logo.svg` — original design (full gradient + drop shadow).
- `logo-optimized.svg` — compact/minified SVG for embedding or CDN use.
- `logo-dark.svg` — darker gradient color variant.
- `logo-mono.svg` — monochrome variant for favicons or single-color prints.

Export to PNG (local):

- Using Inkscape (recommended):
  inkscape frontend/public/logo-optimized.svg --export-type=png --export-filename=frontend/public/logo-optimized.png --export-width=512 --export-height=512

- Using CairoSVG (Python):
  pip install cairosvg
  python -c "import cairosvg; cairosvg.svg2png(url='frontend/public/logo-optimized.svg', write_to='frontend/public/logo-optimized.png', output_width=512, output_height=512)"

Optimization tips:
- The `logo-optimized.svg` is already compact. For further size reductions, run it through `svgo`.

Would you like me to generate a PNG now (requires `cairosvg` or `inkscape` available), or produce additional sizes/colors?