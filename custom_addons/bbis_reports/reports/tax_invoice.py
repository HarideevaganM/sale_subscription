from odoo import api, models, _
from odoo.exceptions import ValidationError

class BbisTaxInvoiceReport(models.AbstractModel):
    _name = 'report.bbis_reports.tax_invoice'
    _description = 'BBIS Tax Invoice Report'

    def _get_job_card(self, job_id):
        job = self.env['job.card'].search([('name', '=', job_id)], limit=1)
        return job

    def _get_excluding_vat(self, line):
        amount_excluding_vat = (line.quantity * line.price_unit) - line.discount_fix
        return amount_excluding_vat

    def _get_output_vat(self, line):
        after_discount = (line.quantity * line.price_unit) - line.discount_fix
        amount = sum(line.invoice_line_tax_ids.mapped('amount'))
        output_vat = (after_discount * amount) / 100
        return output_vat

    # Single vat amount calculation - 25-01-2024
    def _get_per_unit_vat(self, line):
        discount = (line.price_unit * line.discount) / 100
        after_discount = line.price_unit - discount
        amount = sum(line.invoice_line_tax_ids.mapped('amount'))
        per_unit_vat = (after_discount * amount) / 100
        return per_unit_vat

    # Find out Vat Name 25-01-2024
    def _get_tax_name(self, line):
        tax_name = ''
        tax_id = line.invoice_line_tax_ids.mapped('id')
        tax = self.env['account.tax'].search([('id', '=', tax_id)])
        if tax.name:
            tax_name = tax.name[6:]
        return tax_name

    def _get_total(self, line):
        output_vat = self.get_output_vat(line)
        after_discount = (line.quantity * line.price_unit) - line.discount_fix
        return after_discount + output_vat

    def _prepare_line(self, invoice_ids):
        lines = []
        for inv_line in invoice_ids.mapped('invoice_line_ids'):
            lines.append({
                    'default_code': inv_line.product_id.default_code,
                    'name': inv_line.name,
                    'quantity': inv_line.quantity,
                    'price_unit': inv_line.price_unit,
                    'discount_fix': inv_line.discount_fix,
                    'amount_excluding_vat': self.get_excluding_vat(inv_line),
                    'output_vat': self.get_output_vat(inv_line),
                    'total': self.get_total(inv_line),
                    'sequence_ref': inv_line.sequence_ref,
                    'tax_name': self.get_tax_name(inv_line),
                    'tax_unit': self.get_per_unit_vat(inv_line)

            })
        return lines

    # For renewal, rental, lease sales
    # Change the select query for getting the tax name on 25-01-2024.
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
                iv.price_unit,
                SUM(iv.discount_fix) total_discount,
                SUBSTRING(tax.name,7,8) as tax_name
                FROM account_invoice_line iv
                INNER JOIN product_product pp ON (pp.id = iv.product_id)
                INNER JOIN product_template pt ON (pt.id = pp.product_tmpl_id)
                LEFT JOIN account_invoice_line_tax line_tax on iv.id = line_tax.invoice_line_id
                LEFT JOIN account_tax tax on tax.id = line_tax.tax_id
                WHERE iv.invoice_id = %d
                GROUP BY pt.name, pt.default_code, iv.price_unit, pp.id, iv.invoice_id, tax.name
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
                for prod in invoice_lines:
                    after_discount = (prod.quantity * prod.price_unit) - prod.discount_fix
                    amount = sum(prod.invoice_line_tax_ids.mapped('amount'))
                    output_vat.append((after_discount * amount) / 100)

                    # Single vat amount calculation - 25-01-2024
                    single_discount = (prod.price_unit * prod.discount) / 100
                    after_discount = prod.price_unit - single_discount
                    per_unit_vat = (after_discount * amount) / 100

                sum_output_vat = sum(output_vat)
                line['total_price_exclude_vat'] = (line['price_unit'] * line['total_quantity']) - line['total_discount']
                line['total_vat'] = sum_output_vat
                line['total_amount'] = (line['price_unit'] * line['total_quantity']) + sum_output_vat - line['total_discount']
                line['tax_unit'] = per_unit_vat
                group_invoice_lines.append(line)

        return group_invoice_lines

    # Get Vehicle Details
    def _get_vehicle_details(self, invoice_ids):
        vehicles = []
        for inv_line in invoice_ids.mapped('vehicle_detail_ids').sorted(lambda move: move.start_date):
            vehicles.append({
                'serial': inv_line.serial_no_id.name,
                'device': inv_line.device_id.name,
                'vehicle': inv_line.vehicle_id.name,
                'start_date': inv_line.start_date,
                'end_date': inv_line.end_date,
            })

        return vehicles

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['account.move'].browse(docids)

        for inv_type in docs.mapped('type'):
            if inv_type not in ['out_invoice']:
                raise ValidationError("This is not a Customer Invoice.")

        company_id = self.env.user.company_id
        invoice_lines = self._prepare_line(docs)
        group_invoice_lines = self._prepare_group_lines(docs)
        vehicle_details = self._get_vehicle_details(docs)
        default_bank = self.env['account.journal'].browse(7)

        return {
            'doc_model': 'account.move',
            'docs': docs,
            'company': company_id,
            'invoice_lines': invoice_lines,
            'group_invoice_lines': group_invoice_lines,
            'vehicles': vehicle_details,
            'get_job_card': self.get_job_card,
            'default_bank': default_bank,
        }
