# INNOVA Tools — Procesador de Fondos Fotográficos en alta definición Sublimados

Suite de herramientas para automatizar el flujo de trabajo de fondos fotográficos sublimados sobre tela. Procesa imágenes JPG/PNG, las corta cuando superan el ancho del rollo, genera etiquetas de identificación y calcula los costos de costura.

---

## Funcionalidad

El flujo completo se ejecuta en cadena automáticamente al lanzar el cortador:

### 1. Cortador (`cortador/`)
- Lee todos los JPG/PNG de una carpeta.
- Determina si cada diseño entra en el rollo de tela (160 cm de ancho).
  - **Entra:** copia el archivo con el código grabado.
  - **No entra:** lo divide en dos paños (vertical u horizontal) con margen de costura incluido, priorizando el corte que menos tela desperdicia.
- Asigna un código correlativo (`COD001`, `COD002`…) grabado como badge en la esquina superior derecha de cada imagen.
- Muestra al final los metros lineales totales de tela necesarios.
- Mueve los originales a `originales/` y escribe los paños procesados en `cortados/`.

### 2. Etiquetador (`etiquetador/`)
- Lee la carpeta `cortados/` y parsea el nombre de cada archivo para extraer código, cliente, medida y observación.
- Genera en `etiquetados/`:
  - `lista_etiquetado_<cierre>.json` — para importar en la app de etiquetado.
  - `tabla_<cierre>.pdf` — lista de chequeo imprimible con miniaturas.
  - `etiquetas_<cierre>.pdf` — páginas 50×50 mm listas para imprimir en la DT01 (WePrint).

### 3. Costura (`costura/`)
- Lee `cortados/` y calcula el tipo y costo de costura por diseño según sus dimensiones.
- Genera `costura/costura_<cierre>.pdf` con tabla de precios y total del lote.

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
4. El script procesa las imágenes, luego llama automáticamente al etiquetador y al generador de costura.

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

### Convención de nombres de archivos en `cortados/`

El etiquetador y el generador de costura esperan este formato:

```
COD001 - NombreCliente - 290x200 - Observacion.jpg
```

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
