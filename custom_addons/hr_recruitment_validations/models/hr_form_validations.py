# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AddValidationHr(models.Model):
    _inherit = 'hr.applicant'

    stage_check = fields.Char(related='stage_id.name')

    #~ #@api.multi
    #~ def write(self, data):
        #~ res = super(AddValidationHr, self).write(data)
        #~ print("RES",res,data['stage_id'])
        #~ if data['stage_id'] and data['last_stage_id']:
            #~ print("IFFFFFFFFFFF")
            #~ if data['last_stage_id'] > data['stage_id']:
                #~ raise UserError(_("Invalid movement!!!"))
        #~ return res
