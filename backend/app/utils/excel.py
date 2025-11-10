from openpyxl import Workbook
def payments_to_xlsx(rows, out_path):
    wb = Workbook()
    ws = wb.active
    ws.append(['id','client_id','year','month','amount','status','paid_date','payment_type'])
    for r in rows:
        ws.append([r['id'], r['client_id'], r['year'], r['month'], r['amount'], r['status'], r['paid_date'], r['payment_type']])
    wb.save(out_path)
    return out_path
