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
       └─ importlib → costura/generar_costura.py  generar_pdf_costura()

index.html                             (opened by hand on labeling day)
  └─ imports etiquetados/lista_etiquetado_<cierre>.json
```

1. **cortador** — reads JPG/PNG from a folder, moves them into `originales/`,
   decides whether each design fits the 160cm fabric roll, splits it into two
   panels if not, burns a `CODnnn` badge into the image, writes to `cortados/`,
   and reports total linear meters of fabric.
2. **etiquetador** — parses filenames in `cortados/`, writes `etiquetados/` with a
   JSON package (consumed by `index.html`), a printable A4 checklist PDF with
   thumbnails, and one 50x50mm label page per design for the WePrint DT01 printer.
3. **costura** — from the same `cortados/` folder, prices the sewing work per
   design against a fixed tariff table and emits `costura/costura_<cierre>.pdf`.
4. **index.html** — see *The labeling web app* below.

### Folder layout the pipeline produces

```
/Fondos semana/
  originales/     originals, moved (not copied) out of the root
  cortados/       processed panels, "COD001 - <original name>.jpg"
                  + medidas_reales.json (real cm per design, read by costura)
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
`--calidad` 97, `--salida` (default: `cortados/` inside the input folder).
The other two take only `--cierre` and `--sin-pausa`.

Dependencies are `Pillow` and `reportlab`; the `.bat` files `pip install` them on
demand. Both are already installed in this environment (Python 3.14).

`Prueba imagenes/` holds sample backdrops (RGB and CMYK-FLUO) for manual testing —
note the folder is doubly nested (`Prueba imagenes/Prueba imagenes/...`).

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
- **Sewing tariffs** (`costura/generar_costura.py`, marked "Marzo 2026"): 2180 one
  panel / 4350 join <= 450cm (`UNION_THRESHOLD_CM`) / 6950 join > 450cm / 2350
  neoprene, plus 5000 fixed viáticos, total rounded up to the next 1000.
  "neoprene"/"neopreno" and "funda" in a filename select special handling.
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

`costura` re-derives the cut decision itself from the filename measurements
(`calcular_costura`), *without* the seam margin or the `UMBRAL_DESPERDICIO`
heuristic — it just halves each side and prefers vertical. It can therefore disagree
with what `cortador` actually did. Keep the two in sync by hand when changing either.

## Filename contract

`cortados/` filenames are the interface between the stages — there is no database.
Every consumer re-parses them with its own near-duplicate regexes (`COD_RE`,
`MED_RE`): `etiquetador`, `costura`, and `index.html`. The Python `parse_name` in
`etiquetador` is a line-by-line port of `parseName` in `index.html`; fix a parsing
bug in one and check the other two.

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

- **`costura/` is gitignored** (the rule was meant for the generated output folder),
  so `costura/generar_costura.py` and `costura/GENERAR_COSTURA.bat` are **untracked**
  — edits there are invisible to `git status` and absent from a fresh clone. `*.json`
  is ignored globally too. Use `git add -f` if these should be committed.
- **The code counter is persistent**, stored in `cortador/ultimo_codigo.txt` next to
  the script. `main()` prompts for a starting code (blank = last + 1). That file is
  untracked and may not exist on a fresh checkout.
- **The badge lands on the second panel for vertical cuts** (`DERECHO`), on the first
  for horizontal (`SUPERIOR`) — see the branch in `procesar_imagen`.
- The badge is drawn rotated 90° counter-clockwise at a fixed 56px font (~0.95cm at
  150dpi), inset 50px from the top-right corner to clear the seam.
- **The prose docs are stale in three specific ways** — the module docstring of
  `cortador_innova.py`, `cortador/README_INSTRUCCIONES.md` (and its `.html` twin,
  both untracked) and `README.md` all still say the counter resets to COD001 each
  run, that the badge scales with image size, and that the badge goes on
  IZQUIERDO/SUPERIOR. The code is authoritative on all three. Update them together
  or not at all.
- **`cortador` moves originals with `os.replace`** — it empties the input folder's
  root into `originales/`. Point it at a copy when experimenting.
- **The two chaining lookups are asymmetric.** `cortador` finds the etiquetador
  next to itself *or* at `../etiquetador/`, so it works both in this repo layout and
  in the flattened folder handed to staff. `etiquetador` only looks at
  `../costura/generar_costura.py` — in a flattened distribution folder the sewing PDF
  is silently skipped (`_intentar_costura` also swallows every exception).
- `etiquetador/generar_lista_etiquetado.py` is ~176KB because `LOGO_B64` and `QR_B64`
  are inline base64 PNGs on two single lines (94: 63KB, 95: 98KB). Never `cat` it
  whole; use `sed -n` on line ranges, and skip lines 94–95.
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
