# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class BbisSaleOrderInherit(models.Model):
    _inherit = 'sale.order'

    tc_vehicle_details = fields.Char(string="Vehicle Details")
    inclusive_order_line = fields.One2many('inclusive.order.line', 'order_id', string='Inclusive Order Lines',
                                           copy=True)
    customer_class = fields.Selection(related='partner_id.customer_class', string='Customer Class', readonly=True)
    approve_customer_x = fields.Boolean(default=False, copy=False)
    contract_period = fields.Selection(
        selection_add=[
            ("13", "13"),
            ("72", "72"),
            ("20", "20"),
            ("21", "21"),
            ("22", "22")
        ],
        ondelete={
            "13": "set default",
            "72": "set default",
            "20": "set default",
            "21": "set default",
            "22": "set default"
        }
    )

    def action_approve_customer_x(self):
        self.write({'approve_customer_x': True})
        self.message_post("X-Class Customer approve done by " + self.env.user.name)

    @api.onchange('customer_class', 'partner_id')
    def reset_approve_customer_class(self):
        self.write({'approve_customer_x': False})

    #@api.multi
    def action_submit(self):
        if self.customer_class == 'class_x' and not self.approve_customer_x:
            raise ValidationError("Sorry! Customers with Class X needs approval before you can submit this order.")

        return super(BbisSaleOrderInherit, self).action_submit()

    #@api.multi
    def action_send_bbis_quotation(self):
        """
        This is sending sale quotation / order template with BBIS Format
        """
        self.ensure_one()
        ir_model_data = self.env['ir.model.data']

        pdf_template = 'bbis_send_quotation_order_email_v1'

        if self.sale_type in ('service', 'support'):
            pdf_template = 'bbis_send_service_quotation_order_email'

        if self.inclusive_order_line:
            pdf_template = 'bbis_send_quotation_order_email_inclusive'

        try:
            template_id = ir_model_data.get_object_reference('bbis_reports', pdf_template)[1]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False

        ctx = {
            'default_model': 'sale.order',
            'default_res_id': self.ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'mark_so_as_sent': True,
            'force_email': True
        }

        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }

    # copy inclusive order line to inclusive invoice line
    #@api.multi
    def action_invoice_create(self, grouped=False, final=False):
        """
        Copy inclusive order line to inclusive invoice line
        """

        # Do not allow creating invoice for support or service sale if one of support ticket is not closed
        for r in self:
            if r.support_id:
                tickets_domain = [('customer_support_id', '=', r.support_id.id), ('states', '=', 'done')]
                tickets = self.env['website.support.ticket'].search(tickets_domain)

                if not tickets:
                    raise ValidationError("Invoice cannot be created for this Sale Order because at least one ticket "
                                          "is not yet closed.")

        invoice = super(BbisSaleOrderInherit, self).action_invoice_create(grouped, final)

        for invoice_id in invoice:
            for order in self:

                # check first if the invoice_id is the same with order.origin
                invoice = self.env['account.move'].search([('origin', '=', order.name)], limit=1)

                if invoice.id == invoice_id:
                    # if it is the same then copy the inclusive order line to inclusive invoice lines
                    if order.inclusive_order_line:
                        for line in order.inclusive_order_line:
                            line.inclusive_invoice_line_create(invoice_id, line)

        return invoice

    @api.depends('inclusive_order_line.price_total')
    def _amount_all_inclusive(self):
        for order in self:
            amount_untaxed = amount_tax = 0.0
            for line in order.inclusive_order_line:
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
            order.update({
                'amount_untaxed_inclusive': amount_untaxed,
                'amount_tax_inclusive': amount_tax,
                'amount_total_inclusive': amount_untaxed + amount_tax,
            })

    amount_untaxed_inclusive = fields.Monetary(string='Untaxed Amount', store=True, readonly=True,
                                               compute='_amount_all_inclusive', track_visibility='onchange')
    amount_tax_inclusive = fields.Monetary(string='Taxes', store=True, readonly=True, compute='_amount_all_inclusive')
    amount_total_inclusive = fields.Monetary(string='Total', store=True, readonly=True, compute='_amount_all_inclusive')

    # page breaks
    renewal_charges_pb = fields.Boolean(default=False, string="Renewal Charges")
    optional_items_pb = fields.Boolean(default=False, string="Optional Items")
    terms_pb = fields.Boolean(default=False, string="Terms & Conditions")
    vehicles_pb = fields.Boolean(default=False, string="Vehicle List")

    # rename support service to support sales
    sale_type = fields.Selection(
        selection_add=[
            ('support', 'Support Sale')
        ],
        ondelete={
            'support': 'set default'
        }
    )
    invoice_status_change = fields.Text(string='Manual Invoice Status Change Reason', track_visibility='onchange')

    # make po number and date mandatory if sale type is service or support. Only after confirmation
    #@api.multi
    def action_confirm(self):
        for sale in self.filtered(lambda x: x.sale_type in ('service', 'support', 'pilot')):
            po_data = sale.purchase_order_no and sale.purchase_order_date
            if not po_data:
                raise UserError(_('Please assign Purchase Order No. and Purchase Order Date in this order.'))
        return super(BbisSaleOrderInherit, self).action_confirm()

    def update_invoice_status(self):
        return {
            'name': 'Update Invoice Status',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'bbis.update.po.so.invoice.status',
            'target': 'new',
            'context': {'default_model_type': 'sale', 'default_sale_order_id': self.id},
        }

    def _get_current_user(self):
        current_uid = self.env.uid
        user = self.env['res.users'].browse(current_uid)

        return user

# Add the sales order cancel checking in delivery note sales invoice and job card
class BBISSalesOrderInheritWizard(models.TransientModel):
    _inherit = 'sale.advance.cancel.inv'

    #@api.multi
    def update_details(self):
        so_number = self.env['sale.order'].search([('id', '=', self.order_id.id)])
        delivery_id = self.env['stock.picking'].search([('sale_id', '=', self.order_id.id)])
        job_id = self.env['job.card'].search([('sale_order_id', '=', self.order_id.id)])
        invoice_id = self.env['account.move'].search([('origin', '=', so_number.name)])

        # Checking whether the invoice is paid or there is a credit note against this invoice
        for invoice in invoice_id:
            if invoice.state == 'paid':
                credit_note_id = self.env['account.move'].search([('refund_invoice_id', '=', invoice.id)])
                if credit_note_id:
                    if credit_note_id.state != 'paid':
                        raise UserError(_("Credit Note was created against the Sales Invoice, but it's not paid."))
                else:
                    raise UserError(_('Sales Invoice was already paid for this Sales Order. '
                                      'Please create a Credit Note.'))

        # Checking whether the Delivery Note is Done or any other returns are pending.
        for rec in delivery_id:
            if rec.state == 'done':
                name = rec.origin.split()
                if name[0].lower() == 'return':
                    continue
                ctr = 0
                for delivery in delivery_id:
                    if rec.name != delivery.name:
                        return_name = delivery.origin.split()
                        if return_name[0].lower() == 'return':
                            if rec.name == return_name[2]:
                                if delivery.state == 'done' or delivery.state == 'cancel':
                                    ctr = ctr + 1
                                    break
                                else:
                                    raise UserError(_('Sorry! You can not cancel Sale Order with delivery in Done '
                                                      'state. Please return the delivery.'))
                if ctr == 0:
                    raise UserError(_('Sorry! You can not cancel Sale Order with delivery in Done state. '
                                      'Please return the delivery.'))

        # If the Delivery Note status is not 'Done' or 'Cancel' need to cancel those Delivery Notes.
        for rec in delivery_id:
            if rec.state != 'done' and rec.state != 'cancel':
                rec.action_cancel()

        # Job Card Delete
        for jobs in job_id:
            self.env["job.card"].search([('id', '=', jobs.id)]).unlink()

        return super(BBISSalesOrderInheritWizard, self).update_details()
