# INNOVA — Cortador de Fondos para Sublimación

Herramienta para dividir automáticamente los diseños de fondos fotográficos que no entran en el rollo de tela de 1.60m, aplicar el solape de costura, grabar un código de identificación en cada imagen y calcular los metros lineales para descontar del inventario.

---

## ¿Qué hace esta herramienta?

Toma todos los archivos JPG y PNG de una carpeta y, según las medidas de cada diseño, decide automáticamente qué hacer con cada uno:

- **Si el diseño entra en el rollo de 1.60m** (al menos uno de sus lados mide 1.60m o menos): lo guarda en la carpeta de salida con su código de identificación grabado en la imagen.
- **Si ambos lados superan 1.60m:** lo divide en dos paños con un solape de costura de 0.45cm a cada lado del corte. El script elige automáticamente si conviene cortar vertical (izquierdo/derecho) u horizontal (superior/inferior), priorizando la costura menos visible y minimizando el desperdicio de tela. Solo el primer paño lleva el badge del código; ambos paños llevan el código en el nombre del archivo.
- **A cada imagen** se le asigna un código correlativo (`COD001`, `COD002`, ...) que se graba como badge blanco semitransparente en la **esquina superior derecha** de la imagen y al inicio del nombre del archivo en `cortados`.
- **Al finalizar**, muestra el total de metros lineales de tela necesarios para descontar del inventario.

Todos los archivos finales (cortados y sin cortar) quedan unificados en una sola carpeta llamada `cortados`, nombrados como `COD001 - nombre_original.ext`.

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

### Paso 2 — Instalar la librería Pillow

Pillow es la herramienta que el script usa para abrir, cortar y grabar el código en las imágenes.

1. Hacer clic en el botón de Inicio de Windows y escribir **`cmd`**
2. Aparece "Símbolo del sistema" → hacer clic para abrirlo (se abre una ventana negra).
3. Escribir o copiar este comando y presionar ENTER:
   ```
   pip install Pillow
   ```
4. Esperar a que termine (va a mostrar un mensaje "Successfully installed Pillow...").
5. Cerrar la ventana negra.

### Paso 3 — Guardar los archivos del cortador

1. Crear una carpeta en el escritorio llamada **"Cortador Innova"** (o donde sea más cómodo).
2. Copiar adentro estos dos archivos:
   - **`cortador_innova.py`** → el script principal
   - **`CORTAR_FONDOS.bat`** → el lanzador para abrir con doble clic

¡Listo! La instalación ya está hecha. No hay que repetirla nunca más.

---

## Cómo usar el cortador (uso diario)

1. Poner todos los fondos de la semana (JPG y/o PNG) en una carpeta cualquiera.
2. Hacer **doble clic** en `CORTAR_FONDOS.bat`.
3. Se abre una ventana negra que pide la carpeta. **Arrastrar la carpeta con los fondos hasta la ventana** (el path se va a escribir solo).
4. Presionar **ENTER**.
5. Esperar a que termine. Va a procesar cada archivo y mostrar qué hizo con cada uno.
6. Al final, dentro de la carpeta original aparece una subcarpeta llamada **`cortados`** con todos los archivos listos para sublimar, nombrados como `COD001 - nombre_original.ext`. Cada imagen tiene el código grabado en la esquina superior derecha.
7. La ventana muestra el total de **metros lineales de tela** que se van a usar — anotar ese número para descontarlo del stock.

---

## Código de identificación

Al procesar cada imagen el script asigna automáticamente un código correlativo que se graba de dos formas:

**En la imagen** — un badge con texto negro sobre fondo blanco semitransparente aparece en la esquina superior derecha de cada archivo en `cortados`. El tamaño del badge escala en proporción al tamaño de la imagen, por lo que es legible tanto en pantalla como sobre el fondo impreso o sublimado.

**En el nombre del archivo** — todos los archivos en `cortados` incluyen el código al inicio del nombre:

```
COD001 - Flor Gonzalez - 290x200.jpg
COD002 - Maria Soledad - 500x290_IZQUIERDO.jpg
COD002 - Maria Soledad - 500x290_DERECHO.jpg
```

En los diseños que se cortan en dos paños, **solo el primer paño** (IZQUIERDO o SUPERIOR) lleva el badge en la imagen. Ambos paños llevan el código en el nombre del archivo para que puedan asociarse.

El contador **reinicia en `COD001`** en cada corrida del script.

### Integración con la herramienta de etiquetado

Los archivos de `cortados` — que ya tienen el código en el nombre — son compatibles directamente con **INNOVA Etiquetado** (`INNOVA_Etiquetado.html`). Al cargar la carpeta `cortados` en esa herramienta, cada diseño aparece automáticamente con su código, cliente, medida y miniatura listos para verificar e imprimir la etiqueta 50×50mm para la impresora DT01.

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
No se modifican. El script solo lee los originales y guarda copias procesadas en la subcarpeta `cortados`.

**¿Soporta JPG y PNG?**
Sí, ambos formatos. Los PNG conservan transparencia si la tienen.

**¿Qué pasa si dejo otros archivos en la carpeta (PDF, PSD, etc.)?**
Los ignora. Solo procesa archivos `.jpg`, `.jpeg` y `.png`.

**¿Cómo sé cuántos metros de tela voy a usar?**
Al final del proceso, la ventana muestra `METROS LINEALES: X.XXm`. Ese es el total a descontar del inventario.

**¿Qué significa el código COD001 que aparece en los archivos?**
Es un identificador correlativo que el script asigna automáticamente a cada diseño de esa corrida. Aparece en la esquina superior derecha de la imagen (badge blanco) y al inicio del nombre del archivo. Permite asociar cada paño físico con su cliente en la herramienta de etiquetado sin depender de la memoria del operador.

**¿Por qué uno de los dos paños cortados no tiene el badge?**
Solo el primer paño (IZQUIERDO o SUPERIOR) lleva el badge en la imagen. El segundo paño (DERECHO o INFERIOR) lleva el código en el nombre del archivo pero no en la imagen, porque no es necesario grabarlo dos veces para identificar el diseño.

**¿El código se puede usar con la herramienta de etiquetado?**
Sí. Al cargar la carpeta `cortados` en `INNOVA_Etiquetado.html`, la herramienta lee el código del nombre del archivo automáticamente y lo asocia con cada cliente para imprimir las etiquetas 50×50mm.

**Me aparece el error "python no se reconoce como comando"**
Significa que al instalar Python no se marcó la casilla "Add python.exe to PATH". Solución: desinstalar Python desde Panel de Control → Programas, volver a instalarlo y esta vez marcar esa casilla en la primera pantalla.

**¿Puedo cambiar el margen de costura o el ancho del rollo?**
Sí, abriendo una terminal y ejecutando el script con opciones. Por ejemplo:
```
python cortador_innova.py "C:\Fondos" --margen 0.50 --ancho-rollo 155
```
Para uso normal con doble clic en el `.bat`, los valores por defecto (0.45cm y 160cm) ya están configurados.
