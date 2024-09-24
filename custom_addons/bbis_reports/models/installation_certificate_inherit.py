from odoo import api, fields, models, _
from datetime import datetime, date, timedelta, time
from dateutil.relativedelta import relativedelta


class InstallationCertificateInherit(models.Model):
    _inherit = 'installation.certificate'

    # Added RMA Closed in Installation Certificate screen for renewal.
    rma_closed_date = fields.Date('RMA Closed Date', compute='_get_rma_closed_date')

    # Computed field function for find out the latest RMA Closing Date.
    #@api.multi
    def _get_rma_closed_date(self):
        for rec in self:
            certificate_name = rec.name.split('/')[1]
            if rec.subscription_id or certificate_name == 'RW':
                rma = self.env['repair.order'].sudo().search([('product_id', '=', rec.device_id.id),
                                                            ('lot_id', '=', rec.serial_no.id)],
                                                           order='id desc', limit=1)
                if rma.close_date:
                    rec.rma_closed_date = rma.close_date
