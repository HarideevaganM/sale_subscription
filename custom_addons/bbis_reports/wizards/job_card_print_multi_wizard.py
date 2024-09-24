# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PrintMultipleJobCards(models.TransientModel):
    _name = 'job.card.print_multiple_job_cards'
    _description = 'Wizard: Print Multiple Job Cards'

    def default_job_cards(self):
        return self.env['job.card'].browse(self._context.get('active_ids'))

    job_card_ids = fields.Many2many('job.card', string='Job Cards', required=True, default=default_job_cards)

    def print_job_cards(self):
        company_ids = []
        so_ids = []
        job_types = []
        for job_card in self.job_card_ids:
            if job_card.company_id not in company_ids:
                company_ids.append(job_card.company_id)
                so_ids.append(job_card.sale_order_id)
                job_types.append(job_card.job_card_type)

            if len(company_ids) > 1:
                raise ValidationError(_('Please select only Job Cards with the same Client Name.'))

            if len(so_ids) > 1:
                raise ValidationError(_('Please select only Job Cards with the same Sale Order.'))

            if len(job_types) > 1:
                raise ValidationError(_('Please select only Job Cards with the same Job Type.'))

        return self.env.ref('bbis_reports.bbis_reports_job_card_multi').report_action(self.job_card_ids)

