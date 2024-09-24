from odoo import api, fields, models, _


class BbisCRMLeadInherit(models.Model):
    _inherit = 'crm.lead'

    customer_class = fields.Selection(related='partner_id.customer_class', string='Customer Class', readonly=True)
