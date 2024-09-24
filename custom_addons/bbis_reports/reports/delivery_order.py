from odoo import api, models, _
from odoo.exceptions import ValidationError


class BbisDeliveryOrderReport(models.AbstractModel):
    _name = 'report.bbis_reports.delivery_order'
    _description = 'BBIS Delivery Order Report'

    def _get_serials(self, stock_move):
        serials = stock_move.mapped('move_line_ids').mapped('lot_id.name')

        return ", ".join(serials) if serials else False

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['stock.picking'].browse(docids)
        company_id = self.env.user.company_id

        return {
            'doc_model': 'stock.picking',
            'docs': docs,
            'company': company_id,
            'get_serials': self.get_serials,
        }
