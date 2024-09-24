# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class InclusiveOrderLine(models.Model):
    _name = "hr.working.branch"
    _description = "HR Working Branch"

    name = fields.Char()
    monday = fields.Boolean()
    tuesday = fields.Boolean()
    wednesday = fields.Boolean()
    thursday = fields.Boolean()
    friday = fields.Boolean()
    saturday = fields.Boolean()
    sunday = fields.Boolean()
