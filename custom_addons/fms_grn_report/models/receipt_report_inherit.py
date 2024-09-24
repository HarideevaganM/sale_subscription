
from odoo import api, fields, models, _


class ReportInvoiceWithPayments(models.AbstractModel):
    _name = 'report.account.report_invoice_with_payments'
    _description = "fms_card"


    # @api.multi
    def _get_report_values(self, ids, data=None):
        report_obj = self.env['account.move'].browse(ids)
        return {
            'doc_ids': ids,
            'doc_model': 'account.move',
            'docs': report_obj,
            'data': data,
            'convert_num_to_word': self.convert_num_to_word,
        }

class AccountMove(models.Model):
    _inherit = 'account.move'

    def convert_num_to_word(self, data):
        amount = data.amount_total
        amount_in_words = data.currency_id.with_context(lang=data.partner_id.lang or 'es_ES').amount_to_text(amount).title()
        return amount_in_words