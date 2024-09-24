from odoo import api, models, _


class BbisJobCardReport(models.AbstractModel):
    _name = 'report.bbis_reports.job_card'
    _description = 'BBIS Job Card Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['job.card'].browse(docids)
        company_id = self.env.user.company_id

        return {
            'doc_model': 'job.card',
            'docs': docs,
            'company': company_id,
        }
