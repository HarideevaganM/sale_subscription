# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    is_approved = fields.Boolean(string="Approved")

    @api.model
    def default_get(self, vals):
        res = super(StockPicking, self).default_get(vals)
        if self.env.context.get('default_code') == 'internal':
            picking_type_id = self.env['stock.picking.type'].search([('code', '=', 'internal')], limit=1)
            res['picking_type_id'] = picking_type_id and picking_type_id.id
        return res

    #@api.multi
    def button_validate(self):
        if not self.is_approved and self.picking_type_id.code == 'internal':
            raise UserError(_("You need to take approval for this internal transfer"))
        return super(StockPicking, self).button_validate()

    def approval_internal_picking(self):
        self.is_approved = True
        self.action_assign()
        return True