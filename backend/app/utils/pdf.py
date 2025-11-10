from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
def invoice_pdf(client, payments, out_path):
    c = canvas.Canvas(out_path, pagesize=A4)
    w, h = A4
    c.setFont('Helvetica-Bold', 14)
    c.drawString(40, h-60, f'Factura - {client.get("name")}')
    c.setFont('Helvetica', 10)
    y = h-120
    c.drawString(40, y, 'Año')
    c.drawString(120, y, 'Mes')
    c.drawString(200, y, 'Monto')
    c.drawString(300, y, 'Estado')
    y -= 20
    for p in payments:
        c.drawString(40, y, str(p['year']))
        c.drawString(120, y, str(p['month']))
        c.drawString(200, y, f"{p['amount']}")
        c.drawString(300, y, p['status'])
        y -= 18
        if y < 80:
            c.showPage()
            y = h-80
    c.save()
    return out_path
