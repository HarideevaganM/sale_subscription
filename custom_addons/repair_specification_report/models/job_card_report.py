from odoo import api, fields, models, _

class JobCardReport(models.AbstractModel):
    _name = 'report.repair_specification_report.repair_card_specification'
    _description = "Job Card Report Specification"

    #@api.multi
    def _get_report_values(self, ids, data=None):
        report_obj = self.env['job.card'].browse(ids)
        return {
            'doc_ids': ids,
            'doc_model': 'job.card',
            'docs': report_obj,
            'data': data,
        }
