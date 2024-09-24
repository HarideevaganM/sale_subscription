from odoo import api, models, _
from odoo.exceptions import ValidationError


# Job Completion Certificate for ITC.
class BbisRenewalCertificateMulti(models.AbstractModel):
    _name = 'report.bbis_itc_permits.job_completion_certificate'
    _description = 'BBIS Job Completion Certificate'

    @api.model
    def _get_report_values(self, docids, data=None):
        itc_permits = self.env['itc.permit'].browse(docids)
        partner_ids = itc_permits.mapped('partner_id')
        company_id = self.env.user.company_id

        if len(partner_ids) > 1:
            raise ValidationError('Sorry! Please select certificates that belongs to one Partner.')

        return {
            'doc_model': 'itc.permit',
            'docs': itc_permits,
            'company': company_id,
        }
