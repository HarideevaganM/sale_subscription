from odoo import models, fields, api, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError, ValidationError


class PurchaseOrderLineInherit(models.Model):
    _inherit = 'purchase.order.line'

    # Adding discount and discount amount column in purchase order.
    discount = fields.Float(string='Discount (%)', digits=(2, 5), default=0.0)
    discount_fix = fields.Float(string='Discount (Fix)', digits=dp.get_precision('Product Price'), default=0.0,
                                 compute='_compute_discount_amount', store=True, readonly=False)

    # Compute function for calculatinf the discount percentage while entering the discount amount.
    @api.depends('discount', 'product_qty', 'price_unit')
    def _compute_discount_amount(self):
        for r in self:
            if r.price_unit and r.product_qty:
                r.discount_fix = (r.discount / 100) * r.price_unit
            else:
                if r.discount_fix > r.price_unit:
                    raise ValidationError(_('You can not give discount more than unit price!'))

    # Calculating the discount percentage from discount amount.
    @api.onchange('discount_fix')
    def onchange_discount_amount(self):
        for r in self:
            if r.price_unit and r.product_qty:
                r.discount = ((r.discount_fix / r.price_unit) * 100)

    # Calculating the subtotal and tax amount after discount. inherited method.
    @api.depends('product_qty', 'price_unit', 'taxes_id', 'discount')
    def _compute_amount(self):
        res = super(PurchaseOrderLineInherit, self)._compute_amount()
        for line in self:
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.taxes_id.compute_all(price, line.order_id.currency_id, line.product_qty, product=line.product_id, partner=line.order_id.partner_id)
            line.discount_fix = (line.discount / 100) * line.price_unit
            total_discount = line.discount_fix * line.product_qty
            line.update({
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'price_total': taxes['total_included'],
                'price_subtotal': (line.price_unit * line.product_qty) - total_discount,
            })
        return res
