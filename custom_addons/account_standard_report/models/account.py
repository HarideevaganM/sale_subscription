# -*- coding: utf-8 -*-

from odoo import models, fields


class AccountAccount(models.Model):
    _inherit = 'account.account'

    compacted = fields.Boolean('Compacte entries.', help='If flagged, no details will be displayed in the Standard report, only compacted amounts.', default=False)
    type_third_parties = fields.Selection([('no', 'No'), ('supplier', 'Supplier'), ('customer', 'Customer')], string='Third Partie', required=True, default='no')

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    narration = fields.Text(related='move_id.narration', string='Narration', store=True)
