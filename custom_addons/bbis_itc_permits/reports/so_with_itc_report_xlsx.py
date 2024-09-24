from odoo import models
from datetime import datetime


class SaleOrderWithItcReport(models.AbstractModel):
    _name = 'report.bbis_itc_permits.so_with_itc_report'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, orders):
        start_date = data['start_date']
        end_date = data['end_date']
        sales = []
        sale_order = self.env['sale.order'].search([('confirmation_date', '>=', start_date),
                                                    ('confirmation_date', '<=', end_date),
                                                    ('state', '!=', 'cancel')])
        for sale in sale_order:
            sales.append(sale.id)

        itc_product_template = self.env['product.template'].search([('is_itc_product', '=', True)], limit=1)
        itc_product = self.env['product.product'].search([('product_tmpl_id', '=', itc_product_template.id)])
        sale_order_lines = self.env['sale.order.line'].search([('order_id', 'in', sales), ('product_id', '=', itc_product.id), ('product_uom_qty', '>=', 1)])

        line_items = {}
        for line in sale_order_lines:

            if line.order_id.name not in line_items:
                line_items[line.order_id.name] = {
                    'partner': line.order_id.partner_id.name,
                    'order_id': line.order_id.id,
                    'confirmation_date': line.order_id.confirmation_date,
                    'purchase_order_no': line.order_id.purchase_order_no or '',
                    'purchase_order_date': line.order_id.purchase_order_date or '',
                    'order_line_ids': [line.id],
                    'product_id': line.product_id.id,
                    'qty': int(line.product_uom_qty),
                    'itc_notes': line.order_id.itc_notes or '',
                }
            else:
                line_items[line.order_id.name]['qty'] += int(line.product_uom_qty)
                line_items[line.order_id.name]['order_line_ids'].append(line.id)

        # Formats
        title_format = workbook.add_format({'bold': True, 'border': True, 'align': 'center', 'valign': 'vcenter',
                                            'font_size': 14})
        header_format = workbook.add_format({'bold': True, 'border': True, 'font_size': 11, 'align': 'center',
                                             'valign': 'vcenter', 'bg_color': '#f05a29', 'font_color': 'white'})
        sub_header_format = workbook.add_format({'bold': True, 'border': True, 'font_size': 9, 'align': 'center',
                                             'valign': 'vcenter', 'bg_color': '#f05a29', 'font_color': 'white'})
        cell_format_center = workbook.add_format({'valign': 'vcenter', 'border': True, 'font_size': 9, 'align': 'center', 'text_wrap': True})
        cell_format_left = workbook.add_format(
            {'valign': 'vcenter', 'border': True, 'font_size': 9, 'align': 'left', 'text_wrap': True})
        date_format_center = workbook.add_format({'valign': 'vcenter', 'border': True, 'font_size': 9, 'align': 'center', 'text_wrap': True, 'num_format': 'dd-mm-yyyy'})
        cell_format_total = workbook.add_format({'valign': 'vcenter', 'border': True, 'font_size': 9,
                                                 'align': 'center', 'text_wrap': True, 'bold': True})

        start_date_1 = datetime.strptime(start_date, '%Y-%m-%d')
        end_date_1 = datetime.strptime(end_date, '%Y-%m-%d')
        from_to_date = '{} - {}'.format(start_date_1.strftime('%b %d, %Y'), end_date_1.strftime('%b %d, %Y'))
        sheet_title = 'ITC Permit Report from {}'.format(from_to_date)

        sheet_sales = workbook.add_worksheet('ITC Permit Report')
        row, col = 0, 0
        sheet_sales.merge_range('A1:N1', sheet_title, title_format)
        sheet_sales.set_row(row, 30)
        sheet_sales.freeze_panes(3, 0)

        # Header of the Excel Report Declaration.
        sheet_sales.merge_range('A2:A3', "CUSTOMER", header_format)
        sheet_sales.merge_range('B2:F2', "SALE ORDER", header_format)
        sheet_sales.merge_range('G2:K2', "ITC PERMIT STATUS", header_format)
        sheet_sales.merge_range('L2:M2', "BILLING STATUS", header_format)

        row += 2
        col += 1
        sheet_sales.write(row, col, "SO No.", sub_header_format)
        col += 1
        sheet_sales.write(row, col, "Confirmation Date", sub_header_format)
        col += 1
        sheet_sales.write(row, col, "PO No.", sub_header_format)
        col += 1
        sheet_sales.write(row, col, "PO Date", sub_header_format)
        col += 1
        sheet_sales.write(row, col, "Ordered Permits", sub_header_format)
        col += 1
        sheet_sales.write(row, col, "Applied Permits", sub_header_format)
        col += 1
        sheet_sales.write(row, col, "Active Permits", sub_header_format)
        col += 1
        sheet_sales.write(row, col, "Expired Permits", sub_header_format)
        col += 1
        sheet_sales.write(row, col, "Cancelled Permits", sub_header_format)
        col += 1
        sheet_sales.write(row, col, "Pending Permits", sub_header_format)
        col += 1
        sheet_sales.write(row, col, "Invoiced Permits", sub_header_format)
        col += 1
        sheet_sales.write(row, col, "Pending Invoice", sub_header_format)
        col += 1
        sheet_sales.merge_range('N2:N3', "ITC Notes", header_format)
        col += 1

        col = 0
        # Adjust the column width.
        sheet_sales.set_column(col, col, 40)
        col += 1
        sheet_sales.set_column(col, col, 12)
        col += 1
        sheet_sales.set_column(col, col, 15)
        col += 1
        sheet_sales.set_column(col, col, 12)
        col += 1
        sheet_sales.set_column(col, col, 12)
        col += 1
        sheet_sales.set_column(col, col, 12)
        col += 1
        sheet_sales.set_column(col, col, 12)
        col += 1
        sheet_sales.set_column(col, col, 12)
        col += 1
        sheet_sales.set_column(col, col, 12)
        col += 1
        sheet_sales.set_column(col, col, 12)
        col += 1
        sheet_sales.set_column(col, col, 12)
        col += 1
        sheet_sales.set_column(col, col, 12)
        col += 1
        sheet_sales.set_column(col, col, 12)
        col += 1
        sheet_sales.set_column(col, col, 40)
        col += 1

        row += 1
        itc = self.env['itc.permit']
        # For loop for getting all the vehicle details.
        order_total = 0
        applied_total = 0
        running_total = 0
        expired_total = 0
        cancelled_total = 0
        invoiced_total = 0
        pending_total = 0
        pending_invoice_total = 0

        for key,line in line_items.items():
            sheet_sales.write(row, 0, line['partner'], cell_format_center)
            sheet_sales.write(row, 1, key, cell_format_center)

            applied_permits = itc.search([('sale_order_id', '=', line['order_id']), ('state', '=', 'applied'), ('free_permit', '=', False)])
            running_permits = itc.search([('sale_order_id', '=', line['order_id']), ('state', '=', 'done'), ('free_permit', '=', False)])
            expired_permits = itc.search([('sale_order_id', '=', line['order_id']), ('state', '=', 'expired'), ('free_permit', '=', False)])
            cancelled_permits = itc.search([('sale_order_id', '=', line['order_id']), ('state', '=', 'cancel'), ('free_permit', '=', False), ('invoice_no', '!=', False)])

            total_permits = len(applied_permits) + len(running_permits) + len(expired_permits) + len(cancelled_permits)
            pending_permits = line['qty'] - total_permits

            invoiced_permits = self.env['account.move.line'].search([('sale_line_ids', 'in', line['order_line_ids']), ('product_id', '=', line['product_id'])])
            invoiced_permits_cnt = 0
            for invoice_line in invoiced_permits:
                if invoice_line.invoice_id.state not in ('draft', 'cancel'):
                    invoiced_permits_cnt += invoice_line.quantity

            pending_invoice = total_permits - invoiced_permits_cnt

            if line['confirmation_date']:
                confirm_date = datetime.strptime(line['confirmation_date'], '%Y-%m-%d %H:%M:%S')
            else:
                confirm_date = ''

            sheet_sales.write(row, 2, confirm_date, date_format_center)
            sheet_sales.write(row, 3, line['purchase_order_no'], cell_format_center)
            sheet_sales.write(row, 4, line['purchase_order_date'], cell_format_center)
            sheet_sales.write(row, 5, line['qty'], cell_format_center)
            sheet_sales.write(row, 6, len(applied_permits), cell_format_center)
            sheet_sales.write(row, 7, len(running_permits), cell_format_center)
            sheet_sales.write(row, 8, len(expired_permits), cell_format_center)
            sheet_sales.write(row, 9, len(cancelled_permits), cell_format_center)
            sheet_sales.write(row, 10, pending_permits, cell_format_center)
            sheet_sales.write(row, 11, invoiced_permits_cnt, cell_format_center)
            sheet_sales.write(row, 12, pending_invoice, cell_format_center)
            sheet_sales.write(row, 13, line['itc_notes'], cell_format_left)

            order_total += line['qty']
            applied_total += len(applied_permits)
            running_total += len(running_permits)
            expired_total += len(expired_permits)
            cancelled_total += len(cancelled_permits)
            invoiced_total += invoiced_permits_cnt
            pending_total += pending_permits
            pending_invoice_total += pending_invoice
            row += 1

        sheet_sales.write(row, 0, 'TOTAL', cell_format_total)
        sheet_sales.write(row, 5, order_total, cell_format_total)
        sheet_sales.write(row, 6, applied_total, cell_format_total)
        sheet_sales.write(row, 7, running_total, cell_format_total)
        sheet_sales.write(row, 8, expired_total, cell_format_total)
        sheet_sales.write(row, 9, cancelled_total, cell_format_total)
        sheet_sales.write(row, 10, pending_total, cell_format_total)
        sheet_sales.write(row, 11, invoiced_total, cell_format_total)
        sheet_sales.write(row, 12, pending_invoice_total, cell_format_total)
