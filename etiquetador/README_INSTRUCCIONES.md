# INNOVA — Generador de lista de etiquetado

Herramienta que toma los fondos ya procesados por el cortador y arma los tres archivos que se usan el día del etiquetado: la lista para la app, la planilla de chequeo imprimible y las etiquetas de 50×50mm para la DT01.

---

## ¿Cuándo se ejecuta?

**Normalmente no hay que ejecutarlo a mano.** El cortador lo llama solo apenas termina de cortar los fondos de la semana, y este a su vez llama al generador de costura. Si la corrida del cortador terminó bien, los archivos de etiquetado ya están hechos.

Se ejecuta por separado solo cuando hace falta **rehacer** los archivos: por ejemplo si se corrigió el nombre de un archivo en `cortados`, si se agregó un fondo que faltaba, o si se quiere regenerar con otra fecha de cierre.

---

## ¿Qué hace?

Lee todos los JPG y PNG de la carpeta `cortados` y saca del **nombre de cada archivo** cuatro datos: el código, el cliente, la medida y la observación.

```
COD001 - Flor Gonzalez - 290x200 - Con ojales.jpg
  │        │              │         └─ observación
  │        │              └─ medida
  │        └─ cliente
  └─ código
```

- Los diseños que se cortaron en dos paños aparecen **una sola vez** en la lista: se agrupan por código.
- Las medidas se leen del nombre del archivo, **no de los píxeles**. Son las que puso el cliente.
- Un archivo del que no se puede sacar ni código ni medida se **omite** y se avisa en pantalla con `[omitido]`. Si aparece ese mensaje, conviene revisar el nombre del archivo y volver a correr el generador.

---

## ¿Qué genera?

Tres archivos en una carpeta `etiquetados`, con la fecha de cierre en el nombre:

| Archivo | Para qué sirve |
|---|---|
| `lista_etiquetado_<fecha>.json` | Se importa en la app de etiquetado (`index.html`) — es lo que se lleva al día del etiquetado |
| `tabla_<fecha>.pdf` | Planilla A4 imprimible con miniatura, código, cliente, medida, observación y un casillero para tildar |
| `etiquetas_<fecha>.pdf` | Una página de 50×50mm por diseño, lista para mandar a la DT01 |

> **Dónde quedan:** la carpeta `etiquetados` se crea **al lado** de la carpeta que le pasaste, no adentro. Si le pasás `/Fondos semana/cortados`, los archivos van a `/Fondos semana/etiquetados`. Es a propósito, para que queden hermanas de `cortados` y `costura`.

### Qué lleva cada etiqueta de 50×50mm

De arriba hacia abajo: el logo de INNOVA, una línea punteada de corte, el **nombre del cliente** (el tamaño de letra se achica solo si el nombre es largo), la leyenda *¡Gracias por elegirnos!*, el código QR de reseñas y el pie *Tu opinión cuenta. Contanos tu experiencia en Google*.

El PDF tiene una página por diseño, del tamaño exacto de la etiqueta. En el diálogo de impresión de la DT01 hay que imprimir **a tamaño real (100%)**, sin "ajustar a la página", o las etiquetas salen escaladas.

---

## Cómo ejecutarlo a mano

### Opción A — doble clic (la más simple)

1. Hacer **doble clic** en `GENERAR_LISTA_ETIQUETADO.bat`.
2. Cuando pida la carpeta, **arrastrar la carpeta `cortados`** hasta la ventana negra y presionar ENTER.

También se puede arrastrar la carpeta `cortados` directamente **encima** del `.bat` y suelta: hace lo mismo sin preguntar.

El `.bat` verifica que estén instaladas Pillow y ReportLab, y las instala solo si faltan.

### Opción B — por terminal

```
python generar_lista_etiquetado.py "C:\ruta\Fondos semana\cortados"
python generar_lista_etiquetado.py "C:\ruta\Fondos semana\cortados" --cierre 2026-05-30
```

| Parámetro | Default | Para qué |
|---|---|---|
| `carpeta` | pregunta al arrancar | La carpeta `cortados` |
| `--cierre` | la fecha de hoy | Identificador del lote; va en el nombre de los tres archivos |
| `--sin-pausa` | — | No espera ENTER al terminar. Lo usa el cortador cuando llama solo; a mano no hace falta |

---

## Después de generarlo

Subir el `lista_etiquetado_<fecha>.json` a **Google Drive**. Ese es el archivo que se abre el día del etiquetado desde la app `index.html`, con el botón **Importar lista**: cada diseño aparece con su miniatura, su código y su cliente, se va tildando lo que ya se imprimió y se puede reimprimir una etiqueta suelta sin volver a generar el PDF completo.

La `tabla_<fecha>.pdf` es el respaldo en papel de esa misma lista, para tildar a mano sobre la mesa de trabajo.

---

## Instalación

Si se usa el sistema completo, ya quedó instalado con el cortador y no hay que hacer nada. Si no:

```
pip install Pillow reportlab
```

Pillow arma las miniaturas y ReportLab arma los dos PDF. Hacen falta las dos.

---

## Preguntas frecuentes

**¿Puedo correrlo dos veces sobre la misma carpeta?**
Sí. Regenera los tres archivos y pisa los anteriores si la fecha de cierre es la misma. Si usás otra fecha de cierre, quedan los dos juegos de archivos conviviendo en `etiquetados`.

**Un fondo no aparece en la lista, ¿por qué?**
Porque del nombre del archivo no se pudo sacar ni el código ni la medida. La ventana lo avisa con `[omitido] sin codigo/medida: <archivo>`. Corregir el nombre en `cortados` y volver a correr.

**Un diseño cortado en dos, ¿sale dos veces?**
No. Los dos paños comparten el código, así que en la lista y en las etiquetas aparece una sola vez. Se imprime una etiqueta por diseño, no por paño.

**¿De dónde saca la medida?**
Del nombre del archivo, tal como lo mandó el cliente. No la mide de la imagen. Si la medida del nombre está mal, va a estar mal en la etiqueta y en la lista de costura.

**¿Puedo cambiar la fecha del cierre?**
Sí, con `--cierre` por terminal. Por defecto usa la fecha del día en que se corre.

**¿Genera también la lista de costura?**
Sí, al terminar llama solo al generador de costura, que deja su PDF en la carpeta `costura`. Para que eso funcione, la carpeta `costura/` tiene que estar al lado de `etiquetador/`; si no está, se omite en silencio y el resto del proceso sigue igual.

**Me dice que falta Pillow o ReportLab**
Abrir el `cmd` y correr `pip install Pillow reportlab`. Si se ejecuta por el `.bat`, esto lo hace solo.
