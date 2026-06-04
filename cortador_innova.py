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

  Al finalizar, muestra el total de metros lineales de tela necesarios.

CODIGO DE IDENTIFICACION:
  Cada diseno recibe un codigo correlativo (COD001, COD002, ...) que se
  graba visualmente en la esquina superior derecha de la imagen de salida
  (badge blanco semitransparente con texto negro) y se incluye al inicio
  del nombre del archivo.
  En disenos cortados, solo el primer pano (IZQUIERDO o SUPERIOR) lleva
  el badge; ambos panos llevan el codigo en el nombre del archivo.
  El contador reinicia en COD001 en cada corrida del script.

USO:
  python cortador_innova.py                          -> Usa la carpeta actual
  python cortador_innova.py "C:\ruta\a\carpeta"      -> Usa la carpeta indicada
  python cortador_innova.py --margen 0.50             -> Cambia el margen (cm)

REQUISITOS:
  pip install Pillow
"""

import os
import sys
import time
import argparse
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
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
CALIDAD_JPG = 97          # Calidad de exportacion JPG (1-100)
EXTENSIONES = {'.jpg', '.jpeg', '.png'}
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


def grabar_codigo(img_original, codigo_str):
    """
    Devuelve una COPIA de img_original con el badge del codigo grabado
    en la esquina superior derecha.
    - Badge: pill blanco al 80% de opacidad.
    - Texto: negro solido, fuente escalada al 1.2% del lado menor de la imagen.
    - No modifica la imagen original.
    """
    img = img_original.convert("RGBA")
    w, h = img.size

    # Escalar fuente segun el tamano de la imagen (min 28px para imagenes muy pequenas)
    font_size = max(28, int(min(w, h) * 0.012))
    font = _cargar_fuente(font_size)

    # Capa transparente donde se dibuja el badge
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Medir el texto (compatible con Pillow 8+ y versiones anteriores)
    try:
        bbox = draw.textbbox((0, 0), codigo_str, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        txt_offset_x = -bbox[0]
        txt_offset_y = -bbox[1]
    except AttributeError:
        try:
            tw, th = draw.textsize(codigo_str, font=font)
        except Exception:
            tw = font_size * len(codigo_str) // 2
            th = font_size
        txt_offset_x = 0
        txt_offset_y = 0

    pad_x = int(font_size * 0.5)
    pad_y = int(font_size * 0.3)
    margin = int(font_size * 0.6)

    pill_w = tw + pad_x * 2
    pill_h = th + pad_y * 2
    radius = pill_h // 2

    # Posicion: esquina superior derecha
    x1 = w - margin - pill_w
    y1 = margin
    x2 = x1 + pill_w
    y2 = y1 + pill_h

    # Dibujar pill (blanco, alpha 204 ≈ 80%)
    try:
        draw.rounded_rectangle([x1, y1, x2, y2], radius=radius, fill=(255, 255, 255, 204))
    except (AttributeError, TypeError):
        draw.rectangle([x1, y1, x2, y2], fill=(255, 255, 255, 204))

    # Texto negro solido
    draw.text(
        (x1 + pad_x + txt_offset_x, y1 + pad_y + txt_offset_y),
        codigo_str, font=font, fill=(20, 20, 20, 255)
    )

    return Image.alpha_composite(img, overlay)   # RGBA; el caller convierte si es JPEG


def _guardar(img_rgba, ruta, ext, calidad, dpi_tuple):
    """Guarda img_rgba en disco, convirtiendo a RGB si el formato lo requiere."""
    if ext == '.png':
        img_rgba.save(ruta, 'PNG', dpi=dpi_tuple)
    else:
        img_rgba.convert("RGB").save(ruta, 'JPEG', quality=calidad,
                                     dpi=dpi_tuple, subsampling=0)


def cm_a_px(cm, dpi):
    """Convierte centimetros a pixeles segun los DPI."""
    return round(cm * dpi / 2.54)


def px_a_cm(px, dpi):
    """Convierte pixeles a centimetros segun los DPI."""
    return px * 2.54 / dpi


def obtener_dpi(img):
    """Obtiene los DPI horizontales de la imagen. Default: 150."""
    try:
        dpi_info = img.info.get('dpi', (150, 150))
        dpi_x = dpi_info[0]
        if 50 < dpi_x < 1200:
            return int(dpi_x)
    except (TypeError, IndexError, ValueError):
        pass
    return 150


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


def procesar_imagen(ruta_archivo, carpeta_salida, margen_cm, ancho_rollo_cm,
                    umbral_desp, calidad, codigo):
    """
    Procesa una imagen:
    - Si al menos un lado <= rollo -> graba el codigo y guarda en la salida
    - Si ambos > rollo -> corta segun las reglas de optimizacion;
      el primer pano lleva el badge, ambos panos llevan el codigo en el nombre
    Devuelve: (estado, mensaje, metros_lineales)
      metros_lineales = lista con el lado mas largo de cada pano (en cm)
    """
    nombre = Path(ruta_archivo).stem
    ext = Path(ruta_archivo).suffix.lower()
    codigo_str = f"COD{codigo:03d}"

    try:
        img = Image.open(ruta_archivo)
    except Exception as e:
        return "ERROR", f"[ERROR] No se pudo abrir {nombre}{ext}: {e}", []

    dpi = obtener_dpi(img)
    margen_px = cm_a_px(margen_cm, dpi)
    dpi_tuple = (dpi, dpi)

    ancho_px = img.width
    alto_px = img.height
    ancho_cm = px_a_cm(ancho_px, dpi)
    alto_cm = px_a_cm(alto_px, dpi)

    # --- CASO: entra en el rollo sin corte ---
    if ancho_cm <= ancho_rollo_cm or alto_cm <= ancho_rollo_cm:
        nombre_salida = f"{codigo_str} - {os.path.basename(ruta_archivo)}"
        ruta_destino = os.path.join(carpeta_salida, nombre_salida)

        img_con_codigo = grabar_codigo(img, codigo_str)
        img.close()
        _guardar(img_con_codigo, ruta_destino, ext, calidad, dpi_tuple)

        lado_largo = max(ancho_cm, alto_cm)
        return "SIN CORTE", (
            f"[SIN CORTE] {codigo_str} · {nombre}{ext}\n"
            f"     {ancho_cm:.1f}cm x {alto_cm:.1f}cm @ {dpi} DPI\n"
            f"     Entra en el rollo de {ancho_rollo_cm}cm, guardado con codigo\n"
            f"     -> {nombre_salida}\n"
            f"     Metros lineales: {lado_largo / 100:.2f}m"
        ), [lado_largo]

    # --- CASO: ambos lados superan el rollo ---
    entra_vert, desp_vert, entra_horiz, desp_horiz = evaluar_corte(
        ancho_cm, alto_cm, ancho_rollo_cm, margen_cm
    )

    if not entra_vert and not entra_horiz:
        img.close()
        return "ERROR", (
            f"[ERROR] {nombre}{ext}\n"
            f"     {ancho_cm:.1f}cm x {alto_cm:.1f}cm @ {dpi} DPI\n"
            f"     Ningun corte produce panos que entren en el rollo de {ancho_rollo_cm}cm.\n"
            f"     Este fondo necesita un tratamiento especial."
        ), []

    # Decidir eje de corte
    if entra_vert and entra_horiz:
        if desp_vert - desp_horiz > umbral_desp:
            cortar_horizontal = True
            razon = f"Desp. vertical ({desp_vert:.0f}cm) supera al horizontal ({desp_horiz:.0f}cm) por mas de {umbral_desp}cm"
        else:
            cortar_horizontal = False
            razon = f"Desp. vertical ({desp_vert:.0f}cm) vs horizontal ({desp_horiz:.0f}cm), diferencia <= {umbral_desp}cm"
    elif entra_horiz:
        cortar_horizontal = True
        lado_corto_vert = ancho_cm / 2 + margen_cm
        razon = f"Corte vertical no entra en rollo (pano de {lado_corto_vert:.0f}cm > {ancho_rollo_cm}cm)"
    else:
        cortar_horizontal = False
        lado_corto_horiz = alto_cm / 2 + margen_cm
        razon = f"Corte horizontal no entra en rollo (pano de {lado_corto_horiz:.0f}cm > {ancho_rollo_cm}cm)"

    if cortar_horizontal:
        tipo_corte = "HORIZONTAL (superior / inferior)"
        mitad = alto_px // 2

        pano_1 = img.crop((0, 0, ancho_px, mitad + margen_px))
        pano_2 = img.crop((0, mitad - margen_px, ancho_px, alto_px))

        sufijo_1 = "SUPERIOR"
        sufijo_2 = "INFERIOR"

        alto_1_cm = px_a_cm(mitad + margen_px, dpi)
        alto_2_cm = px_a_cm(alto_px - (mitad - margen_px), dpi)
        medida_1 = f"{ancho_cm:.1f}cm x {alto_1_cm:.1f}cm"
        medida_2 = f"{ancho_cm:.1f}cm x {alto_2_cm:.1f}cm"
        largo_1 = max(ancho_cm, alto_1_cm)
        largo_2 = max(ancho_cm, alto_2_cm)
    else:
        tipo_corte = "VERTICAL (izquierdo / derecho)"
        mitad = ancho_px // 2

        pano_1 = img.crop((0, 0, mitad + margen_px, alto_px))
        pano_2 = img.crop((mitad - margen_px, 0, ancho_px, alto_px))

        sufijo_1 = "IZQUIERDO"
        sufijo_2 = "DERECHO"

        ancho_1_cm = px_a_cm(mitad + margen_px, dpi)
        ancho_2_cm = px_a_cm(ancho_px - (mitad - margen_px), dpi)
        medida_1 = f"{ancho_1_cm:.1f}cm x {alto_cm:.1f}cm"
        medida_2 = f"{ancho_2_cm:.1f}cm x {alto_cm:.1f}cm"
        largo_1 = max(ancho_1_cm, alto_cm)
        largo_2 = max(ancho_2_cm, alto_cm)

    # Nombres de salida: ambos panos llevan el codigo en el nombre
    nombre_1 = f"{codigo_str} - {nombre}_{sufijo_1}{ext}"
    nombre_2 = f"{codigo_str} - {nombre}_{sufijo_2}{ext}"

    ruta_1 = os.path.join(carpeta_salida, nombre_1)
    ruta_2 = os.path.join(carpeta_salida, nombre_2)

    # Pano 1: lleva el badge del codigo
    pano_1_con_codigo = grabar_codigo(pano_1, codigo_str)
    _guardar(pano_1_con_codigo, ruta_1, ext, calidad, dpi_tuple)

    # Pano 2: sin badge (no necesita codigo visual)
    _guardar(pano_2.convert("RGBA"), ruta_2, ext, calidad, dpi_tuple)

    pano_1.close()
    pano_2.close()
    img.close()

    metros_lineales = [largo_1, largo_2]

    msg = (
        f"[OK] {codigo_str} · {nombre}{ext}\n"
        f"     Original: {ancho_cm:.1f}cm x {alto_cm:.1f}cm @ {dpi} DPI\n"
        f"     Corte: {tipo_corte}\n"
        f"     Razon: {razon}\n"
        f"     Margen de costura: {margen_cm}cm ({margen_px}px)\n"
        f"     -> {nombre_1}  ({medida_1}) | Lineal: {largo_1 / 100:.2f}m  [codigo grabado]\n"
        f"     -> {nombre_2}  ({medida_2}) | Lineal: {largo_2 / 100:.2f}m"
    )
    return "OK", msg, metros_lineales


def main():
    parser = argparse.ArgumentParser(
        description='INNOVA - Cortador de fondos fotograficos para sublimacion'
    )
    parser.add_argument(
        'carpeta',
        nargs='?',
        default='.',
        help='Carpeta con los archivos JPG (default: carpeta actual)'
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

    # Buscar archivos de imagen
    archivos = sorted([
        f for f in os.listdir(carpeta)
        if Path(f).suffix.lower() in EXTENSIONES
    ])

    if not archivos:
        print(f"\nNo se encontraron archivos JPG/PNG en: {carpeta}")
        sys.exit(0)

    # Crear carpeta de salida
    carpeta_salida = args.salida or os.path.join(carpeta, 'cortados')
    os.makedirs(carpeta_salida, exist_ok=True)

    # Cabecera
    print("")
    print("=" * 62)
    print("  INNOVA - Cortador de Fondos para Sublimacion")
    print("=" * 62)
    print(f"  Carpeta:       {carpeta}")
    print(f"  Salida:        {carpeta_salida}")
    print(f"  Archivos:      {len(archivos)} JPG/PNG encontrados")
    print(f"  Margen:        {args.margen}cm")
    print(f"  Ancho rollo:   {args.ancho_rollo}cm")
    print(f"  Umbral desp.:  {args.umbral}cm")
    print(f"  Calidad:       {args.calidad}%")
    print(f"  Codigos:       COD001 - COD{len(archivos):03d}")
    print("=" * 62)
    print("")

    # Procesar
    inicio = time.time()
    cortados = 0
    sin_corte = 0
    errores = 0
    todos_los_metros = []
    contador_codigo = 0

    for i, archivo in enumerate(archivos, 1):
        contador_codigo += 1
        print(f"[{i}/{len(archivos)}] Procesando {archivo}...")
        ruta = os.path.join(carpeta, archivo)
        estado, mensaje, metros = procesar_imagen(
            ruta, carpeta_salida,
            args.margen, args.ancho_rollo, args.umbral, args.calidad,
            contador_codigo
        )
        print(mensaje)
        print("")

        todos_los_metros.extend(metros)

        if estado == "OK":
            cortados += 1
        elif estado == "SIN CORTE":
            sin_corte += 1
        else:
            errores += 1

    # Resumen
    duracion = time.time() - inicio
    total_metros = sum(todos_los_metros) / 100   # cm -> metros
    total_panos = len(todos_los_metros)

    print("=" * 62)
    print("  RESUMEN")
    print("-" * 62)
    print(f"  Cortados:      {cortados}")
    print(f"  Sin corte:     {sin_corte}")
    print(f"  Errores:       {errores}")
    print(f"  Tiempo total:  {duracion:.1f} segundos")
    print(f"  Archivos en:   {carpeta_salida}")
    print("-" * 62)
    print(f"  Total panos:           {total_panos}")
    print(f"  METROS LINEALES:       {total_metros:.2f}m")
    print("=" * 62)
    print("")


if __name__ == '__main__':
    main()
