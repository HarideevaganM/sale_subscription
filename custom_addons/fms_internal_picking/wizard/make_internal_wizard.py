# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class InternalPicking(models.TransientModel):
    _name = 'internal.mrp.wizard'

    product_id = fields.Many2one('product.product', string="Product")
    lot_id = fields.Many2one('stock.lot', 'Lot')
    product_quantity = fields.Float(string="Product Qty")
    product_uom = fields.Many2one('product.uom', string="UOM")
    source_location_id = fields.Many2one('stock.location', sting="Source Location")
    destination_location_id = fields.Many2one('stock.location', sting="Destination Location")

    @api.model
    def default_get(self, fields):
        res = super(InternalPicking, self).default_get(fields)
        repair_id = self.env['repair.order'].browse(self.env.context.get('active_id', False))
        if repair_id:
            stock = self.env['stock.picking'].search([('repair_id', '=', repair_id.id)], limit=1, order="id desc")
            if stock and stock.state != 'done' and not stock.state == 'cancel':
                raise UserError("Please process remaining return pickings")
            res['product_id'] = repair_id.product_id.id
            res['product_quantity'] = repair_id.product_qty
            res['product_uom'] = repair_id.product_uom.id
            res['lot_id'] = repair_id.lot_id.id
            res['source_location_id'] = stock.location_dest_id.id
        return res

    def create_internal_location(self):
        picking = self.env['stock.picking']
        repair_id = self.env['repair.order'].browse(self.env.context.get('active_id', False))
        if repair_id:
            for rec in self:
                vals = {
                        'origin' : repair_id.name,
                        'repair_id' : repair_id.id,
                        'move_type' : 'direct',
                        'location_id' : rec.source_location_id.id,
                        'location_dest_id': rec.destination_location_id.id,
                        'picking_type_id': self.env.ref('stock.picking_type_internal').id,
                        'job_id': repair_id.job_id and repair_id.job_id.id,
                        'product_lots_id':repair_id.lot_id and repair_id.lot_id.id,
                    }
                picking_id = picking.create(vals)
                if picking_id:
                    picking_id.write({
                        'move_lines': [(0, 0, {
                        'product_id': self.product_id.id,
                        'name': repair_id.name,
                        'product_uom': self.product_uom.id,
                        'product_uom_qty': self.product_quantity,
                        'reserved_availability': self.product_quantity,
                        'location_id':rec.source_location_id.id,
                        'location_dest_id': rec.destination_location_id.id,
                        'picking_id' : picking_id.id
                        })]
                    })
                    picking_id.action_assign()
