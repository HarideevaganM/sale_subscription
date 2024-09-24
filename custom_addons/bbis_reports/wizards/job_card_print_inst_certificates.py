# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PrintInstallationCertificates(models.TransientModel):
    _name = 'job.card.print_installation_certificates'
    _description = 'Wizard: Print Installation Certificates'

    def default_job_cards(self):
        return self.env['job.card'].browse(self._context.get('active_ids'))

    job_card_ids = fields.Many2many('job.card', string='Job Cards',
                                    required=True, default=default_job_cards)

    def print_installation_certificates(self):
        company_ids = []
        if self.job_card_ids:
            for job_card in self.job_card_ids:
                if job_card.company_id not in company_ids:
                    company_ids.append(job_card.company_id)

                if len(company_ids) > 1:
                    raise ValidationError(_('Please select only Job Cards with the same Client Name.'))

                if job_card.state != 'done':
                    raise ValidationError(_('Only Job Cards with status of Done can have installation certificates.'))

            return self.env.ref('bbis_reports.bbis_reports_installation_certificate_multi').report_action(self.job_card_ids)

        return False
