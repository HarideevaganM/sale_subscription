# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class InclusiveOrderLine(models.Model):
    _name = "inclusive.order.line"
    _description = "Sale Quotation/Order Inclusive. Only used for reporting and does not affect inventory"

    #@api.multi
    def inclusive_invoice_line_create(self, invoice_id, order):
        """
        This method will copy the inclusive order lines to inclusive invoice lines
        """
        inclusive_invoice_lines = self.env['inclusive.invoice.line']

        # Select all ids of the inclusive order lines
        order_ids = order.order_line_ids.mapped('id')

        # select all product form order lines from the inclusive order line ids
        invoice_order_lines = self.env['account.move.line'].search([('invoice_id', '=', invoice_id),
                                                                       ('sale_line_ids', 'in', order_ids)])

        # Prepare the values, only invoice_line_ids is needed. All fields will be automatically computed
        values = {
            'name': order.name,
            'invoice_id': invoice_id,
            'invoice_id': invoice_id,
            'quantity': order.quantity,
            'invoice_line_ids': [(6, 0, invoice_order_lines.ids)],
        }

        # create the invoice inclusive lines
        inclusive_invoice_lines |= self.env['inclusive.invoice.line'].create(values)

        return inclusive_invoice_lines

    @api.depends('order_line_ids')
    def _compute_group_quantity(self):
        for r in self:
            r.group_quantity = sum(r.order_line_ids.mapped('product_uom_qty'))

    @api.depends('order_line_ids', 'quantity', 'contract_period', 'so_amount_total')
    def _compute_amounts(self):
        """
        Compute the total unit price of the order lines of the SO line.
        """
        for r in self:

            contract_period = 0
            sale_type = ''
            price_unit = 0
            total_price_unit = []
            vat = []
            for order in r.order_line_ids:
                tax_amount = sum(order.tax_id.mapped('amount')) / 100
                contract_period = int(order.order_id.contract_period)

                if not order.order_id.sale_type:
                    raise ValidationError(_('Please select a Sale Type from the Sale Order.'))

                if order.order_id.sale_type in ('lease', 'rental'):
                    # check if compute contract
                    compute_contract = order.product_id.type in ('product', 'service') and order.product_id.categ_id.enable_total
                    subtotal = order.price_unit * order.product_uom_qty

                    if compute_contract:
                        price_vat = ((subtotal - order.discount_amount) * contract_period) * tax_amount
                        price = (subtotal - order.discount_amount) * contract_period
                    else:
                        price_vat = (subtotal - order.discount_amount) * tax_amount
                        price = subtotal - order.discount_amount
                elif order.order_id.sale_type == 'pilot':
                    price_vat = ((order.price_unit * order.product_uom_qty) - order.discount_amount) * tax_amount
                    price = (order.price_unit * order.product_uom_qty) - order.discount_amount
                else:
                    price_temp = order.price_unit * r.quantity
                    price_vat = (price_temp - order.discount_amount) * tax_amount
                    price = price_temp - order.discount_amount
                vat.append(price_vat)
                total_price_unit.append(price)

            # get the first order line to have a single product and single order
            if len(r.order_line_ids):
                single_product = r.order_line_ids[0].product_id
                single_order = r.order_line_ids[0].order_id
                contract_period = int(single_order.contract_period)
                sale_type = single_order.sale_type
                price_unit = r.order_line_ids[0].price_unit if sale_type in 'pilot' \
                    else sum(r.order_line_ids.mapped('price_unit'))

            discount = sum(r.order_line_ids.mapped('discount_amount'))
            total_vat = sum(vat)
            r.price_unit = price_unit
            r.discount = discount
            r.price_tax = total_vat

            if sale_type in ('lease', 'rental'):
                r.price_subtotal = sum(total_price_unit)
                r.price_total = sum(total_price_unit) + total_vat
                # check if compute contract
                # compute_contract = single_product.type in ('product', 'service') and single_product.categ_id.enable_total
                # # subtotal = price_unit * r.group_quantity
                # subtotal = price_unit * r.quantity
                #
                # if compute_contract:
                #     r.discount = discount * contract_period
                #     r.price_subtotal = (subtotal * contract_period) - r.discount
                #     r.price_total = ((subtotal * contract_period) - r.discount) + total_vat
                # else:
                #     r.price_subtotal = (subtotal - discount)
                #     r.price_total = (subtotal - discount) + total_vat
            elif sale_type == 'pilot':
                subtotal = price_unit * r.group_quantity

                r.price_subtotal = (subtotal - discount)
                r.price_total = (subtotal - discount) + total_vat
            else:
                subtotal = price_unit * r.quantity

                r.price_subtotal = subtotal - discount
                r.price_total = (subtotal - discount) + total_vat

    name = fields.Text(string='Item Description')
    order_id = fields.Many2one("sale.order", string="Order Reference", required=True, index=True, copy=False)
    order_line_ids = fields.Many2many("sale.order.line", string="Products from Order Lines", required=True)

    quantity = fields.Float(string='Quantity', digits=(6, 0), required=True, default="1")
    price_unit = fields.Float(compute='_compute_amounts', string='Unit Price', readonly=True, store=True)
    price_subtotal = fields.Float(compute='_compute_amounts', string='Subtotal', readonly=True, store=True)
    price_tax = fields.Float(compute='_compute_amounts', string='Tax Amount', readonly=True, store=True)
    discount = fields.Float(compute='_compute_amounts', string='Discount Fix', readonly=True, store=True)
    price_total = fields.Float(compute='_compute_amounts', string='Price Total', readonly=True, store=True)

    currency_id = fields.Many2one(related='order_id.currency_id', store=True, string='Currency', readonly=True)
    contract_period = fields.Selection(related='order_id.contract_period', store=True, string='Contract Period', readonly=True)
    group_quantity = fields.Integer(compute='_compute_group_quantity', string="Quantity", readonly=True, store=True)

    # will be used to trigger compute amounts if sale order amount_total changes
    so_amount_total = fields.Monetary(related='order_id.amount_total', store=True, string='Sale Order Total Amount', readonly=True)


