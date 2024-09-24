from odoo import api, models, _
from odoo.exceptions import ValidationError


class BbisTaxCreditNoteReport(models.AbstractModel):
    _name = 'report.bbis_reports.tax_credit_note'
    _description = 'BBIS Tax Credit Note Report'

    # Get discount in amount per line
    def _get_discount(self, line):
        sub_total = line.quantity * line.price_unit
        discount = sub_total * (line.discount / 100)
        return discount

    # Get amount excluding vat and discount
    def _get_excluding_vat(self, line):
        # amount_excluding_vat = (line.quantity * line.price_unit) - line.discount_fix
        sub_total = line.quantity * line.price_unit
        discount = sub_total * (line.discount / 100)
        amount_excluding_vat = sub_total - discount
        return amount_excluding_vat

    # Get amount including vat and discount
    def _get_output_vat(self, line):
        # after_discount = (line.quantity * line.price_unit) - line.discount_fix
        sub_total = line.quantity * line.price_unit
        discount = sub_total * (line.discount / 100)
        after_discount = (line.quantity * line.price_unit) - discount
        amount = sum(line.invoice_line_tax_ids.mapped('amount'))
        output_vat = (after_discount * amount) / 100
        return output_vat

    # get the total amount
    def _get_total(self, line):
        output_vat = self.get_output_vat(line)
        # after_discount = (line.quantity * line.price_unit) - line.discount_fix
        sub_total = line.quantity * line.price_unit
        discount = sub_total * (line.discount / 100)
        after_discount = sub_total - discount
        return after_discount + output_vat

    # Get invoice line items
    def _prepare_line(self, invoice_ids):
        lines = []
        for inv_line in invoice_ids.mapped('invoice_line_ids'):
            lines.append({
                'default_code': inv_line.product_id.default_code,
                'name': inv_line.name,
                'quantity': inv_line.quantity,
                'price_unit': inv_line.price_unit,
                'discount': inv_line.discount,
                'discount_amount': self.get_discount(inv_line),
                'amount_excluding_vat': self.get_excluding_vat(inv_line),
                'output_vat': self.get_output_vat(inv_line),
                'total': self.get_total(inv_line),
                'sequence_ref': inv_line.sequence_ref
            })
        return lines

    # For renewal/rental/lease sales grouped by product and price
    def _prepare_group_lines(self, invoice_ids):
        for invoice_id in invoice_ids:
            self.env.cr.execute(
                """
                SELECT
                pp.id product_id,
                iv.invoice_id,
                iv.invoice_id,
                pt.default_code,
                pt.name,
                SUM(iv.quantity) total_quantity,
                iv.price_unit
                FROM account_invoice_line iv
                INNER JOIN product_product pp ON (pp.id = iv.product_id)
                INNER JOIN product_template pt ON (pt.id = pp.product_tmpl_id)
                WHERE iv.invoice_id = %d
                GROUP BY pt.name, pt.default_code, iv.price_unit, pp.id, iv.invoice_id
                ORDER BY pt.default_code ASC
                """ % int(invoice_id))

            grouped_invoice = self.env.cr.dictfetchall()

            group_invoice_lines = []
            for line in grouped_invoice:
                prod_id = line['product_id']
                invoice_id = line['invoice_id']
                price_unit = line['price_unit']
                invoice_lines = self.env['account.move.line'].search([('product_id', '=', prod_id),
                                                                         ('invoice_id', '=', invoice_id),
                                                                         ('price_unit', '=', price_unit)])
                output_vat = []
                total_discount = []
                for prod in invoice_lines:
                    subtotal = prod.quantity * prod.price_unit
                    discount = subtotal * (prod.discount / 100)
                    after_discount = subtotal - discount
                    amount = sum(prod.invoice_line_tax_ids.mapped('amount'))
                    output_vat.append((after_discount * amount) / 100)
                    total_discount.append(discount)

                sum_output_vat = sum(output_vat)
                sum_total_discount = sum(total_discount)
                line['total_price_exclude_vat'] = (line['price_unit'] * line['total_quantity']) - sum_total_discount
                line['total_vat'] = sum_output_vat
                line['total_discount'] = sum_total_discount
                line['total_amount'] = (line['price_unit'] * line[
                    'total_quantity']) + sum_output_vat - sum_total_discount
                group_invoice_lines.append(line)

        return group_invoice_lines

    # Get Vehicle Details
    def _get_vehicle_details(self, invoice_ids):
        vehicles = []
        for inv_line in invoice_ids.mapped('vehicle_detail_ids'):
            vehicles.append({
                'client': inv_line.partner_id.name,
                'device_name': inv_line.device_id.name,
                'vehicle': inv_line.vehicle_id.name,
                'vehicle_name': inv_line.vehicle_id.vehicle_name,
                'serial': inv_line.serial_no_id.name,
                'start_date': inv_line.start_date,
                'end_date': inv_line.end_date,
            })

        return vehicles

    @api.model
    def _get_report_values(self, ids, data=None):
        docs = self.env['account.move'].browse(ids)

        for inv_type in docs.mapped('type'):
            if inv_type not in ['out_refund', 'in_refund']:
                raise ValidationError("This is not Credit or Debit Note.")

        company_id = self.env.user.company_id
        invoice_lines = self._prepare_line(docs)
        group_invoice_lines = self._prepare_group_lines(docs)
        vehicle_details = self._get_vehicle_details(docs)

        return {
            'doc_model': 'account.move',
            'docs': docs,
            'company': company_id,
            'invoice_lines': invoice_lines,
            'group_invoice_lines': group_invoice_lines,
            'vehicles': vehicle_details,
        }
