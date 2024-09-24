
from odoo import api, fields, models, _


class ITCProductInherit(models.Model):
    _inherit = 'product.template'

    # Add one field is_itc_product for identifying if it is an ITC product.
    is_itc_product = fields.Boolean(string='ITC Product')
