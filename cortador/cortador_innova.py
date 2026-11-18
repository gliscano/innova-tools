r"""
INNOVA - Cortador de Fondos Fotograficos para Sublimacion
Detecta automaticamente si un fondo necesita corte y en que eje.

LOGICA DE CORTE:
  El rollo de tela tiene 160cm de ancho x 1000cm de largo.
  Los panos se apilan en columna para sublimacion por calandrado.

  1. Si al menos un lado <= 160cm -> no corta (copia el archivo a la salida)
  2. Si ambos lados > 160cm:
     a. Verificar que el pano resultante ENTRE en el rollo (lado corto <= 160cm)
     b. Si solo un eje produce panos validos -> ese eje
     c. Si ambos ejes producen panos validos -> preferir vertical,
        salvo que desperdicie mas de 30cm extra vs horizontal
     d. Si ningun corte en 2 panos entra -> 3 o mas panos IGUALES, siempre
        en HORIZONTAL (cada pano <= 160cm con el margen incluido). Ej: 500x400
        -> 3 panos de 500 x ~134cm; 1200x500 -> 4 panos de 1200 x ~126cm.
        Sufijos: _SUPERIOR, _MEDIO1.., _INFERIOR.
  3. Si el nombre dice "horizontal" o "vertical" -> corta SIEMPRE en ese eje,
     aunque el diseno entre sin corte. Si 2 panos no entran en el rollo, lo
     divide en 3 o mas panos iguales en ese eje (vertical: _IZQUIERDO,
     _CENTRO1.., _DERECHO).

  Al finalizar, muestra los metros lineales de tela necesarios, separados en
  poliester y neoprene ("neoprene"/"neopreno" en el nombre).

CODIGO DE IDENTIFICACION:
  Cada diseno recibe un codigo correlativo (COD001, COD002, ...) que se
  graba visualmente en la esquina superior derecha de la imagen de salida
  (badge blanco semitransparente con texto negro, de tamano fijo impreso:
  ~3.8cm x 1cm, a 0.5cm del borde superior para que entre en el bolsillo de
  5cm y a 2.5cm del lateral para que no se pierda en la costura, sin importar
  el DPI del archivo) y se incluye al inicio del nombre del archivo.
  En disenos cortados, solo un pano lleva el badge: el DERECHO en cortes
  verticales, el SUPERIOR en horizontales; todos los panos llevan el codigo
  en el nombre del archivo.
  Los fondos de neoprene no llevan badge: el codigo va solo en el nombre.
  El contador es persistente: el ultimo codigo usado se guarda en
  ultimo_codigo.txt (junto al script) y al arrancar se propone el siguiente.

CALIDAD:
  Avisa (sin frenar el corte) si la imagen tiene menos de 72 DPI, si parece
  borrosa o ampliada, o si parece pixelada. Es una heuristica: ver
  evaluar_calidad().

ESTRUCTURA DE CARPETAS RESULTANTE:
  /Fondos semana/
    originales/     <- JPG/PNG originales sin modificar
    cortados/       <- panos procesados con codigo grabado
    etiquetados/    <- JSON + tabla.pdf + etiquetas.pdf (generados automaticamente)
    costura/        <- costura_<cierre>.pdf (generado automaticamente)

USO:
  python cortador_innova.py                          -> Usa la carpeta actual
  python cortador_innova.py "C:\ruta\a\carpeta"      -> Usa la carpeta indicada
  python cortador_innova.py --margen 0.50             -> Cambia el margen (cm)

REQUISITOS:
  pip install Pillow reportlab
"""

import os
import sys
import math
import time
import json
import shutil
import struct
import datetime
import subprocess
import argparse
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageStat, ImageChops
    Image.MAX_IMAGE_PIXELS = None
except ImportError:
    print("")
    print("ERROR: No se encontro la libreria Pillow.")
    print("  Instalala ejecutando:  pip install Pillow")
    print("  Luego volve a correr este script.")
    print("")
    sys.exit(1)


# --- Configuracion por defecto ------------------------------------------------
MARGEN_CM = 0.45          # Margen de seguridad para costura (en cm)
ANCHO_ROLLO_CM = 160      # Ancho maximo del rollo de tela (en cm)
UMBRAL_DESPERDICIO = 30   # Diferencia en cm para cambiar de vertical a horizontal
CALIDAD_JPG = 100         # Calidad de exportacion JPG (1-100). 100 = maxima
                          # fidelidad de color; el archivo pesa mas pero el
                          # error de recompresion baja a un tercio.
MAX_PX_OPTIMIZE = 80_000_000   # Limite de pixeles para usar optimize=True al
                          # guardar JPG (ver _guardar). Por encima, libjpeg
                          # necesita GB de buffer extra y se queda sin memoria.
EXTENSIONES = {'.jpg', '.jpeg', '.png'}

# Badge del codigo: medidas IMPRESAS en cm, iguales en todos los fondos sin
# importar su DPI. Tiene que caber en el bolsillo superior, que mide 5cm en los
# fondos mas chicos (7.5cm en el resto): margen + largo = 4.5cm.
BADGE_LETRA_CM = 0.76     # Tamano de la letra
BADGE_LARGO_MAX_CM = 3.8  # Largo maximo del badge (vertical, ya rotado)
BADGE_MARGEN_CM = 0.5     # Separacion del borde superior
BADGE_MARGEN_LATERAL_CM = 2.5  # Separacion del borde derecho: el lateral se
                          # dobla al coser y un badge mas pegado se perdia.

# Corte en 3 o mas panos (fondos que no entran en 2 panos)
LARGO_ROLLO_CM = 1000     # Largo del rollo: un pano mas largo genera un aviso

# Deteccion de baja calidad (heuristica, solo avisa; ver evaluar_calidad)
CALIDAD_DPI_MIN = 72          # Por debajo, resolucion baja para impresion
CALIDAD_MUESTRA_PX = 512      # Lado de cada zona analizada (pixeles nativos)
CALIDAD_ZONAS = 5             # Por lado: se analizan ZONAS x ZONAS recortes
CALIDAD_NITIDEZ_MIN = 0.47    # Detalle fino / detalle a escala 1/2. Calibrado con
                              # fotos reales: originales 0.49-1.0, ampliadas 2x
                              # o mas y desenfocadas 0.36-0.6.
CALIDAD_PIXELADO_MAX = 3.0    # Periodicidad de bloques. Originales 1.0-1.6 (aun
                              # en JPG calidad 60), ampliadas "vecino" 3.3 o mas.
# ------------------------------------------------------------------------------


def _cargar_fuente(size):
    """Carga una fuente TrueType del sistema. Si no encuentra ninguna usa el default de Pillow."""
    rutas = [
        "arial.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/Arial.ttf",
        "C:/Windows/Fonts/arialbd.ttf",   # Arial Bold
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Arial.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for ruta in rutas:
        try:
            return ImageFont.truetype(ruta, size)
        except (OSError, IOError):
            pass
    # Fallback: fuente bitmap incluida en Pillow
    try:
        return ImageFont.load_default(size=size)   # Pillow >= 10
    except TypeError:
        return ImageFont.load_default()             # Pillow < 10


def _colores_badge(modo):
    """
    Devuelve (color_pill, color_texto) expresados en el modo de la imagen.
    No hay conversion de espacio de color: se escriben los valores directos de
    cada modo, asi un CMYK nunca pasa por RGB.
      CMYK -> blanco = sin tinta; texto = solo canal K (evita negro de registro
              al 300% de tinta, impracticable en sublimacion).
    """
    if modo == 'CMYK':
        return (0, 0, 0, 0), (0, 0, 0, 235)
    if modo == 'RGBA':
        return (255, 255, 255, 255), (20, 20, 20, 255)
    if modo == 'LA':
        return (255, 255), (20, 255)
    if modo in ('I;16', 'I;16B', 'I;16L'):
        return 65535, 5140
    if modo == 'I':
        return 65535, 5140
    if modo in ('L', 'F'):
        return 255, 20
    return (255, 255, 255), (20, 20, 20)


def _medir_texto(codigo_str, font, font_size):
    """Devuelve (ancho, alto, offset_x, offset_y) del texto en pixeles."""
    draw = ImageDraw.Draw(Image.new("L", (1, 1)))
    # Compatible con Pillow 8+ y versiones anteriores
    try:
        bbox = draw.textbbox((0, 0), codigo_str, font=font)
        return bbox[2] - bbox[0], bbox[3] - bbox[1], -bbox[0], -bbox[1]
    except AttributeError:
        try:
            tw, th = draw.textsize(codigo_str, font=font)
        except Exception:
            tw = font_size * len(codigo_str) // 2
            th = font_size
        return tw, th, 0, 0


def grabar_codigo(img_original, codigo_str, dpi, copiar=True):
    """
    Devuelve img_original con el badge del codigo grabado en la esquina superior
    derecha, rotado 90 grados en sentido antihorario.
    - Badge: pill blanco al 80% de opacidad.
    - Tamano FIJO EN CM (BADGE_*), convertido a pixeles con el DPI del archivo:
      mide lo mismo impreso en un fondo de 72dpi que en uno de 300dpi y entra
      siempre en el bolsillo de 5cm. Si un codigo largo no entra en
      BADGE_LARGO_MAX_CM, se achica la letra.
    - CONSERVA EL MODO DE COLOR: el badge se compone con mascaras en escala de
      grises, de modo que una imagen CMYK sigue siendo CMYK al salir. Cambiar
      esto por un convert() reintroduce el desvio de color en sublimacion.
    - copiar=True no toca la imagen recibida. Con copiar=False la modifica en el
      lugar: usarlo solo cuando el llamador es dueno de la imagen (un recorte
      recien hecho), porque evita duplicar en RAM varios GB por fondo.
    """
    img = img_original
    if img.mode == 'P':   # paleta: no admite colores arbitrarios para el badge
        img = img.convert('RGBA' if 'transparency' in img.info else 'RGB')
    elif copiar:
        img = img.copy()
    w, h = img.size

    # Letra en cm -> px segun el DPI; se achica hasta que el pill (texto +
    # relleno de medio cuerpo por lado) entre en el largo maximo.
    largo_max_px = cm_a_px(BADGE_LARGO_MAX_CM, dpi)
    font_size = max(8, cm_a_px(BADGE_LETRA_CM, dpi))
    while True:
        font = _cargar_fuente(font_size)
        tw, th, txt_offset_x, txt_offset_y = _medir_texto(codigo_str, font, font_size)
        pad_x = int(font_size * 0.5)
        if tw + pad_x * 2 <= largo_max_px or font_size <= 8:
            break
        font_size = max(8, min(font_size - 1,
                               int(font_size * largo_max_px / (tw + pad_x * 2))))

    pad_y = int(font_size * 0.3)
    margin = int(font_size * 0.6)

    pill_w = tw + pad_x * 2
    pill_h = th + pad_y * 2
    radius = pill_h // 2

    # Dos mascaras en escala de grises (texto horizontal): una para el pill,
    # otra para las letras. La mascara ES la opacidad; el color se aplica
    # despues, ya expresado en el modo de la imagen.
    surf_w = pill_w + margin * 2
    surf_h = pill_h + margin * 2
    mask_pill = Image.new("L", (surf_w, surf_h), 0)
    mask_txt = Image.new("L", (surf_w, surf_h), 0)
    sx1, sy1 = margin, margin
    sx2, sy2 = margin + pill_w, margin + pill_h

    dp = ImageDraw.Draw(mask_pill)
    try:
        dp.rounded_rectangle([sx1, sy1, sx2, sy2], radius=radius, fill=204)  # 80%
    except (AttributeError, TypeError):
        dp.rectangle([sx1, sy1, sx2, sy2], fill=204)

    ImageDraw.Draw(mask_txt).text(
        (sx1 + pad_x + txt_offset_x, sy1 + pad_y + txt_offset_y),
        codigo_str, font=font, fill=255
    )

    # Rotar 90 grados antihorario (expand=True intercambia dimensiones)
    mask_pill = mask_pill.rotate(90, expand=True)
    mask_txt = mask_txt.rotate(90, expand=True)

    # Pegar con margen de seguridad en ambos ejes (evita que la costura tape el
    # badge). La superficie de las mascaras tiene 'margin' px de aire alrededor
    # del pill: se descuenta para que el margen impreso sea el del pill.
    margen_sup_px = cm_a_px(BADGE_MARGEN_CM, dpi)
    margen_lat_px = cm_a_px(BADGE_MARGEN_LATERAL_CM, dpi)
    pos = (w - mask_pill.width - margen_lat_px + margin, margen_sup_px - margin)

    color_pill, color_txt = _colores_badge(img.mode)
    img.paste(color_pill, pos, mask_pill)
    img.paste(color_txt, pos, mask_txt)

    return img   # mismo modo que la original


def leer_metadatos(img):
    """
    Extrae todos los metadatos del archivo original para reinyectarlos al
    guardar: perfil de color, EXIF, XMP de Adobe y el bloque Photoshop/IPTC.
    Se leen del archivo abierto ANTES de recortar, porque el recorte no arrastra
    los segmentos crudos del JPEG.
    """
    meta = {
        'icc_profile': img.info.get('icc_profile'),
        'exif': img.info.get('exif'),
        'xmp': img.info.get('xmp'),
        'extra': b'',
    }
    # APP13 (Photoshop / IPTC) no tiene parametro propio en Pillow: se reinyecta
    # como segmento crudo a traves de 'extra'.
    for marca, datos in getattr(img, 'applist', []):
        if marca == 'APP13':
            meta['extra'] += b'\xff\xed' + struct.pack('>H', len(datos) + 2) + datos
    return meta


def _guardar(img, ruta, ext, calidad, dpi_tuple, meta=None):
    """Guarda img en disco preservando su modo de color y todos sus metadatos.

    NO convierte espacios de color: un CMYK se guarda como CMYK y un RGB como
    RGB. Convertir aca (por ejemplo con .convert('RGB')) usa la formula naive de
    Pillow, que ignora el perfil ICC: el archivo saldria con pixeles RGB pero
    etiquetado con el perfil CMYK del original. Eso es lo que producia el
    desvio de color fuerte en los archivos CMYK al sublimar."""
    meta = meta or {}
    kwargs = {'dpi': dpi_tuple}
    for clave in ('icc_profile', 'exif', 'xmp'):
        if meta.get(clave):
            kwargs[clave] = meta[clave]

    if ext == '.png':
        kwargs.pop('xmp', None)          # PNG no lleva el XMP de Adobe
        img.save(ruta, 'PNG', **kwargs)
    else:
        kwargs['quality'] = calidad
        kwargs['subsampling'] = 0        # 4:4:4, sin submuestreo de color
        # optimize=True da tablas Huffman optimas: mismo pixel, ~3% menos peso.
        # Pero obliga a libjpeg a bufferizar TODOS los coeficientes DCT
        # (ancho x alto x bandas x 2 bytes: 3.2GB en un pano de 530 MP), encima
        # de la imagen fuente ya decodificada -> MemoryError en los fondos
        # grandes. Se aplica solo por debajo del umbral.
        if img.width * img.height <= MAX_PX_OPTIMIZE:
            kwargs['optimize'] = True
        if meta.get('extra'):
            kwargs['extra'] = meta['extra']
        if img.mode in ('RGBA', 'LA', 'P'):
            img = img.convert('RGB')     # JPEG no admite canal alfa ni paleta
        img.save(ruta, 'JPEG', **kwargs)


def cm_a_px(cm, dpi):
    """Convierte centimetros a pixeles segun los DPI."""
    return round(cm * dpi / 2.54)


def px_a_cm(px, dpi):
    """Convierte pixeles a centimetros segun los DPI."""
    return px * 2.54 / dpi


def obtener_dpi(img):
    """
    Obtiene los DPI horizontales de la imagen.
    Devuelve (dpi, del_metadato). Si del_metadato es False se uso el default de
    150 y TODAS las medidas en cm son sospechosas: el llamador debe avisar.
    Photoshop e Illustrator siempre exportan la densidad, asi que un archivo sin
    ella salio de otro lado o paso por un conversor que la perdio.
    """
    try:
        dpi_info = img.info.get('dpi')
        if dpi_info:
            dpi_x = dpi_info[0]
            if 50 < dpi_x < 1200:
                return int(round(dpi_x)), True
    except (TypeError, IndexError, ValueError):
        pass
    return 150, False


def evaluar_corte(ancho_cm, alto_cm, ancho_rollo_cm, margen_cm):
    """
    Evalua ambos ejes de corte y devuelve:
    - Si el pano resultante entra en el rollo (lado corto <= ancho_rollo)
    - El desperdicio de tela
    """
    # Corte vertical
    lado_corto_vert = ancho_cm / 2 + margen_cm
    entra_vert = lado_corto_vert <= ancho_rollo_cm
    desp_vert = ancho_rollo_cm - lado_corto_vert if entra_vert else None

    # Corte horizontal
    lado_corto_horiz = alto_cm / 2 + margen_cm
    entra_horiz = lado_corto_horiz <= ancho_rollo_cm
    desp_horiz = ancho_rollo_cm - lado_corto_horiz if entra_horiz else None

    return entra_vert, desp_vert, entra_horiz, desp_horiz


def corte_pedido(nombre):
    """
    Eje de corte pedido en el nombre del archivo: 'HORIZONTAL', 'VERTICAL',
    'AMBOS' (dice las dos palabras, se ignora) o None (decide el cortador).
    """
    n = nombre.lower()
    h = 'horizontal' in n
    v = 'vertical' in n
    if h and v:
        return 'AMBOS'
    if h:
        return 'HORIZONTAL'
    if v:
        return 'VERTICAL'
    return None


def es_neoprene(nombre):
    """Mismo criterio que detectar_especial() en generar_costura.py."""
    n = nombre.lower()
    return 'neoprene' in n or 'neopreno' in n


def calcular_n_panos(lado_cm, ancho_rollo_cm, margen_cm):
    """
    Cantidad de panos (3 o mas) en que se divide 'lado_cm' en partes iguales
    para que cada pano entre en el rollo. Los panos del medio llevan margen de
    costura de los dos lados, asi que cada uno mide lado/n + 2*margen.
    Devuelve None si no hay forma (margen mayor que el rollo).
      400cm de alto -> 3 panos de ~134cm;  500cm de alto -> 4 panos de ~126cm
    """
    util = ancho_rollo_cm - 2 * margen_cm
    if util <= 0:
        return None
    n = max(3, math.ceil(lado_cm / util))
    while lado_cm / n + 2 * margen_cm > ancho_rollo_cm:
        n += 1
    return n


def cajas_de_corte(ancho_px, alto_px, n, horizontal, margen_px):
    """
    Cajas (x1, y1, x2, y2) de n panos iguales sobre el eje elegido. Cada pano
    se extiende margen_px mas alla de cada corte, asi dos panos vecinos se
    solapan 2*margen y la maquina de coser lo consume. Para n=2 da exactamente
    las mismas cajas que el cortador de siempre (corte en lado // 2).
    """
    lado = alto_px if horizontal else ancho_px
    limites = [lado * i // n for i in range(n + 1)]
    cajas = []
    for i in range(n):
        a = limites[i] - margen_px if i > 0 else 0
        b = limites[i + 1] + margen_px if i < n - 1 else lado
        a, b = max(0, a), min(lado, b)
        cajas.append((0, a, ancho_px, b) if horizontal else (a, 0, b, alto_px))
    return cajas


def sufijos_panos(n, horizontal):
    """SUPERIOR, MEDIO1.., INFERIOR (horizontal) o IZQUIERDO, CENTRO1.., DERECHO."""
    if horizontal:
        primero, medio, ultimo = 'SUPERIOR', 'MEDIO', 'INFERIOR'
    else:
        primero, medio, ultimo = 'IZQUIERDO', 'CENTRO', 'DERECHO'
    return [primero] + [f"{medio}{k}" for k in range(1, n - 1)] + [ultimo]


def _zona_gris(img, caja):
    """Recorte chico en escala de grises SOLO para analizar (no se guarda)."""
    zona = img.crop(caja)
    if zona.mode.startswith('I') or zona.mode == 'F':
        zona = zona.convert('F')
        if zona.getextrema()[1] > 255:      # 16 bits -> 8 bits
            zona = zona.point(lambda v: v / 257.0)
        zona = zona.convert('L')
    elif zona.mode != 'L':
        zona = zona.convert('L')
    return zona


_LAPLACIANO = ImageFilter.Kernel((3, 3), [0, 1, 0, 1, -4, 1, 0, 1, 0], scale=1, offset=128)


def _energia_borde(zona):
    """Desvio del laplaciano: cuanto detalle fino tiene la zona."""
    return ImageStat.Stat(zona.filter(_LAPLACIANO)).stddev[0]


def evaluar_calidad(img, dpi):
    """
    Heuristica de calidad, solo para AVISAR (nunca bloquea ni modifica nada).
    Mira CALIDAD_ZONAS x CALIDAD_ZONAS recortes chicos a resolucion nativa (no
    se reescala la imagen entera: estos fondos pesan GB).
      - Resolucion: DPI < CALIDAD_DPI_MIN.
      - Borrosa / ampliada: en las zonas con dibujo, el detalle fino (pixel a
        pixel) es mucho menor que el detalle a escala 1/4. Una imagen ampliada
        tiene contornos pero no tiene nada entre pixel y pixel. Las zonas lisas
        (degrades de estudio) se ignoran para no marcarlas como borrosas.
      - Pixelada: en las zonas con dibujo, casi todos los pixeles son iguales
        a su vecino (bloques repetidos de una ampliacion "vecino mas cercano").
    Devuelve (lista de avisos, dict de metricas para el manifiesto).
    """
    avisos = []
    if dpi < CALIDAD_DPI_MIN:
        avisos.append(f"resolucion baja: {dpi} DPI (recomendado {CALIDAD_DPI_MIN} o mas)")

    w, h = img.size
    t = min(CALIDAD_MUESTRA_PX, w, h)
    if t < 64:
        return avisos, None
    z = CALIDAD_ZONAS
    nitideces, periodos = [], []
    for iy in range(z):
        for ix in range(z):
            x = (w - t) * ix // (z - 1)
            y = (h - t) * iy // (z - 1)
            zona = _zona_gris(img, (x, y, x + t, y + t))
            if _energia_borde(zona.resize((t // 4, t // 4), Image.BOX)) < 3:
                continue              # zona lisa (degrade, cielo): no dice nada
            mitad = zona.resize((t // 2, t // 2), Image.BOX)
            nitideces.append(_energia_borde(zona) / max(_energia_borde(mitad), 0.01))
            periodos.append(_periodicidad_bloques(zona))

    if len(nitideces) < 2:
        return avisos, {'zonas_con_detalle': len(nitideces)}
    nitideces.sort()
    periodos.sort()
    nitidez = nitideces[len(nitideces) // 2]
    pixelado = periodos[len(periodos) // 2]
    if pixelado > CALIDAD_PIXELADO_MAX:
        avisos.append(f"posible imagen PIXELADA (bloques repetidos, indice {pixelado:.1f})")
    elif nitidez < CALIDAD_NITIDEZ_MIN:
        avisos.append(f"posible imagen BORROSA o ampliada (nitidez {nitidez:.2f},"
                      f" minimo {CALIDAD_NITIDEZ_MIN})")
    return avisos, {'nitidez': round(nitidez, 2), 'pixelado': round(pixelado, 1),
                    'zonas_con_detalle': len(nitideces)}


def _periodicidad_bloques(zona):
    """
    Cuanto se repite un patron de bloques de 2 a 7 pixeles: en una imagen
    ampliada por "vecino mas cercano" los saltos entre pixeles vecinos caen
    todos en la misma columna de cada bloque. Devuelve el cociente entre esa
    columna y el resto (1 = sin patron).
    """
    t = zona.width
    dif = ImageChops.difference(zona.crop((1, 0, t, zona.height)),
                                zona.crop((0, 0, t - 1, zona.height)))
    perfil = list(dif.resize((t - 1, 1), Image.BOX).tobytes())
    mejor = 1.0
    for k in range(2, 8):
        fases = [sum(perfil[i::k]) / len(perfil[i::k]) for i in range(k)]
        pico = max(fases)
        if pico < 2:
            continue
        resto = (sum(fases) - pico) / (k - 1)
        mejor = max(mejor, pico / max(resto, 0.05))
    return mejor


def procesar_imagen(ruta_archivo, carpeta_salida, margen_cm, ancho_rollo_cm,
                    umbral_desp, calidad, codigo):
    """
    Procesa una imagen:
    - Si al menos un lado <= rollo -> graba el codigo y guarda en la salida
    - Si ambos > rollo -> corta segun las reglas de optimizacion;
      el primer pano lleva el badge, ambos panos llevan el codigo en el nombre
    Devuelve: (estado, mensaje, metros_lineales, datos)
      metros_lineales = lista con el lado mas largo de cada pano (en cm)
      datos = dict con la medida REAL del diseno para el manifiesto que
              consumen los scripts de costura y de stock
    """
    nombre = Path(ruta_archivo).stem
    ext = Path(ruta_archivo).suffix.lower()
    codigo_str = f"COD{codigo:03d}"

    try:
        img = Image.open(ruta_archivo)
    except Exception as e:
        return "ERROR", f"[ERROR] No se pudo abrir {nombre}{ext}: {e}", [], None

    dpi, dpi_del_metadato = obtener_dpi(img)
    margen_px = cm_a_px(margen_cm, dpi)
    dpi_tuple = (dpi, dpi)
    meta = leer_metadatos(img)   # ICC + EXIF + XMP + Photoshop/IPTC

    ancho_px = img.width
    alto_px = img.height
    ancho_cm = px_a_cm(ancho_px, dpi)
    alto_cm = px_a_cm(alto_px, dpi)

    aviso_dpi = ""
    if not dpi_del_metadato:
        aviso_dpi = (
            f"\n     [AVISO] El archivo no declara densidad: se asumieron {dpi} DPI.\n"
            f"     Las medidas y los metros lineales pueden estar equivocados.\n"
            f"     Reexportalo desde Photoshop/Illustrator con la resolucion incluida."
        )

    # Calidad (solo aviso): resolucion baja, borrosa/ampliada o pixelada
    try:
        avisos_calidad, metricas_calidad = evaluar_calidad(img, dpi)
    except Exception as e:      # el analisis es solo un aviso: nunca frena el corte
        avisos_calidad, metricas_calidad = [], {'error': str(e)}
    for aviso in avisos_calidad:
        aviso_dpi += f"\n     [aviso] Calidad: {aviso}."

    # El nombre puede pedir el eje de corte ("horizontal"/"vertical") y marcar
    # el fondo como neoprene, que no lleva el codigo grabado en la imagen.
    pedido = corte_pedido(nombre)
    if pedido == 'AMBOS':
        aviso_dpi += (
            "\n     [aviso] El nombre dice 'horizontal' y 'vertical': se ignora y"
            "\n     se decide el corte automaticamente."
        )
        pedido = None
    neoprene = es_neoprene(nombre)
    aviso_badge = "  [sin codigo grabado: neoprene]" if neoprene else ""

    datos = {
        'codigo': codigo_str,
        'archivo_original': os.path.basename(ruta_archivo),
        'ancho_cm': round(ancho_cm, 1),
        'alto_cm': round(alto_cm, 1),
        'dpi': dpi,
        'dpi_del_metadato': dpi_del_metadato,
        'tela': 'neoprene' if neoprene else 'poliester',
        'calidad': {'avisos': avisos_calidad, **(metricas_calidad or {})},
    }

    # --- CASO: entra en el rollo sin corte (y el nombre no pide cortar) ---
    if pedido is None and (ancho_cm <= ancho_rollo_cm or alto_cm <= ancho_rollo_cm):
        nombre_salida = f"{codigo_str} - {os.path.basename(ruta_archivo)}"
        ruta_destino = os.path.join(carpeta_salida, nombre_salida)

        # copiar=False: 'img' es nuestra y se cierra abajo. Evita duplicar en
        # RAM una imagen que en estos fondos pesa varios GB.
        if neoprene:
            img_con_codigo = img
        else:
            img_con_codigo = grabar_codigo(img, codigo_str, dpi, copiar=False)
        _guardar(img_con_codigo, ruta_destino, ext, calidad, dpi_tuple, meta)
        img_con_codigo.close()

        lado_largo = max(ancho_cm, alto_cm)
        datos.update({'panos': 1, 'corte': 'SIN CORTE', 'archivos': [nombre_salida],
                      'metros_lineales': round(lado_largo / 100, 2)})
        guardado = "guardado sin codigo grabado (neoprene)" if neoprene else "guardado con codigo"
        return "SIN CORTE", (
            f"[SIN CORTE] {codigo_str} · {nombre}{ext}\n"
            f"     {ancho_cm:.1f}cm x {alto_cm:.1f}cm @ {dpi} DPI\n"
            f"     Entra en el rollo de {ancho_rollo_cm}cm, {guardado}\n"
            f"     -> {nombre_salida}\n"
            f"     Metros lineales: {lado_largo / 100:.2f}m" + aviso_dpi
        ), [lado_largo], datos

    if pedido:
        # --- CASO: el nombre pide el eje; se corta asi aunque entre sin corte ---
        cortar_horizontal = pedido == 'HORIZONTAL'
        if cortar_horizontal:
            entra = ancho_cm <= ancho_rollo_cm or alto_cm / 2 + margen_cm <= ancho_rollo_cm
        else:
            entra = alto_cm <= ancho_rollo_cm or ancho_cm / 2 + margen_cm <= ancho_rollo_cm
        # Si 2 panos no entran, se divide en partes iguales en el eje pedido
        n_panos = 2 if entra else calcular_n_panos(
            alto_cm if cortar_horizontal else ancho_cm, ancho_rollo_cm, margen_cm)
    else:
        # --- CASO: ambos lados superan el rollo ---
        entra_vert, desp_vert, entra_horiz, desp_horiz = evaluar_corte(
            ancho_cm, alto_cm, ancho_rollo_cm, margen_cm
        )

        if not entra_vert and not entra_horiz:
            # No entra en 2 panos: 3 o mas panos iguales, SIEMPRE en horizontal
            # (solo se corta vertical si el nombre lo pide).
            cortar_horizontal = True
            n_panos = calcular_n_panos(alto_cm, ancho_rollo_cm, margen_cm)
        else:
            n_panos = 2
            # Decidir eje de corte
            if entra_vert and entra_horiz:
                cortar_horizontal = desp_vert - desp_horiz > umbral_desp
            elif entra_horiz:
                cortar_horizontal = True
            else:
                cortar_horizontal = False

    if n_panos is None:
        img.close()
        datos.update({'panos': 0, 'corte': 'ERROR', 'archivos': [], 'metros_lineales': 0})
        return "ERROR", (
            f"[ERROR] {nombre}{ext}\n"
            f"     {ancho_cm:.1f}cm x {alto_cm:.1f}cm @ {dpi} DPI\n"
            f"     Ningun corte produce panos que entren en el rollo de {ancho_rollo_cm}cm.\n"
            f"     Este fondo necesita un tratamiento especial." + aviso_dpi
        ), [], datos

    origen_corte = " (pedido en el nombre)" if pedido else ""
    if cortar_horizontal:
        tipo_corte = ("HORIZONTAL (superior / inferior)" if n_panos == 2
                      else f"HORIZONTAL en {n_panos} panos iguales (de arriba hacia abajo)")
    else:
        tipo_corte = ("VERTICAL (izquierdo / derecho)" if n_panos == 2
                      else f"VERTICAL en {n_panos} panos iguales (de izquierda a derecha)")

    cajas = cajas_de_corte(ancho_px, alto_px, n_panos, cortar_horizontal, margen_px)
    sufijos = sufijos_panos(n_panos, cortar_horizontal)

    # Nombres de salida: todos los panos llevan el codigo en el nombre
    nombres = [f"{codigo_str} - {nombre}_{suf}{ext}" for suf in sufijos]

    # Badge en el SUPERIOR (corte horizontal) o el DERECHO (corte vertical).
    # El neoprene no lleva badge en ningun pano.
    idx_badge = None if neoprene else (0 if cortar_horizontal else n_panos - 1)

    # Un pano por vez: recortar, grabar, guardar y liberar antes de pasar al
    # siguiente. Tener varios vivos a la vez multiplica el pico de RAM, que en
    # estos fondos se mide en GB.
    for k, (caja, nombre_pano) in enumerate(zip(cajas, nombres)):
        pano = img.crop(caja)
        if k == idx_badge:
            pano = grabar_codigo(pano, codigo_str, dpi, copiar=False)
        _guardar(pano, os.path.join(carpeta_salida, nombre_pano), ext, calidad, dpi_tuple, meta)
        pano.close()
        del pano

    img.close()

    metros_lineales = []
    lineas = []
    aviso_largo = ""
    for k, ((x1, y1, x2, y2), nombre_pano) in enumerate(zip(cajas, nombres)):
        pw_cm = px_a_cm(x2 - x1, dpi)
        ph_cm = px_a_cm(y2 - y1, dpi)
        largo = max(pw_cm, ph_cm)
        metros_lineales.append(largo)
        marca = '  [codigo grabado]' if k == idx_badge else ''
        lineas.append(f"     -> {nombre_pano}  ({pw_cm:.1f}cm x {ph_cm:.1f}cm)"
                      f" | Lineal: {largo / 100:.2f}m{marca}")
        if largo > LARGO_ROLLO_CM and not aviso_largo:
            aviso_largo = (f"\n     [aviso] Hay panos de {largo / 100:.2f}m: superan el largo"
                           f" del rollo ({LARGO_ROLLO_CM / 100:.0f}m).")

    datos.update({
        'panos': n_panos,
        'corte': 'HORIZONTAL' if cortar_horizontal else 'VERTICAL',
        'archivos': nombres,
        'metros_lineales': round(sum(metros_lineales) / 100, 2),
    })

    msg = (
        f"[OK] {codigo_str} · {nombre}{ext}{aviso_badge}\n"
        f"     Original: {ancho_cm:.1f}cm x {alto_cm:.1f}cm @ {dpi} DPI\n"
        f"     Corte: {tipo_corte}{origen_corte}\n"
        f"     Margen de costura: {margen_cm}cm ({margen_px}px)\n"
        + "\n".join(lineas) + aviso_largo + aviso_dpi
    )
    return "OK", msg, metros_lineales, datos


NOMBRE_MANIFIESTO = 'medidas_reales.json'


def escribir_manifiesto(carpeta_salida, medidas, total_metros):
    """
    Escribe cortados/medidas_reales.json con la medida REAL de cada diseno,
    calculada desde los pixeles y el DPI del archivo.

    Existe porque el nombre del archivo que manda el cliente no siempre coincide
    con el diseno: nuestros fondos llevan 15cm extra arriba para el bolsillo que
    los sostiene del soporte, y ese agregado no figura en el nombre. Cotizar y
    descontar stock por el nombre subestima la tela. generar_costura.py lee este
    archivo cuando existe y recurre al nombre solo si falta.
    """
    if not medidas:
        return None
    ruta = os.path.join(carpeta_salida, NOMBRE_MANIFIESTO)
    paquete = {
        'innova_medidas': 1,
        'generado': datetime.datetime.now().isoformat(timespec='seconds'),
        'nota': 'Medidas en cm calculadas desde pixeles y DPI, no desde el nombre.',
        'metros_lineales_total': round(total_metros, 2),
        'disenos': medidas,
    }
    try:
        with open(ruta, 'w', encoding='utf-8') as fh:
            json.dump(paquete, fh, ensure_ascii=False, indent=1)
        print(f"  Medidas reales -> {ruta}")
        print("")
        return ruta
    except Exception as e:
        print(f"  [aviso] No se pudo escribir {NOMBRE_MANIFIESTO}: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(
        description='INNOVA - Cortador de fondos fotograficos para sublimacion'
    )
    parser.add_argument(
        'carpeta',
        nargs='?',
        default='.',
        help='Carpeta con los archivos JPG/PNG (default: carpeta actual)'
    )
    parser.add_argument(
        '--margen',
        type=float,
        default=MARGEN_CM,
        help=f'Margen de costura en cm (default: {MARGEN_CM})'
    )
    parser.add_argument(
        '--ancho-rollo',
        type=float,
        default=ANCHO_ROLLO_CM,
        help=f'Ancho del rollo de tela en cm (default: {ANCHO_ROLLO_CM})'
    )
    parser.add_argument(
        '--umbral',
        type=float,
        default=UMBRAL_DESPERDICIO,
        help=f'Diferencia de desperdicio en cm para cambiar de vertical a horizontal (default: {UMBRAL_DESPERDICIO})'
    )
    parser.add_argument(
        '--calidad',
        type=int,
        default=CALIDAD_JPG,
        help=f'Calidad JPG de salida 1-100 (default: {CALIDAD_JPG})'
    )
    parser.add_argument(
        '--salida',
        type=str,
        default=None,
        help='Carpeta de salida (default: subcarpeta "cortados" dentro de la carpeta de entrada)'
    )

    args = parser.parse_args()
    carpeta = os.path.abspath(args.carpeta)

    if not os.path.isdir(carpeta):
        print(f"\nERROR: La carpeta no existe: {carpeta}")
        sys.exit(1)

    # Buscar archivos de imagen en la raiz de la carpeta
    archivos = sorted([
        f for f in os.listdir(carpeta)
        if Path(f).suffix.lower() in EXTENSIONES
    ])

    if not archivos:
        print(f"\nNo se encontraron archivos JPG/PNG en: {carpeta}")
        sys.exit(0)

    # Crear subcarpetas
    carpeta_originales = os.path.join(carpeta, 'originales')
    carpeta_salida     = args.salida or os.path.join(carpeta, 'cortados')
    os.makedirs(carpeta_originales, exist_ok=True)
    os.makedirs(carpeta_salida,     exist_ok=True)

    # Cabecera
    print("")
    print("=" * 62)
    print("  INNOVA - Cortador de Fondos para Sublimacion")
    print("=" * 62)
    print(f"  Carpeta:       {carpeta}")
    print(f"  Originales:    {carpeta_originales}")
    print(f"  Cortados:      {carpeta_salida}")
    print(f"  Archivos:      {len(archivos)} JPG/PNG encontrados")
    print(f"  Margen:        {args.margen}cm")
    print(f"  Ancho rollo:   {args.ancho_rollo}cm")
    print(f"  Umbral desp.:  {args.umbral}cm")
    print(f"  Calidad:       {args.calidad}%")
    print("=" * 62)
    print("")

    # Contador persistente: leer ultimo codigo usado
    archivo_contador = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'ultimo_codigo.txt'
    )
    ultimo = 0
    try:
        ultimo = int(open(archivo_contador).read().strip())
    except Exception:
        pass
    siguiente = ultimo + 1
    print(f"  Ultimo codigo usado: COD{ultimo:03d}")
    resp = input(f"  Iniciar desde [COD{siguiente:03d}]: ").strip()
    if resp:
        try:
            inicio_codigo = max(1, int(resp))
        except ValueError:
            print("  Valor invalido, se usa el siguiente automatico.")
            inicio_codigo = siguiente
    else:
        inicio_codigo = siguiente
    fin_codigo = inicio_codigo + len(archivos) - 1
    print(f"  Codigos:       COD{inicio_codigo:03d} - COD{fin_codigo:03d}")
    print("=" * 62)
    print("")

    # Mover originales a subcarpeta (mezcla si ya existen)
    print("  Moviendo originales...")
    for archivo in archivos:
        src = os.path.join(carpeta, archivo)
        dst = os.path.join(carpeta_originales, archivo)
        try:
            os.replace(src, dst)          # atomico, sobreescribe si existe
        except OSError:
            shutil.copy2(src, dst)        # fallback: copiar + borrar
            try:
                os.remove(src)
            except OSError:
                pass
    print(f"  {len(archivos)} archivo(s) -> originales/")
    print("")

    # Procesar desde originales/
    inicio = time.time()
    cortados = 0
    sin_corte = 0
    errores = 0
    todos_los_metros = []
    medidas_reales = []
    contador_codigo = inicio_codigo - 1

    for i, archivo in enumerate(archivos, 1):
        contador_codigo += 1
        print(f"[{i}/{len(archivos)}] Procesando {archivo}...")
        ruta = os.path.join(carpeta_originales, archivo)
        estado, mensaje, metros, datos = procesar_imagen(
            ruta, carpeta_salida,
            args.margen, args.ancho_rollo, args.umbral, args.calidad,
            contador_codigo
        )
        print(mensaje)
        print("")

        todos_los_metros.extend(metros)
        if datos:
            medidas_reales.append(datos)

        if estado == "OK":
            cortados += 1
        elif estado == "SIN CORTE":
            sin_corte += 1
        else:
            errores += 1

    # Resumen del corte
    duracion = time.time() - inicio
    total_metros = sum(todos_los_metros) / 100
    total_panos  = len(todos_los_metros)
    metros_neoprene = sum(d.get('metros_lineales', 0) for d in medidas_reales
                          if d.get('tela') == 'neoprene')
    metros_poliester = total_metros - metros_neoprene

    print("=" * 62)
    print("  RESUMEN CORTE")
    print("-" * 62)
    print(f"  Cortados:      {cortados}")
    print(f"  Sin corte:     {sin_corte}")
    print(f"  Errores:       {errores}")
    print(f"  Tiempo total:  {duracion:.1f} segundos")
    print(f"  Archivos en:   {carpeta_salida}")
    print("-" * 62)
    print(f"  Total panos:           {total_panos}")
    print(f"  Tela poliester:        {metros_poliester:.2f}m")
    print(f"  Tela neoprene:         {metros_neoprene:.2f}m")
    print(f"  METROS LINEALES:       {total_metros:.2f}m")
    print("=" * 62)
    print("")

    # Manifiesto de medidas REALES (medidas desde los pixeles y el DPI, no desde
    # el nombre del archivo). Lo consume generar_costura.py para cotizar y sirve
    # de referencia para descontar del stock.
    escribir_manifiesto(carpeta_salida, medidas_reales, total_metros)

    sin_dpi = [d['codigo'] for d in medidas_reales if not d.get('dpi_del_metadato')]
    if sin_dpi:
        print("  [AVISO] Sin densidad declarada: " + ", ".join(sin_dpi))
        print("          Sus medidas y metros lineales son estimados a 150 DPI.")
        print("")

    con_calidad = [d['codigo'] for d in medidas_reales
                   if d.get('calidad', {}).get('avisos')]
    if con_calidad:
        print("  [AVISO] Revisar calidad (baja resolucion, borrosa o pixelada): "
              + ", ".join(con_calidad))
        print("          Es una deteccion orientativa: mirar el archivo antes de imprimir.")
        print("")

    # Guardar ultimo codigo usado para la proxima corrida
    try:
        open(archivo_contador, 'w').write(str(contador_codigo))
        print(f"  Ultimo codigo guardado: COD{contador_codigo:03d}")
    except Exception as e:
        print(f"  [aviso] No se pudo guardar el contador: {e}")
    print("")

    # Llamar automaticamente al generador de etiquetado
    # Busca en la misma carpeta del cortador y luego en ../etiquetador/
    _base = os.path.dirname(os.path.abspath(__file__))
    _candidatos = [
        os.path.join(_base, 'generar_lista_etiquetado.py'),
        os.path.join(_base, '..', 'etiquetador', 'generar_lista_etiquetado.py'),
    ]
    script_etiqueta = next((c for c in _candidatos if os.path.exists(c)), None)
    if script_etiqueta:
        cierre = datetime.date.today().isoformat()
        print("=" * 62)
        print("  INNOVA - Generando lista de etiquetado...")
        print("=" * 62)
        print("")
        subprocess.run(
            [sys.executable, script_etiqueta,
             carpeta_salida, '--cierre', cierre, '--sin-pausa'],
            check=False
        )
    else:
        print("[AVISO] No se encontro generar_lista_etiquetado.py")
        print("  Coloca ese archivo en la misma carpeta que el cortador.")
        print("  Luego genera la lista manualmente arrastrando cortados/ al .bat")
        print("")

    input("Listo. Enter para salir...")


if __name__ == '__main__':
    main()
