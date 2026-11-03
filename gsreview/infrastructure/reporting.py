from gsreview.configuration import COLORS, BRAND, APP_ROOT

"""PDF y gráficos locales sin enlaces, telemetría ni recursos remotos."""
import io
from html import escape
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from gsreview.domain.rules import NOTICE


def chart_png(rows):
    fig, axes = plt.subplots(3, 1, figsize=(9, 6), sharex=True)
    axes[0].plot(rows.timestamp, rows.reported_3d_movement_mm, color=COLORS["blue"], linewidth=1.2)
    axes[0].set_ylabel("Movimiento (mm)")
    for ax, score, threshold in [
        (axes[1], "baseline_score", 4.439772224885318),
        (axes[2], "isolation_forest_score", 0.5872931971929567),
    ]:
        ax.plot(rows.timestamp, rows[score], color=COLORS["teal"], marker=".", markersize=3)
        ax.axhline(threshold, color=COLORS["purple"], linestyle="--", label="q99 congelado")
        ax.set_ylabel("Base" if score == "baseline_score" else "Isolation Forest")
        ax.legend(loc="upper left", fontsize=7)
    fig.suptitle("Mediciones reales y marcas estadísticas experimentales")
    for ax in axes:
        ax.grid(alpha=0.15)
    fig.autofmt_xdate()
    fig.tight_layout()
    output = io.BytesIO()
    fig.savefig(output, format="png", dpi=150)
    plt.close(fig)
    return output.getvalue()


def make_pdf(payload, rows):
    pdfmetrics.registerFont(TTFont("GSSans", str(APP_ROOT / "assets/fonts/DejaVuSans.ttf")))
    pdfmetrics.registerFont(
        TTFont("GSSansBold", str(APP_ROOT / "assets/fonts/DejaVuSans-Bold.ttf"))
    )
    pdfmetrics.registerFontFamily(
        "GSSans", normal="GSSans", bold="GSSansBold", italic="GSSans", boldItalic="GSSansBold"
    )
    stream = io.BytesIO()
    styles = getSampleStyleSheet()
    for style in styles.byName.values():
        style.fontName = (
            "GSSansBold"
            if style.name in ("Title", "Heading1", "Heading2", "Heading3")
            else "GSSans"
        )
    styles.add(ParagraphStyle(name="SmallGS", parent=styles["BodyText"], fontSize=8, leading=11))
    story = [
        Paragraph(BRAND["name"], styles["Title"]),
        Paragraph(escape(payload["title"]), styles["Heading2"]),
        Paragraph("Sistema local offline | Evidencia estadística experimental", styles["BodyText"]),
        Spacer(1, 12),
        Paragraph(escape(NOTICE), styles["SmallGS"]),
        Spacer(1, 12),
    ]
    for title, value in payload["summary"].items():
        story.append(
            Paragraph(f"<b>{escape(str(title))}:</b> {escape(str(value))}", styles["BodyText"])
        )
    story += [
        Spacer(1, 12),
        Paragraph("Parámetros congelados", styles["Heading2"]),
        Paragraph(
            "Política híbrida; 72 horas; mínimo 2 marcas. Base q99: 4.439772224885318. "
            "Isolation Forest q99: 0.5872931971929567.",
            styles["BodyText"],
        ),
    ]
    if len(rows):
        story += [Spacer(1, 12), Image(io.BytesIO(chart_png(rows)), width=470, height=313)]
    story.append(Paragraph("Evaluaciones humanas registradas", styles["Heading2"]))
    if not payload["reviews"]:
        story.append(Paragraph("Sin evaluaciones humanas registradas.", styles["BodyText"]))
    for review in payload["reviews"]:
        for k, v in review.items():
            story.append(Paragraph(f"<b>{escape(str(k))}:</b> {escape(str(v))}", styles["SmallGS"]))
        story.append(Spacer(1, 8))
    story += [
        Paragraph("Limitaciones", styles["Heading2"]),
        Paragraph(
            "Los estados del periodo de entrenamiento son retrospectivos. Coordenadas y referencia "
            "espacial pendientes de validación; no hay superficie topográfica. Ausencia de datos "
            "no significa estabilidad. Requiere revisión especializada.",
            styles["BodyText"],
        ),
        Spacer(1, 12),
        Paragraph("Trazabilidad: " + escape(payload["manifest_hash"]), styles["SmallGS"]),
    ]

    def footer(canvas, doc):
        canvas.setFont("GSSans", 8)
        canvas.setFillColor(colors.HexColor(COLORS["navy"]))
        canvas.drawString(
            40, 25, BRAND["name"] + " | Apoyo experimental a la revisión especializada"
        )
        canvas.drawRightString(555, 25, str(doc.page))

    SimpleDocTemplate(
        stream, pagesize=(595, 842), rightMargin=40, leftMargin=40, topMargin=35, bottomMargin=45
    ).build(story, onFirstPage=footer, onLaterPages=footer)
    return stream.getvalue()
