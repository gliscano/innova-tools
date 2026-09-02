# INNOVA — Cortador de Fondos para Sublimación

Herramienta para dividir automáticamente los diseños de fondos fotográficos que no entran en el rollo de tela de 1.60m, aplicar el solape de costura, grabar un código de identificación en cada imagen y calcular los metros lineales para descontar del inventario.

---

## ¿Qué hace esta herramienta?

Toma todos los archivos JPG y PNG de una carpeta y, según las medidas de cada diseño, decide automáticamente qué hacer con cada uno:

- **Si el diseño entra en el rollo de 1.60m** (al menos uno de sus lados mide 1.60m o menos): lo guarda en la carpeta de salida con su código de identificación grabado en la imagen.
- **Si ambos lados superan 1.60m:** lo divide en dos paños con un solape de costura de 0.45cm a cada lado del corte. El script elige automáticamente si conviene cortar vertical (izquierdo/derecho) u horizontal (superior/inferior), priorizando la costura menos visible y minimizando el desperdicio de tela. Uno solo de los dos paños lleva el badge del código en la imagen; ambos lo llevan en el nombre del archivo.
- **A cada imagen** se le asigna un código correlativo (`COD001`, `COD002`, ...) que se graba como badge blanco semitransparente en la **esquina superior derecha** de la imagen y al inicio del nombre del archivo en `cortados`.
- **Al finalizar**, muestra el total de metros lineales de tela necesarios para descontar del inventario, y **llama solo** al generador de etiquetas y al de costura.

Todos los archivos finales (cortados y sin cortar) quedan unificados en una sola carpeta llamada `cortados`, nombrados como `COD001 - nombre_original.ext`.

> **Importante:** los archivos originales **se mueven** (no se copian) a una subcarpeta `originales`. La carpeta que le pasás al script queda vacía de imágenes al terminar. Si querés conservar la carpeta tal como está, trabajá sobre una copia.

### Qué se genera en total

Al terminar la corrida, dentro de la carpeta que le pasaste al script quedan cuatro subcarpetas:

```
/Fondos semana/
  originales/     ← los archivos originales, movidos acá sin modificar
  cortados/       ← los paños listos para sublimar, con el código grabado
                    + medidas_reales.json (las medidas medidas por el script)
  etiquetados/    ← la lista .json y los PDF de etiquetado (automático)
  costura/        ← el PDF con el presupuesto de costura (automático)
```

### Las medidas reales

El cortador mide cada diseño desde los píxeles del archivo, no desde el nombre, y guarda esas medidas en `cortados/medidas_reales.json`. El generador de costura las lee de ahí para cotizar.

Importa porque nuestros fondos llevan unos **15cm extra arriba para el bolsillo** del soporte, y el nombre que manda el cliente no los incluye. Un archivo llamado `200x200` mide en realidad 200×215: son 15cm de tela que hay que coser, descontar del stock y cobrar.

Si en la ventana aparece una medida distinta a la del nombre, no es un error: es la medida física del fondo.

---

## Fidelidad de color

El cortador **no convierte espacios de color**. Corta y nada más:

- Un archivo **CMYK** sale CMYK, con su mismo perfil (por ejemplo *Japan Web Coated*).
- Un archivo **Adobe RGB (1998)** sale en Adobe RGB.
- Nunca convierte nada a sRGB, que arruinaría la saturación al sublimar sobre poliéster.

El perfil ICC se extrae individualmente de cada archivo al abrirlo y se vuelve a incrustar al guardar, tanto para JPG como para PNG. Los paños de un diseño cortado quedan los dos con el perfil del original.

El código grabado también respeta el espacio de color: en los archivos CMYK las letras se imprimen **solo con el canal negro (K)**, no con negro de registro, que en sublimación sería tinta al 300%.

También se conservan **todos los metadatos** del archivo: el perfil ICC, el EXIF, el XMP de Adobe y el bloque de Photoshop. El archivo cortado llega al plotter con la misma información que salió del diseño.

La única diferencia contra el original es la mínima pérdida propia de volver a comprimir un JPG. El cortador guarda al **100% de calidad y sin submuestreo de color**, el máximo posible: el error medido sobre los archivos de prueba es de 0.05 sobre 255. A cambio, los archivos cortados pesan bastante más que el original — es tela bien impresa a costa de disco. Los PNG no pierden nada.

### Si un archivo no declara su resolución

El script avisa con `[AVISO] El archivo no declara densidad`. Cuando eso pasa asume 150 DPI y **las medidas quedan mal**: un archivo de 254 DPI leído como 150 mide un 69% de más y termina marcado como error. Photoshop e Illustrator siempre incluyen la resolución al exportar, así que ese aviso significa que el archivo pasó por otra herramienta. Hay que reexportarlo.

---

## Instalación (solo la primera vez)

### Paso 1 — Instalar Python

Python es el programa que necesita la computadora para ejecutar el script. Es gratis y oficial.

1. Abrir el navegador (Chrome, Edge, Firefox) e ir a esta dirección:
   **https://www.python.org/downloads/**

2. Hacer clic en el botón amarillo grande que dice **"Download Python"** (la versión más reciente está bien).

3. Cuando termine de descargar, hacer doble clic en el archivo descargado (algo como `python-3.XX.X-amd64.exe`).

4. **MUY IMPORTANTE:** En la primera pantalla del instalador, antes de hacer clic en "Install Now", **marcar la casilla que dice "Add python.exe to PATH"** (está en la parte de abajo de la ventana). Si no se marca esta casilla, el script no va a funcionar.

5. Hacer clic en **"Install Now"** y esperar a que termine.

6. Cuando aparezca "Setup was successful", cerrar el instalador.

7. **Reiniciar la computadora** (importante para que los cambios tengan efecto).

### Paso 2 — Instalar las librerías Pillow y ReportLab

Pillow es la herramienta que el script usa para abrir, cortar y grabar el código en las imágenes. ReportLab es la que arma los PDF de etiquetado y de costura. Hacen falta las dos.

1. Hacer clic en el botón de Inicio de Windows y escribir **`cmd`**
2. Aparece "Símbolo del sistema" → hacer clic para abrirlo (se abre una ventana negra).
3. Escribir o copiar este comando y presionar ENTER:
   ```
   pip install Pillow reportlab
   ```
4. Esperar a que termine (va a mostrar un mensaje "Successfully installed...").
5. Cerrar la ventana negra.

### Paso 3 — Guardar los archivos

1. Crear una carpeta en el escritorio llamada **"Cortador Innova"** (o donde sea más cómodo).
2. Copiar adentro las tres subcarpetas del sistema, **sin cambiarles el nombre ni sacarlas de lugar**:
   - **`cortador/`** → `cortador_innova.py` y `CORTAR_FONDOS.bat` (el lanzador para abrir con doble clic)
   - **`etiquetador/`** → `generar_lista_etiquetado.py` y su `.bat`
   - **`costura/`** → `generar_costura.py` y su `.bat`

El cortador busca a los otros dos scripts en esas carpetas para llamarlos solo al terminar. Si `costura/` no está donde corresponde, el PDF de costura simplemente no se genera y el resto del proceso sigue igual.

¡Listo! La instalación ya está hecha. No hay que repetirla nunca más.

---

## Cómo usar el cortador (uso diario)

1. Poner todos los fondos de la semana (JPG y/o PNG) en una carpeta cualquiera.
2. Hacer **doble clic** en `CORTAR_FONDOS.bat`.
3. Se abre una ventana negra que pide la carpeta. **Arrastrar la carpeta con los fondos hasta la ventana** (el path se va a escribir solo).
4. Presionar **ENTER**.
5. La ventana muestra el último código usado y pregunta desde cuál arrancar:
   ```
   Ultimo codigo usado: COD042
   Iniciar desde [COD043]:
   ```
   **Presionar ENTER sin escribir nada** para seguir la numeración donde quedó la semana pasada. Solo escribir un número si hace falta forzar otro arranque (por ejemplo, repetir una corrida que salió mal).
6. Esperar a que termine. Va a procesar cada archivo y mostrar qué hizo con cada uno, y después va a generar solo la lista de etiquetado y el PDF de costura.
7. Al final, dentro de la carpeta original aparecen las subcarpetas **`originales`**, **`cortados`**, **`etiquetados`** y **`costura`**. Los archivos listos para sublimar están en `cortados`, nombrados como `COD001 - nombre_original.ext`, cada uno con el código grabado en la esquina superior derecha.
8. La ventana muestra el total de **metros lineales de tela** que se van a usar — anotar ese número para descontarlo del stock.

---

## Código de identificación

Al procesar cada imagen el script asigna automáticamente un código correlativo que se graba de dos formas:

**En la imagen** — un badge con texto negro sobre fondo blanco semitransparente aparece en la esquina superior derecha de cada archivo en `cortados`, girado 90°. El tamaño es fijo: mide alrededor de **0.95cm impreso** a 150dpi, chico como para no molestar en el fondo terminado pero legible sobre la mesa de trabajo.

**En el nombre del archivo** — todos los archivos en `cortados` incluyen el código al inicio del nombre:

```
COD001 - Flor Gonzalez - 290x200.jpg
COD002 - Maria Soledad - 500x290_IZQUIERDO.jpg
COD002 - Maria Soledad - 500x290_DERECHO.jpg
```

En los diseños que se cortan en dos paños, **uno solo lleva el badge** en la imagen: el paño **DERECHO** si el corte fue vertical, el **SUPERIOR** si fue horizontal. En los dos casos el badge queda del lado contrario a la costura. Ambos paños llevan el código en el nombre del archivo para que puedan asociarse.

El contador **no reinicia**: el script guarda el último código usado en un archivo `ultimo_codigo.txt` y en la corrida siguiente propone continuar desde ahí. Así los códigos no se repiten entre semanas.

### Integración con la herramienta de etiquetado

Los archivos de `cortados` — que ya tienen el código en el nombre — son compatibles directamente con **INNOVA Etiquetado** (`index.html`). Al cargar la carpeta `cortados` en esa herramienta, cada diseño aparece automáticamente con su código, cliente, medida y miniatura listos para verificar e imprimir la etiqueta 50×50mm para la impresora DT01.

En la práctica no hace falta cargar la carpeta a mano: el cortador ya deja en `etiquetados/` un archivo `lista_etiquetado_<fecha>.json` que se importa en esa herramienta con el botón **Importar lista**.

---

## Cómo se decide el corte

El rollo de tela mide **1.60m de ancho × 10m de largo**. Los paños se apilan en columna para sublimar por calandrado.

| Caso | Qué hace el script |
|---|---|
| Al menos un lado del diseño ≤ 1.60m | **No corta** — guarda con código en la imagen |
| Ambos lados > 1.60m, los dos cortes son posibles | **Corte vertical** (costura menos visible), salvo que el horizontal ahorre más de 30cm de tela |
| Solo un eje de corte produce paños que entran en el rollo | Usa **ese eje** obligatoriamente |
| Ningún corte produce paños que entren | **Marca error** (caso especial que necesita tratamiento manual) |

El **solape de costura es de 0.45cm a cada lado del corte** (0.90cm en total), para que la máquina de coser consuma esa parte y el diseño quede continuo al unir los paños.

---

## Preguntas frecuentes

**¿Qué pasa con los archivos originales?**
No se modifican, pero **se mueven**: el script los saca de la carpeta y los deja intactos dentro de la subcarpeta `originales`. Los archivos procesados van a `cortados`. Como la carpeta original queda vacía de imágenes, conviene apuntar el script a una carpeta de trabajo y no a un archivo maestro de diseños.

**¿Soporta JPG y PNG?**
Sí, ambos formatos. Los PNG conservan transparencia si la tienen.

**¿Qué pasa si dejo otros archivos en la carpeta (PDF, PSD, etc.)?**
Los ignora. Solo procesa archivos `.jpg`, `.jpeg` y `.png`.

**¿El script cambia los colores del diseño?**
No. No convierte espacios de color: un CMYK sale CMYK y un Adobe RGB sale Adobe RGB, cada uno con su perfil ICC original incrustado. Nunca pasa nada a sRGB. Lo único que cambia es la mínima pérdida de recomprimir el JPG, imperceptible a simple vista.

**¿Cómo sé cuántos metros de tela voy a usar?**
Al final del proceso, la ventana muestra `METROS LINEALES: X.XXm`. Ese es el total a descontar del inventario.

**¿Qué significa el código COD001 que aparece en los archivos?**
Es un identificador correlativo que el script asigna automáticamente a cada diseño. Aparece en la esquina superior derecha de la imagen (badge blanco) y al inicio del nombre del archivo. Permite asociar cada paño físico con su cliente en la herramienta de etiquetado sin depender de la memoria del operador.

**¿Los códigos arrancan de nuevo en COD001 cada semana?**
No. El script recuerda el último código que usó y propone seguir desde el siguiente. Si querés forzar otro número de arranque, escribilo cuando lo pregunte al principio de la corrida.

**¿Por qué uno de los dos paños cortados no tiene el badge?**
Con grabarlo una vez alcanza para identificar el diseño. Lo lleva el paño DERECHO en los cortes verticales y el SUPERIOR en los horizontales; el otro paño lleva el código en el nombre del archivo pero no en la imagen.

**¿El código se puede usar con la herramienta de etiquetado?**
Sí. Se puede importar el `lista_etiquetado_<fecha>.json` que quedó en `etiquetados/`, o cargar la carpeta `cortados` directamente en `index.html`: la herramienta lee el código del nombre del archivo y lo asocia con cada cliente para imprimir las etiquetas 50×50mm.

**¿Tengo que ejecutar algo más después del cortador?**
No. Al terminar de cortar, el script llama solo al generador de etiquetado y a este al de costura. Los `.bat` de `etiquetador/` y `costura/` están para volver a generar esos PDF por separado si hizo falta corregir algo.

**Me aparece el error "python no se reconoce como comando"**
Significa que al instalar Python no se marcó la casilla "Add python.exe to PATH". Solución: desinstalar Python desde Panel de Control → Programas, volver a instalarlo y esta vez marcar esa casilla en la primera pantalla.

**¿Puedo cambiar el margen de costura o el ancho del rollo?**
Sí, abriendo una terminal y ejecutando el script con opciones. Por ejemplo:
```
python cortador_innova.py "C:\Fondos" --margen 0.50 --ancho-rollo 155
```
También se puede mandar la salida a otro lado con `--salida "D:\otra\carpeta"`. Para uso normal con doble clic en el `.bat`, los valores por defecto (0.45cm y 160cm) ya están configurados.
