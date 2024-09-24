# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class LotSerialWizard(models.TransientModel):
    _name = 'lot.serial.wizard'

    message = fields.Text(default="It will only print serials which has qty greater then 1 or yet not used", readonly=True)

    #@api.multi
    def print_report_csv(self):
        jobs_ids = self.env['job.card'].browse(self.env.context.get('active_ids'))
        data = {'job_ids': jobs_ids.ids}
        return self.env.ref('lot_export_csv.lot_serial_csv').report_action(self, data=data)
