# -*- coding: utf-8 -*-

from odoo import models, fields, api


class Partner(models.Model):
    _inherit = "res.partner"

    # @api.multi
    def name_get(self):
        res = []
        for partner in self:
            name = partner.name or ''
            res.append((partner.id, name))
        return res