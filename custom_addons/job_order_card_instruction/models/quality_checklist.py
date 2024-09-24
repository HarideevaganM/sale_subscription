# -*- coding: utf-8 -*-

from odoo import fields, models


class QualityChecklist(models.Model):
    _name = "quality.checklist"

    name = fields.Char(
        string = "Name",
        copy=True,
        required=True,
    )
    code = fields.Char(
        string = "Code",
        copy=True,
        required=True,
    )

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: