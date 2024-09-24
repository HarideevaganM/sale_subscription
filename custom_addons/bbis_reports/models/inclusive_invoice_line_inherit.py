# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class BbisInclusiveInvoiceLineInherit(models.Model):
    _inherit = 'inclusive.invoice.line'

    @api.depends('invoice_line_ids')
    def _compute_group_quantity(self):
        for r in self:
            r.group_quantity = sum(r.invoice_line_ids.mapped('quantity'))

    @api.depends('invoice_line_ids', 'quantity', 'invoice_amount_total')
    def _compute_amounts(self):
        """
        Compute the amounts of the order lines of the SO line.
        """
        for r in self:
            vat = []
            sale_type = ''
            price_unit = 0
            for invoice in r.invoice_line_ids:
                tax_amount = sum(invoice.invoice_line_tax_ids.mapped('amount')) / 100

                if not invoice.invoice_id.sale_type:
                    raise ValidationError(_('Please select a Sale Type from the Account Invoice.'))

                if invoice.invoice_id.sale_type in 'pilot':
                    price_vat = ((invoice.price_unit * invoice.quantity) - invoice.discount_fix) * tax_amount
                else:
                    price = invoice.price_unit * r.quantity
                    price_vat = (price - invoice.discount_fix) * tax_amount
                vat.append(price_vat)

            if len(r.invoice_line_ids):
                single_invoice = r.invoice_line_ids[0].invoice_id
                sale_type = single_invoice.sale_type
                price_unit = r.invoice_line_ids[0].price_unit if sale_type in 'pilot' \
                    else sum(r.invoice_line_ids.mapped('price_unit'))

            discount = sum(r.invoice_line_ids.mapped('discount_fix'))
            total_vat = sum(vat)
            r.price_unit = price_unit
            r.discount = discount
            r.price_tax = total_vat

            if sale_type in 'pilot':
                r.price_subtotal = ((price_unit * r.group_quantity) - discount)
                r.price_total = ((price_unit * r.group_quantity) - discount) + total_vat
            else:
                r.price_subtotal = (price_unit * r.quantity) - discount
                r.price_total = ((price_unit * r.quantity) - discount) + total_vat

    name = fields.Text(string='Item Description')
    invoice_id = fields.Many2one("account.move", string="Invoice Reference", required=True, ondelete='cascade', index=True, copy=False)
    invoice_line_ids = fields.Many2many("account.move.line", string="Products from Invoice Lines", required=True)

    quantity = fields.Float(string='Quantity', digits=(6, 0), required=True, default="1")
    price_unit = fields.Float(compute='_compute_amounts', string='Unit Price', readonly=True, store=True)
    price_subtotal = fields.Float(compute='_compute_amounts', string='Subtotal', readonly=True, store=True)
    price_tax = fields.Float(compute='_compute_amounts', string='Tax Amount', readonly=True, store=True)
    discount = fields.Float(compute='_compute_amounts', string='Discount Fix', readonly=True, store=True)
    price_total = fields.Float(compute='_compute_amounts', string='Price Total', readonly=True, store=True)

    currency_id = fields.Many2one(related='invoice_id.currency_id', store=True, string='Currency', readonly=True)
    group_quantity = fields.Integer(compute='_compute_group_quantity', string="Quantity", readonly=True, store=True)

    # will be used to trigger compute amounts if sale order amount_total changes
    invoice_amount_total = fields.Monetary(related='invoice_id.amount_total', store=True, string='Invoice Total Amount', readonly=True)

