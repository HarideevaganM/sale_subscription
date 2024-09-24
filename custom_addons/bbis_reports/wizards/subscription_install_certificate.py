# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class PrintInstallationCertificates(models.TransientModel):
    _name = 'subscription.install.certificate'
    _description = 'Wizard: Create Subscription Installation Certificates'

    subscription_ids = fields.Many2many('sale.order', string='Subscriptions', required=True, domain=[('is_subscription', '=', True)])

    def install_certificates(self):
        # print(self.subscription_ids)
        for r in self.subscription_ids:
            r.installation_certificate()

        return {
            'name': 'Renewal Certificates',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'installation.certificate',
            'domain': [('subscription_id', 'in', self.subscription_ids.ids)],
            'context': {'group_by': ['partner_id']},
        }
