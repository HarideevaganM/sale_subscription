from odoo import fields, models, api, _
from datetime import datetime, date, timedelta, time
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError


class BBISSupportTicketWizard(models.TransientModel):
    _name = 'bbis.support.ticket.update'
    _description = 'BBIS Support Ticket Update'

    def default_ticket_selected(self):
        return self.env['website.support.ticket'].browse(self._context.get('active_ids'))

    def default_engineer(self):
        return self.env['res.users'].search([('name', '=', 'Marwan Al Charbaji')], limit=1)

    support_ticket_ids = fields.Many2many('website.support.ticket', required=True, default=default_ticket_selected)
    schedule_date = fields.Date(string="Schedule Date")
    ticket_create_date = fields.Date(string="Report on")
    engineer_id = fields.Many2one('res.users', string="Engineer", default=default_engineer)

    @api.onchange('schedule_date')
    def onchange_schedule_date(self):
        if self.schedule_date:
            self.ticket_create_date = self.schedule_date

    def update_ticket(self):
        for tickets in self.support_ticket_ids:
            tickets.schedule_time = self.schedule_date
            tickets.ticket_create_date = self.ticket_create_date
            tickets.engineer_id = self.engineer_id

