# INNOVA Tools — Procesador de Fondos Fotográficos en alta definición Sublimados

Suite de herramientas para automatizar el flujo de trabajo de fondos fotográficos sublimados sobre tela. Procesa imágenes JPG/PNG, las corta cuando superan el ancho del rollo, genera etiquetas de identificación y calcula los costos de costura.

> **¿Sos operador?** El manual de uso paso a paso está en [INSTRUCCIONES.md](INSTRUCCIONES.md) (y en versión para navegador, `INSTRUCCIONES.html`). Este README es la referencia técnica.

---

## Funcionalidad

El flujo completo se ejecuta en cadena automáticamente al lanzar el cortador:

### 1. Cortador (`cortador/`)
- Lee todos los JPG/PNG de una carpeta.
- Determina si cada diseño entra en el rollo de tela (160 cm de ancho): entra si **al menos uno** de sus lados mide 160 cm o menos.
  - **Entra:** copia el archivo con el código grabado.
  - **No entra:** lo divide en dos paños con margen de costura incluido. Prefiere el corte vertical porque la costura se nota menos, salvo que el horizontal ahorre más de 30 cm de tela.
  - **No entra ni en dos paños** (fondos grandes, por ejemplo 500×400 o 1200×500): lo divide en **3 o más paños iguales en horizontal**, cada uno ≤ 160 cm con el margen incluido (los paños del medio llevan margen de los dos lados). Solo corta vertical si el nombre lo pide. Sufijos: `_SUPERIOR`, `_MEDIO1`…, `_INFERIOR` (vertical: `_IZQUIERDO`, `_CENTRO1`…, `_DERECHO`). Avisa si un paño supera el largo del rollo (10 m).
  - **El nombre dice `horizontal` o `vertical`:** corta siempre en ese eje, aunque el diseño entre sin corte. Si dos paños no entran en el rollo, lo divide en 3 o más en ese eje.
- Asigna un código correlativo (`COD001`, `COD002`…) grabado como badge en la esquina superior derecha de la imagen: ~3.8 × 1 cm impresos, a 0.5 cm del borde superior (entra en el bolsillo de 5 cm) y a 2.5 cm del lateral (no se pierde en la costura). En los diseños cortados solo lo lleva un paño: el DERECHO en cortes verticales, el SUPERIOR en horizontales; todos llevan el código en el nombre del archivo. Los fondos de **neoprene** (`neoprene`/`neopreno` en el nombre) no llevan badge, solo el código en el nombre.
- El contador **es persistente** entre corridas: guarda el último código en `cortador/ultimo_codigo.txt` y al arrancar propone continuar desde el siguiente (se puede sobrescribir en el prompt).
- **No convierte espacios de color.** Preserva el modo y el perfil ICC de cada archivo: un CMYK sale CMYK con su perfil, un Adobe RGB sale en Adobe RGB. Nunca pasa nada a sRGB, que arruinaría la saturación al sublimar sobre poliéster. También conserva el EXIF, el XMP de Adobe y el bloque de Photoshop.
- Exporta al **100% de calidad, sin submuestreo de color**. Los archivos pesan más que el original a cambio de fidelidad máxima.
- Mide cada diseño desde los píxeles y el DPI, y escribe `cortados/medidas_reales.json`. Avisa si un archivo no declara su resolución, porque en ese caso las medidas no son confiables.
- **Aviso de calidad** (heurístico, nunca frena el corte): resolución < 72 DPI, imagen borrosa o ampliada (poco detalle fino respecto del detalle a escala 1/2) o pixelada (bloques repetidos de una ampliación "vecino más cercano"). Analiza 25 recortes de 512 px a resolución nativa e ignora las zonas lisas, para no marcar degradés. Las métricas quedan en el manifiesto (`calidad`).
- Acepta PNG en todos sus modos (RGB, RGBA, escala de grises, con transparencia, 16 bits) sin convertirlos.
- Muestra al final los metros lineales de tela necesarios, separados en poliéster y neoprene. El manifiesto guarda por diseño `tela` y `metros_lineales`.
- Mueve los originales a `originales/` y escribe los paños procesados en `cortados/`.

### 2. Etiquetador (`etiquetador/`)
- Lee la carpeta `cortados/` y parsea el nombre de cada archivo para extraer código, cliente, medida y observación.
- Genera en `etiquetados/`:
  - `lista_etiquetado_<cierre>.json` — para importar en la app de etiquetado (`index.html`).
  - `tabla_<cierre>.pdf` — lista de chequeo imprimible con miniaturas, encabezada por el **resumen de producción**: tela poliéster, tela neoprene, sublimación (ambas) en metros, y total de costura.
  - `etiquetas_<cierre>.pdf` — páginas 50×50 mm listas para imprimir en la DT01 (WePrint), con el nombre del cliente y el código tal como se grabó en la imagen (`COD001`).
- Cierra la corrida en consola con el estado de etiquetado y costura (`finalizado` / `error`) y el mismo resumen de producción.

### 3. Costura (`costura/`)
- Lee `cortados/` y calcula el tipo y costo de costura por diseño según sus dimensiones. Tarifas marzo 2026: 1 paño $2.180, unión ≤ 450 cm $4.350, unión > 450 cm $6.950, neoprene $2.350, viáticos $6.000 por cierre. Un fondo en 3 o más paños paga la tarifa de unión + 50% de esa tarifa por cada paño adicional a 2 (3 paños > 4,5 m = $10.425; 4 paños = $13.900).
- Toma la **medida real** y el **corte real** (paños y eje) desde `cortados/medidas_reales.json` (incluye los 15cm del bolsillo superior, que el nombre del cliente no trae); si ese archivo falta, avisa, recurre al nombre y deduce el corte por su cuenta.
- Genera `costura/costura_<cierre>.pdf` con tabla de precios y total del lote.

### 4. App de etiquetado (`index.html`)

Página única y autocontenida — se abre directo en el navegador, sin instalar nada. Es la que se usa el día del etiquetado.

- Importa el `lista_etiquetado_<cierre>.json` generado por el etiquetador (o directamente una carpeta de imágenes, que parsea en el navegador).
- Marca cada diseño como pendiente o impreso y guarda ese estado en el navegador, por cierre.
- Permite reimprimir una etiqueta 50×50 mm suelta (con el mismo diseño y código que el PDF del etiquetador) sin volver a generar el PDF completo.

---

## Tecnología

| Componente | Detalle |
|---|---|
| Lenguaje | Python 3.9+ |
| Procesamiento de imágenes | [Pillow](https://python-pillow.org/) |
| Generación de PDFs | [ReportLab](https://www.reportlab.com/) |
| Entorno | Windows (`.bat`), compatible con macOS/Linux por CLI |
| Sin dependencias de red | Funciona completamente offline |

---

## Instalación

```bash
pip install Pillow reportlab
```

---

## Cómo ejecutar

### Flujo completo (recomendado) — doble clic en Windows

1. Poner los JPG/PNG de la semana en una carpeta.
2. Hacer doble clic en `cortador/CORTAR_FONDOS.bat`.
3. Arrastrar la carpeta al terminal y presionar **Enter**.
4. El script muestra el último código usado y pregunta desde cuál arrancar. **Enter** en blanco continúa la numeración.
5. El script procesa las imágenes, luego llama automáticamente al etiquetador y al generador de costura.

> El cortador **mueve** los originales a `originales/`, no los copia: la raíz de la carpeta de entrada queda vacía de imágenes. Conviene apuntarlo a una carpeta de trabajo.

El encadenamiento depende de la ubicación de los scripts: el cortador busca al etiquetador al lado suyo o en `../etiquetador/`, y el etiquetador busca a la costura únicamente en `../costura/`. Si se distribuyen los archivos aplanados en una sola carpeta, el PDF de costura se omite en silencio.

### Por línea de comandos

```bash
# Paso 1 — Cortar fondos
python cortador/cortador_innova.py "C:\ruta\fondos-semana"

# Paso 2 — Generar etiquetas (si se quiere ejecutar por separado)
python etiquetador/generar_lista_etiquetado.py "C:\ruta\fondos-semana\cortados" --cierre 2026-06-15

# Paso 3 — Generar lista de costura (si se quiere ejecutar por separado)
python costura/generar_costura.py "C:\ruta\fondos-semana\cortados" --cierre 2026-06-15
```

#### Parámetros del cortador

| Parámetro | Default | Descripción |
|---|---|---|
| `carpeta` | `.` (carpeta actual) | Carpeta con los JPG/PNG a procesar |
| `--margen` | `0.45` | Margen de costura en cm |
| `--ancho-rollo` | `160` | Ancho del rollo de tela en cm |
| `--umbral` | `30` | Diferencia de desperdicio (cm) para preferir corte horizontal |
| `--calidad` | `100` | Calidad de exportación JPG (1–100) |
| `--salida` | `cortados/` dentro de la carpeta de entrada | Carpeta de salida alternativa |

El etiquetador y el generador de costura aceptan `--cierre` (default: fecha de hoy) y `--sin-pausa` (no espera Enter al final; lo usan las llamadas automáticas).

### Convención de nombres de archivos en `cortados/`

El etiquetador, el generador de costura y `index.html` esperan este formato:

```
COD001 - NombreCliente - 290x200 - Observacion.jpg
COD002 - Maria Soledad - 500x290_IZQUIERDO.jpg
COD002 - Maria Soledad - 500x290_DERECHO.jpg
COD003 - Juan Perez - 500x400_SUPERIOR.jpg
COD003 - Juan Perez - 500x400_MEDIO1.jpg
COD003 - Juan Perez - 500x400_INFERIOR.jpg
```

Las medidas se leen del **nombre del archivo original del cliente**, no de los píxeles. Un archivo sin medida reconocible se omite en las dos etapas siguientes.

---

## Estructura de salida

```
/fondos-semana/
  originales/              ← JPGs originales (movidos por el cortador)
  cortados/                ← paños procesados con badge CODxxx
  etiquetados/
    lista_etiquetado_<cierre>.json
    tabla_<cierre>.pdf
    etiquetas_<cierre>.pdf
  costura/
    costura_<cierre>.pdf
```

---

## Licencia

Uso interno — INNOVA Fondos Fotográficos.
