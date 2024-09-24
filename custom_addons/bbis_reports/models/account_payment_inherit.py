# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class BbisAccountPaymentInherit(models.Model):
    _inherit = 'account.payment'

    un_applied_payment = fields.Boolean(compute="_get_un_applied_payment", readonly=True, store=True)

    @api.depends('move_id.line_ids.reconciled')
    def _get_un_applied_payment(self):
        for r in self:
            # Check if any of the move's lines are not reconciled
            unreconciled_lines = r.move_id.line_ids.filtered(lambda l: not l.reconciled)
            r.un_applied_payment = bool(unreconciled_lines)


    #@api.multi
    def post(self):
        """
        Do not allow posting if there's no default payable and receivable accounts under contacts so that
        the sequence will not skip.
        """
        for rec in self:
            if not rec.partner_id.property_account_receivable_id or not rec.partner_id.property_account_payable_id:
                raise ValidationError("Please add the partner default payable & receivable accounts under contacts.")
            
        return super(BbisAccountPaymentInherit, self).post()
