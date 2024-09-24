from odoo import api, fields, models, _


class JobCardReport(models.AbstractModel):
    _name = 'report.job_card_reports.fms_report_opal_ivms'
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


class CompanyInherit(models.Model):
    _inherit = "res.company"

    authorized_signature = fields.Binary(string="Authorized Signature")
    job_certy_sign =  fields.Binary(string='Job Certy Sign')
    seal = fields.Binary(string="Company Seal")
