# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Python toolset for INNOVA's photographic backgrounds (fondos) sublimation workflow. Processes large-format JPG/PNG images intended for printing on 160cm-wide fabric rolls, then generates labeling and sewing-cost documents.

## Running the Tools

Each tool has a Windows batch entry point and a Python script for CLI use:

**Cortador** (main entry point — chains to etiquetador automatically):
```
python cortador/cortador_innova.py [carpeta] [--margen 0.45] [--ancho-rollo 160] [--umbral 30] [--calidad 97]
```

**Etiquetador** (chains to costura automatically):
```
python etiquetador/generar_lista_etiquetado.py <ruta/cortados> [--cierre 2026-06-15] [--sin-pausa]
```

**Costura** (standalone or called from etiquetador):
```
python costura/generar_costura.py [carpeta_cortados] [--cierre 2026-06-15] [--sin-pausa]
```

**Dependencies:** `pip install Pillow reportlab`

## Architecture

Three tools that run sequentially (each auto-chains to the next):

```
cortador_innova.py
  → reads JPGs from input folder
  → moves originals to originales/
  → writes cut panels to cortados/   (with CODxxx badge stamped)
  → auto-calls generar_lista_etiquetado.py

generar_lista_etiquetado.py
  → reads cortados/
  → writes to etiquetados/:
      lista_etiquetado_<cierre>.json
      tabla_<cierre>.pdf  (checklist with thumbnails)
      etiquetas_<cierre>.pdf  (50×50mm labels for DT01/WePrint)
  → auto-calls generar_costura.py (via importlib, not subprocess)

generar_costura.py
  → reads cortados/
  → writes costura/<cierre>.pdf  (pricing table)
```

**Expected output folder layout:**
```
/Fondos semana/
  originales/     ← original JPGs moved here
  cortados/       ← cut panels with code badge
  etiquetados/    ← JSON + tabla.pdf + etiquetas.pdf
  costura/        ← costura_<fecha>.pdf
```

## Key Domain Logic

**Cutting decision** (`cortador_innova.py → evaluar_corte`):
- If either dimension ≤ 160cm → no cut needed, just stamp the code
- If both dimensions > 160cm → must cut in half (vertical or horizontal)
- Prefer vertical cut unless it wastes >30cm more than horizontal
- If a cut would produce a panel still wider than 160cm → error, manual handling required

**Code stamping**: Every design gets a sequential `CODxxx` badge (white pill, rotated 90°, placed 160px from the top-right edge to avoid the seam). On cut designs, only the first panel (LEFT for vertical cuts, TOP for horizontal) gets the visual badge; both panels get the code in their filename.

**Filename convention** (required by etiquetador and costura for parsing):
```
COD001 - NombreCliente - ANCHOxALTO - Observacion.jpg
```
The `MED_RE` regex extracts `WxH` dimensions; `COD_RE` extracts the code number.

**Sewing pricing** (`costura/generar_costura.py`):
- 1 panel (fits roll): $2,180
- 2-panel union ≤ 450cm: $4,350
- 2-panel union > 450cm: $6,950
- Neoprene (detected from filename): $2,350
- Viáticos: $5,000 fixed per batch
- Total rounded up to nearest $1,000

Files containing "neoprene"/"neopreno" in their name are treated as flat-price neoprene; files containing "funda" are detected as a special type (currently no special pricing).

## Post-run Workflow

After a full run, the `etiquetados/lista_etiquetado_<cierre>.json` is meant to be uploaded to Google Drive for use on the physical labeling day (the script reminds you of this at the end of its run).

## Embedded Assets

`etiquetador/generar_lista_etiquetado.py` has `LOGO_B64` and `QR_B64` embedded as base64 strings — these are used in both the tabla PDF and the 50×50mm label pages.

`costura/generar_costura.py` has `LOGO_B64 = ""` — copy the `LOGO_B64` variable from the etiquetador script to enable the logo in the costura PDF.
