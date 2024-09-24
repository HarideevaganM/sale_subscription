from odoo import api, fields, models, _


class PaymentReport(models.AbstractModel):
    _name = 'report.account.report_payment_receipt'
    _description = "fms_card"

    # @api.multi
    def convert_num_to_word(self, data):
        amount = data.amount
        amount_in_words = data.currency_id.with_context(lang=data.partner_id.lang or 'es_ES').amount_to_text(amount).title()
        return amount_in_words

    # @api.multi
    def _get_report_values(self, ids, data=None):
        report_obj = self.env['account.payment'].browse(ids)
        return {
            'doc_ids': ids,
            'doc_model': 'account.move',
            'docs': report_obj,
            'data': data,
            'convert_num_to_word': self.convert_num_to_word,
        }






