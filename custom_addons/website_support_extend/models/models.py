# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class WebsiteSupportTicketCategories(models.Model):
    _inherit = "website.support.ticket.category"

    code = fields.Char(string="Code")

    @api.constrains('code')
    def constrain_code(self):
        record = self.search([('code', '=', self.code), ('id', '!=', self.id)])
        if record:
            raise UserError(_("You have same code define in multiple category !"))

 
class WebsiteSupportTicket(models.Model):
    _inherit = "website.support.ticket"

    cat_code = fields.Char(string="Categ Code", related='category_id.code', store=True)

    def set_to_under_repair(self):
        self.states = 'under_repair'


class JobCard(models.Model):
    _inherit = "job.card"

    def close_job_card(self):
        res = super(JobCard, self).close_job_card()
        rec = self.search([('state', '=', 'done'), ('vehicle_number', '=', self.vehicle_number.id), ('id', '!=', self.id)])

        for each in rec:
            each.write({'device_status': 'in_active'})

        if self.support_id:
            close = self.env['website.support.ticket.close'].create({
                'ticket_id': self.support_id.id,
                'message': ' <p><br></p>'
            })
            close.close_ticket()
        return res
