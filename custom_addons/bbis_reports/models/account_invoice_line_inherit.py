# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class BbisAccountInvoiceLineInherit(models.Model):
    _inherit = 'account.move.line'

    discount = fields.Float(string='Discount (%)', digits=(2, 5), default=0.0)
    price_unit = fields.Float(string='Unit Price', digits=(2, 5), default=0.0)
