# -*- coding: utf-8 -*-

from odoo import models, fields, api


class BiometricDevice(models.Model):
    _name = 'bbis.message.wizard'
    _description = 'BBIS Message Wizard'

    message = fields.Text(required=True)

    #@api.multi
    def action_close(self):
        """ close wizard"""
        return {'type': 'ir.actions.act_window_close'}
