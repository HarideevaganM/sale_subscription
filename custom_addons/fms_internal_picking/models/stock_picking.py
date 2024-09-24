from odoo import models,fields,api, _

class MRPRepair(models.Model):
    _inherit="repair.order"

    picking_count = fields.Integer(compute='_picking_count')

    #@api.multi
    def _picking_count(self):
        for rec in self:
            picking_ids= self.env['stock.picking'].search([('repair_id', '=', rec.id)])
            rec.picking_count = len(picking_ids.ids)

    #@api.multi
    def open_picking(self):
        picking_ids= self.env['stock.picking'].search([('repair_id', '=', self.id)])
        return {
            'name': _('Internal Transfer'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'stock.picking',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', picking_ids.ids)],
        }