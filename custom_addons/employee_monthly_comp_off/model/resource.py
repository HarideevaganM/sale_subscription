# -*- coding: utf-8 -*-
from odoo import fields, api, models, _


class ResourceCalendar(models.Model):
    _inherit='resource.calendar'

    total_working_hrs=fields.Float(string='Total Working Hours', default=0.0)