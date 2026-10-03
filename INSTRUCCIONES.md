# INNOVA — Manual de uso

Cómo pasar de la carpeta con los fondos de la semana a los paños listos para sublimar, las etiquetas impresas y el presupuesto de costura.

---

## Qué hace el sistema

Con **un solo doble clic** en `CORTAR_FONDOS.bat` se hace todo el proceso de la semana, en cadena:

1. **Cortador** — toma los JPG y PNG de la carpeta, corta en dos los que no entran en el rollo de 1.60m, les graba un código de identificación y calcula los metros lineales de tela.
2. **Etiquetador** — arma la lista para la app de etiquetado, la planilla de chequeo imprimible y las etiquetas de 50×50mm para la DT01.
3. **Costura** — arma el PDF con el detalle y el costo de la costura para pasarle al taller.

Las etapas 2 y 3 arrancan solas cuando termina la 1. No hay que ejecutar nada más.

Al terminar, dentro de la carpeta de la semana quedan cuatro subcarpetas:

```
/Fondos semana/
  originales/     ← los archivos originales, movidos acá sin modificar
  cortados/       ← los paños listos para sublimar, con el código grabado
                    + medidas_reales.json (las medidas medidas por el script)
  etiquetados/    ← lista_etiquetado_<fecha>.json, tabla_<fecha>.pdf, etiquetas_<fecha>.pdf
  costura/        ← costura_<fecha>.pdf
```

> **Importante:** los archivos originales **se mueven** (no se copian) a la subcarpeta `originales`. La carpeta que le pasás al script queda vacía de imágenes al terminar. Si querés conservarla tal cual, trabajá sobre una copia.

---

## Instalación (solo la primera vez)

### Paso 1 — Instalar Python

Python es el programa que necesita la computadora para ejecutar los scripts. Es gratis y oficial.

1. Abrir el navegador (Chrome, Edge, Firefox) e ir a **https://www.python.org/downloads/**
2. Hacer clic en el botón amarillo grande que dice **"Download Python"** (la versión más reciente está bien).
3. Cuando termine de descargar, hacer doble clic en el archivo descargado (algo como `python-3.XX.X-amd64.exe`).
4. **MUY IMPORTANTE:** en la primera pantalla del instalador, antes de hacer clic en "Install Now", **marcar la casilla "Add python.exe to PATH"** (está abajo de todo). Si no se marca, nada va a funcionar.
5. Hacer clic en **"Install Now"** y esperar a que termine.
6. Cuando aparezca "Setup was successful", cerrar el instalador.
7. **Reiniciar la computadora.**

### Paso 2 — Instalar las librerías Pillow y ReportLab

Pillow abre, corta y graba el código en las imágenes. ReportLab arma los PDF de etiquetado y de costura. Hacen falta las dos.

1. Hacer clic en el botón de Inicio de Windows y escribir **`cmd`**.
2. Abrir "Símbolo del sistema" (se abre una ventana negra).
3. Escribir este comando y presionar ENTER:
   ```
   pip install Pillow reportlab
   ```
4. Esperar el mensaje "Successfully installed..." y cerrar la ventana.

### Paso 3 — Guardar los archivos

1. Crear una carpeta en el escritorio llamada **"Cortador Innova"** (o donde sea más cómodo).
2. Copiar adentro las tres subcarpetas del sistema, **sin cambiarles el nombre ni sacarlas de lugar**:
   - **`cortador/`** → `cortador_innova.py` y `CORTAR_FONDOS.bat`
   - **`etiquetador/`** → `generar_lista_etiquetado.py` y su `.bat`
   - **`costura/`** → `generar_costura.py` y su `.bat`
3. Copiar también `index.html` (la app de etiquetado).

El cortador busca a los otros dos scripts en esas carpetas para llamarlos solo al terminar. Si `costura/` no está al lado de `etiquetador/`, el PDF de costura no se genera: solo aparece un aviso de una línea, fácil de pasar por alto, y el resto del proceso sigue igual.

Listo: la instalación no hay que repetirla.

---

## Uso semanal

### 1. Cortar los fondos

1. Poner todos los fondos de la semana (JPG y/o PNG) en una carpeta.
2. Hacer **doble clic** en `CORTAR_FONDOS.bat`.
3. Se abre una ventana negra que pide la carpeta. **Arrastrar la carpeta con los fondos hasta la ventana** y presionar **ENTER**.
4. La ventana muestra el último código usado y pregunta desde cuál arrancar:
   ```
   Ultimo codigo usado: COD042
   Iniciar desde [COD043]:
   ```
   **Presionar ENTER sin escribir nada** para seguir la numeración de la semana pasada. Solo escribir un número para forzar otro arranque (por ejemplo, repetir una corrida que salió mal).
5. Esperar a que termine. Muestra qué hizo con cada archivo y después genera solo el etiquetado y la costura.
6. Al final la ventana muestra si el etiquetado y la costura terminaron bien, y el **resumen de producción**:
   ```
    ETIQUETADO: finalizado
    COSTURA:    finalizado
   ------------------------------------------------------
    RESUMEN DE PRODUCCION
     Tela poliéster:        25.82 m
     Tela neoprene:         9.00 m
     Sublimación (total):   34.82 m
     Total costura:         $ 32.000
   ```
   Los metros de cada tela son los que hay que descontar del stock; sublimación es la suma de las dos. El mismo resumen sale impreso arriba de todo en `etiquetados/tabla_<fecha>.pdf`.
7. Revisar si hubo avisos en la ventana (ver *Avisos a los que prestar atención* más abajo). Si una etapa dice **error**, el motivo aparece en una línea `[ERROR]` o `[aviso]` más arriba.

Los archivos para mandar al plotter están en `cortados`.

#### Palabras clave en el nombre del archivo

Antes de cortar, se puede escribir en el nombre del fondo:

| Si el nombre dice | Qué hace el cortador |
|---|---|
| `horizontal` | Corta **siempre** en SUPERIOR / INFERIOR, aunque el diseño entre en el rollo sin cortar |
| `vertical` | Corta **siempre** en IZQUIERDO / DERECHO, aunque el diseño entre en el rollo sin cortar |
| `neoprene` o `neopreno` | **No graba el código** en la imagen (el nombre del archivo sí lo lleva) y cuenta sus metros como tela neoprene |

Si el corte pedido produce paños que no entran en el rollo, el diseño se marca como **error**. Si el nombre dice `horizontal` y `vertical` a la vez, se avisa y el cortador decide solo.

### 2. Etiquetar

1. Subir `etiquetados/lista_etiquetado_<fecha>.json` a **Google Drive**.
2. El día del etiquetado, abrir `index.html` en el navegador y usar el botón **Importar lista** con ese archivo. Cada diseño aparece con su miniatura, su código y su cliente.
3. Imprimir `etiquetados/etiquetas_<fecha>.pdf` en la DT01. En el diálogo de impresión elegir **tamaño real (100%)**, sin "ajustar a la página", o las etiquetas salen escaladas.
4. Ir tildando en la app lo que ya se imprimió. Si una etiqueta sale mal, la app la reimprime sola sin volver a generar el PDF completo.

`etiquetados/tabla_<fecha>.pdf` es la misma lista en papel, con miniaturas y un casillero para tildar a mano sobre la mesa de trabajo.

Cada etiqueta de 50×50mm lleva, de arriba hacia abajo: el logo de INNOVA, una línea punteada de corte, el **nombre del cliente** (la letra se achica sola si el nombre es largo), la leyenda *¡Gracias por elegirnos!*, el código QR de reseñas y el pie *Tu opinión cuenta. Contanos tu experiencia en Google*.

### 3. Mandar a costura

1. Abrir `costura/costura_<fecha>.pdf`.
2. Revisar si hay **filas pintadas de amarillo y sin monto**: son diseños que necesitan más de dos paños. Se listan también al pie bajo "ATENCIÓN". Hay que cotizarlos a mano antes de mandar el presupuesto.
3. Mandar el PDF al taller. La columna "Check" es para tildar a medida que el taller entrega cada fondo.

---

## Avisos a los que prestar atención

| Aviso en la ventana | Qué significa | Qué hacer |
|---|---|---|
| `[AVISO] El archivo no declara densidad` | El archivo no trae su resolución; el script asume 150 DPI y **las medidas quedan mal** (un archivo de 254 DPI leído como 150 mide un 69% de más). Photoshop e Illustrator siempre la incluyen, así que el archivo pasó por otra herramienta. | Reexportarlo desde Photoshop/Illustrator y volver a cortar. |
| Un diseño marcado como **error** | Ningún corte en dos paños entra en el rollo. | Tratamiento manual. |
| `[omitido] sin codigo/medida` (etiquetado) | Del nombre del archivo no se pudo sacar el código o la medida; el diseño **no aparece** en la lista ni en las etiquetas. | Corregir el nombre en `cortados` y regenerar el etiquetado (ver *Rehacer una etapa*). |
| `[omitido] sin medida` (costura) | El diseño **no aparece** en el presupuesto ni suma al total. | Corregir el nombre y regenerar la costura. |
| `[COSTURA] generar_costura.py no encontrado` | `generar_costura.py` no está ni al lado del etiquetador ni en una carpeta `costura/` vecina. La costura sale **error** y el resumen sin total. | Revisar el Paso 3 de la instalación. |
| `[aviso] No hay medidas_reales.json` | El resumen sale con los metros en "sin datos" (pasa al rehacer el etiquetado sobre una carpeta sin ese archivo). | Volver a cortar si se necesitan los metros. |

---

## Cómo funciona por dentro

### Cómo se decide el corte

El rollo de tela mide **1.60m de ancho × 10m de largo**. Los paños se apilan en columna para sublimar por calandrado.

| Caso | Qué hace el cortador |
|---|---|
| El nombre dice `horizontal` o `vertical` | Corta **en ese eje**, siempre; si los paños no entran en el rollo, marca error |
| Al menos un lado del diseño ≤ 1.60m | **No corta** — guarda con el código grabado |
| Ambos lados > 1.60m, los dos cortes son posibles | **Corte vertical** (costura menos visible), salvo que el horizontal ahorre más de 30cm de tela |
| Solo un eje de corte produce paños que entran en el rollo | Usa **ese eje** |
| Ningún corte produce paños que entren | **Marca error** (tratamiento manual) |

Los metros lineales de cada paño son su lado más largo. Se suman por tipo de tela: neoprene si el nombre dice `neoprene`/`neopreno`, poliéster todo lo demás.

El **solape de costura es de 0.45cm a cada lado del corte** (0.90cm en total): la máquina de coser consume esa parte y el diseño queda continuo al unir los paños.

### El código de identificación

Cada diseño recibe un código correlativo (`COD001`, `COD002`, ...) que se graba de dos formas:

**En la imagen** — un badge con texto negro sobre fondo blanco semitransparente en la **esquina superior derecha**, girado 90°. Tiene un **tamaño fijo impreso**, igual en todos los fondos sin importar su resolución: unos **4cm de largo y 1cm de ancho**, a 0.5cm del borde superior y del derecho. Así ocupa como máximo 4.5cm desde arriba y **entra siempre en el bolsillo**, también en el de 5cm.

**En el nombre del archivo** — todos los archivos de `cortados` empiezan con el código:

```
COD001 - Flor Gonzalez - 290x200 - Con ojales.jpg
COD002 - Maria Soledad - 500x290_IZQUIERDO.jpg
COD002 - Maria Soledad - 500x290_DERECHO.jpg
```

Del nombre se sacan los cuatro datos de la etiqueta: código, cliente, medida y observación (la última es opcional).

En los diseños cortados en dos paños, **uno solo lleva el badge**: el **DERECHO** si el corte fue vertical, el **SUPERIOR** si fue horizontal — siempre del lado contrario a la costura. Los dos llevan el código en el nombre, y en la lista de etiquetado y en el presupuesto el diseño aparece **una sola vez**.

Los fondos de **neoprene no llevan badge** en ningún paño: el código queda solo en el nombre del archivo.

El contador **no reinicia**: se guarda en `cortador/ultimo_codigo.txt` y cada corrida propone seguir desde el siguiente, así los códigos no se repiten entre semanas.

### Las medidas reales

El cortador mide cada diseño desde los píxeles del archivo y guarda esas medidas en `cortados/medidas_reales.json`. Nuestros fondos llevan unos **15cm extra arriba para el bolsillo** del soporte, y el nombre que manda el cliente no los incluye: un archivo llamado `200x200` mide en realidad 200×215.

Por eso hay dos medidas en juego, y cada documento usa la que le corresponde:

| Documento | Medida que muestra |
|---|---|
| Etiquetas, planilla y app de etiquetado | La del **nombre del archivo**, la que pidió el cliente |
| Presupuesto de costura | La **real**, con el bolsillo — es la tela que se cose, se descuenta y se cobra |

Si el `medidas_reales.json` falta, la costura avisa y usa la medida del nombre.

### Fidelidad de color

El cortador **no convierte espacios de color**. Corta y nada más:

- Un archivo **CMYK** sale CMYK, con su mismo perfil (por ejemplo *Japan Web Coated*).
- Un archivo **Adobe RGB (1998)** sale en Adobe RGB.
- Nunca convierte nada a sRGB, que arruinaría la saturación al sublimar sobre poliéster.

Se conservan **todos los metadatos** de cada archivo: el perfil ICC, el EXIF, el XMP de Adobe y el bloque de Photoshop. Los dos paños de un diseño cortado quedan con el perfil del original.

El código grabado también respeta el color: en los CMYK las letras van **solo con el canal negro (K)**, no con negro de registro, que en sublimación sería tinta al 300%.

La única diferencia contra el original es la mínima pérdida de volver a comprimir un JPG. El cortador guarda al **100% de calidad y sin submuestreo de color**: el error medido es de 0.05 sobre 255. A cambio, los archivos cortados pesan bastante más que el original. Los PNG no pierden nada.

### Tipos de costura y tarifas

| Caso | Detalle en el PDF | Monto |
|---|---|---|
| Al menos un lado ≤ 160cm (entra en el rollo) | **1 Paño** | $ 2.180 |
| Ambos lados > 160cm, unión de hasta 450cm | **Unión hasta 4,5 m** | $ 4.350 |
| Ambos lados > 160cm, unión de más de 450cm | **Unión de 4,5 m en adelante** | $ 6.950 |
| El nombre del archivo dice "neoprene" o "neopreno" | **Piso Neoprene** (no importa la medida) | $ 2.350 |
| Ningún corte al medio entra en el rollo | **Múltiples paños (cotizar manual)** | — |
| Viáticos | Una vez por cierre, fila aparte | $ 5.000 |

Tarifas vigentes a **marzo 2026**. El total se **redondea para arriba al próximo múltiplo de $1.000**; el subtotal sin redondear aparece en letra chica debajo de la tabla para poder controlar la cuenta.

El presupuesto cotiza con el corte que **hizo de verdad el cortador** (lo lee de `medidas_reales.json`): un diseño cortado por pedido del nombre se cobra como unión aunque entrara en el rollo, y la unión se mide a lo largo del lado que el corte no parte. Si el `medidas_reales.json` falta, decide el corte por su cuenta desde el nombre, y en ese caso puede no coincidir con los archivos de `cortados`.

**Para actualizar los precios**, abrir `costura/generar_costura.py` con el Bloc de notas y cambiar los números del bloque `tarifas (Marzo 2026)`, cerca del principio:

```python
PRECIO_1_PANO       = 2_180
PRECIO_UNION_CORTA  = 4_350
PRECIO_UNION_LARGA  = 6_950
PRECIO_NEOPRENE     = 2_350
VIATICOS            = 5_000
```

Los guiones bajos son separadores de miles (`2_180` es dos mil ciento ochenta). Actualizar también el mes del comentario.

---

## Rehacer una etapa por separado

Normalmente no hace falta. Sirve cuando se corrigió el nombre de un archivo en `cortados`, se agregó un fondo que faltaba, cambiaron las tarifas o se quiere otra fecha de cierre.

Las dos etapas leen la carpeta `cortados` y dejan su resultado **al lado** de ella, no adentro: si le pasás `/Fondos semana/cortados`, los archivos van a `/Fondos semana/etiquetados` y `/Fondos semana/costura`. Si se regenera con la misma fecha, se pisan los archivos anteriores.

### Etiquetado

Hacer doble clic en `etiquetador/GENERAR_LISTA_ETIQUETADO.bat` y arrastrar la carpeta `cortados` a la ventana (o soltar la carpeta directamente encima del `.bat`). Instala Pillow y ReportLab si faltan.

Al terminar, el etiquetador **también regenera la costura**.

### Costura

Lo más simple es por terminal (abrir `cmd`):

```
python "C:\Cortador Innova\costura\generar_costura.py" "C:\ruta\Fondos semana\cortados"
```

`GENERAR_COSTURA.bat` solo funciona si hay una carpeta `cortados` **al lado del propio `.bat`**: no se le puede arrastrar una carpeta. Para usarlo con doble clic hay que copiar `generar_costura.py` y el `.bat` dentro de la carpeta de la semana.

### Opciones por terminal

```
python cortador_innova.py "C:\Fondos" --margen 0.50 --ancho-rollo 155
python generar_lista_etiquetado.py "C:\Fondos\cortados" --cierre 2026-05-30
python generar_costura.py "C:\Fondos\cortados" --cierre 2026-05-30
```

| Opción | Script | Default | Para qué |
|---|---|---|---|
| `--margen` | cortador | 0.45 | Solape de costura en cm por lado |
| `--ancho-rollo` | cortador | 160 | Ancho del rollo en cm |
| `--umbral` | cortador | 30 | Ahorro de tela (cm) a partir del cual se prefiere el corte horizontal |
| `--calidad` | cortador | 100 | Calidad JPG de salida (1–100) |
| `--salida` | cortador | `cortados/` | Otra carpeta de salida |
| `--cierre` | etiquetador, costura | fecha de hoy | Identificador del lote; va en el nombre de los archivos |
| `--sin-pausa` | etiquetador, costura | — | No espera ENTER al terminar (lo usan las llamadas automáticas) |

---

## Preguntas frecuentes

**¿Qué pasa con los archivos originales?**
No se modifican, pero **se mueven** a la subcarpeta `originales`. Conviene apuntar el script a una carpeta de trabajo y no a un archivo maestro de diseños.

**¿Soporta JPG y PNG? ¿Y otros archivos?**
Procesa `.jpg`, `.jpeg` y `.png` (los PNG conservan su transparencia). Los demás archivos (PDF, PSD, etc.) los ignora.

**¿El script cambia los colores del diseño?**
No. Un CMYK sale CMYK y un Adobe RGB sale Adobe RGB, cada uno con su perfil original. Nunca pasa nada a sRGB.

**¿Los códigos arrancan de nuevo en COD001 cada semana?**
No. El script recuerda el último código y propone seguir desde el siguiente. Para forzar otro número, escribirlo cuando lo pregunta al principio.

**¿Por qué uno de los dos paños cortados no tiene el badge?**
Con grabarlo una vez alcanza. Lo lleva el DERECHO en los cortes verticales y el SUPERIOR en los horizontales; el otro paño tiene el código en el nombre del archivo.

**Un diseño cortado en dos, ¿sale dos veces en la lista o en las etiquetas?**
No. Los dos paños comparten el código: una etiqueta por diseño, no por paño.

**¿Por qué la medida del presupuesto no coincide con la de la etiqueta?**
Porque el presupuesto usa la medida real, con los 15cm del bolsillo. Un fondo `200x200` figura en costura como `200 x 215 cm`. Ver *Las medidas reales*.

**¿Puedo cargar la carpeta `cortados` en la app en vez del `.json`?**
Sí, `index.html` también acepta la carpeta de imágenes y lee el código del nombre de cada archivo. El `.json` es más cómodo porque ya trae las miniaturas.

**¿Los viáticos se cobran por fondo?**
No, una sola vez por cierre.

**¿Por qué el PDF de costura no tiene el logo de INNOVA?**
El script todavía no lo dibuja. El PDF sale bien igual, con el encabezado de texto.

**Me aparece el error "python no se reconoce como comando"**
Al instalar Python no se marcó "Add python.exe to PATH". Desinstalarlo desde Panel de Control → Programas y volver a instalarlo marcando esa casilla.

**Me dice que falta Pillow o ReportLab**
Abrir `cmd` y correr `pip install Pillow reportlab`.
