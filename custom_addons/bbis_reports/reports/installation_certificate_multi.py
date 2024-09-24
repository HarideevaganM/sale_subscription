from odoo import api, models, _
from odoo.exceptions import ValidationError


class BbisInstallationCertificateMulti(models.AbstractModel):
    _name = 'report.bbis_reports.installation_certificate_multi'
    _description = 'BBIS Installation Certificate Multiple'

    def _get_certificates(self, job_cards):
        certificates = []
        no_certificates = []
        for job_card in job_cards:
            job_card_id = job_card.id
            job_card_name = job_card.name
            certificate = self.env['installation.certificate'].search([('job_card_id', '=', job_card_id)],
                                                                      order='id desc', limit=1)

            if certificate:
                certificates.append(certificate)
            else:
                no_certificates.append(job_card_name)

        if len(no_certificates) >= 1:
            len_cert = len(no_certificates)
            card_word = 'Cards' if len_cert > 1 else 'Card'
            cert_word = 'certificates' if len_cert > 1 else 'certificate'
            raise ValidationError(_('Job {}: {} does not have installation {} yet. '
                                    'Please make sure to install {}.'.format(card_word, no_certificates, cert_word,
                                                                             cert_word)))

        return certificates

    @api.model
    def _get_report_values(self, docids, data=None):
        job_cards = self.env['job.card'].browse(docids)
        certificates = self.get_certificates(job_cards)

        return {
            'doc_model': 'job.card',
            'certificates': certificates,
            'doc': certificates[0],
        }
