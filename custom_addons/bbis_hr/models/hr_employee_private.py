# -*- coding: utf-8 -*-

from odoo import models, fields, api


class BbisHrEmployeePrivate(models.Model):
    """
    This model is only to not allow employee to access employee screen
    """
    _name = 'hr.employee.private'
    _description = 'HR Employee Private'

    name = fields.Char()
