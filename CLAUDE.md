# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Internal tooling for **INNOVA** (innova54.com), a photographic-backdrop business in
Argentina. Three standalone Python scripts turn a folder of weekly backdrop designs
into print-ready panels plus the paperwork that goes with them (labeling checklist,
50x50mm labels, sewing quote), and one single-file web app drives the physical
labeling day.

Not a package — no `setup.py`, no `requirements.txt`, no tests. Each script is a
single file paired with a `.bat` launcher that non-technical staff double-click on
Windows. **Console output and all user-facing text is in Spanish.**

## The pipeline

The three scripts chain automatically; the operator only ever runs the first one.

```
cortador/cortador_innova.py            (CORTAR_FONDOS.bat)
  └─ subprocess → etiquetador/generar_lista_etiquetado.py  --cierre <hoy> --sin-pausa
       └─ importlib → costura/generar_costura.py  cotizar() then generar_pdf_costura()

index.html                             (opened by hand on labeling day)
  └─ imports etiquetados/lista_etiquetado_<cierre>.json
```

1. **cortador** — reads JPG/PNG from a folder, moves them into `originales/`,
   decides whether each design fits the 160cm fabric roll, splits it into two
   panels if not, burns a `CODnnn` badge into the image, writes to `cortados/`,
   and reports linear meters of fabric split into polyester and neoprene.
2. **etiquetador** — parses filenames in `cortados/`, writes `etiquetados/` with a
   JSON package (consumed by `index.html`), a printable A4 checklist PDF with
   thumbnails, and one 50x50mm label page per design for the WePrint DT01 printer.
   It also owns the run's closing report: it calls costura's `cotizar()` *before*
   building the checklist, because the "resumen de producción" (polyester m,
   neoprene m, sublimation m = both, sewing total $) heads its first page and is the
   last thing printed to the console, under one-word `finalizado`/`error` statuses
   for ETIQUETADO and COSTURA. Per-design `[ok]` lines are intentionally gone;
   `[omitido]`/`[aviso]`/`[ERROR]` lines stay.
3. **costura** — from the same `cortados/` folder, prices the sewing work per
   design against a fixed tariff table and emits `costura/costura_<cierre>.pdf`.
4. **index.html** — see *The labeling web app* below.

### Folder layout the pipeline produces

```
/Fondos semana/
  originales/     originals, moved (not copied) out of the root
  cortados/       processed panels, "COD001 - <original name>.jpg"
                  + medidas_reales.json (real cm, panos, corte, tela,
                    metros_lineales per design; read by costura and etiquetador)
  etiquetados/    lista_etiquetado_<cierre>.json, tabla_<cierre>.pdf, etiquetas_<cierre>.pdf
  costura/        costura_<cierre>.pdf
```

**Memory is the binding constraint.** These are 200–1150 MP files; a 417 MB CMYK
backdrop peaks around 7 GB of RAM. `procesar_imagen` crops, badges, saves and frees
one panel at a time, and `grabar_codigo(..., copiar=False)` mutates a crop the caller
already owns. Holding both panels at once, or reinstating a defensive `.copy()`,
pushed the same file to 10–11 GB. Measure before changing this path.

`cierre` is the batch/closing identifier — an ISO date by default, slugified into
filenames via `re.sub(r"[^\w\-]+", "-", cierre)`. The chained run always passes
today's date; `cortador` has no `--cierre` flag of its own.

## Running

```bash
# full pipeline (etiquetador + costura fire automatically at the end)
python cortador/cortador_innova.py "C:\ruta\Fondos semana"
python cortador/cortador_innova.py "C:\ruta" --margen 0.50 --ancho-rollo 155
python cortador/cortador_innova.py "C:\ruta" --salida "D:\otra\carpeta"

# individual stages, pointed at cortados/
python etiquetador/generar_lista_etiquetado.py "C:\ruta\cortados" --cierre 2026-05-30
python costura/generar_costura.py "C:\ruta\cortados"
```

`cortador` flags: `--margen` 0.45, `--ancho-rollo` 160, `--umbral` 30,
`--calidad` 100, `--salida` (default: `cortados/` inside the input folder).
The other two take only `--cierre` and `--sin-pausa`.

Dependencies are `Pillow` and `reportlab`. The system Python 3.14 here has Pillow
but **not** reportlab — test the chained stages from a throwaway venv in the
scratchpad rather than installing into the user's Python. `obtener_dpi` ignores DPI
tags outside 50–1200, so synthetic test images need e.g. 60 DPI. The `.bat` launchers are inconsistent about installing
them: `GENERAR_LISTA_ETIQUETADO.bat` installs both, `CORTAR_FONDOS.bat` installs only
Pillow (so the chained etiquetador fails on a machine without reportlab), and
`GENERAR_COSTURA.bat` installs nothing and takes no argument — it expects a
`cortados/` folder next to itself.

There are no sample images in the repo. `Prueba imagenes/` (RGB and CMYK-FLUO test
backdrops) is gitignored and lives outside the checkout when present; `*.jpg` is
ignored globally anyway.

## Domain rules

These constants encode real production constraints. Changing them changes what gets
printed and billed — confirm before touching.

- **Roll**: 160cm wide (`ANCHO_ROLLO_CM`, `ROLL_MAX_CM`). A design needs no cut if
  *either* side is <= 160cm; panels stack in a column for calender sublimation.
- **Seam allowance**: 0.45cm per side of the cut (`MARGEN_CM`), so the two panels
  overlap by 0.9cm and the sewing machine consumes it.
- **Cut axis**: when both axes yield panels that fit, prefer vertical (less visible
  seam) unless horizontal saves more than `UMBRAL_DESPERDICIO` = 30cm of fabric.
  When neither axis fits, the design is flagged as an error needing manual handling.
- **Forced axis by filename**: "horizontal" or "vertical" in the name (`corte_pedido`)
  skips the no-cut branch and *always* cuts on that axis, even if the design fits
  the roll; if the forced panels do not fit, it is an ERROR. Both words → warning,
  normal logic. This is an extra branch; the automatic logic above is unchanged.
- **Neoprene** ("neoprene"/"neopreno", `es_neoprene`): no badge burned on any panel,
  but the `CODnnn - ` filename prefix stays (every downstream stage keys on it).
  Its meters count as neoprene fabric; everything else is polyester.
- **Sewing tariffs** (`costura/generar_costura.py`, marked "Marzo 2026"): 2180 one
  panel / 4350 join <= 450cm (`UNION_THRESHOLD_CM`) / 6950 join > 450cm / 2350
  neoprene, plus 5000 fixed viáticos, total rounded up to the next 1000.
  "neoprene"/"neopreno" in a filename selects the neoprene price. `detectar_especial`
  also recognizes "funda", but a funda has no tariff of its own (confirmed by the
  owner) and is priced like any other design — that is intended, not a gap.
- **DPI**: read from image metadata. `obtener_dpi` returns `(dpi, del_metadato)`;
  when the tag is missing it falls back to 150 **and the caller must warn** — the
  designers' Photoshop/Illustrator exports always carry it, so an absent tag means
  the file came from somewhere else and every cm measurement is wrong (a 254dpi
  file read as 150 measures 69% too large and gets flagged as a manual case).
- **Real measurements beat the filename.** Every backdrop carries an extra ~15cm at
  the top for the pocket that holds it on the stand, and the client's filename does
  not include it. `cortador` measures from pixels and writes
  `cortados/medidas_reales.json` (`escribir_manifiesto`); `costura` reads it
  (`leer_medidas_reales`) and prices from those cm, falling back to the filename
  only when the manifest is absent. Do not "fix" costura back to the filename.
- **JPEG output**: `quality=100`, `subsampling=0`, all metadata re-injected.
  `optimize=True` only under `MAX_PX_OPTIMIZE` (80 MP) — above it libjpeg must
  buffer every DCT coefficient (~3.2 GB on a 530 MP panel) on top of the already
  decoded source and raises `MemoryError`. Measured, not theoretical.
- **`cortador` must never convert color spaces.** Output goes to a plotter and is
  calender-sublimated onto polyester; sRGB must never enter the pipeline. Two
  invariants hold together, and both are load-bearing:
  1. All metadata is carried through byte-for-byte by `leer_metadatos` →
     `_guardar`: ICC profile, EXIF, Adobe XMP, and the Photoshop/IPTC APP13 block
     (the last one has no Pillow kwarg — it is rebuilt as a raw segment and passed
     through `extra=`). Read it from the opened file *before* cropping; crops do
     not carry the raw JPEG segments.
  2. The **image mode** is preserved: CMYK saves as CMYK, RGB as RGB, L as L. The
     only conversions left are format constraints — palette→RGB, and alpha→RGB for
     JPEG. Adding a `.convert("RGB")` anywhere in `grabar_codigo` or `_guardar`
     reintroduces a real production bug: Pillow's naive conversion ignores the
     profile, so a CMYK original came out with RGB pixels still tagged with its
     CMYK profile, which is what caused the strong color shift operators saw.
  Because of this, `grabar_codigo` composites the badge through **greyscale masks**
  rather than an RGBA overlay, and `_colores_badge` expresses white and black in
  each mode directly — in CMYK the text is pure K, since naive black would be
  300%-ink registration black.
- `Image.MAX_IMAGE_PIXELS = None` is set deliberately: large-format backdrops exceed
  Pillow's decompression-bomb limit.

`costura` prices from the cut `cortador` actually made — `panos`/`corte` in the
manifest (`calcular_costura_real`); the join runs along `alto` for VERTICAL and
`ancho` for HORIZONTAL. Only without a manifest does it fall back to re-deriving the
cut from the filename (`calcular_costura`: no seam margin, no `UMBRAL_DESPERDICIO`,
no forced axis), which can disagree with what `cortador` did.

## Filename contract

`cortados/` filenames are the interface between the stages — there is no database.
Every consumer re-parses them with its own near-duplicate regexes (`COD_RE`,
`MED_RE`): `etiquetador`, `costura`, and `index.html`. The Python `parse_name` in
`etiquetador` is a line-by-line port of `parseName` in `index.html`; fix a parsing
bug in one and check the other two. Both strip the cortador's `_IZQUIERDO`/
`_DERECHO`/`_SUPERIOR`/`_INFERIOR` suffix from the observation separately
(`PANO_RE`), because `_` is a word character and `SUF_RE`'s `` never matches it.

```
COD001 - Cliente Nombre - 290x200 - Observacion.jpg
COD002 - Maria Soledad - 500x290_IZQUIERDO.jpg
COD002 - Maria Soledad - 500x290_DERECHO.jpg
```

Measurements come from the **client's original filename**, not from the pixels —
`etiquetador` and `costura` trust the `<ancho>x<alto>` text, while `cortador` measures
in cm from pixels and DPI. A file with no recognizable measurement is skipped by both
downstream scripts.

Both downstream scripts deduplicate the two panels of a cut design: `etiquetador` by
code, `costura` by code + measurement.

## The labeling web app (`index.html`)

A single self-contained page (~550KB, jsPDF vendored inline, no build step, no
network beyond Google Fonts) — open it directly in a browser. It is what the operator
uses on labeling day.

- Loads either a `lista_etiquetado_<cierre>.json` (Importar) or a dropped folder of
  images it parses client-side.
- Tracks pendiente/impreso per design in `localStorage` under
  `innova_estado::<cierre>::<codigoNum>`, plus `innova_cierre` for the current batch.
- Reprints 50x50mm labels on demand via jsPDF, so a single label can be redone
  without regenerating the whole `etiquetas_<cierre>.pdf`.

The JSON is the contract between Python and this page, versioned by the
`innova_etiquetado: 2` key:

```json
{"innova_etiquetado": 2, "cierre": "...", "generado": "...",
 "designs": [{"codigo": "Cod.0001", "codigoNum": 1, "cliente": "...",
              "medida": "290x200", "observacion": "", "img": "<base64 thumb>"}],
 "estados": {}}
```

`importPackage` rejects anything without `innova_etiquetado` and a `designs` array.
Changing the shape means changing `generar_lista_etiquetado.py` and this page
together, and bumping the version key.

## Gotchas

- **`*.json` and `*.jpg` are gitignored globally**, so `medidas_reales.json`,
  `lista_etiquetado_*.json` and any test image never show up in `git status`.
- **The code counter is persistent**, stored in `cortador/ultimo_codigo.txt` next to
  the script. `main()` prompts for a starting code (blank = last + 1). The file is
  **tracked**, so every real run leaves it modified in the working tree — don't
  commit a counter bump by accident.
- **The badge lands on the second panel for vertical cuts** (`DERECHO`), on the first
  for horizontal (`SUPERIOR`) — see `pano_badge` in `procesar_imagen`. Neoprene gets
  none.
- The badge is drawn rotated 90° counter-clockwise with a **fixed printed size in
  cm** (`BADGE_LETRA_CM` 0.8, `BADGE_LARGO_MAX_CM` 4.0, `BADGE_MARGEN_CM` 0.5),
  converted to px with the file's DPI — `grabar_codigo` takes `dpi`. It must fit in
  the top pocket, which is 5cm on the smallest backdrops (7.5cm otherwise), so
  margin + length stays <= 4.5cm; long codes shrink the font to fit. It used to be a
  fixed 56px, which printed ~7.7cm long on a 72dpi file and overflowed the pocket.
- **Docs are split by audience.** `README.md` is the technical reference;
  `INSTRUCCIONES.md` is the single operator manual for the whole weekly flow
  (Spanish, non-technical), and `INSTRUCCIONES.html` is a hand-maintained twin of it
  — keep the two in sync. Behavior they describe (counter, badge placement, real
  measurements, tariffs, flag defaults, console messages like `[omitido]`) also
  appears in the module docstring of `cortador_innova.py`. When changing any of it,
  update all of them together.
- **`cortador` moves originals with `os.replace`** — it empties the input folder's
  root into `originales/`. Point it at a copy when experimenting.
- **Chaining lookups.** `cortador` finds the etiquetador next to itself *or* at
  `../etiquetador/`; `_cargar_costura` in the etiquetador does the same for
  `generar_costura.py`, so both the repo layout and the flattened folder handed to
  staff work. Costura failures are caught and reported as `COSTURA: error`.
- `generar_pdf_costura` no longer prints its console box; `imprimir_detalle` does,
  and only in costura's own manual `main()`.
- `etiquetador/generar_lista_etiquetado.py` is ~176KB because `LOGO_B64` and `QR_B64`
  are inline base64 PNGs on two single lines (161: 63KB, 162: 98KB). Never `cat` it
  whole; use `sed -n` on line ranges, and skip those two lines (find them with
  `awk 'length($0)>10000{print NR}'` if they move again).
- `costura/generar_costura.py` has its own empty `LOGO_B64 = ""` and prints no logo.
  Its comment asks for the blob to be pasted over from the etiquetador.
- Both PDF generators define their own `CheckBox` flowable, brand palette, and page
  header/footer. They have drifted apart (different color schemes); a change to one
  does not propagate.
- Failures are handled by printing a Spanish `[ERROR]`/`[aviso]` line and continuing.
  Keep that style — the operator sees only the console window.
- `--sin-pausa` suppresses the trailing `input("Enter para salir...")`; the automatic
  chained calls pass it, manual runs do not.

## Conventions

- Python 2-era string formatting (`%`) in `etiquetador`/`costura`, f-strings in
  `cortador`. Match the file you are editing.
- `cortador_innova.py` avoids non-ASCII entirely (no accents) so it survives cp1252
  Windows consoles; the other two use UTF-8 with escaped literals (`\u00f1`) and
  their `.bat` files set `chcp 65001`.
- Section headers are box-drawing rules (`# ═══ SECCIÓN ═══`, `# --- ... ---`).
- Identifiers and comments are Spanish (`pano`, `cortar_horizontal`, `carpeta_salida`).
