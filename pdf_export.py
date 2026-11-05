"""Fuvarozói PDF: terv, visszaigazolás és díj külön, belső haszon nélkül."""
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape
import reportlab
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
from reportlab.graphics.shapes import Drawing, Rect, String


def ajanlat_pdf(terv, fejlec, kovetes, dij, feltetelek="", jovahagyva=False):
    font = Path(__file__).parent / "assets" / "DejaVuSans.ttf"
    if "Fuvar" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("Fuvar", str(font)))
    styles = getSampleStyleSheet()
    for style in styles.byName.values():
        style.fontName = "Fuvar"
        style.leading = 14
    styles["Title"].fontSize = 21
    styles["Title"].leading = 27
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    def p(s, style="BodyText"):
        return Paragraph(escape(str(s)).replace("\n", "<br/>"), styles[style])
    def table(rows, widths=(200, 315)):
        t = Table([[p(c) for c in row] for row in rows], colWidths=widths, repeatRows=1)
        t.setStyle(TableStyle([("BACKGROUND", (0,0),(-1,0), colors.HexColor("#e4effa")),
                              ("GRID",(0,0),(-1,-1),.4,colors.HexColor("#cad8e5")),
                              ("VALIGN",(0,0),(-1,-1),"TOP"), ("LEFTPADDING",(0,0),(-1,-1),8),
                              ("TOPPADDING",(0,0),(-1,-1),6), ("BOTTOMPADDING",(0,0),(-1,-1),6)]))
        return t
    safe_approval = (jovahagyva and terv.berakhato and kovetes.visszaigazolt
                     and bool(kovetes.visszaigazolas_hivatkozas.strip()) and bool(feltetelek.strip())
                     and all(c.halmozas.statusz != "Nem igazolt" for c in terv.csoportok))
    story = [p("FuvarDíj 4.0", "Title"), p("Fuvarozói egyeztető és ajánlati lap", "Heading2"),
             p("Felhasználó által jóváhagyott ajánlat" if safe_approval else "ELŐZETES TERV - VISSZAIGAZOLÁSRA VÁR"), Spacer(1,12),
             table([("Adat", "Érték"), ("Hivatkozás", fejlec.hivatkozas), ("Viszonylat", fejlec.viszonylat),
                    ("Fuvarozó", fejlec.fuvarozo), ("Készítette", fejlec.keszitette),
                    ("Raktér H × Sz × M (cm)", f"{terv.potkocsi.rakter_hossz_cm:g} × {terv.potkocsi.rakter_szelesseg_cm:g} × {terv.potkocsi.rakter_magassag_cm:g}"),
                    ("Össztömeg", f"{terv.ossz_suly_kg:g} kg")]), Spacer(1,12),
             p("Tervezett és visszaigazolt adatok", "Heading2"),
             table([("Mutató", "Érték"), ("A. Tervezett fizikai LDM", f"{terv.fizikai_ldm:.3f}"),
                    ("Igazolt geometriai alsó korlát", f"{terv.pakolas.also_korlat_cm/100:.3f} LDM"),
                    ("Elrendezés minősítése", terv.pakolas.modszer),
                    ("Tervezett elszámolási LDM", f"{terv.elszamolas.elszamolasi_ldm:.3f}"),
                    ("B. Fuvarozó által visszaigazolt", kovetes.visszaigazolt_ldm if kovetes.visszaigazolt else "Nincs"),
                    ("Visszaigazolás hivatkozása", kovetes.visszaigazolas_hivatkozas),
                    ("C. Tényleges rakodási LDM", kovetes.tenyleges_ldm if kovetes.tenyleges_ldm is not None else "Nincs"),
                    ("Eltérés indoka", kovetes.elteres_indoka)]), Spacer(1,12)]
    rows = [("Csoport", "db", "H × Sz × M (cm)", "kg/db", "szint")]
    for c in terv.csoportok:
        a=c.csoport
        rows.append((a.nev, a.darab, f"{a.hossz_cm:g} × {a.szelesseg_cm:g} × {a.magassag_cm:g}", f"{a.suly_kg:g}", c.halmozas.alkalmazott_szint))
    story += [p("Rakomány", "Heading2"),table(rows,(145,35,175,85,75))]
    scale=500/max(terv.potkocsi.rakter_hossz_cm,terv.pakolas.hasznalt_hossz_cm,1)
    height=terv.potkocsi.rakter_szelesseg_cm*scale
    drawing=Drawing(515,height+30)
    drawing.add(Rect(0,15,terv.potkocsi.rakter_hossz_cm*scale,height,fillColor=colors.HexColor("#edf3f8")))
    palette=["#1976d2","#43a047","#ef8b20","#8e24aa"]
    for e in terv.pakolas.elhelyezesek:
        drawing.add(Rect(e.x_cm*scale,15+e.y_cm*scale,e.hossz_cm*scale,e.szelesseg_cm*scale,
                         fillColor=colors.HexColor(palette[e.csoport%4]),strokeColor=colors.white,strokeWidth=.5))
        if min(e.hossz_cm,e.szelesseg_cm)*scale>15:
            drawing.add(String((e.x_cm+e.hossz_cm/2)*scale,15+(e.y_cm+e.szelesseg_cm/2)*scale,
                               f"{e.sorszam}x{terv.halmok.get(e.sorszam,1)}",fontName="Fuvar",fontSize=6,textAnchor="middle",fillColor=colors.white))
    story += [KeepTogether([p("Javasolt rakodás - felülnézet", "Heading2"), drawing]),
              p("Fuvarozói díj", "Heading2"),
              table([("Tétel", f"Nettó összeg ({dij.penznem})"), ("Alapdíj", f"{dij.alapdij:.2f}"),
                     ("Felárak", f"{dij.felarak_osszesen:.2f}"), ("Fuvarozói díj összesen", f"{dij.beszerzesi_koltseg:.2f}")]),
              p("Szerződéses feltételek", "Heading2"), p(feltetelek or "Még nincsenek rögzítve."),
              p("Ellenőrzendő feltételek", "Heading2")]
    for text in terv.feltetelezesek: story += [p(text), Spacer(1,5)]
    for u in terv.uzenetek + [u for c in terv.csoportok for u in c.uzenetek]:
        story += [p(u.szoveg), Spacer(1,5)]
    def footer(canvas, doc):
        canvas.setFont("Fuvar",8)
        canvas.drawString(40,23,"Geometriai terv; nem rakodásbiztonsági tanúsítás.")
        canvas.drawRightString(555,23,str(doc.page))
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    return buf.getvalue()
