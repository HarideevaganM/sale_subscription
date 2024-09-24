from odoo import api, fields, models, _


class SaleOrderInherit(models.Model):
    _inherit = "sale.order"

    cancellation_reason = fields.Text("Cancellation Reason")


