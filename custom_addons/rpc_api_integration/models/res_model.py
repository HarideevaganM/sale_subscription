# -*- coding: utf-8 -*-

from odoo import fields, models

class JobCard(models.Model):
    _inherit = 'job.card'

    is_exported = fields.Boolean(string='Exported' ,copy=False)
    device_code = fields.Char(related='device_id.default_code', string='Device Code', store=True)
