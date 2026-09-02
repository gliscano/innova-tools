# INNOVA Tools — Procesador de Fondos Fotográficos en alta definición Sublimados

Suite de herramientas para automatizar el flujo de trabajo de fondos fotográficos sublimados sobre tela. Procesa imágenes JPG/PNG, las corta cuando superan el ancho del rollo, genera etiquetas de identificación y calcula los costos de costura.

---

## Funcionalidad

El flujo completo se ejecuta en cadena automáticamente al lanzar el cortador:

### 1. Cortador (`cortador/`)
- Lee todos los JPG/PNG de una carpeta.
- Determina si cada diseño entra en el rollo de tela (160 cm de ancho): entra si **al menos uno** de sus lados mide 160 cm o menos.
  - **Entra:** copia el archivo con el código grabado.
  - **No entra:** lo divide en dos paños con margen de costura incluido. Prefiere el corte vertical porque la costura se nota menos, salvo que el horizontal ahorre más de 30 cm de tela.
- Asigna un código correlativo (`COD001`, `COD002`…) grabado como badge en la esquina superior derecha de la imagen. En los diseños cortados solo lo lleva un paño: el DERECHO en cortes verticales, el SUPERIOR en horizontales; ambos llevan el código en el nombre del archivo.
- El contador **es persistente** entre corridas: guarda el último código en `cortador/ultimo_codigo.txt` y al arrancar propone continuar desde el siguiente (se puede sobrescribir en el prompt).
- **No convierte espacios de color.** Preserva el modo y el perfil ICC de cada archivo: un CMYK sale CMYK con su perfil, un Adobe RGB sale en Adobe RGB. Nunca pasa nada a sRGB, que arruinaría la saturación al sublimar sobre poliéster. También conserva el EXIF, el XMP de Adobe y el bloque de Photoshop.
- Exporta al **100% de calidad, sin submuestreo de color**. Los archivos pesan más que el original a cambio de fidelidad máxima.
- Mide cada diseño desde los píxeles y el DPI, y escribe `cortados/medidas_reales.json`. Avisa si un archivo no declara su resolución, porque en ese caso las medidas no son confiables.
- Muestra al final los metros lineales totales de tela necesarios.
- Mueve los originales a `originales/` y escribe los paños procesados en `cortados/`.

### 2. Etiquetador (`etiquetador/`)
- Lee la carpeta `cortados/` y parsea el nombre de cada archivo para extraer código, cliente, medida y observación.
- Genera en `etiquetados/`:
  - `lista_etiquetado_<cierre>.json` — para importar en la app de etiquetado (`index.html`).
  - `tabla_<cierre>.pdf` — lista de chequeo imprimible con miniaturas.
  - `etiquetas_<cierre>.pdf` — páginas 50×50 mm listas para imprimir en la DT01 (WePrint).

### 3. Costura (`costura/`)
- Lee `cortados/` y calcula el tipo y costo de costura por diseño según sus dimensiones.
- Toma la **medida real** desde `cortados/medidas_reales.json` (incluye los 15cm del bolsillo superior, que el nombre del cliente no trae); si ese archivo falta, avisa y recurre al nombre.
- Genera `costura/costura_<cierre>.pdf` con tabla de precios y total del lote.

### 4. App de etiquetado (`index.html`)

Página única y autocontenida — se abre directo en el navegador, sin instalar nada. Es la que se usa el día del etiquetado.

- Importa el `lista_etiquetado_<cierre>.json` generado por el etiquetador (o directamente una carpeta de imágenes, que parsea en el navegador).
- Marca cada diseño como pendiente o impreso y guarda ese estado en el navegador, por cierre.
- Permite reimprimir una etiqueta 50×50 mm suelta sin volver a generar el PDF completo.

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
| `--calidad` | `97` | Calidad de exportación JPG (1–100) |
| `--salida` | `cortados/` dentro de la carpeta de entrada | Carpeta de salida alternativa |

El etiquetador y el generador de costura aceptan `--cierre` (default: fecha de hoy) y `--sin-pausa` (no espera Enter al final; lo usan las llamadas automáticas).

### Convención de nombres de archivos en `cortados/`

El etiquetador, el generador de costura y `index.html` esperan este formato:

```
COD001 - NombreCliente - 290x200 - Observacion.jpg
COD002 - Maria Soledad - 500x290_IZQUIERDO.jpg
COD002 - Maria Soledad - 500x290_DERECHO.jpg
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
