# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class BbisSoLineMultiUpdate(models.TransientModel):
    _name = 'bbis.so.line.multi.update'
    _description = 'BBIS Sales Order Multi Update Wizard'

    def _get_default_order(self):
        active_id = self._context.get('active_id')
        if active_id:
            order = self.env['sale.order'].search([('id', '=', active_id)], limit=1)
            return order
        return False

    order_id = fields.Many2one('sale.order', default=_get_default_order, readonly=True)
    order_line_ids = fields.Many2many('sale.order.line', 'bbis_so_line_multi_update_rel', 'so_line_id', 'multi_update_id', string="Order Lines")
    price = fields.Float()

    def update_price(self):
        if self.order_id.state in ('sale', 'done', 'cancel', 'cancel_req'):
            raise ValidationError("Sorry, you are only allowed to update Sale Orders in Draft, Quotation Sent and Submitted States.")

        if not self.order_line_ids:
            raise ValidationError("Please select product from the order lines.")

        for r in self.order_line_ids:
            # print(r.name)
            r.update({'price_unit': self.price})
