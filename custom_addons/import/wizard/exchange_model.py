# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools, _
from datetime import timedelta


class PosOrderExchange(models.TransientModel):
    _name = 'pos.order.exchange'
    
    exchange_product_line = fields.One2many("pos.exchange.orderline", "pro_id", "Exchange Product")
    order_id = fields.Many2one("pos.order", "Order Ref", required=True)
    session_id = fields.Many2one("pos.session", "Session Ref", readonly=True)
    order_date = fields.Datetime("Purchase Date", readonly=True)
    customer_id = fields.Many2one("res.partner", "Customer Name",readonly=True)
    
    # @api.multi
    @api.onchange('order_id')
    def onchange_order(self):
        self.session_id = self.order_id.session_id
        self.order_date = self.order_id.date_order
        self.customer_id = self.order_id.partner_id
        #~ self.exchange_product_line.write({'product_id':self.order_id.lines.product_id.id})

	#~ @api.model
	#~ def create_exchange(self):
	#~ @api.model
    #~ def default_get(self, fields):
        #~ if len(self.env.context.get('active_ids', list())) > 1:
            #~ raise UserError("You may only return one picking at a time!")
        #~ res = super(ReturnPicking, self).default_get(fields)

        #~ Quant = self.env['stock.quant']
        #~ move_dest_exists = False
        #~ product_return_moves = []
        #~ picking = self.env['stock.picking'].browse(self.env.context.get('active_id'))
        #~ if picking:
            #~ if picking.state != 'done':
                #~ raise UserError(_("You may only return Done pickings"))
            #~ for move in picking.move_lines:
                #~ if move.scrapped:
                    #~ continue
                #~ if move.move_dest_id:
                    #~ move_dest_exists = True
                #~ # Sum the quants in that location that can be returned (they should have been moved by the moves that were included in the returned picking)
                #~ quantity = sum(quant.qty for quant in Quant.search([
                    #~ ('history_ids', 'in', move.id),
                    #~ ('qty', '>', 0.0), ('location_id', 'child_of', move.location_dest_id.id)
                #~ ]).filtered(
                    #~ lambda quant: not quant.reservation_id or quant.reservation_id.origin_returned_move_id != move)
                #~ )
                #~ quantity = move.product_id.uom_id._compute_quantity(quantity, move.product_uom)
                #~ product_return_moves.append((0, 0, {'product_id': move.product_id.id, 'quantity': quantity, 'move_id': move.id}))

            #~ if not product_return_moves:
                #~ raise UserError(_("No products to return (only lines in Done state and not fully returned yet can be returned)!"))
            #~ if 'product_return_moves' in fields:
                #~ res.update({'product_return_moves': product_return_moves})
            #~ if 'move_dest_exists' in fields:
                #~ res.update({'move_dest_exists': move_dest_exists})
            #~ if 'parent_location_id' in fields and picking.location_id.usage == 'internal':
                #~ res.update({'parent_location_id': picking.picking_type_id.warehouse_id and picking.picking_type_id.warehouse_id.view_location_id.id or picking.location_id.location_id.id})
            #~ if 'original_location_id' in fields:
                #~ res.update({'original_location_id': picking.location_id.id})
            #~ if 'location_id' in fields:
                #~ location_id = picking.location_id.id
                #~ if picking.picking_type_id.return_picking_type_id.default_location_dest_id.return_location:
                    #~ location_id = picking.picking_type_id.return_picking_type_id.default_location_dest_id.id
                #~ res['location_id'] = location_id
        #~ return res

class PosExchangeOrderline(models.TransientModel):
    _name = 'pos.exchange.orderline'
    
    pro_id = fields.Many2one("pos.order.exchange", "Order Ref")
    product_id = fields.Many2one("product.product", "Product")
    qty = fields.Float("Quantity")
    discount = fields.Float("Discount")
    unit_price = fields.Float("Unit Price")
    sub_tax = fields.Float("Subtotal W/O Tax")
    sub_total = fields.Float("Subtotal")
    tax_id = fields.Many2one("account.tax", "Taxes")
   
