# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


# Inherit Product pricelist for adding price list code.
class GfmsProductPriceListInherit(models.Model):
    _inherit = 'product.pricelist'

    pricelist_code = fields.Char(string='Code')