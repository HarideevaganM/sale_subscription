from odoo import api, fields, models, _
from odoo.exceptions import UserError, AccessError
from datetime import datetime, date, timedelta, time
from dateutil.relativedelta import relativedelta
import calendar
import dateutil.parser
from calendar import monthrange
import json
from lxml import etree


# class SaleSubscriptionStage(models.Model):
#     _inherit = 'sale.subscription.stage'
#
#     category = fields.Selection(selection_add=[('pending', 'Quotation'), ('closed',), ('cancel', 'Cancelled')], ondelete={'pending': 'cascade', 'cancel': 'cascade'})


# class SaleSubscriptionLog(models.Model):
#     _inherit = 'sale.subscription.log'
#
#     subscription_period = fields.Integer(string="Subscription Period", help="No Of Months")
#     category = fields.Selection(selection_add=[('pending', 'Quotation'), ('closed',), ('cancel', 'Cancelled')],
#                                 ondelete={'pending': 'cascade', 'cancel': 'cascade'})


class SaleSubscriptionInherit(models.Model):
    _inherit = "sale.order"

    sale_order_id = fields.Many2one("sale.order", "Sale Reference")
    invoice_type = fields.Selection([('post', 'Post Invoice'), ('pre', 'Previous Inovice')], string='Invoice Type', default='post')
    start_date = fields.Date('Period Start Date')
    end_date = fields.Date('Period End Date')
    job_card_id = fields.Many2one("job.card", "Job Card Reference")
    subscription_period = fields.Integer(string="Subscription Period", help="No Of Months")
    period = fields.Integer(string="Period")
    serial_no = fields.Many2one("stock.lot", string="Device Serial No")
    note = fields.Text("Note")
    user_id = fields.Many2one("res.users", "Validated by")
    validation_date = fields.Date("Validation Date", default=fields.datetime.now())
    vehicle_number = fields.Many2one("vehicle.master", "Vehicle")
    contract_type = fields.Selection([('direct', 'Normal Customer'), ('partner', 'Reseller')], string="Customer Category")
    installation_date = fields.Date("Installation Date")
    activation_date = fields.Date("Activation Date")
    imei_no = fields.Char("Satellite IMEI No")
    gsm_number = fields.Char("GSM Number")
    date_start = fields.Date(string='Subscription Start Date')
    date = fields.Date(string='Subscription End Date', help="If set in advance, the subscription will be set to pending 1 month before the date and will be closed on the date set in this field.")
    subscription_status = fields.Selection([('active', 'Active'), ('in_active', 'Closed')], string="Device Status", related='job_card_id.device_status', store=True)
    renewal_status = fields.Selection([('due_for_renewal', 'Due for Renewal'), ('over_due', 'Over Due'),('renewed', 'Renewed'),('na', 'Running')], string="Renewal Status", compute='compute_renewal_status')
    status_renewal = fields.Char("Renewal Status")
    # state = fields.Selection([('draft', 'New'), ('open', 'In Progress'), ('pending', 'Quotation'),
    #                           ('close', 'Hold'), ('cancel', 'Cancelled')
    #                           ], string='State', required=True, track_visibility='onchange', copy=False, default='draft')
    billing_days = fields.Integer(compute='compute_invoicing_period', string="Billing days")
    prorate_invoice_count = fields.Integer(compute="count_prorate_invoice", string="Prorate Invoice Count")
    sale_type = fields.Selection([('cash', 'Retail Sales'),
                                  ('purchase', 'Corporate Sales'),
                                  ('lease', 'Lease (To Own) Sale'),
                                  ('rental', 'Lease (Rental) Sale'),
                                  ('pilot', 'Renewal Sale'),
                                  ], string='Sale Type', default='rental')
    engineer_id = fields.Many2one('res.users', 'Engineer')
    device_id = fields.Many2one("product.product", "Device Type")
    renewal_date = fields.Date("Renewal Date")    
    invoiced_date = fields.Date("Invoice Date")
    invoice_status = fields.Selection([('invoiced', 'Invoiced'), ('upselling', "Upselling Opportunity"), ('to invoice', "To Invoice"),
            ('no', "Nothing to Invoice"), ('to_invoiced', 'To be Invoiced')],string="Invoice Status")
    store_end_date = fields.Date(string="Billing End Date", store=True)
    template_id = fields.Many2one('sale.order.template', string='Billing cycle', required=True, track_visibility='onchange')
    bill_start_date = fields.Datetime(string="Billing Start Date")
    bill_end_date = fields.Datetime(string="Billing End Date")
    auto_renewal = fields.Boolean("Auto Renewal")
    auto_bill = fields.Boolean("Auto Billing")
    customer_types = fields.Selection([('opal customer', 'OPAL Customer'),('non opal customer', ' NON OPAL Customer')], string="Customer Type")
    is_reseller = fields.Boolean("Reseller", default= False, store = True, related = 'partner_id.is_reseller')
    category = fields.Selection([('draft', 'Draft'), ('progress', 'In Progress'), ('closed', 'Closed')],related='stage_id.category')
    recurring_next_date = fields.Date(string='Date of Next Invoice', default=fields.Date.today, help="The next invoice will be created on this date then the period will be extended.", tracking=True)

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(SaleSubscriptionInherit, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if view_type == 'form':
            doc = etree.XML(res['arch'])
            for node in doc.xpath("//field[@name='recurring_next_date']"):
                is_admin = self.env.user.has_group('base.group_system')
                modifiers = json.loads(node.get("modifiers"))
                if not is_admin:
                    modifiers['readonly'] = True
                    node.set("modifiers", json.dumps(modifiers))
            res['arch'] = etree.tostring(doc, encoding='unicode')
        return res

    # @api.multi
    def compute_period(self):
        start_dt = fields.Datetime.from_string(self.date_start)
        finish_dt = fields.Datetime.from_string(self.date)
        difference = relativedelta(finish_dt, start_dt)
        self.subscription_period = difference.days

    #### FUNCTION ADDED TO CALCULATE END DATE
    def run_compute_manual(self):
        for rec in self:
            rec.get_end_date()

    def _get_end_date(self):
        if self.date_start and self.subscription_period:
            start_date = datetime.strptime(str(self.date_start), "%Y-%m-%d")
            start_period = start_date + relativedelta(months=int(self.subscription_period))
            start_sub_period = start_period - relativedelta(days=1)
            self.date = fields.Date.to_string(start_sub_period)
            self.store_end_date = fields.Date.to_string(start_sub_period)

    @api.onchange('subscription_period', 'date_start')
    def onchange_date_start(self):
        if self.date_start and self.subscription_period:
            end_date = fields.Date.from_string(self.date_start) + relativedelta(months=self.subscription_period)
            self.date = end_date - relativedelta(days=1)
            self.renewal_date = end_date

    ### TO GET START DATE BASED ON ACTIVATION DATE
    @api.onchange('activation_date')
    def onchange_activation_date(self):
        if self.activation_date:
            self.update({'date_start': self.activation_date})

    # TO Change the status based on end date
    # @api.multi
    def compute_renewal_status(self):
        for vals in self:
            fmt = '%Y-%m-%d'
            date_today = datetime.strptime(str(datetime.now().date()), '%Y-%m-%d')
            today = date_today.strftime(fmt)
            if vals.date:
                date_end = datetime.strptime(str(vals.date), fmt)
                end = date_end.strftime(fmt)
                start_date = fields.Datetime.from_string(today)
                end_date = fields.Datetime.from_string(end)
                ending_date = end_date - relativedelta(days=1)
                daysDiff = str((end_date - start_date).days)
                daysDiff = int(daysDiff)
                if 0 < daysDiff < 30:
                    vals.write({'renewal_status': 'due_for_renewal'})
                    vals.write({'status_renewal': 'Due For Renewal'})
                elif date_today > date_end:
                    vals.write({'renewal_status': 'over_due'})
                    vals.write({'status_renewal': 'Over Due'})
                else:
                    vals.write({'renewal_status': 'na'})
                    vals.write({'status_renewal': 'Running'})

    # @api.multi
    def status_update(self):
        subscription = self.env['sale.order'].search([('is_subscription', '=', True)])
        for vals in subscription:
            fmt = '%Y-%m-%d'
            date_today = datetime.strptime(str(datetime.now().date()), '%Y-%m-%d')
            today = date_today.strftime(fmt)
            date_end = datetime.strptime(str(vals.date), fmt)
            end = date_end.strftime(fmt)
            start_date = fields.Datetime.from_string(today)
            end_date = fields.Datetime.from_string(end)
            ending_date = end_date - relativedelta(days=1)
            daysDiff = str((end_date - start_date).days)
            daysDiff = int(daysDiff)           
            if 0 < daysDiff < 30:
                vals.write({'renewal_status': 'due_for_renewal'})
                vals.write({'status_renewal': 'Due For Renewal'})
            elif date_today > date_end:
                vals.write({'renewal_status': 'over_due'})
                vals.write({'status_renewal': 'Over Due'})
            else:
                vals.write({'renewal_status': 'na'})
                vals.write({'status_renewal': 'Running'})

    ## To calculate billing days
    # @api.one
    @api.depends('activation_date')
    def compute_invoicing_period(self):
        for rec in self:
            if rec.activation_date:
                fmt = '%Y-%m-%d'
                activate_date = datetime.strptime(str(rec.activation_date), fmt)
                act_date = activate_date.strftime(fmt)
                month_end_date = str(datetime.now() + relativedelta(months=+1, day=1, days=-1))[:10]
                final = datetime.strptime(str(month_end_date), fmt)
                month_end = final.strftime(fmt)
                d1 = fields.Datetime.from_string(month_end)
                d2 = fields.Datetime.from_string(act_date)
                billing = str((d1 - d2).days)
                rec.billing_days = int(billing) + 1
            else:
                rec.billing_days = 0

    ## To Create Prorate Invoice
    # @api.multi
    def prorate_invoice_creation(self):
        now = datetime.now()
        current_month_days = monthrange(now.year, now.month)[1]
        invoice_obj = self.env['account.move']
        invoice_line_obj = self.env['account.move.line']
        subscription_line = self.env['sale.order.line'].search([('analytic_account_id', '=', self.id)])
        vals = {
            'account_id': self.partner_id.property_account_receivable_id.id,
            'sale_subscription_id': self.id,
            'partner_id': self.partner_id.id,
        }
        result = invoice_obj.create(vals)
        for line in subscription_line:
            account = line.product_id.property_account_income_id
            price_unit = (line.price_unit / current_month_days) * self.billing_days
            if not account:
                account = line.product_id.categ_id.property_account_income_categ_id
            line_values = {
                'move_id': result.id,
                'product_id': line.product_id.id,
                'name': line.name,
                'quantity': line.quantity,
                'uom_id': line.uom_id.id,
                'price_unit': price_unit,
                'account_id': account.id,
            }
            invoice_line_obj.create(line_values)

    # @api.multi
    def open_prorate_invoice(self):
        # res = self.env['ir.actions.act_window'].for_xml_id('account', 'action_invoice_tree')
        res = self.env.ref('account.action_invoice_tree')
        invoice_ids = self.env['account.move'].search([('sale_subscription_id', '=', self.id)])
        res['domain'] = [('id', 'in', invoice_ids.ids)]
        return res

    # @api.multi
    def count_prorate_invoice(self):
        for rec in self:
            rec.prorate_invoice_count = len(
                self.env["account.move"].search([('sale_subscription_id', '=', rec.id)]).ids)

    # @api.multi
    # def _prepare_invoice_data(self):
    #     self.ensure_one()
    #     if not self.partner_id:
    #         raise UserError(_("You must first select a Customer for Subscription %s!") % self.name)
    #     if 'force_company' in self.env.context:
    #         company = self.env['res.company'].browse(self.env.context['force_company'])
    #     else:
    #         company = self.company_id
    #         self = self.with_context(force_company=company.id, company_id=company.id)
    #     fpos_id = self.env['account.fiscal.position'].get_fiscal_position(self.partner_id.id)
    #     journal = self.template_id.journal_id or self.env['account.journal'].search([('type', '=', 'sale'), ('company_id', '=', company.id)], limit=1)
    #     if not journal:
    #         raise UserError(_('Please define a sale journal for the company "%s".') % (company.name or '',))
    #     periods = {'daily': 'days', 'weekly': 'weeks', 'monthly': 'months', 'yearly': 'years'}
    #     subscription_period = relativedelta(**{periods[self.recurring_rule_type]: self.recurring_interval})
    #     if self.end_date and self.invoice_type == 'pre':
    #         current_date = fields.Date.from_string(self.start_date)
    #         end_date = current_date - relativedelta(days=1)
    #         start_date = current_date - subscription_period
    #         str_start_date = datetime.strftime(start_date, "%d-%m-%Y")
    #         str_end_date = datetime.strftime(end_date, "%d-%m-%Y")
    #         return {
    #             'account_id': self.partner_id.property_account_receivable_id.id,
    #             'move_type': 'out_invoice',
    #             'partner_id': self.partner_id.id,
    #             'currency_id': self.pricelist_id.currency_id.id or company.currency_id.id,
    #             'journal_id': journal.id,
    #             'invoice_date': self.recurring_next_date,
    #             'invoice_origin': self.code,
    #             'fiscal_position_id': fpos_id,
    #             'invoice_payment_term_id': self.partner_id.property_payment_term_id.id,
    #             'company_id': company.id,
    #             'comment': _("This invoice covers the following period: %s - %s") % (str_start_date, str_end_date),
    #             }
    #
    #     # elif self.end_date and self.invoice_type == 'post':
    #     #     new_date = next_date + subscription_period
    #     #     pre_new_date = new_date - relativedelta(days=1)
    #     #     new_date = datetime.strftime(pre_new_date, "%d-%m-%Y")
    #     #     next_date = datetime.strftime(next_date, "%d-%m-%Y")
    #     #     print("\n---",new_date, pre_new_date, new_date, next_date,"--new_date, pre_new_date, new_date, next_date- Post Invoice-\n")
    #     #     return {
    #     #         'account_id': self.partner_id.property_account_receivable_id.id,
    #     #         'type': 'out_invoice',
    #     #         'partner_id': self.partner_id.id,
    #     #         'currency_id': self.pricelist_id.currency_id.id or company.currency_id.id,
    #     #         'journal_id': journal.id,
    #     #         'date_invoice': self.recurring_next_date,
    #     #         'origin': self.code,
    #     #         'fiscal_position_id': fpos_id,
    #     #         'payment_term_id': self.partner_id.property_payment_term_id.id,
    #     #         'company_id': company.id,
    #     #         'comment': _("This invoice covers the following period: %s - %s") % (next_date, new_date),
    #     #         }
    #     elif self.invoice_type == 'post':
    #         if self.start_date and self.end_date:
    #             return {
    #                 'account_id': self.partner_id.property_account_receivable_id.id,
    #                 'move_type': 'out_invoice',
    #                 'partner_id': self.partner_id.id,
    #                 'currency_id': self.pricelist_id.currency_id.id or company.currency_id.id,
    #                 'journal_id': journal.id,
    #                 'invoice_date': self.recurring_next_date,
    #                 'invoice_origin': self.code,
    #                 'fiscal_position_id': fpos_id,
    #                 'invoice_payment_term_id': self.partner_id.property_payment_term_id.id,
    #                 'company_id': company.id,
    #                 'comment': _("This invoice covers the following period: %s to %s") % (
    #                 fields.Date.from_string(self.start_date).strftime('%d-%m-%Y'), fields.Date.from_string(self.end_date).strftime('%d-%m-%Y')),
    #             }
    #         else:
    #             raise UserError(_("Please enter the invoice period for subcription invoice"))

    def _prepare_renewal_order_values(self, discard_product_ids=False, new_lines_ids=False):
        res = dict()
        for subscription in self:
            subscription = subscription.with_company(subscription.company_id)
            order_lines = []
            fpos = subscription.env['account.fiscal.position'].get_fiscal_position(subscription.partner_id.id)
            partner_lang = subscription.partner_id.lang
            if discard_product_ids:
                # Prevent to add products discarded during the renewal
                line_ids = subscription.with_context(active_test=False).recurring_invoice_line_ids.filtered(
                    lambda l: l.product_id.id not in discard_product_ids)
            else:
                line_ids = subscription.recurring_invoice_line_ids
            for line in line_ids:
                product = line.product_id.with_context(lang=partner_lang) if partner_lang else line.product_id
                order_lines.append((0, 0, {
                    'product_id': product.id,
                    'name': product.with_context(active_test=False).get_product_multiline_description_sale(),
                    'subscription_id': subscription.id,
                    'product_uom': line.uom_id.id,
                    'product_uom_qty': line.quantity,
                    'price_unit': line.price_unit,
                    'discount': line.discount,
                }))
            if new_lines_ids:
                # Add products during the renewal (sort of upsell)
                for line in new_lines_ids:
                    existing_line_ids = subscription.recurring_invoice_line_ids.filtered(
                        lambda l: l.product_id.id == line.product_id.id)
                    if existing_line_ids:
                        # The product already exists in the SO lines, update the quantity
                        def _update_quantity(so_line):
                            # Map function to update the quantity of the SO line.
                            if so_line[2]['product_id'] in existing_line_ids.mapped('product_id').ids:
                                so_line[2]['product_uom_qty'] = line.quantity + so_line[2]['product_uom_qty']
                            return so_line

                        # Update the order lines with the new quantity
                        order_lines = list(map(_update_quantity, order_lines))
                    else:
                        order_lines.append((0, 0, {
                            'product_id': line.product_id.id,
                            'name': line.name,
                            'subscription_id': subscription.id,
                            'product_uom': line.uom_id.id,
                            'product_uom_qty': line.quantity,
                            'price_unit': subscription.pricelist_id.with_context(uom=line.uom_id.id).get_product_price(
                                line.product_id, line.quantity, subscription.partner_id),
                            'discount': 0,
                        }))
            addr = subscription.partner_id.address_get(['delivery', 'invoice'])
            res[subscription.id] = {
                'pricelist_id': subscription.pricelist_id.id,
                'partner_id': subscription.partner_id.id,
                'partner_invoice_id': subscription.partner_invoice_id.id or addr['invoice'],
                'partner_shipping_id': subscription.partner_shipping_id.id or addr['delivery'],
                'currency_id': subscription.pricelist_id.currency_id.id,
                'order_line': order_lines,
                'analytic_account_id': subscription.analytic_account_id.id,
                'subscription_management': 'renew',
                'origin': subscription.code,
                'note': subscription.description,
                'fiscal_position_id': fpos.id,
                'user_id': subscription.user_id.id,
                'payment_term_id': subscription.payment_term_id.id,
                'company_id': subscription.company_id.id,
                'sale_type': subscription.sale_type,
            }
        return res


class SubscriptionRenewalList(models.TransientModel):
    _name = "subscription.renewal.list.wizard"
        
    start_date = fields.Date("Start Date", required=True)
    end_date = fields.Date("End Date")
    month_period = fields.Integer("Subscription Period", required=True)

    # @api.multi
    def update_renewal(self):
        active = self.env.context.get('active_ids')
        # stage = self.env['sale.subscription.stage'].search([('category', '=', 'progress')], limit=1)
        # subs = self.env["sale.order"].search([('id', 'in', active), ('stage_id', '=', stage.id)])
        if subs:
            subs.write({
                'date_start': self.start_date,
                'renewal_status': 'renewed',
                'status_renewal': 'Renewed',
                'renewal_date': datetime.now(),
                'subscription_period': self.month_period
            })


class InvocieStatusList(models.TransientModel):
    _name = "invoice.state.list.wizard"

    invoice_date = fields.Date("Invoice Date", required=True)

    # @api.multi
    def update_invoice_state(self):
        active = self.env.context.get('active_ids')
        stage = self.env['sale.subscription.stage'].search([('category', '=', 'progress')], limit=1)
        subs = self.env["sale.order"].search([('id', 'in', active), ('stage_id', '=', stage.id)])
        for sub in subs:
            sub.write({
                'invoiced_date': self.invoice_date,
                'invoice_status': 'invoiced',
            })

