from odoo import api, fields, models, _


class PickingOperationReportInherit(models.AbstractModel):
    _name = 'report.stock.report_picking_operations'
    _description = "picking_operations"

    # @api.model
    def _get_report_values(self, docids, data=None):
        delivery_obj = self.env["stock.picking"].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': "stock.picking",
            'docs': delivery_obj,
            'data': data,


        }
