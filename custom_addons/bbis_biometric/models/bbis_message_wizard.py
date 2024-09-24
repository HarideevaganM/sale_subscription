# -*- coding: utf-8 -*-

from odoo import models, fields, api


class BiometricDevice(models.Model):
    _name = 'bbis.message.wizard'
    _description = 'BBIS Message Wizard'

    message = fields.Text(required=True)
