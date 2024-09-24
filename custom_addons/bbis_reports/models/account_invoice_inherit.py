# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.tools.float_utils import float_compare
from datetime import datetime


class BbisAccountInvoiceInherit(models.Model):
    _inherit = 'account.move'

    has_no_taxes = fields.Boolean(default=False, compute="_compute_has_no_taxes", search='_search_field')
    origin = fields.Char(string='Source Document', track_visibility='onchange',
                         help="Reference of the document that generated this sales order request.")

    @api.depends('invoice_line_ids')
    def _compute_has_no_taxes(self):
        for r in self:
            for line in r.invoice_line_ids:
                if not line.invoice_line_tax_ids:
                    r.has_no_taxes = True

    def total_amount_in_word_v2(self, total_amount, currency):
        amount_in_words = self.currency_id.with_context(lang=self.partner_id.lang or 'es_ES').amount_to_text(
            total_amount).title()

        if currency == 'AED':
            amount_in_words = "{} {} {}".format('UAE Dirham', amount_in_words.replace('Dirham', ''), 'Only')
        else:
            amount_in_words = "{} {} {}".format(currency, amount_in_words, 'Only')

        return amount_in_words

    #@api.one
    @api.depends('inclusive_invoice_line.price_subtotal', 'currency_id')
    def _compute_amount_inclusive(self):
        res = super(BbisAccountInvoiceInherit, self)._compute_amount_inclusive()
        total_tax = sum(line.price_tax for line in self.inclusive_invoice_line)
        self.amount_tax1 = total_tax
        self.amount_total1 = self.amount_untaxed1 + total_tax
        return res

    amount_tax1 = fields.Monetary(string='Taxes', store=True, readonly=True, compute='_compute_amount_inclusive')
    account_journal_id = fields.Many2one('account.journal', string='Bank Account', domain=[('type', '=', 'bank')],
                                         default=7)

    # page breaks
    amounts_pb = fields.Boolean(default=False, string="Amount in Words")
    remarks_pb = fields.Boolean(default=False, string="Remarks")
    vehicles_pb = fields.Boolean(default=True, string="Vehicle List")

    job_card_date = fields.Date()

    # Change the job_card_reference (job_id field) in to manytomany field.
    job_id = fields.Many2many('job.card', string="Job Card Reference")

    # delivery details
    invoice_sent_via = fields.Selection([('email', 'Email'), ('office_messenger', 'Office Messenger')
                                            , ('courier', 'Courier'), ('customer_collected', 'Customer Collected')])
    invoice_sent_date = fields.Date()
    invoice_sent_location = fields.Selection([('city', 'City'), ('musaffah', 'Musaffah'), ('mz', 'Madinat Zayed')])

    # delivery details2
    invoice_sent_via_2 = fields.Selection([('email', 'Email'), ('office_messenger', 'Office Messenger')
                                              , ('courier', 'Courier'), ('customer_collected', 'Customer Collected')],
                                          string='Invoice Sent Via')
    invoice_sent_date_2 = fields.Date(string='Invoice Sent Date')
    invoice_sent_location_2 = fields.Selection([('city', 'City'), ('musaffah', 'Musaffah'), ('mz', 'Madinat Zayed')],
                                               string='Invoice Sent Location')

    # Adding the discount and discount percentage in account invoice from purchase order.
    def _prepare_invoice_line_from_po_line(self, line):
        data = super(BbisAccountInvoiceInherit, self)._prepare_invoice_line_from_po_line(line)
        data['discount'] = line.discount
        data['discount_fix'] = line.discount_fix
        return data

    def action_invoice_paid(self):
        due_customer = 0
        """Inherit the invoice paid funtion for updating the x-class customer to normal customers when
        they pay the full amount."""
        now = datetime.now()
        current_date = now.strftime("%Y-%m-%d")
        res = super(BbisAccountInvoiceInherit, self).action_invoice_paid()
        customer_data = self.env['res.partner'].search([('id', '=', self.partner_id.id)])
        if customer_data.customer_class == 'class_x':
            invoices = self.env['account.move'].search([('state', '=', 'open'), ('type', '=', 'out_invoice'),
                                                           ('partner_id', '=', self.partner_id.id)],
                                                          order='partner_id asc')
            for invoice in invoices:
                day_diff = datetime.strptime(current_date, "%Y-%m-%d") - datetime.strptime(invoice.date_due, "%Y-%m-%d")
                if day_diff.days > 120:
                    due_customer = 1
            if due_customer != 1:
                customer_data.write({'customer_class': customer_data.previous_customer_class})
        return res
