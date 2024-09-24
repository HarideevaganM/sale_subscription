from odoo import api, models, _
from odoo.exceptions import ValidationError


class BbisRenewalCertificateMulti(models.AbstractModel):
    _name = 'report.bbis_reports.installation_certificate'
    _description = 'BBIS Renewal Certificate Multiple'

    @api.model
    def _get_report_values(self, docids, data=None):
        certificates = self.env['installation.certificate'].browse(docids)
        partner_ids = certificates.mapped('partner_id')
        # print(partner_ids)

        if len(partner_ids) > 1:
            raise ValidationError('Sorry! Please select certificates that belongs to one Partner.')

        return {
            'doc_model': 'installation.certificate',
            'docs': certificates,
        }
