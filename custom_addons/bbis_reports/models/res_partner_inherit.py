# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from datetime import datetime


class BbisResPartnerInherit(models.Model):
    _inherit = 'res.partner'

    accounting_person = fields.Many2one('res.users')
    customer_class = fields.Selection([('class_a', 'A Class (Major Customers)'),
                                       ('class_b', 'B Class  (Regular Customers)'),
                                       ('class_c', 'C Class (Retail Customer)'),
                                       ('class_x', 'X Class (On Hold Customers)')])
    previous_customer_class = fields.Char(string='Previous Customer Class')

    @api.model
    def _notify_prepare_email_values(self, message):
        res = super(BbisResPartnerInherit, self)._notify_prepare_email_values(message)

        if message.model:
            res['model'] = message.model

        if message.attachment_ids:
            res['attachment_ids'] = message.attachment_ids
        else:
            res['attachment_ids'] = False

        if message.email_from:
            res['email_from'] = message.email_from

        if message.email_cc:
            res['email_cc'] = message.email_cc

        return res

    @api.model
    def _notify_send(self, body, subject, recipients, **mail_values):
        res = super(BbisResPartnerInherit, self)._notify_send(body, subject, recipients, **mail_values)

        if mail_values['model'] == 'sale.order':
            current_uid = self.env.uid
            user = self.env['res.users'].browse(current_uid)
            company_email = user.company_id.email

            template_obj = self.env['mail.mail']
            template_data = {
                'subject': subject,
                'body_html': body,
                'body': 'Send email copy to ' + mail_values['email_from'],
                'email_from': company_email,
                # send to the sender/sales person
                'email_to': mail_values['email_from']
            }
            template_id = template_obj.create(template_data)
            template_id.attachment_ids = mail_values['attachment_ids']
            template_id.send()
            # template_id.attachment_ids = [(3, mail_values['attachment_ids'].id)]

        return res

    # Function for updating the customer to X - Class who have the due days more than 120.
    def update_due_customers(self):
        now = datetime.now()
        current_date = now.strftime("%Y-%m-%d")
        users_groups = self.env.ref('bbis_reports.group_customer_due_mail').users.ids
        user = self.env['res.users'].browse(self.env.uid)
        from_email = user.company_id.email
        customer_count = 0
        customer_detail = ''
        body_html = ''
        invoices = self.env['account.move'].search([('state', '=', 'open'), ('type', '=', 'out_invoice')],
                                                      order='partner_id asc')
        for invoice in invoices:
            if invoice.date_due:
                mail_date_due = datetime.strftime(datetime.strptime(invoice.date_due, "%Y-%m-%d"), "%d-%m-%Y")
                day_diff = datetime.strptime(current_date, "%Y-%m-%d") - datetime.strptime(invoice.date_due, "%Y-%m-%d")
                if day_diff.days > 90:
                    customers = self.env['res.partner'].search([('id', '=', invoice.partner_id.id)])
                    if customers:
                        if customers.customer_class != 'class_x':
                            customers.write({'previous_customer_class': customers.customer_class,
                                             'customer_class': 'class_x'})
                            customer_count += 1
                            customer_detail += "<tr>"
                            customer_detail += """<td align="center">%s</td>
                                                  <td align="center">%s</td>
                                                  <td align="center">%s</td>
                                                  <td align="center">%s</td>
                                                  <td align="center">%s</td>
                                                  <td align="center">%s</td>""" % \
                                               (str(customer_count), str(customers.name), str(customers.email),
                                                str(invoice.number), mail_date_due, str(invoice.residual_signed))

        customer_detail += '</table>'
        if users_groups and customer_count:
            # Find out one finance user from the account advisor group.
            users = self.env['res.users'].search([('id', 'in', users_groups), ('id', '!=', 1)])
            emails = users.mapped('partner_id').mapped('email')
            user_mail = '%s' % ",".join(emails)
            if user_mail:
                # Preparing the mail content for sending.
                body_html = """
                                              <div style="font-family:Arial;font-size:10pt;">
                                              <p>Dear Accounts Team,</p>
                                              <p>These are the Customer List move to Class-X after the due process..
                                              </p>
                                              <table style="border-collapse:collapse; font-family:Arial;font-size:10pt;
                                              margin-top:10px; text-align:left" cellpadding="5" border="1">
                                              <tr>
                                                  <th style="background-color:#2c286c; color:white; text-align:center;">SN</th>
                                                  <th style="background-color:#2c286c; color:white;">Customer Name</th>
                                                  <th style="background-color:#2c286c; color:white;">Email</th>
                                                  <th style="background-color:#2c286c; color:white;">Invoice No</th>
                                                  <th style="background-color:#2c286c; color:white;">Due Date</th>
                                                  <th style="background-color:#2c286c; color:white; text-align:center;">Remaining Amount</th>
                                              </tr>
                                              """
                body_html += customer_detail
                body_html += '''<br/><br/><p>Thank You,</p>'''
                body_html += '''<p style="margin:0; color:#f05a28"><b>%s</b></p>''' % user.company_id.name
                body_html += '''<p style="color: #808080; margin:0;"><small>This is a system generated mail.
                              No need of sending replies.</small></p>'''

            template_obj = self.env['mail.mail']
            template_data = {
                'subject': 'X-Class Update Customer List',
                'body_html': body_html,
                'email_from': from_email,
                'email_to': user_mail
            }

            template_id = template_obj.create(template_data)
            template_id.send()
