#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
INNOVA — Generador de Lista de Costura
=======================================
Genera un PDF con la lista de costura a partir de los archivos de la
carpeta "cortados/", usando la misma lógica de corte que cortador_innova.py.

MODO AUTOMÁTICO : llamado desde generar_lista_etiquetado.py al finalizar.
MODO MANUAL     : doble-click en GENERAR_COSTURA.bat

Salida: carpeta hermana "costura/" → costura_<cierre>.pdf

INSTRUCCIÓN para integrar el logo:
  Copiá la variable LOGO_B64 completa de generar_lista_etiquetado.py
  y reemplazá la cadena vacía LOGO_B64 = "" de abajo.
  El script funciona igual sin logo (lo omite silenciosamente).
"""

import os
import sys
import re
import json
import math
import datetime
import argparse

# ── dependencias ──────────────────────────────────────────────────────────────
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
    from reportlab.lib.utils import ImageReader
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle,
        Paragraph, Spacer, HRFlowable, Flowable
    )
except ImportError:
    print("\n[ERROR] Falta ReportLab. Instalala con:  pip install reportlab\n")
    input("Enter para salir...")
    sys.exit(1)

# ── tarifas (Marzo 2026, +15% vs Q4-2025) ──────────────────────────────────────────────────────
PRECIO_1_PANO       = 2_180   # Sin costura / entra en rollo
PRECIO_UNION_CORTA  = 4_350   # 2 paños, unión de hasta 450 cm (inclusive)
PRECIO_UNION_LARGA  = 6_950   # 2 paños, unión de más de 450 cm
PRECIO_NEOPRENE     = 2_350   # Fijo, sin importar medida
VIATICOS            = 6_000   # Fijo por cierre
RECARGO_PANO_ADICIONAL = 0.5  # 3+ paños: tarifa de unión + 50% de esa tarifa
                              # por cada paño adicional a 2.
                              # 3 paños > 4,5 m = 6.950 + 3.475 = 10.425
                              # 4 paños > 4,5 m = 6.950 + 2 x 3.475 = 13.900

ROLL_MAX_CM         = 160     # Ancho máximo del rollo
MARGEN_CM           = 0.45    # Margen de costura por lado (igual que el cortador)
UNION_THRESHOLD_CM  = 450     # 4,5 m en cm

# ── logo (completar con LOGO_B64 de generar_lista_etiquetado.py) ──────────────
# Pegá aquí la misma variable LOGO_B64 que tiene el script de etiquetado.
# Si queda vacía simplemente no se imprime logo.
LOGO_B64   = ""
LOGO_RATIO = 187 / 777   # alto / ancho del logo Innova

# ── paleta de marca ───────────────────────────────────────────────────────────
AZUL_HDR   = colors.HexColor("#1B3A5C")
AZUL_MED   = colors.HexColor("#2E6DA4")
GRIS_PAR   = colors.HexColor("#EFF4FA")
AMARILLO   = colors.HexColor("#FFF3CD")
ROJO_TOTAL = colors.HexColor("#C0392B")
BLANCO     = colors.white
NEGRO      = colors.HexColor("#1A1A1A")
GRIS_TEXT  = colors.HexColor("#555555")
INK        = colors.HexColor("#0f0e0c")
MUTED      = colors.HexColor("#6b6357")
RULE       = colors.HexColor("#d6cdb8")
ACCENT     = colors.HexColor("#c2410c")

# ── regex ──────────────────────────────────────────────────────────────────────
COD_RE  = re.compile(r"cod[\s._\-]*0*(\d+)", re.IGNORECASE)
MED_RE  = re.compile(r"(\d{2,4})\s*[xX\u00d7]\s*(\d{2,4})", re.IGNORECASE)
IMG_EXT = (".jpg", ".jpeg", ".png")


# =============================================================================
# CHECKBOX (mismo estilo que generar_lista_etiquetado.py)
# =============================================================================

class CheckBox(Flowable):
    """Cuadrado vacio para marcar a mano."""
    def __init__(self, size_pt=9):
        Flowable.__init__(self)
        self.size   = size_pt
        self.width  = size_pt
        self.height = size_pt

    def draw(self):
        self.canv.setLineWidth(0.9)
        self.canv.setStrokeColor(MUTED)
        self.canv.rect(0, 0, self.size, self.size)


# =============================================================================
# LÓGICA DE COSTURA
# =============================================================================

def detectar_especial(nombre_base):
    nb = nombre_base.lower()
    if "neoprene" in nb or "neopreno" in nb:
        return "neoprene"
    if "funda" in nb:
        return "funda"
    return None


def cotizar_uniones(n_panos, largo_union_cm):
    """
    Precio de un fondo en n_panos (2 o mas): la tarifa de union segun el largo
    de la costura (<= 450cm corta, > 450cm larga) mas RECARGO_PANO_ADICIONAL
    (50%) de esa tarifa por cada pano por encima de 2.
    Retorna (descripcion, precio, False).
    """
    adicionales = n_panos - 2
    corta = largo_union_cm <= UNION_THRESHOLD_CM
    tarifa = PRECIO_UNION_CORTA if corta else PRECIO_UNION_LARGA
    tramo = "hasta 4,5 m" if corta else "de mas de 4,5 m"
    if adicionales <= 0:
        return "Union %s" % tramo, tarifa, False
    precio = int(round(tarifa + tarifa * RECARGO_PANO_ADICIONAL * adicionales))
    return ("Union %s + %d pano%s adicional%s (%d panos)"
            % (tramo, adicionales, "s" if adicionales > 1 else "",
               "es" if adicionales > 1 else "", n_panos)), precio, False


def calcular_costura(ancho_cm, alto_cm, tipo_especial):
    """
    Cotiza re-deduciendo el corte desde la medida (solo cuando falta el
    manifiesto del cortador). Retorna (descripcion, precio|None, advertencia).
    """
    if tipo_especial == "neoprene":
        return "Piso Neoprene", PRECIO_NEOPRENE, False

    # Sin corte: entra en el rollo si al menos un lado <= 160 cm
    if ancho_cm <= ROLL_MAX_CM or alto_cm <= ROLL_MAX_CM:
        return "1 Pano", PRECIO_1_PANO, False

    # Ambos lados > 160 -> necesita corte
    panel_v = ancho_cm / 2   # corte vertical
    panel_h = alto_cm  / 2   # corte horizontal

    puede_v = panel_v <= ROLL_MAX_CM
    puede_h = panel_h <= ROLL_MAX_CM

    if not puede_v and not puede_h:
        # Igual que el cortador: 3 o mas panos iguales en horizontal; las
        # uniones corren a lo ancho.
        util = ROLL_MAX_CM - 2 * MARGEN_CM
        n = max(3, int(math.ceil(alto_cm / util)))
        while alto_cm / n + 2 * MARGEN_CM > ROLL_MAX_CM:
            n += 1
        return cotizar_uniones(n, ancho_cm)

    # Preferir corte vertical; la union corre a lo largo del otro lado
    longitud = alto_cm if puede_v else ancho_cm
    return cotizar_uniones(2, longitud)


def calcular_costura_real(real, tipo_especial):
    """
    Cotiza con el corte que el cortador hizo de verdad (medidas_reales.json:
    'panos' y 'corte'), no con uno re-deducido. Asi un fondo cortado por pedido
    del nombre ("horizontal"/"vertical"), por el umbral de desperdicio o en 3+
    panos se cobra con las uniones correctas.
    Retorna lo mismo que calcular_costura, o None si el manifiesto no alcanza.
    """
    if tipo_especial == "neoprene":
        return "Piso Neoprene", PRECIO_NEOPRENE, False

    panos = real.get("panos")
    corte = real.get("corte")
    if panos == 1:
        return "1 Pano", PRECIO_1_PANO, False
    if isinstance(panos, int) and panos >= 2 and corte in ("VERTICAL", "HORIZONTAL"):
        # Las uniones corren a lo largo del lado que el corte no parte
        longitud = real["alto_cm"] if corte == "VERTICAL" else real["ancho_cm"]
        return cotizar_uniones(panos, longitud)
    return None


# =============================================================================
# PARSEO DE NOMBRES
# =============================================================================

def _limpiar(s):
    s = re.sub(r"^[\s\-_\u2013\u00b7.|]+|[\s\-_\u2013\u00b7.|]+$", "", s)
    return re.sub(r"\s+", " ", s).strip()


def parsear_archivo(filename):
    """
    Retorna (codigo, cliente, ancho_cm, alto_cm, tipo_especial) o None.
    """
    base = os.path.splitext(filename)[0]
    med  = MED_RE.search(base)
    if not med:
        return None

    ancho_cm = int(med.group(1))
    alto_cm  = int(med.group(2))
    tipo_especial = detectar_especial(base)

    cod = COD_RE.search(base)
    if cod:
        codigo = "Cod." + str(int(cod.group(1))).zfill(4)
        segmento = base[cod.end():med.start()]
    else:
        codigo   = "\u2014"
        segmento = base[:med.start()]

    partes  = [_limpiar(p) for p in segmento.split("-")]
    cliente = " ".join(p for p in partes if p).title() or "(sin nombre)"

    return codigo, cliente, ancho_cm, alto_cm, tipo_especial


# =============================================================================
# GENERACIÓN DEL PDF
# =============================================================================

def _cel(texto, bold=False, size=9, align=TA_LEFT, color=NEGRO):
    font = "Helvetica-Bold" if bold else "Helvetica"
    st   = ParagraphStyle("c", fontName=font, fontSize=size,
                          textColor=color, alignment=align)
    return Paragraph(str(texto), st)


MANIFIESTO = "medidas_reales.json"


def leer_medidas_reales(carpeta):
    """
    Lee cortados/medidas_reales.json, que el cortador escribe con la medida real
    de cada diseno calculada desde los pixeles y el DPI.

    Se usa en lugar de la medida del nombre del archivo porque el nombre trae la
    medida que pidio el cliente, sin los 15cm del bolsillo superior. Cotizar por
    el nombre subestima la tela y la costura.

    Devuelve {"cod.0001": {"ancho_cm": .., "alto_cm": ..}, ...} o {} si no esta.
    """
    ruta = os.path.join(carpeta, MANIFIESTO)
    if not os.path.isfile(ruta):
        print("  [aviso] No hay %s: se cotiza con la medida del nombre." % MANIFIESTO)
        return {}
    try:
        with open(ruta, encoding="utf-8") as fh:
            paquete = json.load(fh)
        reales = {}
        for d in paquete.get("disenos", []):
            if d.get("ancho_cm") and d.get("alto_cm"):
                reales[str(d["codigo"]).lower()] = d
        # El cortador escribe "COD001"; el parseo de nombres arma "Cod.0001".
        normalizado = {}
        for k, v in reales.items():
            m = COD_RE.search(k)
            if m:
                normalizado["cod." + str(int(m.group(1))).zfill(4)] = v
        return normalizado
    except Exception as e:
        print("  [aviso] No se pudo leer %s (%s): se usa la medida del nombre." % (MANIFIESTO, e))
        return {}


def cotizar(carpeta_origen):
    """
    Cotiza la costura de los fondos en 'cortados/' sin generar nada en disco.
    Retorna None si no hay nada que cotizar, o un dict con:
      filas            -> [(nro, codigo, cliente, medida, detalle, precio_str, adv)]
      subtotal         -> suma de precios + viaticos
      total_redondeado -> subtotal redondeado al proximo multiplo de 1.000
      advertencias     -> archivos a cotizar manualmente (sin precio)
    """
    carpeta = os.path.abspath(carpeta_origen)
    if not os.path.isdir(carpeta):
        print("[COSTURA] ERROR: carpeta no encontrada:", carpeta)
        return None

    archivos = sorted(f for f in os.listdir(carpeta) if f.lower().endswith(IMG_EXT))
    if not archivos:
        print("[COSTURA] No se encontraron imagenes en:", carpeta)
        return None

    filas_data   = []
    total_acum   = 0
    advertencias = []
    vistos       = set()

    reales = leer_medidas_reales(carpeta)

    for archivo in archivos:
        r = parsear_archivo(archivo)
        if r is None:
            print("  [omitido] sin medida:", archivo)
            continue
        codigo, cliente, ancho_cm, alto_cm, tipo_especial = r

        # La medida REAL manda sobre la del nombre: los fondos llevan 15cm extra
        # arriba para el bolsillo y el nombre del cliente no los incluye.
        real = reales.get(codigo.lower())
        if real:
            ancho_cm, alto_cm = real["ancho_cm"], real["alto_cm"]

        # Deduplicar: 2do pano del mismo diseno tiene mismo COD + medida
        key = codigo.lower() + "_" + str(ancho_cm) + "x" + str(alto_cm)
        if key in vistos:
            continue
        vistos.add(key)

        cotizado = calcular_costura_real(real, tipo_especial) if real else None
        if cotizado is None:
            cotizado = calcular_costura(ancho_cm, alto_cm, tipo_especial)
        desc, precio, adv = cotizado
        medida_str = "%.0f x %.0f cm" % (ancho_cm, alto_cm)

        if adv:
            advertencias.append(archivo)
            precio_str = ""
        else:
            total_acum += precio
            precio_str = "$ {:,.0f}".format(precio).replace(",", ".")

        filas_data.append((len(filas_data) + 1, codigo, cliente,
                           medida_str, desc, precio_str, adv))

    if not filas_data:
        print("[COSTURA] No se pudo procesar ningun archivo.")
        return None

    subtotal = total_acum + VIATICOS
    return {
        "filas":            filas_data,
        "subtotal":         subtotal,
        "total_redondeado": math.ceil(subtotal / 1_000) * 1_000,
        "advertencias":     advertencias,
    }


def generar_pdf_costura(carpeta_origen, cierre=None, sin_pausa=False, cot=None):
    """
    Genera costura_<cierre>.pdf en carpeta hermana 'costura/'.
    cot: resultado de cotizar() si el llamador ya lo tiene (evita recalcular).
    Retorna la ruta del PDF o None si no hay archivos.
    """
    carpeta = os.path.abspath(carpeta_origen)
    if cot is None:
        cot = cotizar(carpeta)
    if cot is None:
        return None

    costura_dir = os.path.join(os.path.dirname(carpeta), "costura")
    os.makedirs(costura_dir, exist_ok=True)

    if not cierre:
        cierre = datetime.date.today().isoformat()

    safe    = re.sub(r"[^\w\-]+", "-", cierre)
    ruta_pdf = os.path.join(costura_dir, "costura_%s.pdf" % safe)

    filas_data       = cot["filas"]
    advertencias     = cot["advertencias"]
    subtotal         = cot["subtotal"]
    total_redondeado = cot["total_redondeado"]
    n = len(filas_data)

    # -- tabla --------------------------------------------------------------
    enc = ["Nro", "Codigo", "Cliente", "Medida", "Detalle costura", "Monto", "Check"]
    tabla_filas = [[_cel(h, bold=True, align=TA_CENTER, color=BLANCO) for h in enc]]

    for nro, cod, cli, med, det, prec, adv in filas_data:
        tabla_filas.append([
            _cel(nro, align=TA_CENTER),
            _cel(cod, bold=True),
            _cel(cli),
            _cel(med, align=TA_CENTER),
            _cel(det),
            _cel(prec, bold=(prec != ""), align=TA_RIGHT),
            CheckBox(size_pt=9),
        ])

    # Fila viaticos
    tabla_filas.append([
        _cel(""), _cel(""), _cel(""), _cel(""),
        _cel("Viaticos", bold=True, color=AZUL_MED),
        _cel("$ {:,.0f}".format(VIATICOS).replace(",", "."),
             bold=True, align=TA_RIGHT, color=AZUL_MED),
        _cel(""),
    ])

    tabla_filas.append([
        _cel(""), _cel(""), _cel(""), _cel(""),
        _cel("TOTAL", bold=True, size=11, color=AZUL_HDR),
        _cel("$ {:,.0f}".format(total_redondeado).replace(",", "."),
             bold=True, size=11, align=TA_RIGHT, color=ROJO_TOTAL),
        _cel(""),
    ])

    # Anchos: Nro + Cod + Cliente + Medida + Detalle + Monto + Check = ~178mm
    col_widths = [10*mm, 22*mm, 44*mm, 25*mm, 47*mm, 22*mm, 10*mm]
    tabla = Table(tabla_filas, colWidths=col_widths, repeatRows=1)

    fv = n + 1
    ft = n + 2
    ts = TableStyle([
        ("BACKGROUND",    (0,0),  (-1,0),  AZUL_HDR),
        ("TOPPADDING",    (0,0),  (-1,0),  7),
        ("BOTTOMPADDING", (0,0),  (-1,0),  7),
        ("ROWBACKGROUNDS",(0,1),  (-1,n),  [BLANCO, GRIS_PAR]),
        ("INNERGRID",     (0,0),  (-1,-1), 0.3, colors.HexColor("#CCCCCC")),
        ("BOX",           (0,0),  (-1,-1), 0.5, AZUL_HDR),
        ("TOPPADDING",    (0,1),  (-1,n),  5),
        ("BOTTOMPADDING", (0,1),  (-1,n),  5),
        ("LEFTPADDING",   (0,0),  (-1,-1), 5),
        ("RIGHTPADDING",  (0,0),  (-1,-1), 5),
        ("BACKGROUND",    (0,fv), (-1,fv), GRIS_PAR),
        ("TOPPADDING",    (0,fv), (-1,fv), 7),
        ("BOTTOMPADDING", (0,fv), (-1,fv), 7),
        ("BACKGROUND",    (0,ft), (-1,ft), AZUL_HDR),
        ("TOPPADDING",    (0,ft), (-1,ft), 9),
        ("BOTTOMPADDING", (0,ft), (-1,ft), 9),
        ("LINEABOVE",     (0,ft), (-1,ft), 1.5, AZUL_MED),
        ("ALIGN",         (-1,1),  (-1,n),  "CENTER"),
        ("VALIGN",        (-1,1),  (-1,n),  "MIDDLE"),
    ])
    for idx, (nro, cod, cli, med, det, prec, adv) in enumerate(filas_data, 1):
        if adv:
            ts.add("BACKGROUND", (0,idx), (-1,idx), AMARILLO)
    tabla.setStyle(ts)

    # -- estilos de texto ---------------------------------------------------
    s_t = ParagraphStyle("t", fontName="Helvetica-Bold", fontSize=15,
                         textColor=AZUL_HDR, alignment=TA_CENTER, spaceAfter=4)
    s_s = ParagraphStyle("s", fontName="Helvetica",     fontSize=9,
                         textColor=GRIS_TEXT, alignment=TA_CENTER, spaceAfter=2)
    s_n = ParagraphStyle("n", fontName="Helvetica-Oblique", fontSize=7.5,
                         textColor=GRIS_TEXT, alignment=TA_RIGHT)
    s_a = ParagraphStyle("a", fontName="Helvetica-Oblique", fontSize=8,
                         textColor=colors.HexColor("#856404"), alignment=TA_LEFT)

    # -- documento ----------------------------------------------------------
    doc = SimpleDocTemplate(
        ruta_pdf, pagesize=A4,
        leftMargin=16*mm, rightMargin=16*mm,
        topMargin=15*mm,  bottomMargin=14*mm,
        title="INNOVA - Lista de Costura - " + cierre,
    )

    def on_page(canv, doc):
        canv.saveState()
        PW, PH = A4
        canv.setStrokeColor(RULE); canv.setLineWidth(0.5)
        canv.line(16*mm, PH-11*mm, PW-16*mm, PH-11*mm)
        canv.setFont("Helvetica-Bold", 9); canv.setFillColor(INK)
        canv.drawString(16*mm, PH-7.5*mm, "INNOVA - Lista de Costura")
        canv.setFont("Helvetica", 8); canv.setFillColor(MUTED)
        canv.drawString(16*mm, PH-11.5*mm, "Cierre: " + cierre)
        canv.setFont("Helvetica", 7.5)
        canv.drawRightString(PW-16*mm, PH-9.5*mm, "Pag. %d" % doc.page)
        canv.setStrokeColor(RULE)
        canv.line(16*mm, 10*mm, PW-16*mm, 10*mm)
        canv.setFont("Helvetica", 7); canv.setFillColor(MUTED)
        canv.drawString(16*mm, 7*mm, "INNOVA - Fondos fotograficos")
        canv.drawRightString(PW-16*mm, 7*mm, "innova54.com")
        canv.restoreState()

    story = [
        Paragraph("INNOVA - Lista de Costura", s_t),
        Paragraph(
            "Lote/Cierre: <b>%s</b>  -  Fecha: %s  -  Fondos: %d"
            % (cierre, datetime.date.today().strftime("%d/%m/%Y"), n),
            s_s
        ),
        Spacer(1, 3*mm),
        HRFlowable(width="100%", thickness=1.5, color=AZUL_MED),
        Spacer(1, 3*mm),
        tabla,
        Spacer(1, 3*mm),
        Paragraph(
            "* Subtotal bruto: $ {:,.0f}".format(subtotal).replace(",", ".")
            + "  ->  Total redondeado al proximo multiplo de $ 1.000", s_n
        ),
    ]

    if advertencias:
        story += [
            Spacer(1, 4*mm),
            HRFlowable(width="100%", thickness=0.5,
                       color=colors.HexColor("#856404")),
            Spacer(1, 2*mm),
            Paragraph(
                "ATENCION: los siguientes fondos no se pudieron cotizar "
                "automaticamente y deben cotizarse manualmente:", s_a
            ),
        ]
        for a in advertencias:
            story.append(Paragraph("  - " + a, s_a))

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    return ruta_pdf


def imprimir_detalle(cot, ruta_pdf):
    """Cuadro de consola con el detalle (solo en modo manual: en la corrida
    encadenada el etiquetador muestra un estado y el resumen de produccion)."""
    print("\n" + "=" * 54)
    print(" COSTURA: %d fondo(s) procesado(s)" % len(cot["filas"]))
    if cot["advertencias"]:
        print(" ATENCION: %d con +2 panos (sin precio)" % len(cot["advertencias"]))
    print("")
    print("  Subtotal bruto  : $ {:,.0f}".format(cot["subtotal"]).replace(",", "."))
    print("  Total redondeado: $ {:,.0f}".format(cot["total_redondeado"]).replace(",", "."))
    print("")
    print("  PDF costura -> %s" % ruta_pdf)
    print("=" * 54 + "\n")


# =============================================================================
# ENTRY POINT (modo manual)
# =============================================================================

def main():
    ap = argparse.ArgumentParser(description="INNOVA - Generador de Lista de Costura")
    ap.add_argument("carpeta", nargs="?",
                    help="Ruta a la carpeta 'cortados/' con los fondos procesados")
    ap.add_argument("--cierre", default=None,
                    help="Identificador del lote (default: fecha de hoy)")
    ap.add_argument("--sin-pausa", action="store_true",
                    help="No espera Enter al final (para llamada automatica)")
    args = ap.parse_args()

    carpeta = args.carpeta
    if not carpeta:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        candidato  = os.path.join(script_dir, "cortados")
        if os.path.isdir(candidato):
            carpeta = candidato
        else:
            carpeta = input(
                "\nArrastra la carpeta 'cortados' aqui y presiona Enter:\n> "
            ).strip().strip('"')

    if not carpeta or not os.path.isdir(carpeta):
        print("\n[ERROR] Carpeta no valida:", carpeta)
        if not args.sin_pausa:
            input("Enter para salir...")
        sys.exit(1)

    cot = cotizar(carpeta)
    if cot:
        ruta_pdf = generar_pdf_costura(carpeta, cierre=args.cierre,
                                       sin_pausa=args.sin_pausa, cot=cot)
        imprimir_detalle(cot, ruta_pdf)

    if not args.sin_pausa:
        input("Listo. Enter para salir...")


if __name__ == "__main__":
    main()
