# -*- coding: utf-8 -*-
from odoo import models, fields
from odoo.addons.mrp.models.stock_move import StockMove as StockMove2


class StockMove(models.Model):
    _inherit = 'stock.move'

    def action_cancel(self):
        self._action_cancel()
        return True

    def _action_cancel(self):

        quant_obj = self.env['stock.quant']
        for move in self.filtered(lambda mv: mv.state == 'done' and mv.product_id.type == 'product'):
            for sm_line in move.move_line_ids:
                line_qty = sm_line.product_uom_id._compute_quantity(sm_line.qty_done, sm_line.product_id.uom_id)
                quant_obj._update_available_quantity(sm_line.product_id, sm_line.location_id, line_qty, lot_id=sm_line.lot_id, package_id=sm_line.package_id, owner_id=sm_line.owner_id)
                quant_obj._update_available_quantity(sm_line.product_id, sm_line.location_dest_id, line_qty * -1, lot_id=sm_line.lot_id, package_id=sm_line.package_id, owner_id=sm_line.owner_id)

            if move.procure_method == 'make_to_order' and not move.move_orig_ids:
                move.state = 'waiting'
            elif move.move_orig_ids and not all(orig.state in ('done', 'cancel') for orig in move.move_orig_ids):
                move.state = 'waiting'
            else:
                move.state = 'confirmed'

            if move.scrap_ids:
                move.scrap_ids.write({'state': 'cancel'})
            if move.account_move_ids:
                move.account_move_ids.button_cancel()
                move.account_move_ids.with_context(force_delete=True).unlink()

            # if move.stock_valuation_layer_ids:
            # move.stock_valuation_layer_ids.sudo().unlink()
            # if move.raw_material_production_id:
            #     move.raw_material_production_id.move_raw_ids._action_cancel()
            # else:
            #     if move.production_id:
            #         move.production_id.action_cancel()
        return super(StockMove, self)._action_cancel()


class StockScrap(models.Model):
    _inherit = 'stock.scrap'

    state = fields.Selection(
        selection_add=[
            ('cancel', 'Cancel')
        ],
        ondelete={
            'cancel': 'set default'
        }
    )

    def btn_action_cancel(self):
        for scrap in self.filtered(lambda x: x.move_id):
            scrap.move_id._action_cancel()


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def btn_reset_to_draft(self):
        for picking in self:
            move_raw_ids = picking.move_lines.filtered(lambda x: x.state == 'cancel').sudo()
            move_raw_ids.write({'state':'draft'})
