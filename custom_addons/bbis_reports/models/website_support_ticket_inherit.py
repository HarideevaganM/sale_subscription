from odoo import fields, models, api, _


# Make the Marwan Al Charbaji as a default engineer for creating the new support ticket.
class BBISWebsiteSupportTicketInherit(models.Model):
    _inherit = 'website.support.ticket'

    engineer_id = fields.Many2one('res.users', string="Engineer", default=23)
    schedule_time = fields.Datetime(default=fields.Datetime.now)

    # On change of schedule date changes the reported on date also.
    @api.onchange('schedule_time')
    def schedule_date_change(self):
        self.ticket_create_date = self.schedule_time


class SupportTicketCloseInherit(models.TransientModel):
    """Inherit website.support.ticket.close model for sending the ticket closing mail to the sale team."""
    _inherit = 'website.support.ticket.close'

    def close_ticket(self):
        """Inherit close method for adding the ticket close notification to sales team."""
        res = super(SupportTicketCloseInherit, self).close_ticket()
        if self.ticket_id.service_sub_type in ('same_remove_replace', 'diff_remove_replace'):
            self.sales_support_ticket_mail()
        return res

    def sales_support_ticket_mail(self):
        """Send notifications to Sales Team"""
        users_groups = self.env.ref('bbis_reports.group_csm_ticket_close_mail_users').users.ids
        values = {"object": self}
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        values['base_url'] = base_url
        body = self.env.ref('bbis_reports.ticket_closing_mail').render(values=values)
        if users_groups:
            users = self.env['res.users'].search([('id', 'in', users_groups), ('id', '!=', 1)])
            emails = users.mapped('partner_id').mapped('email')
            users_mail = '%s' % ",".join(emails)
            mail_values = {
                'email_from': self.env.user.email_formatted,
                "email_to": users_mail,
                'subject': 'Closed Support Ticket - Device Replacement',
                'body_html': body,
                'auto_delete': True,
            }
            mail = self.env['mail.mail'].create(mail_values)
            mail.send()