# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from openerp.exceptions import UserError, ValidationError
import requests
import json
import logging
_logger = logging.getLogger("res_company")

class JobCard(models.Model):
    _inherit = "job.card"

    #@api.multi
    def close_job_card(self):
        if not self.activation_date:
            raise UserError(_('Invalid action! Please provide Activation date.'))
        if not self.installation_date:
            raise UserError(_('Invalid action! Please provide Installation date.'))
        if not self.company_id:
            raise UserError(_('Invalid action! Please provide Client Name.'))
        if not self.device_serial_number_new_id:
            raise UserError(_('Invalid action! Please provide Device ID.'))
        if not self.device_id:
            raise UserError(_('Invalid action! Please provide Device Type.'))
        self.env['job.card.line'].create({
            'name': self.env.uid,
            'job_card_id': self.id,
            'date_accomplished': fields.Date.today(),
            'state': 'done'
        })
        if self.device_status == 'active':
            if self.sale_order_id:
                job_test_ids = self.env["job.card"].search([('sale_order_id', '=', self.sale_order_id.id)])
                if job_test_ids:
                    job_list_ids = job_test_ids.filtered(lambda x: x.state == 'done')
                    if job_list_ids:
                        self.sale_order_id.installed_device_count = len(job_list_ids.ids)
        else:
            raise UserError(_("Device status is not active"))

        if self.job_card_type == 'sale':
            if self.vehicle_number:
                self.env.cr.execute("""update vehicle_master set
                installation_date='%s',activation_date='%s',partner_id='%s',serial_no='%s',device_duplicate='%s' where id=%s""" % (
                self.installation_date,
                self.activation_date,
                self.company_id.id,
                self.device_serial_number_new_id.name,
                self.device_id.name,
                self.vehicle_number.id))
            else:
                raise UserError(_('Invalid action! Please provide vehicle details.'))
        self.write({'state': 'done'})

class Company(models.Model):
    _inherit='res.company'

    url = fields.Char(string="Token URL", copy=False)
    result_url = fields.Char(string="Result URL", copy=False)
    user_name = fields.Char(string="User", copy=False)
    password = fields.Char(string="Password")
    token = fields.Char(string="Token")
    sign = fields.Char(string="Sign", default='>=')
    filters = fields.Char(string="Filters", default='[]')
    predicate = fields.Char(string="Predicate")
    param = fields.Char(string="Parameter", default='[]')
    order_by = fields.Char(string="Order By", default='[]')
    topclause = fields.Integer(string="TopClause", default=0)

    def generate_token(self):
        if self.url and self.user_name and self.password:
            data_dict = {"username": self.user_name,"password": self.password}
            return_request = requests.post(self.url, data=json.dumps(data_dict), headers={'Content-Type': 'application/json'})
            response = return_request.json()
            conf_response = response.get('token')
            self.token = conf_response

            if not conf_response:
                message = response.get('Message', '')
                raise ValidationError('Something went wrong while fetching FMS API Token. %s' % message)
        else:
            raise ValidationError('Url or User or Password is missing !')

    def generate_token_scheduler(self):
        bbis = self.env['res.company'].browse(1)
        conf_response = False
        message = ''

        if bbis and bbis.url and bbis.user_name and bbis.password:
            try:
                data_dict = {"username": bbis.user_name, "password": bbis.password}
                return_request = requests.post(bbis.url, data=json.dumps(data_dict), headers={'Content-Type': 'application/json'})
                response = return_request.json()
                conf_response = response.get('token')
                bbis.token = conf_response

                if not conf_response:
                    message = response.get('Message', '')
                    _logger.warning('========== Something went wrong while fetching FMS API Token. %s ==========', message)
                else:
                    _logger.info('========== FMS API Token was successfully saved. ==========')
            except Exception as e:
                message = e
                _logger.warning('========== Something went wrong while fetching FMS API Token, %s ==========', message)
        else:
            message = "Either API link, username and password is not defined."
            _logger.warning('========== Unable to fetch FMS API Token. %s==========', message)

        if not conf_response:
            body = """<div>"""
            body += """<p>Something went wrong while fetching FMS API Token.</p>"""
            body += """<p>Error: %s</p>""" % message
            body += """</div>"""
            self.send_unsuccessful_fms_api(body)

    def send_unsuccessful_fms_api(self, body):
        template_obj = self.env['mail.mail']
        company = self.env['res.company'].browse(1)
        email_to = self.env['ir.config_parameter'].get_param('fms_api_email_notify')

        template_data = {
            'subject': "API Token Failed - %s" % company.name,
            'body_html': body,
            'email_from': company.email,
            'email_to': email_to
        }

        template_id = template_obj.create(template_data)
        template_id.send()

    def message_wizard(self, context):
        return {
            'name': ('Success'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'message.wizard',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': context
        }