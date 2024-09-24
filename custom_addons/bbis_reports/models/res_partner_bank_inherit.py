# -*- coding: utf-8 -*-

from odoo import api, fields, models


class BbisResPartnerBankInherit(models.Model):
    _inherit = 'res.partner.bank'

    iban = fields.Char(string='IBAN')
