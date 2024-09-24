from odoo import api, models, _
from odoo.exceptions import ValidationError


class BbisTaxCreditInclusiveReport(models.AbstractModel):
    _name = 'report.bbis_reports.tax_credit_note_inclusive'
    _description = 'BBIS Tax Credit Note Inclusive Report'

    # check if invoice lines has unique products. only used for lease/rental
    def _get_unique_products(self, invoice_ids):
        products = []
        price_units = []
        for invoice in invoice_ids:
            if invoice.product_id not in products:
                products.append(invoice.product_id)

            if invoice.price_unit not in price_units:
                price_units.append(invoice.price_unit)

        data = {'products': len(products), 'price_units': len(price_units)}

        return data

    # Get Vehicle Details
    def _get_vehicle_details(self, invoice_ids):
        vehicles = []
        for inv_line in invoice_ids.mapped('vehicle_detail_ids'):
            vehicles.append({
                'serial': inv_line.serial_no_id.name,
                'device': inv_line.device_id.name,
                'vehicle': inv_line.vehicle_id.name,
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

        for invoice in docs:
            if not invoice.inclusive_invoice_line:
                raise ValidationError(_('There is no Inclusive Invoice Lines record. Please make sure to add.'))

            if invoice.amount_total != invoice.amount_total1:
                raise ValidationError(_('Invoice Lines total amount ({}) is not equal to Inclusive Invoice Lines total '
                                        'amount ({}). Please make sure to make it equal.')
                                      .format(invoice.amount_total, invoice.amount_total1))

            for invoice_line in invoice.inclusive_invoice_line:
                if not len(invoice_line.invoice_line_ids):
                    raise ValidationError(_('Please remove items with Zero quantity or no Products added '
                                            'from the Invoice Lines'))

        company_id = self.env.user.company_id
        vehicle_details = self._get_vehicle_details(docs)
        default_bank = self.env['account.journal'].browse(7)

        return {
            'doc_model': 'account.move',
            'docs': docs,
            'company': company_id,
            'vehicles': vehicle_details,
            'get_unique_products': self.get_unique_products,
            'default_bank': default_bank,
        }
