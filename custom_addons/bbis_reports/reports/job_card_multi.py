from odoo import api, models, _


class BbisJobCardMultipleReport(models.AbstractModel):
    _name = 'report.bbis_reports.job_card_multi'
    _description = 'BBIS Job Card Multiple Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        job_cards = self.env['job.card'].browse(docids)
        company_id = self.env.user.company_id

        return {
            'doc_model': 'job.card',
            'job_cards': job_cards,
            'doc': job_cards[0],
            'company': company_id,
        }
