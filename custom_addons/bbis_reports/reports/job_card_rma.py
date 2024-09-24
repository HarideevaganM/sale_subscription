from odoo import api, models, _


class BbisJobCardReport(models.AbstractModel):
    _name = 'report.bbis_reports.job_card_rma'
    _description = 'BBIS RMA Job Card Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['repair.order'].browse(docids)
        company_id = self.env.user.company_id

        return {
            'doc_model': 'repair.order',
            'docs': docs,
            'company': company_id,
        }
