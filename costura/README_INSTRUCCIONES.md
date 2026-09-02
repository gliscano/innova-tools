# INNOVA — Generador de lista de costura

Herramienta que arma el PDF con el detalle y el costo de la costura de todos los fondos de un cierre, para pasarle al taller.

---

## ¿Cuándo se ejecuta?

**Normalmente no hay que ejecutarlo a mano.** Es el último eslabón de la cadena: el cortador llama al etiquetador y el etiquetador llama a este. Si la corrida del cortador terminó bien, el PDF de costura ya está hecho.

Se ejecuta por separado solo cuando hace falta **rehacer** el presupuesto: por ejemplo si se corrigió una medida mal escrita en el nombre de un archivo, o si cambiaron las tarifas.

---

## ¿Qué hace?

Lee todos los JPG y PNG de la carpeta `cortados` y, para cada diseño, decide qué tipo de costura necesita y cuánto sale. Después suma todo, agrega los viáticos y redondea.

**Cotiza por la medida real, no por la del nombre.** El cortador mide cada diseño desde los píxeles y deja esas medidas en `cortados/medidas_reales.json`; este script las lee de ahí. Es importante porque nuestros fondos llevan unos **15cm extra arriba para el bolsillo** que los sostiene del soporte, y el nombre que manda el cliente no los incluye. Cotizar por el nombre subestima la tela y la costura.

El cliente puede pedir un fondo de 290×150 (que entraría en el rollo, un solo paño) y el archivo real medir 290×165 con el bolsillo: ahí ya no entra y hay que unir dos paños. Son $2.180 contra $4.350.

Si el archivo `medidas_reales.json` no está, el script avisa en pantalla y vuelve a usar la medida del nombre.

Genera un solo archivo: `costura/costura_<fecha>.pdf`, con una tabla de una fila por diseño (número, código, cliente, medida, detalle de la costura, monto y un casillero para tildar), la fila de viáticos y el total.

> **Dónde queda:** la carpeta `costura` se crea **al lado** de la carpeta que le pasaste, no adentro. Si le pasás `/Fondos semana/cortados`, el PDF va a `/Fondos semana/costura`.

---

## Cómo se decide el tipo de costura

| Caso | Detalle en el PDF |
|---|---|
| Al menos un lado del diseño ≤ 160cm (entra en el rollo) | **1 Paño** |
| Ambos lados > 160cm y la unión mide hasta 450cm | **Unión hasta 4,5 m** |
| Ambos lados > 160cm y la unión mide más de 450cm | **Unión de 4,5 m en adelante** |
| El nombre del archivo dice "neoprene" o "neopreno" | **Piso Neoprene** (precio fijo, no importa la medida) |
| Ningún corte al medio entra en el rollo (haría falta más de 2 paños) | **Múltiples paños (cotizar manual)** |

Los diseños que necesitan más de dos paños salen en el PDF con la **fila pintada de amarillo y sin monto**, y además se listan al pie bajo el título "ATENCIÓN: los siguientes fondos requieren más de 2 paños y deben cotizarse manualmente". Hay que ponerles precio a mano antes de mandar el presupuesto.

Los dos paños de un mismo diseño cortado se cuentan **una sola vez**: se agrupan por código y medida.

---

## Tarifas

Vigentes a **marzo 2026**:

| Concepto | Monto |
|---|---|
| 1 paño (entra en el rollo, sin unión) | $ 2.180 |
| Unión de 2 paños, hasta 4,5 m | $ 4.350 |
| Unión de 2 paños, más de 4,5 m | $ 6.950 |
| Piso de neoprene | $ 2.350 |
| Viáticos (fijos, una vez por cierre) | $ 5.000 |

El total se **redondea para arriba al próximo múltiplo de $1.000**. El PDF muestra igual el subtotal bruto sin redondear, en letra chica debajo de la tabla, para poder controlar la cuenta.

### Cómo actualizar los precios

Abrir `generar_costura.py` con el Bloc de notas y cambiar los números del bloque que dice `tarifas (Marzo 2026)`, cerca del principio del archivo:

```python
PRECIO_1_PANO       = 2_180
PRECIO_UNION_CORTA  = 4_350
PRECIO_UNION_LARGA  = 6_950
PRECIO_NEOPRENE     = 2_350
VIATICOS            = 5_000
```

Los guiones bajos son separadores de miles: `2_180` es dos mil ciento ochenta. Conviene actualizar también el comentario con el mes, para saber de cuándo son los precios.

---

## Cómo ejecutarlo a mano

### Por terminal (la forma recomendada)

```
python generar_costura.py "C:\ruta\Fondos semana\cortados"
python generar_costura.py "C:\ruta\Fondos semana\cortados" --cierre 2026-05-30
```

| Parámetro | Default | Para qué |
|---|---|---|
| `carpeta` | pregunta al arrancar | La carpeta `cortados` |
| `--cierre` | la fecha de hoy | Identificador del lote; va en el nombre del PDF y en el encabezado |
| `--sin-pausa` | — | No espera ENTER al terminar. Lo usa la llamada automática; a mano no hace falta |

### Sobre el `.bat`

`GENERAR_COSTURA.bat` busca una carpeta llamada `cortados` **al lado del propio `.bat`**, y no acepta que se le arrastre una carpeta encima. Si la carpeta `cortados` de la semana está en otro lado — que es lo habitual — el `.bat` corta con un error y no genera nada.

Para una corrida suelta conviene usar la terminal como se muestra arriba. La otra opción es copiar `generar_costura.py` y `GENERAR_COSTURA.bat` adentro de la carpeta de la semana, al lado de `cortados`, y ahí sí funciona el doble clic.

---

## Instalación

Si se usa el sistema completo, ya quedó instalado con el cortador y no hay que hacer nada. Si no:

```
pip install reportlab
```

Este script no usa Pillow: no abre las imágenes, solo lee los nombres de los archivos.

---

## Preguntas frecuentes

**¿De dónde saca las medidas?**
De `cortados/medidas_reales.json`, que el cortador genera midiendo los píxeles y el DPI de cada archivo. Es la medida física real del fondo, con el bolsillo incluido. La medida del nombre solo se usa como respaldo si ese archivo no está.

**¿Por qué la medida del PDF no coincide con la del nombre del archivo?**
Porque el PDF muestra la medida real. Un fondo llamado `200x200` puede figurar como `200 x 215 cm`: esos 15cm son el bolsillo superior. Es la medida que hay que coser y la que hay que descontar del stock.

**¿Y si un archivo no tiene la medida en el nombre?**
Se omite del presupuesto y se avisa en pantalla con `[omitido] sin medida`. Ese fondo no aparece en el PDF ni suma al total, así que conviene revisar los avisos antes de mandarlo.

**¿El presupuesto siempre coincide con lo que hizo el cortador?**
Ahora sí en las medidas, porque las dos partes usan la misma fuente. Lo que este script todavía decide por su cuenta es el eje del corte: lo recalcula sin el solape de costura ni el criterio de desperdicio del cortador, así que en diseños justo en el límite de los 160cm puede elegir distinto. Ante la duda, mandan los archivos que están en `cortados`.

**¿Los viáticos se cobran una vez por fondo?**
No, una sola vez por cierre. Aparecen como una fila aparte al final de la tabla.

**¿Por qué el PDF no tiene el logo de INNOVA?**
Porque el script todavía no lo dibuja. El comentario al principio del archivo dice que alcanza con pegar la variable `LOGO_B64` de `generar_lista_etiquetado.py`, pero eso hoy no alcanza: falta además el código que la dibuje en el encabezado, como sí lo tiene el generador de etiquetado. El PDF sale bien igual, solo que con el encabezado de texto y sin logo.

**¿Qué es la columna "Check" del PDF?**
Un casillero vacío para tildar a mano a medida que el taller va entregando cada fondo.
