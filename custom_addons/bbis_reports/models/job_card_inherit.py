# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError, ValidationError
from datetime import datetime, date
from dateutil.relativedelta import relativedelta


class BbisCustomRequirementsJobCardInherit(models.Model):
    _name = "job.card"
    _inherit = ["job.card", "mail.thread"]

    purchase_order_no = fields.Char(related='sale_order_id.purchase_order_no', store=True, string='PO #', readonly=True)
    job_done_by = fields.Char(string='Jobs Done', compute='search_job_done')
    jobs_done = fields.Char(string='Jobs Done By')
    has_subscription = fields.Boolean(compute="compute_has_subscription", default=False, store=True)
    subscription_ids = fields.One2many('sale.order', 'job_card_id', domain=[('is_subscription', '=', True)])
    job_order_no = fields.Char()
    job_order_date = fields.Date()

    # Compute function for finding the user that done the job card.
    @api.depends('card_line', 'name', 'state')
    def search_job_done(self):
        for job_cards in self:
            job_card_line = self.env['job.card.line'].search([('state', '=', 'done'),
                                                              ('job_card_id', '=', job_cards.id)], limit=1)
            if job_card_line:
                job_cards.write({'jobs_done': job_card_line.name.name})
            else:
                job_cards.jobs_done = ''

    # Checking the selected device type available in the Sales Order Line Items.
    @api.onchange('device_id')
    def onchange_device_id(self):
        # BBIS - Checking whether the job card device type available in the sales order.
        if self.name:
            sales_order_line = self.env['sale.order.line'].search([('order_id', '=', self.sale_order_id.id),
                                                                   ('product_id', '=', self.device_id.id),
                                                                   ('product_uom_qty', '>', 0)], limit=1)
            if sales_order_line:
                # Check if the product sale order qty greater than delivered qty.
                if sales_order_line.product_uom_qty < sales_order_line.qty_delivered:
                    raise UserError(_("Device Type in Job Card does not have any available delivery"))
            else:
                raise UserError(_("Device Type in Job Card does not have any available delivery. Please ensure it "
                                  "is included in the order lines of the Sales Order"))

    #@api.multi
    @api.depends('subscription_ids')
    def compute_has_subscription(self):
        """Function for getting the count of subscriptions in job card."""
        for record in self:
            record.has_subscription = True if record.subscription_ids else False
