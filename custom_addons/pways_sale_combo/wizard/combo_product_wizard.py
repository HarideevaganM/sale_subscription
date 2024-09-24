# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import api, fields, models, _
from odoo.exceptions import UserError
import psycopg2

class ComboProductWizard(models.TransientModel):
    _name = 'combo.product.wizard'

    product_id = fields.Many2one('product.product')
    quantity = fields.Float("Quantity", default=1.0)
    type = fields.Selection([('individual', 'Own Price'), ('total_price', 'Component Price')], required=True, default='total_price')
    price = fields.Float(string="Bundle Price",)

    @api.onchange('product_id', 'type')
    def _onchange_price(self):
        combo_price = sum(self.product_id.mapped("product_combo_ids").mapped("combo_price"))
        total_price = self.product_id.list_price if self.type == "individual" else combo_price
        self.price = total_price

    def prepaire_order_line(self):
        line_ids = []
        line_ids.append((0, 0, {
                "product_id" : self.product_id.id,
                "product_uom_qty" : self.quantity,
                "price_unit" : self.price,
                "name" : self.product_id.display_name,
                "product_uom" : self.product_id.uom_id.id,
            }))
        return line_ids

    def action_set_order_line(self):
        active_id = self._context.get('active_id')
        if active_id:
            order_id = self.env['sale.order'].search([('id', '=', active_id)], limit=1)
            if order_id and order_id.state != 'sale':
                if order_id.order_line:
                    order_id.order_line = [(5, 0, 0)]
                lines = self.prepaire_order_line()
                order_id.order_line = lines