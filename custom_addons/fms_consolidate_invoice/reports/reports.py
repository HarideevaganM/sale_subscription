from odoo import models, api
from odoo.exceptions import ValidationError


class SaleInvoiceReport(models.AbstractModel):
    _name = 'report.fms_consolidate_invoice.sale_invoice_report'

    def _get_purchase_date(self, data):
        self.env.cr.execute("""SELECT TO_CHAR(po.date_order,'dd-MM-YY') as date_order FROM purchase_order po
                            JOIN account_invoice ai ON(po.name=ai.origin)WHERE ai.id=%d""" % data.id)
        date_order = self.env.cr.dictfetchall()
        return date_order

    #@api.multi
    def _get_currency_name(self, data):
        self.env.cr.execute('''select rc.name as currency, rc.rounding from account_invoice ai 
                                join res_currency rc on ai.currency_id=rc.id where ai.id =%s ''' % (data.id))
        currency_name = self.env.cr.dictfetchall()
        return currency_name


    #@api.multi
    def convert_num_to_word(self, data):
        amount = data.amount_total
        amount_in_words = data.currency_id.with_context(lang=data.partner_id.lang or 'es_ES').amount_to_text(
            amount).title()
        return amount_in_words

    #@api.multi
    def _get_report_values(self, ids, data=None):
        report_obj = self.env['consolidate.invoice'].browse(ids)
        for report in report_obj:
            return {
                'doc_ids': ids,
                'doc_model': 'consolidate.invoice',
                'docs': report_obj,
                'data': data,
                'get_purchase_date': self.get_purchase_date,
                'convert_num_to_word': self.convert_num_to_word,
                'get_currency_name': self.get_currency_name,
            }