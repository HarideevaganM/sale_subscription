from odoo import api, fields, models, _


class JobCardReport(models.AbstractModel):
    _name = 'report.job_card_report.job_card_report_template'
    _description = "Job Card Report"

    # @api.multi
    def _get_report_values(self, ids, data=None):
        report_obj = self.env['job.card'].browse(ids)
        return {
            'doc_ids': ids,
            'doc_model': 'job.card',
            'docs': report_obj,
            'data': data,
        }
