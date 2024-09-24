from odoo import api, fields, models, _
from dateutil.relativedelta import relativedelta
from datetime import datetime, date, timedelta
from odoo.exceptions import UserError, AccessError
from odoo.addons import decimal_precision as dp

class SaleVehicleDetails(models.Model):
    _name = "sale.vehicle.details"

    sale_id = fields.Many2one('sale.order', string="Sale")
    serial_no_id = fields.Many2one("stock.production.lot", string="Device Serial No")
    device_id = fields.Many2one("product.product", string="Device Name")
    vehicle_id = fields.Many2one('vehicle.master', string="Vehicle Reg No")
    vehicle_name = fields.Char(related='vehicle_id.vehicle_name', string="Vehicle Name")
    partner_id = fields.Many2one('res.partner', string="Client Name")
    installation_date = fields.Date('Installation Date')
    start_date = fields.Date('Subscription Start')
    end_date = fields.Date('Subscription End', store=True)
    status = fields.Selection([('active', 'Active'), ('in_active', 'In Active'), ('non_active', 'Non Active')], string='Status')
    num_of_period = fields.Integer('Periods(M)', default=1)

    @api.onchange('start_date', 'num_of_period')
    def onchange_start_date(self):
        if self.start_date and self.num_of_period:
            periods = {'daily': 'days', 'weekly': 'weeks', 'monthly': 'months', 'yearly': 'years'}
            val = relativedelta(**{periods['monthly']: self.num_of_period})
            start_date = fields.Date.from_string(self.start_date) - timedelta(days=1)
            self.end_date = start_date + val



class SaleOrderInherit(models.Model):
    _inherit = "sale.order"

    # @api.multi
    def action_confirm(self):
        res = super(SaleOrderInherit, self).action_confirm()
        line_obj = self.order_line
        self.tree_qty = sum(line_obj.filtered(lambda x: x.product_id.type == 'product').mapped('product_uom_qty'))
        return res

    # @api.multi
    def action_submit(self):
        self.write({'state': 'submit'})
        lead_ids = self.env['crm.lead'].search([('id', '=', self.opportunity_id.id)])
        if lead_ids:
            won_stage = self.env['crm.stage'].search([('is_won', '!=', False)], limit=1)
            if won_stage:
                lead_ids.write({'stage_id': won_stage.id})

    # @api.multi
    def action_cancel(self):
        return self.write({'state': 'cancel'})
        lead_ids = self.env['crm.lead'].search([('id', '=', self.opportunity_id.id)])
        if lead_ids:
            self.write({'active': False})

    # @api.multi
    def action_quotation_send(self):
        res = super(SaleOrderInherit,self).action_quotation_send()
        lead_ids = self.env['crm.lead'].search([('id', '=', self.opportunity_id.id)])
        if lead_ids:
            lead_ids.write({'stage_id': 3})
        return res

    def get_terms(self):
        payment_lines = []
        warranty_lines = []
        contract_lines = []
        delivery_lines = []
        service_lines = []
        validity_lines = []
        other_lines = []
        terms_list = self.env['terms.conditions'].search([('sale_type', '=', self.sale_type)], limit=1)
        self.report_payment_terms_line = False
        self.report_warranty_line = False
        self.contract_period_report_line = False
        self.delivery_installation_schedule = False
        self.report_service_support = False
        self.report_validity = False
        self.other_information_line = False
        for payment_list in terms_list.tc_paymentterms_line:
            payment_vals = {'name': payment_list.name}
            payment_lines.append((0, 0, payment_vals))
        for warranty_list in terms_list.tc_warranty_line:
            warranty_vals = {'name': warranty_list.name}
            warranty_lines.append((0, 0, warranty_vals))
        for contract_list in terms_list.tc_contract_period:
            contract_vals = {'name': contract_list.name}
            contract_lines.append((0, 0, contract_vals))
        for delivery_list in terms_list.tc_delivery_installation:
            delivery_vals = {'name': delivery_list.name}
            delivery_lines.append((0, 0, delivery_vals))
        for service_list in terms_list.tc_service_support:
            service_vals = {'name': service_list.name}
            service_lines.append((0, 0, service_vals))
        for validity_list in terms_list.tc_validity:
            validity_vals = {'name': validity_list.name}
            validity_lines.append((0, 0, validity_vals))
        for other_list in terms_list.tc_other:
            other_vals = {'name': other_list.name}
            other_lines.append((0, 0, other_vals))
        self.update({
            'report_payment_terms_line': payment_lines,
            'report_warranty_line': warranty_lines,
            'contract_period_report_line': contract_lines,
            'delivery_installation_schedule': delivery_lines,
            'report_service_support': service_lines,
            'report_validity': validity_lines,
            'other_information_line': other_lines,
        })

    # @api.multi
    def _prepare_invoice(self):
        """
        Prepare the dict of values to create the new invoice for a sales order. This method may be
        overridden to implement custom invoice generation (making sure to call super() to establish
        a clean extension chain).
        """
        self.ensure_one()
        journal = self.env['account.move'].with_context(default_move_type='out_invoice')._get_default_journal()
        if not journal:
            raise UserError(_('Please define an accounting sales journal for the company %s (%s).', self.company_id.name, self.company_id.id))

        invoice_vals = {
            'ref': self.client_order_ref or '',
            'move_type': 'out_invoice',
            'narration': self.note,
            'currency_id': self.pricelist_id.currency_id.id,
            'campaign_id': self.campaign_id.id,
            'medium_id': self.medium_id.id,
            'source_id': self.source_id.id,
            'user_id': self.user_id.id,
            'invoice_user_id': self.user_id.id,
            'team_id': self.team_id.id,
            'partner_id': self.partner_invoice_id.id,
            'partner_shipping_id': self.partner_shipping_id.id,
            'fiscal_position_id': (self.fiscal_position_id or self.fiscal_position_id.get_fiscal_position(
                self.partner_invoice_id.id)).id,
            'partner_bank_id': self.company_id.partner_id.bank_ids.filtered(
                lambda bank: bank.company_id.id in (self.company_id.id, False))[:1].id,
            'journal_id': journal.id,  # company comes from the journal
            'invoice_origin': self.name,
            'invoice_payment_term_id': self.payment_term_id.id,
            'payment_reference': self.reference,
            'transaction_ids': [(6, 0, self.transaction_ids.ids)],
            'invoice_line_ids': [],
            'company_id': self.company_id.id,
            'purchase_order_no': self.purchase_order_no,
            'purchase_order_date': self.purchase_order_date,
            'sale_type': self.sale_type,
        }
        return invoice_vals

        # invoice_vals = {
        #     'ref': self.client_order_ref or '',
        #     'invoice_origin': self.name,
        #     'move_type': 'out_invoice',
        #     'account_id': self.partner_invoice_id.property_account_receivable_id.id,
        #     'partner_id': self.partner_invoice_id.id,
        #     'partner_shipping_id': self.partner_shipping_id.id,
        #     'journal_id': journal_id,
        #     'currency_id': self.pricelist_id.currency_id.id,
        #     'comment': self.note,
        #     'payment_term_id': self.payment_term_id.id,
        #     'fiscal_position_id': self.fiscal_position_id.id or self.partner_invoice_id.property_account_position_id.id,
        #     'company_id': self.company_id.id,
        #     'user_id': self.user_id and self.user_id.id,
        #     'team_id': self.team_id.id,
        #     'purchase_order_no': self.purchase_order_no,
        #     'purchase_order_date': self.purchase_order_date,
        #     'sale_type': self.sale_type,
        # }
        # return invoice_vals

    # To Count Purchase Order
    # @api.multi
    def count_po(self):
        for rec in self:
            rec.po_count = len(self.env["purchase.order"].search([('sale_id', '=', rec.id)]).ids)

    # To view purchase order
    # @api.multi
    def open_po_view(self):
        if self._context is None:
            context = {}
        # res = self.env['ir.actions.act_window'].for_xml_id('purchase', 'purchase_form_action')
        res = self.env.ref('purchase.purchase_form_action')
        res['context'] = self._context
        purchase_ids = self.env['purchase.order'].search([('sale_id', '=', self.id)])
        res['domain'] = [('id', 'in', purchase_ids.ids)]
        return res

    # To create Direct PO for principal supplier
    # @api.multi
    def create_po(self):
        create_po = True
        ## Check PO count ##
        if self.po_count < 1:
            self.write({'show_po': True})
            user = self.env['res.users'].search([('id', '=', self._uid)], limit=1)
            values = {
                'user_id': self.user_id.id,
                'sale_id': self.id,
                'company_id': user and user.company_id.id,
                'origin': self.name,
                'partner_id': self.partner_id.id,
                'make_vendor_readonly': True,
                'order_id': self.id
            }
            purchase_order = self.env['purchase.order'].create(values)
            if purchase_order:
                for len_val in self.order_line:
                    line_value = {
                        'product_id': len_val.product_id.id,
                        'product_qty': len_val.product_uom_qty,
                        'qty_ordered': len_val.product_uom_qty,
                        'product_uom_id': len_val.product_uom.id,
                        'price_unit': len_val.price_unit,
                        'name': len_val.name,
                        'date_planned': self.date_order,
                        'product_uom': len_val.product_id.uom_id.id,
                        'order_id': purchase_order.id
                    }
                    self.env['purchase.order.line'].create(line_value)
        else:
            raise UserError(_(" You can create only one Purchase Order!!!"))

    # To create RFQ for Other suppliers
    # @api.multi
    def create_rfq(self):
        create_quote = True
        self.write({'show_rfq': True})
        user = self.env['res.users'].search([('id', '=', self._uid)], limit=1)
        values = {
            'user_id': self.user_id.id,
            'sale_id': self.id,
            'company_id': user and user.company_id.id,
            'origin': self.name,
            'partner_id': self.partner_id.id,
            'order_id': self.id
        }
        purchase_order = self.env['purchase.order'].create(values)
        if purchase_order:
            for len_val in self.order_line:
                line_value = {
                    'product_id': len_val.product_id.id,
                    'product_qty': len_val.product_uom_qty,
                    'qty_ordered': len_val.product_uom_qty,
                    'product_uom_id': len_val.product_uom.id,
                    'price_unit': len_val.price_unit,
                    'name': len_val.name,
                    'date_planned': self.date_order,
                    'product_uom': len_val.product_id.uom_id.id,
                    'order_id': purchase_order.id
                }
                self.env['purchase.order.line'].create(line_value)

    ## To Count Purchase Order
    # @api.multi
    def count_rfq(self):
        for rec in self:
            rec.rfq_count = len(self.env["purchase.order"].search([('sale_id', '=', rec.id)]).ids)

    ## To view purchase order
    # @api.multi
    def open_rfq_view(self):
        # res = self.env['ir.actions.act_window'].for_xml_id('purchase', 'purchase_form_action')
        res = self.env.ref('purchase.purchase_form_action')
        purchase_order_ids = self.env['purchase.order'].search([('sale_id', '=', self.id)])
        res['domain'] = [('id', 'in', purchase_order_ids.ids)]
        return res

    # To create Contract
    # @api.multi
    def create_contract(self):
        if self.contract_count != 1:
            lease_id = self.env['contract.order']
            project_id = self.env['project.project'].search([('sale_order_id', '=', self.id)])
            values = {
                'sale_order_id': self.id,
                'partner_id': self.partner_id.id,
                'Contract_po_reference': self.contract_lpo_test,
                'sale_type': self.sale_type,
                'project_id': project_id.id,
            }
            lease = lease_id.create(values)
            if lease:
                sale_order_line = self.env['sale.order.line'].search([('order_id', '=', self.id)])
                for line_val in sale_order_line:
                    line_value = {
                        'product_id': line_val.product_id.id,
                        'product_uom_qty': line_val.product_uom_qty,
                        'price_unit': line_val.price_unit,
                        'price_subtotal': line_val.price_subtotal,
                        'name': line_val.name,
                        'product_uom': line_val.product_id.uom_id.id,
                        'contract_id': lease.id,

                    }
                    self.env['device.details.line'].create(line_value)
        else:
            raise UserError(_("You Can Create Only One Contract For This Sale Order"))

    # To count Contract
    # @api.multi
    def count_contract(self):
        for rec in self:
            rec.contract_count = len(self.env["contract.order"].search([('sale_order_id', '=', rec.id)]).ids)

    # To view Contract
    # @api.multi
    def open_contract(self):
        if self._context is None:
            context = {}
        # res = self.env['ir.actions.act_window'].for_xml_id('fms_sale', 'contract_order_action')
        res = self.env.ref('fms_sale.contract_order_action')
        res['context'] = self._context
        lease_ids = self.env['contract.order'].search([('sale_order_id', '=', self.id)])
        res['domain'] = [('id', 'in', lease_ids.ids)]
        return res

    # To create project
    # @api.multi
    def create_project(self):
        company = self.env['res.company']._company_default_get('sale.order')
        if self.sale_type in ['lease', 'rental'] or self.purchase_type == 'project':
            self.write({'show_project': True})
            project_id = self.env['project.project']
            values = {
                'name': self.name,
                'partner_id': self.partner_id.id,
                'sale_type': self.sale_type,
                'sale_order_id': self.id,
            }
            project_id.create(values)
        for order in self.filtered(lambda x: x.state == 'sale' and not company.keep_name_so):
            if order.origin and order.origin != '':
                quo = order.origin + ', ' + order.name
            else:
                quo = order.name
            order.write({
                'origin': quo,
                'name': self.env['ir.sequence'].next_by_code('sale.order')
            })

    # To view project ##
    # @api.multi
    def open_project_view(self):
        if self._context is None:
            context = {}
        # res = self.env['ir.actions.act_window'].for_xml_id('fms_sale', 'sale_project_action_id')
        res = self.env.ref('fms_sale.sale_project_action_id')
        res['context'] = self._context
        project_ids = self.env['project.project'].search([('sale_order_id', '=', self.id)])
        res['domain'] = [('id', 'in', project_ids.ids)]
        return res

    # To count project ##
    # @api.multi
    def count_project(self):
        for rec in self:
            rec.project_count = len(self.env["project.project"].search([('sale_order_id', '=', rec.id)]).ids)

    # Inherited this function to create project ##
    # @api.multi
    def confirm_order(self):
        self.write({'state': 'sale'})
        self.tree_qty = sum(self.order_line.filtered(lambda x: x.product_id.type == 'product').mapped('product_uom_qty'))
        self.create_project()

    ## To View Division Invoice ##
    # @api.multi
    def open_division_invoice(self):
        # res = self.env['ir.actions.act_window'].for_xml_id('fms_sale', 'division_invoice_action')
        res = self.env.ref('fms_sale.division_invoice_action')
        project_id = self.env['division.invoice'].search([('sale_order_id', '=', self.id)])
        res['domain'] = [('id', 'in', project_id.ids)]
        return res

    ## To Count Division Invoice ##
    # @api.multi
    def count_invoice(self):
        for rec in self:
            rec.division_invoice_count = len(self.env["division.invoice"].search([('sale_order_id', '=', rec.id)]).ids)

    ## Send Alert Notification For Pending Orders ##
    # @api.multi
    def email_alert_for_pending_order(self):
        send_mail = self.env['mail.mail']
        mail_ids = []
        mail_template = self.env['mail.template']
        obj1 = self.env['res.users'].search([])
        sale_obj = self.env['sale.order'].search([('state', '!=', 'sale')])
        list_obj = []
        for i in sale_obj:
            alert_time = i.validity
            dt = date.today() - timedelta(int(alert_time))
            date_obj = dt
            res = datetime.strptime(str(i.date_order), ('%Y-%m-%d %H:%M:%S')).date()
            if res == date_obj:
                for user in i.responsible_person_ids:
                    rec = user.email
                    email_to = rec
                    subject = 'Sale Order Notification'
                    body = _("Dear Sir/Madam,</br>")
                    body += _(
                        "<br/> Sale Order No. - %s is waiting for your Approval, Kindly approve it as soon as possible." % (
                        i.name))
                    footer = "</br>By,<br/>Administrator<br/>"
                    mail_ids.append(send_mail.create({
                        'email_to': email_to,
                        'subject': subject,
                        'body_html':
                            '''<span  style="font-size:14px"><br/>
                            <br/>%s</span>
                            <br/>%s</span>
                            <br/><br/>''' % (body, footer),
                    }))
                for i in range(len(mail_ids)):
                    mail_ids[i].send(self)

    ## To create Subscription ##
    # @api.multi
    def subscription_create(self):
        job_card_ids = self.env['job.card'].search([('sale_order_id', '=', self.id)])
        picking_id = self.env['stock.picking'].search([('sale_id', '=', self.id)], limit=1)
        for job in job_card_ids.filtered(lambda x: x.state != 'done'):
            if picking_id and picking_id.state != 'done':
                templ_id = self.env['sale.order.template'].search([('name', '=', 'Yearly')])
                if self.count_subscription != 1:
                    if self.env.user.has_group('account.group_account_manager') or self.env.user.has_group('account.group_account_invoice'):
                        subscription_obj = self.env['sale.order']
                        today_date = datetime.strptime(str(datetime.now().date()), '%Y-%m-%d')
                        subscription_date = today_date + relativedelta(years=1)
                        values = {
                            'sale_order_id': self.id,
                            'partner_id': self.partner_id.id,
                            'code': 'SUB/' + self.name,
                            'template_id': templ_id.id,
                            'date_start': subscription_date,
                            'sale_type': self.sale_type,
                            'subscription_period': self.contract_period,
                            'is_subscription': True,
                        }
                        sale_subscription = subscription_obj.create(values)
                        if sale_subscription:
                            for line_val in self.order_line.filtered(lambda x: x.product_id.hosting_charges == True):
                                line_value = {
                                    'product_id': line_val.product_id.id,
                                    'quantity': 1,
                                    'price_unit': line_val.price_unit,
                                    'price_subtotal': line_val.price_subtotal,
                                    'name': line_val.name,
                                    'uom_id': line_val.product_id.uom_id.id,
                                    'analytic_account_id': sale_subscription.id,
                                }
                                self.env['sale.order.line'].create(line_value)
                    else:
                        raise UserError(_("Only Account Persons Can Create The Subscription"))
                else:
                    raise UserError(_("You Can Create Only One Subscription"))
            else:
                raise UserError(_("Job card and DC should be in done state"))

    ## To View Subscription ##
    # @api.multi
    def open_subscription_view(self):
        if self._context is None:
            context = {}
        # res = self.env['ir.actions.act_window'].for_xml_id('sale_subscription', 'sale_subscription_action')
        res = self.env.ref('sale_subscription.sale_subscription_action')
        res['context'] = self._context
        subscription_obj = self.env['sale.order'].search([('sale_order_id', '=', self.id), ('is_subscription', '=', True)])
        res['domain'] = [('id', 'in', subscription_obj.ids)]
        return res

    ## To Count Subscription ##
    # @api.multi
    def subscription_counts(self):
        for rec in self:
            rec.count_subscription = len(self.env["sale.order"].search([('sale_order_id', '=', rec.id)]).ids)

    # @api.multi
    def _get_invoice_status(self):
        for rec in self:
            line_obj = self.env['sale.order.line'].search([('order_id', '=', rec.id)])
            product_qty = 0
            for line in line_obj.filtered(lambda x: x.product_id.type == 'product'):
                product_qty += line.product_uom_qty
            rec.tree_qty = product_qty
            if rec.sale_type in ['lease', 'rental'] or rec.purchase_type == 'project':
                invoice_obj = self.env['account.move'].search([('invoice_origin', '=', rec.name), ('state', '=', 'posted')])

                inv_line = self.env['account.move.line'].search([('move_id', 'in', invoice_obj.ids), ('product_id.type', '=', 'product')])

                subscription_obj_count = len(
                    self.env['sale.order'].search([('sale_order_id', '=', rec.id), ('stage_id.category', '=', 'progress'), ('is_subscription', '=', True)]).ids)
                job_card_count = len(
                    self.env['job.card'].search([('sale_order_id', '=', rec.id), ('state', '=', 'done')]).ids)

                sale_line_obj = self.env['sale.order.line'].search(
                    [('order_id', '=', rec.id), ('product_id.type', '=', 'product')])

                picking_obj = len(
                    self.env['stock.picking'].search([('origin', '=', rec.name), ('state', '=', 'done')]).ids)
                self.env.cr.execute(
                    """update sale_order set invoiced_qty=%s where id=%s""" % (sum(inv_line.mapped('quantity')), rec.id))

                self.env.cr.execute(
                    """update sale_order set delivered_qty=%s where id=%s""" % (sum(sale_line_obj.mapped('qty_delivered')), rec.id))
                self.env.cr.execute(
                    """update sale_order set subscription_qty=%s where id=%s""" % (subscription_obj_count, rec.id))
                if picking_obj == 0:
                    self.env.cr.execute(
                        """update sale_order set account_invoice_status = 'to_be_delivered' where id=%s""" % rec.id)
                elif product_qty != job_card_count and picking_obj == product_qty:
                    self.env.cr.execute(
                        """update sale_order set account_invoice_status = 'to_be_installed' where id=%s""" % rec.id)
                elif product_qty == job_card_count and product_qty != subscription_obj_count:
                    self.env.cr.execute(
                        """update sale_order set account_invoice_status = 'to_be_invoiced' where id=%s""" % rec.id)
                elif product_qty == job_card_count and product_qty == subscription_obj_count and picking_obj == product_qty:
                    self.env.cr.execute(
                        """update sale_order set account_invoice_status = 'invoiced' where id=%s""" % rec.id)
            else:
                job_card_count = len(
                    self.env['job.card'].search([('sale_order_id', '=', rec.id), ('state', '=', 'done')]).ids)
                invoice_obj = self.env['account.move'].search([('invoice_origin', '=', rec.name), ('state', '=', 'posted')])
                subscription_obj_count = len(
                    self.env['sale.order'].search([
                        ('sale_order_id', '=', rec.id),
                        ('stage_id.category', '=', 'progress'),('is_subscription', '=', True)
                    ]).ids)
                inv_line = self.env['account.move.line'].search([('move_id', 'in', invoice_obj.ids), ('product_id.type', '=', 'product')])

                picking_obj = self.env['stock.picking'].search([('sale_id', '=', rec.id), ('state', '=', 'done')])
                line_obj = self.env['sale.order.line'].search([('order_id', '=', rec.id), ('product_id.type', '=', 'product')])
                self.env.cr.execute(
                    """update sale_order set subscription_qty=%s where id=%s""" % (subscription_obj_count, rec.id))
                self.env.cr.execute(
                            """update sale_order set delivered_qty=%s where id=%s""" % (sum(line_obj.mapped('qty_delivered')), rec.id))
                self.env.cr.execute(
                            """update sale_order set invoiced_qty=%s where id=%s""" % (sum(rec.order_line.mapped('qty_invoiced')), rec.id))
                # rec.invoiced_qty = sum(rec.order_line.mapped('qty_invoiced'))
                if not picking_obj:
                    self.env.cr.execute(
                        """update sale_order set account_invoice_status = 'to_be_delivered' where id=%s""" % (rec.id))
                elif picking_obj and job_card_count != product_qty:
                    self.env.cr.execute(
                        """update sale_order set account_invoice_status = 'to_be_installed' where id=%s""" % (rec.id))
                elif job_card_count == product_qty and not invoice_obj:
                    self.env.cr.execute(
                        """update sale_order set account_invoice_status = 'to_be_invoiced' where id=%s""" % (rec.id))
                elif picking_obj and job_card_count == product_qty and invoice_obj:
                    self.env.cr.execute(
                        """update sale_order set account_invoice_status = 'invoiced' where id=%s""" % (rec.id))
            job_card_count = len(self.env['job.card'].search([('sale_order_id', '=', rec.id), ('state', '=', 'done')]).ids)
            self.env.cr.execute("""update sale_order set installed_device_count = %s where id=%s""" % (job_card_count, rec.id))

    # @api.multi
    def create_jobcard(self):
        job_card_obj = self.env['job.card']
        job_card_obj.create({'sale_order_id': self.id, 'job_card_type': 'sale'})

    # To View Job card ##
    # @api.multi
    def open_jobcard_view(self):
        var = []
        subscription_ids = self.env['job.card'].search([('sale_order_id', '=', self.id)])
        return {
            'name': _('Job Card'),
            'type': 'ir.actions.act_window',
            # 'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'job.card',
            'domain': [('id', 'in', subscription_ids.ids)],
        }

    # To Count Job Card ##
    # @api.multi
    def job_card_counts(self):
        for rec in self:
            rec.count_card = len(self.env["job.card"].search([('sale_order_id', '=', rec.id)]).ids)

    # Open Job Card Wizard
    # @api.multi
    def open_job_card_wizard(self):
        qty = []
        view_id = self.env.ref('fms_sale.job_card_wizard').id
        for line in self.order_line.filtered(lambda x: x.product_id.type == 'product'):
            qty.append(line.product_uom_qty)
        return {
            'name': _('Create Job Card'),
            'type': 'ir.actions.act_window',
            # 'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'job.card.wizard',
            'views': [(view_id, 'form')],
            'view_id': view_id,
            'context': {'default_no_of_devices': sum(qty), 'default_origin': self.name},
            'target': 'new',
        }

    job_card_wizard = open_job_card_wizard

    @api.onchange('partner_id')
    # @api.depends('partner_id')
    def _get_contact_names(self):
        if self.partner_id:
            return {'domain': {'res_contact_id': [('id', 'in', self.partner_id.child_ids.ids)]}}

    name = fields.Char(string='Order Reference', required=True, copy=False, readonly=True,
             states={'draft': [('readonly', False)]}, index=True, default=lambda self: _('New'), track_visibility='always')
    sale_type = fields.Selection([('cash', 'Walk In/Cash Sale'),
                                  ('purchase', 'Unit Sale'),
                                  ('lease', 'Lease Sale'),
                                  ('rental', 'Rental Sale'),
                                  ('pilot', 'Renewal Sale'),
                                  ('training', 'GSTI Training Sales'),
                                  ], string='Sale Type', required=True)
    purchase_type = fields.Selection([('project', 'Project'),
                                      ('non_project', 'Non-Project'),
                                      ], string='Purchase Type',default='non_project')
    po_count = fields.Integer(compute='count_po', string="Purchase Request")
    project_count = fields.Integer(compute='count_project', string="Project")
    rfq_count = fields.Integer(compute='count_rfq', string="RFQ")
    show_po = fields.Boolean('PO')
    show_rfq = fields.Boolean('RFQ')
    show_project = fields.Boolean('Project')
    contract_lpo_test = fields.Binary(string="Contract LPO Test")
    file_name = fields.Char('Filename')
    validity = fields.Integer("Sale Order Validity")
    responsible_person_ids = fields.Many2many("res.users", string="Responsible Persons")
    division_wise_billing = fields.Boolean('Division Wise Billing')
    division_invoice_count = fields.Integer(compute="count_invoice", string="Division Bill")
    count_subscription = fields.Integer(compute='subscription_counts', string="Subscriptions")
    contract_count = fields.Integer(compute='count_contract', string="Contract")
    contract_period = fields.Selection([
        ('12', '12'),
        ('18', '18'),
        ('24', '24'),
        ('30', '30'),
        ('36', '36'),
        ('42', '42'),
        ('48', '48'),
        ('54', '54'),
        ('60', '60'),
    ], string='Contract Period In Months', default='12')
    addons_accessories_line = fields.One2many('addons.line', 'sale_order_id', string="Addons Accessories")
    installed_device_count = fields.Integer(string="Installed", compute='get_invoice_status', store=True)
    agreement_date = fields.Date("Agreement Date")
    # new_invoice_status = fields.Selection([
    #     ('partial', 'Partial Invoice'),
    #     ('fully', 'Fully Invoiced'),
    #     ('no', 'To be Invoiced')
    # ], string='Invoice Status', compute='get_invoice_status', default='no')
    account_invoice_status = fields.Selection([
        ('to_be_delivered', 'To be delivered'),
        ('to_be_installed', 'Delivered,To be installed'),
        ('to_be_invoiced', 'Installed,To be invoiced'),
        ('invoiced', 'Invoiced')
    ], string='Order Status',default='to_be_delivered')
    product_qty = fields.Float("Product Quantity")
    tree_qty = fields.Integer("Quantity", compute='get_invoice_status', store=True)
    addons_service_line = fields.One2many('addons.service.line', 'sale_order_id', string="Addons Services")
    report_payment_terms_line = fields.One2many('payment.terms.line', 'sale_order_id', string="Payment Terms")
    report_warranty_line = fields.One2many('warrant.line', 'sale_order_id', string="Warranty")
    contract_period_report_line = fields.One2many('contract.period.line', 'sale_order_id', string="Contract Period")
    delivery_installation_schedule = fields.One2many('delivery.installation.line', 'sale_order_id', string="Delivery Installation Line")
    report_service_support = fields.One2many('service.support.line', 'sale_order_id', string="Service Support")
    other_information_line = fields.One2many('other.line', 'sale_order_id', string="Others")
    report_validity = fields.One2many('validity.line', 'sale_order_id', string="Validity")
    count_card = fields.Integer(compute='job_card_counts', string="Job Card")
    customer_location = fields.Char(string="Customer Location", related="partner_id.city", store=True)
    title = fields.Char(string="Opportunity Name",  store=True)
    invoiced_qty = fields.Integer("Invoiced", compute='get_invoice_status', store=True)
    delivered_qty = fields.Integer("Delivered", compute='get_invoice_status', store=True)
    subscription_qty = fields.Integer("Subscription")
    subscription_template_id = fields.Many2one('sale.order.template', 'Subscription Template')
    contract_reference = fields.Char(string="Contract Reference")
    purchase_order_no = fields.Char("PO #")
    purchase_order_date = fields.Date("PO Date")
    state = fields.Selection([
        ('draft', 'Quotation'),
        ('sent', 'Quotation Sent'),
        ('submit', 'Submitted'),
        ('sale', 'Sales Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'),
    ], string='Status', readonly=True, copy=False, index=True, track_visibility='onchange', default='draft')
    sign_quotation = fields.Many2one('res.users', string='Signature For Quotation', index=True, track_visibility='onchange', default=lambda self: self.env.user)
    res_contact_id = fields.Many2one('res.partner', string='Contact')
    title_name = fields.Many2one('res.partner.title')
    is_reseller = fields.Boolean("Reseller", default=False, store=True, related='partner_id.is_reseller')
    vehicle_number_ids = fields.Many2many('vehicle.master', string="Vehicle Numbers")


class DivisionInvoice(models.Model):
    _name = "division.invoice"

    # @api.one
    @api.depends('division_invoice_line_ids.price_subtotal')
    def _compute_amount(self):
        for rec in self:
            amount_untaxed = 0
            amount_untaxed += sum(line.price_subtotal for line in rec.division_invoice_line_ids)
            rec.amount_untaxed = amount_untaxed
            rec.amount_total = amount_untaxed

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('division.invoice') or _('New')
        result = super(DivisionInvoice, self).create(vals)
        return result

    # update Invoice List
    @api.onchange('from_date', 'to_date', 'partner_id')
    def onchange_invoice(self):
        self.invoice_ids = ''
        if self.partner_id and self.from_date and self.to_date:
            invoice_ids = self.env['account.move'].search([('invoice_date', '>=', self.from_date), ('date_invoice', '<=', self.to_date)])
            inv_list_ids = invoice_ids.filtered(lambda x: x.state == 'open' and x.partner_id == self.partner_id)
            self.update({'invoice_ids': inv_list_ids.ids})

    # Update Job Card List
    @api.onchange('engineer_ids', 'partner_id')
    def onchange_job_card(self):
        if self.engineer_ids:
            card_list = []
            emp_obj = self.env['hr.employee'].search([('id', 'in', self.engineer_ids.ids)])
            for emp in emp_obj:
                resource_obj = self.env['resource.resource'].search([('id', '=', emp.resource_id.id)])
                user_obj = self.env['res.users'].search([('id', '=', resource_obj.user_id.id)])
                for res in user_obj:
                    job_card_obj = self.env['job.card'].search([('engineer_id', '=', res.id)])
                    for job_card in job_card_obj:
                        card_list.append(job_card.id)
            self.update({'job_card_ids': card_list})
        elif self.partner_id:
            job_card_obj = self.env['job.card'].search([('company_id', '=', self.partner_id.id)])
            card_list = []
            for job in job_card_obj:
                card_list.append(job.id)
            self.update({'job_card_ids': card_list})
        else:
            card_list = []
            self.update({'job_card_ids': card_list})

    # @api.multi
    @api.onchange('invoice_ids', 'job_card_ids')
    def update_invoice_details(self):
        self.division_invoice_line_ids = ''
        if self.invoice_type == "consolidated":
            data = []
            for inv in self.invoice_ids:
                inv_line_obj = self.env['account.move.line'].search([('move_id', '=', inv.id)])
                for line_vals in inv_line_obj:
                    line_value = {
                        'invoice_id': False,
                        'product_id': line_vals.product_id.id,
                        'product_uom_qty': line_vals.quantity,
                        'price_unit': line_vals.price_unit,
                        'price_subtotal': inv.amount_total,
                        'name': ' ',
                        'product_uom': line_vals.uom_id.id,
                        'account_analytic_id': None,
                        'analytic_tag_ids': None,
                    }
                    data.append(line_value)
            self.update({'division_invoice_line_ids': data})
            values = []
            for line_obj in self.job_card_ids:
                subscription_obj = self.env['sale.order'].search([('job_card_id', '=', line_obj.id), ('is_subscription', '=', True)])
                for subscription in subscription_obj:
                    line_val = {
                        'name': line_obj.vehicle_description,
                        'chassis_no': line_obj.chassis_no,
                        'device_type_id': line_obj.device_id.id,
                        'installation_location': line_obj.installation_location_id.id,
                        'vehicle_number': subscription.vehicle_number,
                        'device_serial_no_id': subscription.serial_no.id,
                        'sim_no': subscription.gsm_number,
                        'installation_date': subscription.installation_date,
                        'subscription_status': subscription.subscription_status,
                        'partner_id': subscription.partner_id.id,
                        'amount': subscription.recurring_total,
                    }
                    values.append(line_val)
                self.update({'prorate_invoice_line': values})

    name = fields.Char("Invoice Reference")
    partner_id = fields.Many2one("res.partner", "Customer Name")
    shipping_address_id = fields.Many2one("res.partner", "Delivery Address")
    invoicing_address_id = fields.Many2one("res.partner", "Invoicing Address")
    invoice_date = fields.Date("Invoice Date", default=fields.datetime.now())
    due_date = fields.Date("Due Date", default=fields.datetime.now())
    salesperson_id = fields.Many2one("res.users", "Sales Person")
    division_invoice_line_ids = fields.One2many('division.invoice.line', 'invoice_id', string='Invoice Lines')
    sale_order_id = fields.Many2one("sale.order", "Sale Reference")
    order_ids = fields.Many2many("sale.order", 'sale_order_rel', 'sale_id', string="Sale Reference")
    amount_untaxed = fields.Float(string='Untaxed Amount',
                                  store=True, compute='_compute_amount', track_visibility='always',
                                  digits=dp.get_precision('Discount'))
    amount_total = fields.Float(string='Total',
                                store=True, compute='_compute_amount', digits=dp.get_precision('Discount'))
    currency_id = fields.Many2one('res.currency', help='The currency used to enter statement', string="Currency",
                                  default=lambda self: self.env.user.company_id.currency_id)
    company_id = fields.Many2one('res.company', string='Company', index=True,
                                 default=lambda self: self.env.user.company_id,
                                 help="Company related to this journal")
    prorate_invoice_line = fields.One2many('prorate.invoice.details', 'division_id', string='Prorate Invoice Details')
    invoice_type = fields.Selection(
        [('prorate', 'Prorate'), ('division', 'Division Wise'), ('consolidated', 'Consolidated')],string='Invoice Type',default='consolidated')
    sub_partner_ids = fields.Many2many("res.partner", string="Sub Partners")
    from_date = fields.Date("From")
    to_date = fields.Date("To")
    invoice_ids = fields.Many2many('account.move', string='Invoice')
    engineer_ids = fields.Many2many('hr.employee', string='Engineer')
    state = fields.Selection([('draft', 'Draft'),
                              ('confirmed', 'Confirmed')], default='draft',
                             string="States")
    job_card_ids = fields.Many2many('job.card', string='Job Card')

    # @api.multi
    def to_confirm(self):
        self.write({'state': 'confirmed'})


class DivisionInvoiceLine(models.Model):
    _name = "division.invoice.line"

    name = fields.Text(string='Description')
    price_unit = fields.Float('Unit Price', default=0.0, digits=dp.get_precision('Discount'))
    price_subtotal = fields.Float(string='Subtotal', digits=dp.get_precision('Discount'))
    product_id = fields.Many2one('product.product', string='Product')
    product_uom_qty = fields.Float(string='Quantity')
    product_uom = fields.Many2one('uom.uom', string='Unit of Measure')
    invoice_id = fields.Many2one("division.invoice", "Invoice Reference")
    account_analytic_id = fields.Many2one('account.analytic.account', string='Analytic Account')
    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Tags')


class AddonsLine(models.Model):
    _name = "addons.line"

    sale_order_id = fields.Many2one('sale.order', 'Sale Order Reference')
    name = fields.Text(string='Description')
    price_unit = fields.Monetary('Unit Price', default=0.0)
    currency_id = fields.Many2one(related='sale_order_id.currency_id', store=True, string='Currency', readonly=True)
    price_subtotal = fields.Monetary(string='Subtotal', compute='compute_price_subtotal')
    product_id = fields.Many2one('product.product', string='Product')
    product_uom_qty = fields.Integer(string='Quantity')
    product_uom = fields.Many2one('uom.uom', string='Unit of Measure')
    account_analytic_id = fields.Many2one('account.analytic.account', string='Analytic Account')
    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Tags')
    tax_id = fields.Many2many('account.tax', string='Taxes', domain=['|', ('active', '=', False), ('active', '=', True)])
    discount = fields.Float(string='Discount (%)', digits=dp.get_precision('Discount'), default=0.0)

    # @api.one
    @api.depends('product_uom_qty', 'price_unit')
    def compute_price_subtotal(self):
        for rec in self:
            rec.price_subtotal = rec.product_uom_qty * rec.price_unit

    @api.onchange('product_id')
    def onchange_product_details(self):
        if self.product_id:
            self.update({
                'price_unit': self.product_id.lst_price,
                'product_uom': self.product_id.uom_id,
                'name': self.product_id.description,
            })


class ProrateInvoiceDetails(models.Model):
    _name = "prorate.invoice.details"

    name = fields.Char('Vehicle Name')
    vehicle_number = fields.Many2one('vehicle.master', 'Vehicle Number')
    device_type_id = fields.Many2one('product.product', 'Device Type')
    device_serial_no_id = fields.Many2one('stock.lot', 'Device Serial Number')
    chassis_no = fields.Char('Chassis no')
    sim_no = fields.Char('SIM no')
    installation_date = fields.Date('Installation Date')
    subscription_status = fields.Selection([('active', 'Active'), ('in_active', 'Inactive')], string="Device Status", default='in_active')
    installation_location = fields.Many2one('installation.location', "Location")
    division_id = fields.Many2one('division.invoice', string='Division Reference')
    partner_id = fields.Many2one('res.partner', 'Company-Division')
    amount = fields.Float('Amount')


class AddonsServiceLine(models.Model):
    _name = "addons.service.line"

    sale_order_id = fields.Many2one('sale.order', 'Sale Order Reference')
    product_id = fields.Many2one('product.product', string='Product')
    name = fields.Text(string='Description')
    currency_id = fields.Many2one(related='sale_order_id.currency_id', store=True, string='Currency', readonly=True)
    price_unit = fields.Monetary('Unit Price', default=0.0)
    product_uom_qty = fields.Integer(string='Quantity')
    product_uom = fields.Many2one('uom.uom', string='Unit of Measure')
    price_subtotal = fields.Monetary(string='Subtotal', compute='compute_price_subtotal')

    # @api.one
    @api.depends('product_uom_qty', 'price_unit')
    def compute_price_subtotal(self):
        for rec in self:
            rec.price_subtotal = rec.product_uom_qty * rec.price_unit

    @api.onchange('product_id')
    def onchange_product(self):
        if self.product_id:
            self.update({
                'price_unit': self.product_id.lst_price,
                'name': self.product_id.description,
            })


class PaymentTermsLine(models.Model):
    _name = "payment.terms.line"

    sale_order_id = fields.Many2one('sale.order', 'Sale Order Reference')
    name = fields.Text(string=' ')


class WarrantyLine(models.Model):
    _name = "warrant.line"

    sale_order_id = fields.Many2one('sale.order', 'Sale Order Reference')
    name = fields.Text(string=' ')


class ContractPeriodLine(models.Model):
    _name = "contract.period.line"

    sale_order_id = fields.Many2one('sale.order', 'Sale Order Reference')
    name = fields.Text(string=' ')


class DeliveryInstallationLine(models.Model):
    _name = "delivery.installation.line"

    sale_order_id = fields.Many2one('sale.order', 'Sale Order Reference')
    name = fields.Text(string='Name')


class ServiceSupportLine(models.Model):
    _name = "service.support.line"

    sale_order_id = fields.Many2one('sale.order', 'Sale Order Reference')
    name = fields.Text(string='Name')


class OtherLine(models.Model):
    _name = "other.line"

    sale_order_id = fields.Many2one('sale.order', 'Sale Order Reference')
    name = fields.Text(string='Name')


class ValidityLine(models.Model):
    _name = "validity.line"

    sale_order_id = fields.Many2one('sale.order', 'Sale Order Reference')
    name = fields.Text(string='Name')


class TermsandConditions(models.Model):
    _name = 'terms.conditions'

    name = fields.Char('Name', required=True)
    sale_type = fields.Selection([('cash', 'Walk In/Cash Sale'),
                                  ('purchase', 'Unit Sale'),
                                  ('lease', 'Lease Sale'),
                                  ('rental', 'Rental Sale'),
                                  ('pilot', 'Renewal Sale'),
                                  ], string='Sale Type', required=True)
    tc_paymentterms_line = fields.One2many('paymentterms.tc', 'so_ref_id', ondelete= 'cascade', string="Payment Terms")
    tc_warranty_line = fields.One2many('warranty.tc', 'so_ref_id', ondelete= 'cascade', string="Warranty")
    tc_contract_period = fields.One2many('contract.period.tc', 'so_ref_id', string="Contract Period")
    tc_delivery_installation = fields.One2many('delivery.installation.tc', 'so_ref_id', string="Delivery Installation Line")
    tc_service_support = fields.One2many('service.support.tc', 'so_ref_id', string="Service Support")
    tc_validity = fields.One2many('validity.tc', 'so_ref_id', string="Validity")
    tc_other = fields.One2many('other.tc', 'so_ref_id', string="Other")
    
    _sql_constraints = [
        ('sale_type', 'UNIQUE (sale_type)', 'You can not have two records for the same sale type !'),]
    

class TCPaymentterms(models.Model):
    _name = "paymentterms.tc"

    so_ref_id = fields.Many2one('terms.conditions', string='Sale Order Reference')
    name = fields.Text(string='Terms & Conditions')


class TCWarranty(models.Model):
    _name = "warranty.tc"

    so_ref_id = fields.Many2one('terms.conditions', string='Sale Order Reference')
    name = fields.Text(string='Terms & Conditions')


class TCContract(models.Model):
    _name = "contract.period.tc"

    so_ref_id = fields.Many2one('terms.conditions', string='Sale Order Reference')
    name = fields.Text(string='Terms & Conditions')


class TCDeliveryInstallation(models.Model):
    _name = "delivery.installation.tc"

    so_ref_id = fields.Many2one('terms.conditions', string='Sale Order Reference')
    name = fields.Text(string='Terms & Conditions')


class TCServiceSupport(models.Model):
    _name = "service.support.tc"

    so_ref_id = fields.Many2one('terms.conditions', string='Sale Order Reference')
    name = fields.Text(string='Terms & Conditions')


class TCValidity(models.Model):
    _name = "validity.tc"

    so_ref_id = fields.Many2one('terms.conditions', string='Sale Order Reference')
    name = fields.Text(string='Terms & Conditions')


class TCOther(models.Model):
    _name = "other.tc"

    so_ref_id = fields.Many2one('terms.conditions', string='Sale Order Reference')
    name = fields.Text(string='Terms & Conditions')


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.depends('invoice_lines.move_id.state', 'invoice_lines.quantity')
    def _get_invoice_qty(self):
        """
        Compute the quantity invoiced. If case of a refund, the quantity invoiced is decreased. Note
        that this is the case only if the refund is generated from the SO and that is intentional: if
        a refund made would automatically decrease the invoiced quantity, then there is a risk of reinvoicing
        it automatically, which may not be wanted at all. That's why the refund has to be created from the SO
        """
        for line in self:
            qty_invoiced = 0.0
            for invoice_line in line.invoice_lines:
                if invoice_line.move_id.state not in ['cancel', 'draft']:
                    if invoice_line.move_id.move_type == 'out_invoice':
                        qty_invoiced += invoice_line.uom_id._compute_quantity(invoice_line.quantity, line.product_uom)
                    elif invoice_line.move_id.move_type == 'out_refund':
                        qty_invoiced -= invoice_line.uom_id._compute_quantity(invoice_line.quantity, line.product_uom)
            line.qty_invoiced = qty_invoiced