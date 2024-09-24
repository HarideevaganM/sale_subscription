# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class BbisSoLineMultiUpdate(models.TransientModel):
    _name = 'bbis.invoice.line.multi.update'
    _description = 'BBIS Invoice Line Multi Update Wizard'

    def _get_default_invoice(self):
        return self.env['account.move'].browse(self._context.get('active_id'))

    invoice_id = fields.Many2one('account.move', default=_get_default_invoice, readonly=True)
    invoice_line_ids = fields.Many2many('account.move.line', 'bbis_invoice_line_multi_update_rel', 'invoice_line_id', 'multi_update_id', string="Invoice Lines")
    price = fields.Float()

    def update_price(self):
        if self.invoice_id.state != 'draft':
            raise ValidationError("Sorry, you're only allowed to update Invoice Lines in Draft State.")

        if not self.invoice_line_ids:
            raise ValidationError("Please select product from the order lines.")

        for r in self.invoice_line_ids:
            r.update({'price_unit': self.price})
