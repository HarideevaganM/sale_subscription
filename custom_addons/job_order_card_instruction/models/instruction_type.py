# -*- coding: utf-8 -*-

from odoo import models, fields, api


class InstructionType(models.Model):
    _name = "instruction.type"
    _description = 'Instruction Type'

    name = fields.Char(
        string='Name',
        required=True,
    )
    code = fields.Char(
        string='Code',
        required=True,
    )
    image_1 = fields.Binary(
        string='Instruction Photo1',
    )
    image_2 = fields.Binary(
        string='Instruction Photo2',
    )
    image_3 = fields.Binary(
        string='Instruction Photo3',
    )
    image_4 = fields.Binary(
        string='Instruction Photo4',
    )
    image_5 = fields.Binary(
        string='Instruction Photo5',
    )

    # @api.multi
    def name_get(self):
        result = []
        for rec in self:
            name = rec.name + ' ' + '('+ rec.code+ ')'
            result.append((rec.id, name))
        return result

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
