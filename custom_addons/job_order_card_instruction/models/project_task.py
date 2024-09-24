# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProjectTask(models.Model):
    _inherit = "project.task"

    instruction_ids = fields.One2many(
        'job.instruction',
        'job_id',
        string='Instructions',
    )

    # @api.multi
    def show_instruction(self):
        self.ensure_one()
        res = self.env.ref('job_order_card_instruction.action_job_instruction_display')
        res = res.read()[0]
        res['domain'] = str([('id', 'in', self.instruction_ids.ids)])
        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
