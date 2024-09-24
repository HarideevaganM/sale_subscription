# -*- coding: utf-8 -*-
from odoo import api, fields, models


class Purchase(models.Model):
    _inherit = "purchase.order"

    @api.depends('order_line.price_total', 'shoping', 'other')
    def _amount_all(self):
        for order in self:
            amount_untaxed = amount_tax = 0.0
            for line in order.order_line:
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
            order.update({
                'amount_untaxed': order.currency_id.round(amount_untaxed),
                'amount_tax': order.currency_id.round(amount_tax),
                'amount_total': amount_untaxed + amount_tax + order.shoping + order.other,
            })

    shipped_vai = fields.Char(string="Shipped Via")
    fob_point = fields.Char(string="F.O.B.Point" )
    shoping = fields.Float(string="Shoping", readonly=False, store=True)
    other = fields.Float(string="Other", readonly=False, store=True)