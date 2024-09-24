# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class BbisMailMessageInherit(models.Model):
    _inherit = 'mail.message'

    email_cc = fields.Char('Cc', help="Carbon copy recipients (placeholders may be used here)")
