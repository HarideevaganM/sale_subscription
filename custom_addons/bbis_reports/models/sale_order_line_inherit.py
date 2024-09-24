# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp


class BbisSaleOrderLineInherit(models.Model):
    _inherit = 'sale.order.line'

    discount = fields.Float(string='Discount (%)', digits=(2, 5), default=0.0)


class BbisAddonsLineInherit(models.Model):
    _inherit = 'addons.line'

    discount = fields.Float(string='Discount (%)', digits=(2, 5), default=0.0)
    discount_line = fields.Float(string='Discount (Fix)', digits=dp.get_precision('Product Price'), default=0.0,
                                 compute='_compute_discount_amount', store=True, readonly=False)

    # reset old code
    @api.onchange('discount_line', 'price_unit', 'product_uom_qty')
    def onchangediscount(self):
        return False

    @api.depends('discount', 'price_unit', 'product_uom_qty')
    def _compute_discount_amount(self):
        for r in self:
            if r.price_unit and r.product_uom_qty:
                r.discount_line = (r.discount / 100) * r.price_unit
                if r.discount_line > r.price_unit:
                    raise ValidationError(_('You cannot give a discount greater than the unit price!'))


    @api.onchange('discount_line', 'price_unit', 'product_uom_qty')
    def onchange_discount_amount(self):
        for r in self:
            if r.price_unit and r.product_uom_qty:
                r.discount = (r.discount_line * 100) / r.price_unit


class BbisAddonsServiceLineInherit(models.Model):
    _inherit = 'addons.service.line'

    discount = fields.Float(
        string='Discount (%)',
        digits='Discount',
        default=0.0
    )

    discount_line = fields.Float(
        string='Discount (Fix)',
        digits='Product Price',
        default=0.0,
        compute='_compute_discount_amount',
        store=True,
        readonly=False
    )

    @api.depends('discount', 'price_unit', 'product_uom_qty')
    def _compute_discount_amount(self):
        for r in self:
            if not float_is_zero(r.price_unit, precision_digits=2) and not float_is_zero(r.product_uom_qty,
                                                                                         precision_digits=2):
                r.discount_line = (r.discount / 100) * r.price_unit
                if r.discount_line > r.price_unit:
                    raise ValidationError(_('You cannot give a discount greater than the unit price!'))

    @api.onchange('discount_line', 'price_unit', 'product_uom_qty')
    def onchange_discount_amount(self):
        for r in self:
            if not float_is_zero(r.price_unit, precision_digits=2) and not float_is_zero(r.product_uom_qty,
                                                                                         precision_digits=2):
                r.discount = (r.discount_line * 100) / r.price_unit

