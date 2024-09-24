# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError
from datetime import date


TYPE2JOURNAL = {
    'out_invoice': 'sale',
    'in_invoice': 'purchase',
    'out_refund': 'sale',
    'in_refund': 'purchase',
}

class ConsolidateInvoice(models.Model):
    _name = "consolidate.invoice"

    #@api.one
    @api.depends('consolidate_line_ids.price_subtotal', 'tax_line_ids.amount', 'tax_line_ids.amount_rounding',
                 'currency_id', 'company_id', 'date_consolidate')
    def _compute_amount(self):
        round_curr = self.currency_id.round
        self.amount_untaxed = sum(line.price_subtotal for line in self.consolidate_line_ids)
        self.amount_tax = sum(round_curr(line.amount_total) for line in self.tax_line_ids)
        self.amount_total = self.amount_untaxed + self.amount_tax
        amount_total_company_signed = self.amount_total
        amount_untaxed_signed = self.amount_untaxed
        if self.currency_id and self.company_id and self.currency_id != self.company_id.currency_id:
            currency_id = self.currency_id.with_context(date=self.date_invoice)
            amount_total_company_signed = currency_id.compute(self.amount_total, self.company_id.currency_id)
            amount_untaxed_signed = currency_id.compute(self.amount_untaxed, self.company_id.currency_id)
        sign = self.type in ['in_refund', 'out_refund'] and -1 or 1
        self.amount_total_company_signed = amount_total_company_signed * sign
        self.amount_total_signed = self.amount_total * sign
        self.amount_untaxed_signed = amount_untaxed_signed * sign



    @api.model
    def _default_journal(self):
        if self._context.get('default_journal_id', False):
            return self.env['account.journal'].browse(self._context.get('default_journal_id'))
        inv_type = self._context.get('type', 'out_invoice')
        inv_types = inv_type if isinstance(inv_type, list) else [inv_type]
        company_id = self._context.get('company_id', self.env.user.company_id.id)
        domain = [
            ('type', 'in', [TYPE2JOURNAL[ty] for ty in inv_types if ty in TYPE2JOURNAL]),
            ('company_id', '=', company_id),
        ]
        return self.env['account.journal'].search(domain, limit=1)

    @api.model
    def _default_currency(self):
        journal = self._default_journal()
        return journal.currency_id or journal.company_id.currency_id or self.env.user.company_id.currency_id


    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Consolidated'),
        ('cancel', 'Cancelled')], default='draft',
        copy=False, track_visibility='onchange', required=True)
    name = fields.Char('Name', default='New')
    date_from = fields.Date('From date')
    date_to = fields.Date('To date')
    date_consolidate = fields.Date('Consolidate Date', default=fields.Date.today())
    partner_id = fields.Many2one('res.partner', string='Customer')
    consolidate_line_ids = fields.One2many('consolidate.invoice.line', 'consolidate_id', string='Products')
    vehicle_line_ids = fields.One2many('consolidate.vehicle.details', 'consolidate_id', string='Vehicle Details')
    invoice_ids = fields.One2many('account.move', 'consolidate_id', string='Customer of Invoice')
    # consolidated_count = fields.Integer('Consolidated Count', compute='_compute_consolidated_inv', store=False)
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.user.company_id)
    origin = fields.Char(string='Source Document',
                         help="Reference of the document that produced this invoice.")
    client_ref = fields.Char("Ref #")
    purchase_order_no = fields.Char("PO #")
    purchase_order_date = fields.Char("PO Order Date #")
    # currency_id = fields.Many2one('res.currency', string='Currency', required=True, default=lambda self: self.env.user.company_id.currency_id)
    amount_untaxed = fields.Monetary(string='Untaxed Amount',
                                     store=True, readonly=True, compute='_compute_amount', track_visibility='always')
    amount_untaxed_signed = fields.Monetary(string='Untaxed Amount in Company Currency',
                                            currency_field='company_currency_id',
                                            store=True, readonly=True, compute='_compute_amount')
    amount_tax = fields.Monetary(string='Tax',
                                 store=True, readonly=True, compute='_compute_amount')
    amount_total = fields.Monetary(string='Total',
                                   store=True, readonly=True, compute='_compute_amount')
    amount_total_signed = fields.Monetary(string='Total in Invoice Currency', currency_field='currency_id',
                                          store=True, readonly=True, compute='_compute_amount',
                                          help="Total amount in the currency of the invoice, negative for credit notes.")
    amount_total_company_signed = fields.Monetary(string='Total in Company Currency',
                                                  currency_field='company_currency_id',
                                                  store=True, readonly=True, compute='_compute_amount',
                                                  help="Total amount in the currency of the company, negative for credit notes.")
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  required=True, readonly=True, states={'draft': [('readonly', False)]},
                                  default=_default_currency, track_visibility='always')
    company_currency_id = fields.Many2one('res.currency', related='company_id.currency_id', string="Company Currency",
                                          readonly=True)
    tax_line_ids = fields.One2many('account.move.tax', 'consolidate_id', string='Tax Lines', oldname='tax_line',
        readonly=True, states={'draft': [('readonly', False)]}, copy=True)
    type = fields.Selection([
        ('out_invoice', 'Customer Invoice'),
        ('in_invoice', 'Vendor Bill'),
        ('out_refund', 'Customer Credit Note'),
        ('in_refund', 'Vendor Credit Note'),
    ], readonly=True, index=True, change_default=True,
        default=lambda self: self._context.get('type', 'out_invoice'),
        track_visibility='always')
    comment = fields.Text('Additional Information', readonly=True, states={'draft': [('readonly', False)]})


    @api.onchange('date_from', 'date_to', 'partner_id')
    def onchange_invoice(self):
        self.invoice_ids = ''
        if self.partner_id and self.date_from and self.date_to:
            domain = [('date_invoice', '>=', self.date_from), ('date_invoice', '<=', self.date_to),('type', '=', 'out_invoice'),
                      ('state', '=', 'open'), ('partner_id', '=', self.partner_id.id),('is_consolidated', '!=', True)]
            invoices = self.env['account.move'].search(domain)
            if invoices:
                self.update({'invoice_ids': invoices.ids})
            return {'domain': {'invoice_ids': domain}}


    #@api.multi
    @api.onchange('invoice_ids')
    def onchange_invoice_ids(self):
        self.consolidate_line_ids = ''
        self.vehicle_line_ids = ''
        if self.invoice_ids:
            """
                Updating Consolidate Product Details
            """
            lines = self.env['account.move.line'].search([('invoice_id', 'in', self.invoice_ids.ids)])
            products = []
            for line in lines:
                if line.product_id not in products:
                    products.append(line.product_id)
            line_ids = []
            for product in products:
                record = lines.filtered(lambda x: x.product_id.id == product.id)
                rec = (0, 0, {
                    'product_id': product.id,
                    'account_id': record[0].account_id.id,
                    'name': record[0].name,
                    'quantity': sum(record.mapped('quantity')),
                    'uom_id': record[0].uom_id.id,
                    'price_unit': sum(record.mapped('price_unit')),
                    'discount': record[0].discount,
                    'price_subtotal': sum(record.mapped('price_subtotal')),
                })
                line_ids.append(rec)

            orig = ''
            client_ref = ''
            purchase_order_no = ''
            purchase_order_date = ''
            for inv in self.invoice_ids:
                orig += (inv.origin or '' + ',')
                client_ref += (inv.client_ref or '' + ',')
                purchase_order_no += (inv.purchase_order_no or '' + ',')
                purchase_order_date += (inv.purchase_order_date or '' + ',')
            self.update({'consolidate_line_ids': line_ids,
                         'origin': orig,
                         'client_ref': client_ref,
                         'purchase_order_no': purchase_order_no,
                         'purchase_order_date': purchase_order_date,
                         })

            """
                Updating Vehicle Details
            """
            veh_data = []
            vehicle_lines = self.env['invoice.vehicle.details'].search([('invoice_id', 'in', self.invoice_ids.ids)])
            for vehicle in vehicle_lines:
                rec = (0, 0, {
                    'serial_no_id': vehicle.serial_no_id.id,
                    'device_id': vehicle.device_id.id,
                    'vehicle_id': vehicle.vehicle_id.id,
                    'installation_date': vehicle.installation_date,
                    'status': vehicle.status,
                })
                veh_data.append(rec)
            self.update({'vehicle_line_ids': veh_data})

    #@api.multi
    def button_confirm(self):
        code = self.env['ir.sequence'].next_by_code('consolidate.invoice') or '/'
        for rec in self.invoice_ids:
            rec.write({'is_consolidated': True})
        self.write({
            'name': code,
            'state': 'done'
        })

    #@api.multi
    def button_cancel(self):
        self.state = 'cancel'


class ConsolidateInvoiceLine(models.Model):
    _name = "consolidate.invoice.line"

    @api.model
    def _default_account(self):
        if self._context.get('journal_id'):
            journal = self.env['account.journal'].browse(self._context.get('journal_id'))
            if self._context.get('type') in ('out_invoice', 'in_refund'):
                return journal.default_credit_account_id.id
            return journal.default_debit_account_id.id

    consolidate_id = fields.Many2one('consolidate.invoice', string='Consolidate', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    # account_id = fields.Many2one('account.analytic.account', 'Analytic Account', readonly=True)
    name = fields.Text(string='Description', required=True)
    quantity = fields.Float(string='Quantity', help="Quantity that will be invoiced.", default=1.0)
    uom_id = fields.Many2one('product.uom', string='Unit of Measure', required=True)
    price_unit = fields.Float(string='Unit Price', required=True, digits=dp.get_precision('Product Price'))
    discount = fields.Float(string='Discount (%)', digits=dp.get_precision('Discount'))
    price_subtotal = fields.Float(string='Price SubTotal',
                                  digits=dp.get_precision('Account'))
    account_analytic_id = fields.Many2one('account.analytic.account',
                                          string='Analytic Account')
    account_id = fields.Many2one('account.account', string='Account',
                                 required=True, domain=[('deprecated', '=', False)],
                                 default=_default_account,
                                 help="The income or expense account related to the selected product.")
    invoice_line_tax_ids = fields.Many2many('account.tax',
                                            'account_invoice_line_tax', 'invoice_line_id', 'tax_id',
                                            string='Taxes',
                                            domain=[('type_tax_use', '!=', 'none'), '|', ('active', '=', False),
                                                    ('active', '=', True)], oldname='invoice_line_tax_id')
    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Tags')


class ConsolidateVehicleDetails(models.Model):
    _name = "consolidate.vehicle.details"

    consolidate_id = fields.Many2one('consolidate.invoice', string='Consolidate', ondelete='cascade')
    serial_no_id = fields.Many2one("stock.lot", string="Device Serial No")
    device_id = fields.Many2one("product.product", string="Device Name")
    vehicle_id = fields.Many2one('vehicle.master', string="Vehicle Reg No")
    installation_date = fields.Date('Installation Date')
    status = fields.Selection([('active', 'Active'), ('in_Active', 'In Active')], string='Status')


class AccountInvoice(models.Model):
    _inherit = 'account.move'

    consolidate_id = fields.Many2one('consolidate.invoice', string='Consolidate', ondelete='cascade')
    is_consolidated = fields.Boolean("Is Consolidated")

class AccountInvoiceLine(models.Model):
    _inherit = 'account.move.line'

    consolidated_id = fields.Many2one('consolidate.invoice', string='Consolidated', ondelete='cascade')

class InvoiceVehicleDetails(models.Model):
    _inherit = "invoice.vehicle.details"

    consolidated_id = fields.Many2one('consolidate.invoice', string='Consolidated', ondelete='cascade')

class AccountInvoiceTax(models.Model):
    _inherit = 'account.move.tax'

    consolidate_id = fields.Many2one('consolidate.invoice', string='Consolidated', ondelete='cascade')
