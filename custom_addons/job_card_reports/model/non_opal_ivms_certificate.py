from odoo import api, fields, models, _


class NonOpalIvms(models.AbstractModel):
    _name = 'report.job_card_reports.fms_report_non_opal_ivms_certificate'
    _description = "opal ivms"

    # @api.multi
    def _get_report_values(self, ids, data=None):
        report_obj = self.env['installation.certificate'].browse(ids)
        return {
            'doc_ids': ids,
            'doc_model': 'installation.certificate',
            'docs': report_obj,
            'data': data,
        }



