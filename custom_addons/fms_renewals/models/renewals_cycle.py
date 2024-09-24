# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, AccessError,ValidationError


from datetime import datetime
# import datetime as dt
from dateutil import parser
from dateutil.relativedelta import relativedelta
from odoo.addons import decimal_precision as dp
class RenewalContract(models.Model):
    _name='renewal.contract'
    _rec_name='name'
    name=fields.Char("Name",default=('New'))
    state = fields.Selection(string="State", selection=[('to_renew', 'To Renew')
        ,('cancel','Cancelled')
        ,('renewed','Renewed')
        ,('in_progress','In Progress')
        ,('quotation','Quotation Sent')
        ,('expired','Expired')],default='to_renew')
    sale_order_id = fields.Many2one('sale.order', string="Order Reference")
    partner_id = fields.Many2one('res.partner', string="Customer")
    contract_id = fields.Many2one("contract.order", string="Contract")
    project_id = fields.Many2one('project.project', string="Project")
    start_date=fields.Date("Contract Start Date")
    end_date=fields.Date("Contract End Date")
    renew_from_date = fields.Date(string="Renewal From Date")
    renew_to_date = fields.Date(string="Renewal To Date")
    currency_id = fields.Many2one('res.currency')

    renewal_line=fields.One2many('renewal.contract.line','line_id',string="Renewal Line")
    # amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True, readonly=True,
    #                                  track_visibility='onchange')

    invoice_date = fields.Date(string="Invoice Date", required=False,default=fields.Date.today )
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env['res.company']._company_default_get('account.move'))
    sale_type = fields.Selection([
        ('cash', 'Walk In/Cash Sale'),
        ('purchase', 'Purchase Sale'),
        ('lease', 'Lease Sale'),
        ('rental', 'Rental Sale'),
    ], string='Sale Type',compute='sales_type',store=True)
    user_id = fields.Many2one("res.users", string="Engineer")
    is_direct_payment = fields.Boolean("Is Direct Payment")
    quotation_count=fields.Integer('Quotation')
    contract_count=fields.Integer("Contract")





    #COMPUTE FOR SALES TYPE
    @api.depends('sale_order_id')
    def sales_type(self):
        if self.sale_order_id:
            self.sale_type=self.sale_order_id.sale_type

    #ONCHANGE FOR CONTRACT
    @api.onchange('contract_id')
    def onchange_contract_id(self):
        if self.contract_id:
            self.end_date=self.contract_id.contract_end_date
            self.sale_order_id=self.contract_id.sale_order_id
            self.project_id=self.contract_id.project_id
            self.start_date=self.contract_id.contract_start_date
            self.partner_id=self.contract_id.partner_id
            self.currency_id=self.company_id.currency_id

    #CREATE FOR RENEWAL SEQUENCE
    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('renewal.contract') or _('New')
        result = super(RenewalContract, self).create(vals)
        return result



    #FUNCTION FOR CONFIRM RENEWAL
    #@api.multi
    def to_confirm(self):
        renewal_list=self.env['renewal.list'].search([('contract_id','=',self.contract_id.id)])
        if renewal_list:
            if self.renew_from_date and self.renew_to_date:
                if self.state=='to_renew':
                    self.write({'state':'in_progress'})
                    renewal_list.state='in_progress'
                    self.contract_id.state='in_progress'

            else:
                raise ValidationError("Please Select Renew From Date and To Date")


    #SALE ORDER VIEW
    #@api.multi
    def renewal_contract_view(self):
        if self._context is None:
            context = {}
        obj = self.env["ir.actions.act_window"].for_xml_id("sale", 'action_orders')
        obj['context'] = self._context
        sale_order = self.env["sale.order"].search([('name', '=', "Renewal Order "+self.sale_order_id.name)]).ids
        obj['domain'] = [('id', 'in', sale_order)]
        return obj



    #EXISTING RENEWAL
    #@api.multi
    def contract_view(self):
        if self._context is None:
            context = {}
        obj = self.env["ir.actions.act_window"].for_xml_id("fms_sale", 'contract_order_action')
        obj['context'] = self._context
        project = self.env["project.project"].search([('id', '=', self.project_id.id)]).ids
        obj['domain'] = [('id', 'in', project)]
        return obj


    #CONFIRM RENEWAL PROCESS
    def confirm_renewal(self):

        renewal_list=self.env['renewal.list'].search([('contract_id','=',self.contract_id.id)])
        if renewal_list:
            if self.state=='in_progress' and self.is_direct_payment==False:
                self.quotation_count = 1
                self.state='quotation'
                self.contract_id.state='quotation'
                renewal_list.state='quotation'

                vals = {'name':"Renewal Order "+self.sale_order_id.name,
                        'partner_id': self.partner_id.id,
                        'sale_type': self.sale_type,
                        'state': 'draft',
                        'id': self.sale_order_id.id,
                        'date_order': datetime.now().date(),
                        }
                sale = self.env['sale.order'].create(vals)
                sale_order = self.env['sale.order.line'].search([('order_id','=',self.sale_order_id.id)])
                for sales in sale_order:
                    line = {'order_id': sale.id,
                            'product_id': sales.product_id.id,

                            'product_uom': sales.product_uom.id,
                            'price_unit': sales.price_unit,
                            'price_subtotal':sales.price_subtotal,
                            }
                    self.env['sale.order.line'].create(line)



            elif self.state=='in_progress' and self.is_direct_payment==True:
                self.state='renewed'
                self.contract_id.state='renewed'
                renewal_list.state='renewed'
                contract=self.env['contract.order'].search([('sale_order_id','=',self.sale_order_id.id)])
                if contract:
                    values={
                            'contract_start_date':self.renew_from_date,
                            'project_id':self.project_id.id,
                            'contract_end_date':self.renew_to_date,
                            'check_renewal_type':'existing',
                            'sale_order_id':self.sale_order_id.id,
                            'partner_id' : self.partner_id.id,
                            'installation_street':self.contract_id.installation_street,
                            'installation_street2':self.contract_id.installation_street2,
                            'installation_city':self.contract_id.installation_city,
                            'installation_state_id':self.contract_id.installation_state_id.id,
                            'installation_zip':self.contract_id.installation_zip,
                            'installation_country_id':self.contract_id.installation_country_id.id,
                            'sale_type':self.contract_id.sale_type
                            }


                    con=self.env['contract.order'].create(values)
                    contract = self.env['device.details.line'].search([('contract_id', '=', self.contract_id.id)])
                    for line_val in contract:

                        line_value = {
                            'product_id': line_val.product_id.id,
                            'product_uom_qty': line_val.product_uom_qty,
                            'price_unit': line_val.price_unit,
                            'price_subtotal': line_val.price_subtotal,
                            'name': line_val.name,
                            'product_uom': line_val.product_id.uom_id.id,
                            'contract_id': con.id,

                        }

                        self.env['device.details.line'].create(line_value)
                self.renewal_history()
                self.renewal_confirmed()
            # self.create_subscription()

    #history of renewals
    #@api.multi
    def renewal_history(self):
        self.env.cr.execute("""SELECT co.id,co.contract_start_date,co.contract_end_date,dd.product_uom_qty,dd.price_unit FROM contract_order co
                                JOIN project_project pp ON (co.project_id=pp.id)
                                JOIN device_details_line dd ON (dd.contract_id=co.id)
                                 WHERE pp.id=%d  and co.state='renewed'"""%(self.project_id.id))
        renewal=self.env.cr.dictfetchall()
        ids=self.env['renewal.contract'].browse(self.id)
        for val in renewal:
            history={'line_id':ids.id,
                    'contract_id':val['id'],
                     'contract_start_date':val['contract_start_date'],
                     'contract_end_date':val['contract_end_date'],
                     'quantity':val['product_uom_qty'],
                     'total':val['price_unit']}
            self.env['renewal.contract.line'].create(history)

    #@api.multi
    def renewal_confirmed(self):
        send_mail = self.env['mail.mail']
        send_ids = []
        mail_ids = []
        mail_template = self.env['mail.template']
        # dt = datetime.now().date()
        obj = self.env['renewal.contract'].search([('is_direct_payment', '=', True)])
        if obj:
            subject = 'Renewal Confirmation'
            body = _("Dear Customer,</br>")
            body += _("<br/>Your Contract Has Been Created")
            footer = "</br>With Regards,<br/>Admin<br/>"
            self.env.cr.execute(
                '''SELECT email FROM res_partner where id=%d''' % (self.partner_id.id))

            vas = self.env.cr.dictfetchall()
            for res in vas:
                send_ids.append(send_mail.create({
                    'email_to': res['email'],
                    'subject': subject,
                    'body_html':
                        '''<span  style="font-size:14px"><br/>
                        <br/>%s</span>
                        <br/>%s</span>
                        <br/><br/>''' % (body, footer),
                }))
                for i in range(len(send_ids)):
                    send_ids[i].send(self)
        users = self.env['res.users'].search([])
        for i in users:
            if i.has_group('sales_team.group_sale_manager'):
                email_to = i.partner_id.email

                subject = 'Renewal Intimation'
                body = _("Dear Manager,</br>")
                body += _("<br/> Contract Created ")
                # footer = "</br>By,<br/>%s<br/>" % (reb)
                mail_ids.append(send_mail.create({
                    'email_to': email_to,
                    'subject': subject,
                    'body_html':
                        '''<span  style="font-size:14px"><br/>
                        <br/>%s</span>

                        ''' % (body),
                }))
            for i in range(len(mail_ids)):
                mail_ids[i].send(self)

class RenewalContractLine(models.Model):
    _name='renewal.contract.line'
    line_id=fields.Many2one('renewal.contract','Line')
    contract_id = fields.Many2one("contract.order", string="Contract")
    contract_start_date = fields.Date(string="Start Date", required=False, )
    contract_end_date = fields.Date(string="End Date", required=False, )
    quantity = fields.Float(string="Quantity",  required=False, )
    currency_id = fields.Many2one(related='line_id.currency_id', store=True, string='Currency', readonly=True)
    total = fields.Float("Total Amount", store=True, readonly=True)

    #ONCHANGE FOR PRODUCT ID
    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.description=self.product_id.name
            self.product_uom=self.product_id.uom_id.id
            self.price_unit=self.product_id.lst_price

class RenewalList(models.Model):
    _name='renewal.list'
    name=fields.Char("Name")
    state = fields.Selection(string="State", selection=[('to_renew', 'To Renew')
        , ('cancel', 'Cancelled')
        , ('renewed', 'Renewed')
        , ('in_progress', 'In Progress')
        , ('quotation', 'Quotation Sent')
        , ('expired', 'Expired'),('owned','Owned'),('notified client','Notified Client'),('client respond','Client Responded')], default='to_renew')
    project_id=fields.Many2one("project.project","Project")
    contract_from_date = fields.Date(string="Contract Start Date")
    contract_to_date = fields.Date(string="Contract End Date")
    sale_order_id=fields.Many2one("sale.order",'Order Reference')
    is_renew = fields.Boolean(string="Is Renew",store=True)
    invoice_date = fields.Date(string="Invoice Date", required=False, default=fields.Date.today)
    is_expired=fields.Boolean(string='Expired',store=True)
    contract_id = fields.Many2one(comodel_name="contract.order", string="Contract", required=False, )

    partner_id = fields.Many2one("res.partner", string="Partner")
    renewal_count=fields.Integer("Renewal",compute='compute_renewal_count')
    removal_count = fields.Integer("Count")
    sale_type = fields.Selection([
        ('cash', 'Walk In/Cash Sale'),
        ('purchase', 'Purchase Sale'),
        ('lease', 'Lease Sale'),
        ('rental', 'Rental Sale'),
    ], string='Sale Type', store=True)
    Contract_po_reference = fields.Binary("Contract PO")
    remaining_days=fields.Integer("Remaining Days",compute='compute_remaining_days',store=True)
    billing_cycle_type = fields.Selection([('quarterly', 'Quarterly'),
                                           ('monthly', 'Monthly'),
                                           ('half', 'Half Yearly'),
                                           ('annual', 'Annual')], string='Billing Cycle')

    billing_date = fields.Selection([('beginning', 'Beginning of month'),
                                     ('mid', 'Mid month'),
                                     ('end', 'End of the month')], string='Billing Date')

    credit_period = fields.Date("Credit Period")
    check_renewal_type = fields.Selection([('new', 'New'),
                                           ('existing', 'Existing Renewal')], string="Contract Type")

    direct_partner_type = fields.Selection([('direct', 'Direct'),
                                            ('partner', 'Partner')], string="Direct/Partner Sale")
    product_ownership_period = fields.Char("Ownership Period")

    division_billing = fields.Boolean("Division Wise Billing")
    contract_line = fields.One2many('contract.renewal.list', 'renewal_id', "Device details /product")
    installation_date = fields.Datetime("Installation date")
    installation_street = fields.Char('Street')
    installation_street2 = fields.Char('Street2')
    installation_zip = fields.Char('Zip', size=24)
    installation_city = fields.Char('City')
    installation_state_id = fields.Many2one("res.country.state", 'State', ondelete='restrict')
    installation_country_id = fields.Many2one('res.country', 'Country', ondelete='restrict')

    @api.depends('contract_to_date')
    def compute_remaining_days(self):
        for rec in self:
            if rec.state == 'to_renew':
                current_date = datetime.now().date()
                contract_end_date = parser.parse(rec.contract_to_date).date()
                self.env.cr.execute("""SELECT TRUNC(DATE_PART('day', '%s'::timestamp - '%s'::timestamp));"""%(contract_end_date,current_date))
                remaining_date=self.env.cr.dictfetchall()
                for remain in remaining_date:
                    rec.remaining_days=remain['trunc']
                    if rec.remaining_days<0:
                        self.env.cr.execute("""UPDATE renewal_list set is_renew=False WHERE id=%d"""%(rec.id))
                        rec.state='expired'

    #@api.multi
    def respond_to_customer(self):
        self.state = 'notified client'
        send_mail = self.env['mail.mail']
        send_ids = []
        mail_ids = []
        mail_template = self.env['mail.template']
        # dt = datetime.now().date()
        obj = self.env['renewal.list'].search([('is_renew', '=', True)])
        if obj:
            subject = 'Renewal Intimation'
            body = _("Dear Customer,</br>")
            body += _("<br/> Please Renew the Contract.")
            footer = "</br>With Regards,<br/>Admin<br/>"
            self.env.cr.execute(
                '''SELECT email FROM res_partner where id=%d''' % (self.partner_id.id))
            vas = self.env.cr.dictfetchall()
            for res in vas:
                send_ids.append(send_mail.create({
                    'email_to': res['email'],
                    'subject': subject,
                    'body_html':
                        '''<span  style="font-size:14px"><br/>
                        <br/>%s</span>
                        <br/>%s</span>
                        <br/><br/>''' % (body, footer),
                }))
                for i in range(len(send_ids)):
                    send_ids[i].send(self)

    #@api.multi
    def customer_respond(self):
        if self.state == 'notified client':
            self.state = 'client respond'


    # #COMPUTE FOR SALES TYPE
    # @api.depends('sale_order_id')
    # def sales_type(self):
    #     for sale in self:
    #         if sale.sale_order_id:
    #             sale.sale_type = sale.sale_order_id.sale_type

    # CALCULATED LENGTH IN SMART BUTTON
    @api.model
    def compute_renewal_count(self):
        var = self.env['renewal.contract'].search([('contract_id', '=', self.contract_id.id)])
        if var:
            self.renewal_count = len(var)
    # COMPUTE FOR EXPIRY
    # @api.depends('contract_to_date')
    # def compute_expired(self):
    #     current_date = datetime.now().date()
    #     for rec in self:
    #         if rec.contract_to_date:
    #             date_1 = (datetime.strptime(rec.contract_to_date, '%Y-%m-%d') + relativedelta(days=+ 30))
    #             if date_1.date()> current_date:
    #                 rec.is_expired =True
    #                 rec.state='expired'


    #RENEWAL VIEW
    #@api.multi
    def renewal_view(self):
        if self._context is None:
            context = {}

        obj = self.env["ir.actions.act_window"].for_xml_id("fms_renewals", 'renewal_cycle_action')

        obj['context'] = self._context

        contract = self.env["renewal.contract"].search([('contract_id', '=', self.contract_id.id)]).ids

        obj['domain'] = [('id', 'in', contract)]

        return obj

    #RENEWAL CREATION
    #@api.multi
    def create_renewal(self):
        if self.state=='client respond':
            self.state='in_progress'
            vals={'contract_id':self.contract_id.id,
                  'sale_order_id':self.sale_order_id.id,
                  'partner_id':self.partner_id.id,
                  'project_id':self.project_id.id,
                  'start_date':self.contract_from_date,
                  'end_date':self.contract_to_date}
            order=self.env['renewal.contract'].create(vals)

    #RENEWAL REJECT
    #@api.multi
    def reject_renewal(self):

        self.removal_count = 1
        self.contract_id.state = 'cancel'
        self.state = 'cancel'
        vals = {'name': "Removal Order "+self.sale_order_id.name,
                'partner_id': self.partner_id.id,
                'sale_type': self.sale_type,
                'state': 'sale',
                'confirmation_date': datetime.now().date(),
                }
        sale = self.env['sale.order'].create(vals)
        sale_order = self.env['sale.order.line'].search([('order_id', '=', self.sale_order_id.id)])
        for sales in sale_order:
            line = {'order_id': sale.id,
                    'product_id': sales.product_id.id,
                    'product_uom': sales.product_uom.id,
                    'price_unit': sales.price_unit,
                    'price_subtotal': sales.price_subtotal,
                    }
            order = self.env['sale.order.line'].create(line)
        self.cancel_renewal()



    # ACTION VIEW FOR SALE ORDER
    #@api.multi
    def sale_view(self):
        if self._context is None:
            context = {}
        obj = self.env["ir.actions.act_window"].for_xml_id("sale", 'action_orders')
        obj['context'] = self._context
        sale_id = self.env["sale.order"].search([('name', '=', "Removal Order "+self.sale_order_id.name)]).ids
        obj['domain'] = [('id', 'in', sale_id)]
        return obj

    #Transfer Ownership Function For Lease to own
    #@api.multi
    def transfer_ownership(self):
        current_date = datetime.now().date()
        # contract_end_date = parser.parse(self.contract_to_date).date()
        # if current_date > contract_end_date:
        sale = self.env['sale.order'].search([('id', '=', self.sale_order_id.id)])
        self.state = 'owned'

        picking_type_obj = self.env["stock.picking.type"].search([('picking_code', '=', 'DO')])
        location = self.env["stock.location"].search([('location_code', '=', 'CUS')])
        source_location = self.env["stock.location"].search([('location_code', '=', 'WH/L')])
        self.state = 'owned'

        if sale:
            vals = {

                'partner_id': self.partner_id.id,
                'scheduled_date': datetime.now().date(),
                'origin': self.sale_order_id.name,
                'location_id': source_location.id,
                'location_dest_id': location.id,
                'picking_type_id': picking_type_obj.id,

            }

            stock = self.env['stock.picking'].create(vals)

            stock_existing_id = self.env['stock.picking'].search([('sale_id', '=', self.sale_order_id.id)])
            stock_move = self.env['stock.move'].search([('picking_id', '=', stock_existing_id.id)])

            for line_val in stock_move:
                line_value = {
                    'product_id': line_val.product_id.id,
                    'name': line_val.product_id.name,
                    'product_uom_qty': line_val.product_uom_qty,
                    'product_uom': line_val.product_id.uom_id.id,
                    'location_id':  source_location.id,
                    'location_dest_id': location.id,
                    'picking_id': stock.id,
                }

                self.env['stock.move'].create(line_value)
            self.env.cr.execute(
                """UPDATE stock_picking set sale_id =%d where id=%d""" % (self.sale_order_id.id, stock.id))

            self.env.cr.execute(""" UPDATE procurement_group set name='%s'""" % self.sale_order_id.name)
        self.confirm_renewal_mail()
        # else:
        #     raise ValidationError("Contract Period is not completed")

    #@api.multi
    def cancel_renewal(self):
        send_mail = self.env['mail.mail']
        send_ids = []
        mail_ids = []
        mail_template = self.env['mail.template']
        # dt = datetime.now().date()
        obj = self.env['renewal.list'].search([('is_renew', '=', True)])
        if obj:
            subject = 'Renewal Confirmation'
            body = _("Dear Customer,</br>")
            body += _("<br/>Your Contract Has Been Cancelled")
            footer = "</br>With Regards,<br/>Admin<br/>"
            self.env.cr.execute(
                '''SELECT email FROM res_partner where id=%d''' % (self.partner_id.id))

            vas = self.env.cr.dictfetchall()
            for res in vas:
                send_ids.append(send_mail.create({
                    'email_to': res['email'],
                    'subject': subject,
                    'body_html':
                        '''<span  style="font-size:14px"><br/>
                        <br/>%s</span>
                        <br/>%s</span>
                        <br/><br/>''' % (body, footer),
                }))
                for i in range(len(send_ids)):
                    send_ids[i].send(self)
        users = self.env['res.users'].search([])
        for i in users:
            if i.has_group('sales_team.group_sale_manager'):
                email_to = i.partner_id.email

                subject = 'Cancel Intimation'
                body = _("Dear Manager,</br>")
                body += _("<br/> Product Removed ")
                # footer = "</br>By,<br/>%s<br/>" % (reb)
                mail_ids.append(send_mail.create({
                    'email_to': email_to,
                    'subject': subject,
                    'body_html':
                        '''<span  style="font-size:14px"><br/>
                        <br/>%s</span>

                        ''' % (body),
                }))
            for i in range(len(mail_ids)):
                mail_ids[i].send(self)

    #@api.multi
    def confirm_renewal_mail(self):
        send_mail = self.env['mail.mail']
        send_ids = []
        mail_ids = []
        mail_template = self.env['mail.template']
        # dt = datetime.now().date()
        obj = self.env['renewal.list'].search([('is_renew', '=', True)])
        if obj:
            subject = 'Renewal Confirmation'
            body = _("Dear Customer,</br>")
            body += _("<br/>Transferred OwnerShip")
            footer = "</br>With Regards,<br/>Admin<br/>"
            self.env.cr.execute(
                '''SELECT email FROM res_partner where id=%d''' % (self.partner_id.id))

            vas = self.env.cr.dictfetchall()
            for res in vas:
                send_ids.append(send_mail.create({
                    'email_to': res['email'],
                    'subject': subject,
                    'body_html':
                        '''<span  style="font-size:14px"><br/>
                        <br/>%s</span>
                        <br/>%s</span>
                        <br/><br/>''' % (body, footer),
                }))
                for i in range(len(send_ids)):
                    send_ids[i].send(self)
        users = self.env['res.users'].search([])
        for i in users:
            if i.has_group('sales_team.group_sale_manager'):
                email_to = i.partner_id.email

                subject = 'Renewal Intimation'
                body = _("Dear Manager,</br>")
                body += _("<br/> Product Owned ")
                # footer = "</br>By,<br/>%s<br/>" % (reb)
                mail_ids.append(send_mail.create({
                    'email_to': email_to,
                    'subject': subject,
                    'body_html':
                        '''<span  style="font-size:14px"><br/>
                        <br/>%s</span>

                        ''' % (body),
                }))
            for i in range(len(mail_ids)):
                mail_ids[i].send(self)
class RenewalContractList(models.Model):
    _name='contract.renewal.list'
    renewal_id=fields.Many2one("renewal.list","Renewal")
    sale_id = fields.Many2one("sale.order", string="Order Reference")
    name = fields.Text(string='Description')
    price_unit = fields.Float('Unit Price', default=0.0)
    price_subtotal = fields.Float(string='Subtotal', readonly=True)
    product_id = fields.Many2one('product.product', string='Product')
    product_uom_qty = fields.Float(string='Quantity')
    product_uom = fields.Many2one('product.uom', string='Unit of Measure')


class SubscriptionList(models.Model):
    _name='subscription.list'
    name = fields.Char("Name")
    state = fields.Selection(string="State", selection=[('to_renew', 'To Renew')
        , ('cancel', 'Cancelled')
        , ('renewed', 'Renewed')
        , ('in_progress', 'In Progress')
        , ('expired', 'Expired'),('notified client','Notified Client'),('client respond','Client Responded')], default='to_renew')
    subscription_from_date = fields.Date(string="Start Date")
    subscription_to_date = fields.Date(string="End Date")
    subscription_id=fields.Many2one('sale.order','Subscription', domain=[('is_subscription', '=', True)])
    sale_order_id = fields.Many2one("sale.order", 'Order Reference')
    code=fields.Char("Code")
    is_sub_renew = fields.Boolean(string="Is Renew", store=True)
    invoice_date = fields.Date(string="Invoice Date", required=False, default=fields.Date.today)
    is_expired = fields.Boolean(string='Expired', store=True)

    partner_id = fields.Many2one("res.partner", string="Partner")
    # renewal_count = fields.Integer("Renewal", compute='compute_renewal_count')
    # removal_count = fields.Integer("Count")
    sale_type = fields.Selection([
        ('cash', 'Walk In/Cash Sale'),
        ('purchase', 'Purchase Sale'),
        ('lease', 'Lease Sale'),
        ('rental', 'Rental Sale'),
    ], string='Sale Type', store=True)
    remaining_days = fields.Integer("Remaining Days", compute='compute_days_remaining',store=True)
    subscription_renew_date_from=fields.Date("Renewal From Date")
    subscription_renew_date_to=fields.Date("Renewal To Date")
    vehicle_id=fields.Many2one("vehicle.master","Vehicle")
    serial_no=fields.Many2one("stock.lot","Device Serial No")
    validate_date=fields.Date("Validation Date")
    validate_by=fields.Many2one("res.users","Validated By")
    note=fields.Text("Text")
    template_id = fields.Many2one(comodel_name="sale.order.template", string="Subscription Template", required=True, )
    recurring_date = fields.Date(string="Date Of Next Invoice", required=False, default=fields.Date.today)
    invoice_type = fields.Selection([('post', 'Post Invoice'), ('pre', 'Previous Inovice'), ('mid', 'Others')],
                                    'Invoice Type')
    start_date = fields.Date('Period Start Date')
    end_date = fields.Date('Period End Date')
    subscription_line = fields.One2many(comodel_name="subscription.list.line", inverse_name="analytic_account_id", string="Subscription", required=False, )
    tag_ids = fields.Many2many('account.analytic.tag', string='Tags')
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account')
    recurring_total = fields.Float(compute='_compute_recurring_total', string="Recurring Price", store=True,
                                   track_visibility='onchange')

    @api.depends('subscription_line', 'subscription_line.quantity',
                 'subscription_line.price_subtotal')
    def _compute_recurring_total(self):
        for account in self:
            account.recurring_total = sum(line.price_subtotal for line in account.subscription_line)


    @api.depends('subscription_to_date')
    def compute_days_remaining(self):
        for vals in self:
            if vals.state == 'to_renew' or vals.state=='notified client':
                current_date = datetime.now().date()
                contract_end_date = parser.parse(vals.subscription_to_date).date()
                self.env.cr.execute("""SELECT TRUNC(DATE_PART('day', '%s'::timestamp - '%s'::timestamp));""" % (
                contract_end_date, current_date))
                remaining_date = self.env.cr.dictfetchall()
                for remain in remaining_date:
                    vals.remaining_days = remain['trunc']
                    if vals.remaining_days < 0:
                        self.env.cr.execute("""UPDATE subscription_list set is_renew=False WHERE id=%d""" % (vals.id))
                        vals.state = 'expired'



    #@api.multi
    def respond_to_customer(self):
        self.state='notified client'
        send_mail = self.env['mail.mail']
        send_ids = []
        mail_ids = []
        mail_template = self.env['mail.template']
        # dt = datetime.now().date()
        obj = self.env['subscription.list'].search([('is_sub_renew', '=', True)])
        if obj:
            subject = 'Renewal Intimation'
            body = _("Dear Customer,</br>")
            body += _("<br/> Please Renew the Subscription.")
            footer = "</br>With Regards,<br/>Admin<br/>"
            self.env.cr.execute(
                '''SELECT email FROM res_partner where id=%d'''%(self.partner_id.id))

            vas = self.env.cr.dictfetchall()
            for res in vas:
                send_ids.append(send_mail.create({
                    'email_to': res['email'],
                    'subject': subject,
                    'body_html':
                        '''<span  style="font-size:14px"><br/>
                        <br/>%s</span>
                        <br/>%s</span>
                        <br/><br/>''' % (body, footer),
                }))
                for i in range(len(send_ids)):
                    send_ids[i].send(self)
    # #@api.multi
    # def create_subscription_renewal(self):
    #
    #     sale=self.env['sale.order'].search([('id','=',self.sale_order_id.id)])
    #     if sale:
    #         self.state='renewed'
    #         vals={'partner_id':self.partner_id.id,
    #               'template_id':self.subscription_id.template_id.id,
    #               'pricelist_id':self.subscription_id.pricelist_id.id,
    #               'date_start':self.subscription_renew_date_from,
    #               'date':self.subscription_renew_date_to,
    #               'sale_order_id':self.sale_order_id.id,
    #               'serial_no': self.subscription_id.serial_no.id,
    #               'job_card_id':self.subscription_id.job_card_id.id
    #               }
    #         sales=self.env['sale.order'].create(vals)
    #         sale_subscription_line=self.env['sale.order.line'].search([('analytic_account_id','=',self.subscription_id.id)])
    #         if sale_subscription_line:
    #             for sale_line in sale_subscription_line:
    #                 values={
    #                     'analytic_account_id':sales.id,
    #                     'product_id':sale_line.product_id.id,
    #                     'name':sale_line.product_id.name,
    #                     'quantity':sale_line.quantity,
    #                     'price_unit':sale_line.price_unit,
    #                     'price_subtotal':sale_line.price_subtotal,
    #                     'uom_id':sale_line.uom_id.id
    #                 }
    #                 self.env['sale.order.line'].create(values)
    #     self.confirm_subscription()
    #@api.multi
    def confirm_subscription(self):
        send_mail = self.env['mail.mail']
        send_ids = []
        mail_ids = []
        mail_template = self.env['mail.template']
        # dt = datetime.now().date()
        obj = self.env['subscription.list'].search([('is_sub_renew', '=', True)])
        if obj:
            subject = 'Renewal Confirmation'
            body = _("Dear Customer,</br>")
            body += _("<br/> Subscription Has Been Renewed")
            footer = "</br>With Regards,<br/>Admin<br/>"
            self.env.cr.execute(
                '''SELECT email FROM res_partner where id=%d''' % (self.partner_id.id))

            vas = self.env.cr.dictfetchall()
            for res in vas:
                send_ids.append(send_mail.create({
                    'email_to': res['email'],
                    'subject': subject,
                    'body_html':
                        '''<span  style="font-size:14px"><br/>
                        <br/>%s</span>
                        <br/>%s</span>
                        <br/><br/>''' % (body, footer),
                }))
                for i in range(len(send_ids)):
                    send_ids[i].send(self)
        users = self.env['res.users'].search([])
        for i in users:
            if i.has_group('sales_team.group_sale_manager'):
                email_to = i.partner_id.email

                subject = 'Renewal Intimation'
                body = _("Dear Manager,</br>")
                body += _("<br/> Renewed ")
                # footer = "</br>By,<br/>%s<br/>" % (reb)
                mail_ids.append(send_mail.create({
                    'email_to': email_to,
                    'subject': subject,
                    'body_html':
                        '''<span  style="font-size:14px"><br/>
                        <br/>%s</span>

                        ''' % (body),
                }))
            for i in range(len(mail_ids)):
                mail_ids[i].send(self)

    #@api.multi
    def customer_respond(self):
        if self.state=='notified client':
            self.state='client respond'



class SubscriptionListLine(models.Model):
    _name = 'subscription.list.line'
    product_id = fields.Many2one('product.product', string='Product', domain="[('recurring_invoice','=',True)]",
                                 required=True)
    analytic_account_id = fields.Many2one('subscription.list', string='Subscription')
    name = fields.Text(string='Description', required=True)
    quantity = fields.Float(string='Quantity', help="Quantity that will be invoiced.", default=1.0)
    uom_id = fields.Many2one('product.uom', string='Unit of Measure', required=True)
    price_unit = fields.Float(string='Unit Price', required=True, digits=dp.get_precision('Product Price'))
    discount = fields.Float(string='Discount (%)', digits=dp.get_precision('Discount'))
    price_subtotal = fields.Float( string='Sub Total',compute='_compute_price_subtotal',
                                  digits=dp.get_precision('Account'))

    @api.depends('price_unit', 'quantity', 'discount')
    def _compute_price_subtotal(self):
        for line in self:
            line_sudo = line.sudo()
            price = line.env['account.tax']._fix_tax_included_price(line.price_unit, line_sudo.product_id.taxes_id, [])
            line.price_subtotal = line.quantity * price * (100.0 - line.discount) / 100.0


    @api.onchange('product_id', 'quantity')
    def onchange_product_id(self):
        domain = {}
        subscription = self.analytic_account_id
        # company_id = subscription.company_id.id
        # pricelist_id = subscription.pricelist_id.id
        context = dict(self.env.context, quantity=self.quantity)
        if not self.product_id:
            self.price_unit = 0.0
            domain['uom_id'] = []
        else:
            partner = subscription.partner_id.with_context(context)
            if partner.lang:
                context.update({'lang': partner.lang})

            product = self.product_id.with_context(context)
            self.price_unit = product.price

            name = product.display_name
            if product.description_sale:
                name += '\n' + product.description_sale
            self.name = name

            if not self.uom_id:
                self.uom_id = product.uom_id.id
            if self.uom_id.id != product.uom_id.id:
                self.price_unit = product.uom_id._compute_price(self.price_unit, self.uom_id)
            domain['uom_id'] = [('category_id', '=', product.uom_id.category_id.id)]

        return {'domain': domain}

    @api.onchange('uom_id')
    def onchange_uom_id(self):
        if not self.uom_id:
            self.price_unit = 0.0
        else:
            self.onchange_product_id()

    def _get_template_option_line(self):
        """ Return the account.analytic.invoice.line.option which has the same product_id as
        the invoice line"""
        if not self.analytic_account_id and not self.analytic_account_id.template_id:
            return False
        template = self.analytic_account_id.template_id
        return template.sudo().subscription_template_option_ids.filtered(lambda r: r.product_id == self.product_id)

    def _amount_line_tax(self):
        self.ensure_one()
        val = 0.0
        product = self.product_id
        product_tmp = product.sudo().product_tmpl_id
        for tax in product_tmp.taxes_id.filtered(lambda t: t.company_id == self.analytic_account_id.company_id):
            fpos_obj = self.env['account.fiscal.position']
            partner = self.analytic_account_id.partner_id
            fpos_id = fpos_obj.with_context(force_company=self.analytic_account_id.company_id.id).get_fiscal_position(partner.id)
            fpos = fpos_obj.browse(fpos_id)
            if fpos:
                tax = fpos.map_tax(tax, product, partner)
            compute_vals = tax.compute_all(self.price_unit * (1 - (self.discount or 0.0) / 100.0), self.analytic_account_id.currency_id, self.quantity, product, partner)['taxes']
            if compute_vals:
                val += compute_vals[0].get('amount', 0)
        return val











