from odoo import fields, api, models
from urllib.parse import urljoin
from urllib.parse import urlencode


class AssetRequestScheduler(models.Model):
    _inherit = 'asset.request'

    def check_for_pending_approval(self):
        get_pending = self.search([])
        for record in get_pending:
            if record.state == 'submitted':
                mail_mail = self.env['mail.mail']
                template_body = "<p>Dear " + str(record.asset_approval.name) + ",</p> <p>" \
                                + " Asset request for " + str(
                    record.employee.name) + " is waiting for your Approval.</p>" "<p><a href=" \
                                + self._get_url() + " >Click Here to approve</a></p> <p>Thanks</p>" \
                                + "<p>Asset MGT team.</p>"

                template_values = {
                    'auto_delete': True,
                    'body_html': template_body,
                    'email_cc': False,
                    'email_from': str(record.employee.work_email),
                    'email_to': str(record.asset_approval.login),
                    'mail_server_id': False,
                    'model': 'asset.request',
                    'subject': "Pending Asset Request."
                }

                notification_id = mail_mail.sudo().create(template_values)
                notification_id.sudo().send()

    def check_for_pending_receive(self):
        get_pending = self.search([])
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')

        for record in get_pending:
            if record.state == 'allocated':
                mail_mail = self.env['mail.mail']
                template_body = "<p>Dear " + str(record.employee.name) + ",</p> <p>" \
                                + str(record.asset_id.name) + " has been allocated to you. The request ID is " \
                                + record.name +" </p>" "<p><a href="  \
                                + base_url + " >Click Here to receive in good condition</a></p>"\
                                +"<p>Thanks</p>" + "<p>Asset MGT team.</p>"

                template_values = {
                    'auto_delete': True,
                    'body_html': template_body,
                    'email_cc': False,
                    'email_from': str(record.regional_warehouse_manager.login),
                    'email_to': str(record.employee.work_email),
                    'mail_server_id': False,
                    'model': 'asset.request',
                    'subject': "Pending Asset Request."
                }

                notification_id = mail_mail.sudo().create(template_values)
                notification_id.sudo().send()


    #@api.multi
    def _get_url(self):
        fragment = {}
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        action_id = self.env['ir.model.data'].get_object_reference('IT_asset_module', 'asset_request_action')[1]
        menu_id = self.env['ir.model.data'].get_object_reference('IT_asset_module', 'menu_asset_request')[1]
        fragment['view_type'] = 'form'
        fragment['menu_id'] = menu_id
        fragment['model'] = 'asset.request'
        fragment['id'] = self.id
        fragment['action'] = action_id
        query = {'db': self._cr.dbname}
        res = urljoin(base_url, "?%s#%s" % (urlencode(query), urlencode(fragment)))
        return res
