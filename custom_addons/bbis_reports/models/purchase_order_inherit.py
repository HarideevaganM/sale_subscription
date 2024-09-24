# -*- coding: utf-8 -*-

from odoo import api, fields, models


class BbisPurchaseOrderInherit(models.Model):
    _inherit = 'purchase.order'

    invoice_status_change = fields.Text(string='Manual Invoice Status Change Reason', track_visibility='onchange')
    contact_person = fields.Many2one('res.partner')
    partner_child_ids = fields.One2many(related='partner_id.child_ids')

    def update_invoice_status(self):
        return {
            'name': 'Update Invoice Status',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'bbis.update.po.so.invoice.status',
            'target': 'new',
            'context': {'default_model_type': 'purchase', 'default_purchase_order_id': self.id},
        }
