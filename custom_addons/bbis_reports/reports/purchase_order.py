from odoo import api, models, _
# from odoo.exceptions import ValidationError


class BbisPurchaseOrderReport(models.AbstractModel):
    _name = 'report.bbis_reports.purchase_order'
    _description = 'BBIS Purchase Order Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['purchase.order'].browse(docids)
        company_id = self.env.user.company_id

        single_discounts = []
        for invoice in docs.mapped('order_line'):
            single_discounts.append(float(invoice.discount_fix))

        # for doc in docs:
        #     if doc.state in ('draft','sent', 'to approve', 'awaiting_approval', 'cancel'):
        #         raise ValidationError('Sorry! You can only print approved PO.')

        return {
            'doc_model': 'purchase.order',
            'docs': docs,
            'company': company_id,
            'single_total_discount': sum(single_discounts),
        }
