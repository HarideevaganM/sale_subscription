from odoo import api, fields, models, _
from datetime import datetime


class ContractOrder(models.Model):
    _name = 'contract.order'
    
    # CRONJOB FOR RENEWAL LIST
    # @api.multi
    def cron_renewal(self):
        con = self.env['contract.order'].search([])
        for contract in con:
            if contract.contract_end_date:
                current_date = datetime.now().date()
                self.env.cr.execute(""" SELECT DATE_PART('day', '%s'::timestamp - '%s'::timestamp)"""%(contract.contract_end_date,current_date))
                dates = self.env.cr.dictfetchall()
                for val in dates:
                    if 30.0 >= val['date_part'] >= 0.00:
                        self.env.cr.execute("""SELECT contract_id FROM renewal_list""")
                        renew_lists = list(list_renew for list_renew,in self.env.cr.fetchall())
                        if contract.id not in renew_lists:
                            values = {
                                'is_renew': True,
                                'contract_id': contract.id,
                                'partner_id': contract.partner_id.id,
                                'contract_from_date': contract.contract_start_date,
                                'contract_to_date':contract.contract_end_date,
                                'project_id': contract.project_id.id,
                                'sale_order_id': contract.sale_order_id.id,
                                'name': 'Upcoming Renewal',
                                'sale_type': contract.sale_order_id.sale_type
                                  }

                            self.env['renewal.list'].create(values)
        sub = self.env['sale.order'].search([('is_subscription', '=', True)])
        for subscription in sub:
            if subscription.date:
                current_date = datetime.now().date()
                self.env.cr.execute(
                    """ SELECT DATE_PART('day', '%s'::timestamp - '%s'::timestamp)""" % (
                        subscription.date, current_date))
                dates = self.env.cr.dictfetchall()
                for val in dates:
                    if 30.0 >= val['date_part'] >= 0.00:
                        self.env.cr.execute("""SELECT subscription_id FROM subscription_list""")
                        sub_renew_lists = list(list_renew for list_renew, in self.env.cr.fetchall())
                        if subscription.id not in sub_renew_lists:
                            values = {
                                'is_sub_renew': True,
                                'subscription_id': subscription.id,
                                'partner_id': subscription.partner_id.id,
                                'subscription_from_date': subscription.date_start,
                                'subscription_to_date': subscription.date,
                                'template_id': subscription.template_id.id,
                                'sale_order_id': subscription.sale_order_id.id,
                                'name': 'Upcoming Renewal',
                                'validate_date': subscription.validation_date,
                                'vehicle_id': subscription.vehicle_number.id,
                                'serial_no': subscription.serial_no.id,
                                'validate_by': subscription.user_id.id
                            }
                            self.env['subscription.list'].create(values)

    # CRONJOB FOR MAIL FOR RENEWAL LIST
    # @api.multi
    def renewal_mail(self):
        send_mail = self.env['mail.mail']
        send_ids = []
        mail_ids = []
        mail_template = self.env['mail.template']
        # dt = datetime.now().date()
        obj = self.env['renewal.list'].search([('is_renew', '=', True)])
        if obj:
            subject = 'Renewal Intimation'
            body = _("Dear Customer,</br>")
            body += _("<br/> Please Renew the sale.")
            footer = "</br>With Regards,<br/>Admin<br/>"
            self.env.cr.execute(
                '''SELECT email FROM res_partner''')
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

        self.env.cr.execute("""SELECT rl.contract_to_date,so.sale_type,rp.name as rp_name,co.name FROM contract_order co
                                JOIN renewal_list rl ON (co.id=rl.contract_id)
                                JOIN sale_order so on (so.id=rl.sale_order_id)
                                JOIN res_partner rp on (rp.id=rl.partner_id)""")
        con = self.env.cr.dictfetchall()
        for contract in con:

            current_date = datetime.now().date()
            self.env.cr.execute(""" SELECT DATE_PART('day', '%s'::timestamp - '%s'::timestamp)""" % (
                contract['contract_to_date'], current_date))
            dates = self.env.cr.dictfetchall()
            for val in dates:
                if 30.0 == val['date_part'] and contract['sale_type']=='rental':
                    subject = 'Renewal Intimation'
                    body = _("Dear Customer,</br>")
                    body += _("<br/> Please Renew the sale Order.")
                    body += contract['name']
                    body += contract['rp_name']
                    footer = "</br>With Regards,<br/>Admin<br/>"
                    self.env.cr.execute(
                        '''SELECT email FROM res_partner''')
                    vas = self.env.cr.dictfetchall()
                    for res in vas:
                        mail_ids.append(send_mail.create({
                            'email_to': res['email'],
                            'subject': subject,
                            'body_html':
                                '''<span  style="font-size:14px"><br/>
                                <br/>%s</span>
                                <br/>%s</span>
                                <br/><br/>''' % (body, footer),
                        }))

                        for i in range(len(mail_ids)):
                            mail_ids[i].send(self)    

    # @api.multi
    def write(self, vals):
        project_obj = self.env["project.project"].search([('id', '=', self.project_id.id)])
        res = super(ContractOrder, self).write(vals)
        return res
    
    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('contract.order') or _('New')
        result = super(ContractOrder, self).create(vals)
        return result            

    name = fields.Char("Serial Number",readonly=True)
    state = fields.Selection(string="State", selection=[('to_renew', 'To Renew'),
                                                        ('cancel', 'Cancel'),
                                                        ('renewed', 'Renewed'),
                                                        ('in_progress', 'In Progress'),
                                                        ('quotation', 'Quotation Sent'),
                                                        ('expired', 'Expired')], required=False, default='to_renew')
    device_details_line = fields.One2many('device.details.line', 'contract_id', "Device details /product")
    installation_date = fields.Datetime("Installation date")
    contract_start_date = fields.Date(string="Contract Start Date")
    contract_end_date = fields.Date(string="Contract End Date")
    project_id = fields.Many2one("project.project", 'Project')
    sale_order_id = fields.Many2one("sale.order", string="Order Reference")
    partner_id = fields.Many2one("res.partner", "Customer Name")
    Contract_po_reference = fields.Binary("Contract PO")
    installation_street = fields.Char('Street')
    installation_street2 = fields.Char('Street2')
    installation_zip = fields.Char('Zip', size=24)
    installation_city = fields.Char('City')
    installation_state_id = fields.Many2one("res.country.state", 'State', ondelete='restrict')
    installation_country_id = fields.Many2one('res.country', 'Country', ondelete='restrict')

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
    sale_type = fields.Selection([('cash', 'Walk In/Cash Sale'),
                                  ('purchase', 'Purchase Sale'),
                                  ('lease', 'Lease Sale'),
                                  ('rental', 'Rental Sale'),
                                  ('service', 'Service')], string='Sale Type', default='cash')


class DeviceDetailsLine(models.Model):
    _name = 'device.details.line'
    
    contract_id = fields.Many2one("contract.order", "Contract Refernce")
    sale_id = fields.Many2one("sale.order", string="Order Reference")
    name = fields.Text(string='Description')
    price_unit = fields.Float('Unit Price', default=0.0)
    price_subtotal = fields.Float(string='Subtotal', readonly=True)
    product_id = fields.Many2one('product.product', string='Product')
    product_uom_qty = fields.Float(string='Quantity')
    product_uom = fields.Many2one('uom.uom', string='Unit of Measure')
