from odoo import fields, models, api, _
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError


class ITCPermit(models.Model):
    _name = 'itc.permit'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'ITC Permit'
    _rec_name = 'vehicle_no'
    _order = 'name desc'

    name = fields.Char(string='ITC Permit No', track_visibility='onchange')
    sale_order_id = fields.Many2one('sale.order', string="Sale Order")
    partner_id = fields.Many2one(related='sale_order_id.partner_id', string="Client Name", readonly=True, store=True)
    po_number = fields.Char(related='sale_order_id.purchase_order_no', string='PO Number', readonly=True)
    po_date = fields.Date(related='sale_order_id.purchase_order_date', string='PO Date', readonly=True)
    traffic_code_no = fields.Char(string='Traffic Code No')
    chassis_no = fields.Char(string='Chassis No')
    vehicle_no = fields.Many2one('vehicle.master', string="Vehicle No")
    device_no = fields.Char(string='Device No')
    sim_card_no = fields.Char(string='SIM Card No')
    trailer_no = fields.Char(string='Trailer No')
    trailer_chassis_no = fields.Char(string='Trailer Chassis No')
    state = fields.Selection([('draft', 'Pending'),
                              ('applied', 'Applied'),
                              ('done', 'Active'),
                              ('expired', 'Expired'),
                              ('cancel', 'Cancelled')], default='draft', track_visibility='onchange')
    vehicle_status = fields.Char(string='Vehicle Status')
    permit_start_date = fields.Date(string='Start Date', track_visibility='onchange')
    permit_end_date = fields.Date(string='Expiry Date', track_visibility='onchange')
    remarks = fields.Text(string='Remarks')
    invoice_no = fields.Many2one('account.move', string='Invoice Number', track_visibility='onchange')
    job_card_id = fields.Many2one('job.card', string='Job Card No')
    cancel_reason = fields.Text(string='Cancel Reason', track_visibility='onchange')
    sale_subscription_id = fields.Many2one('sale.order', string='Subscription No',  domain=[('is_subscription', '=', True)])
    subscription_end_date = fields.Date(string="Subscription End Date")
    device_id = fields.Many2one('stock.lot', string="Device ID")
    request_number = fields.Char(string='Request Number', track_visibility='onchange')
    free_permit = fields.Boolean(string='Free Permit', default=False)

    # Function to update the status if it is expired.
    def itc_expired_update(self):
        now = datetime.now()
        current_date = now.strftime("%Y-%m-%d")
        itc_permits = self.env['itc.permit'].search([('permit_end_date', '=', current_date), ('state', '!=', 'cancel')])
        for rec in itc_permits:

            rec.write({'state': 'expired'})

    # Fetch the name.
    #@api.multi
    def name_get(self):
        result = []
        for record in self:
            result.append((record.id, record.name))
        return result

    # Function to confirm the permit.
    def action_confirm(self):
        now = datetime.now()
        current_date = now.strftime("%Y-%m-%d")

        # Updating the status as Confirmed.
        # Check there is ITC permit number before confirming.
        if not self.name:
            raise UserError(_('Please fill out the ITC Permit Number before confirming.'))
        # Check the Permit Start and End dates are filled.
        if not self.permit_start_date or not self.permit_end_date:
            raise UserError(_('Please fill out the ITC Permit Start and End Dates before confirming.'))
        # Checking whether the Permit End date lesser than the Permit Start Date.
        if self.permit_end_date < self.permit_start_date:
            raise UserError(_('The Permit End Date is lesser than Permit Start Date. Please update the dates.'))
        # Check the given ITC Permit number already exists.
        itc_permit_no = self.env['itc.permit'].search([('name', '=', self.name),
                                                       ('state', 'not in', ('expired', 'cancel')),
                                                       ('id', '!=', self.id)])
        if itc_permit_no:
            raise UserError(_('This Permit number already exists. Please make Mark it as Expired for '
                              'reuse this Permit Number.'))

        # Check if the vehicle is already in the ITC Permit having pending or running state.
        if self.vehicle_no:
            itc_vehicles = self.env['itc.permit'].search([('vehicle_no', '=', self.vehicle_no.name),
                                                          ('state', '=', 'done')])
            if itc_vehicles:
                raise UserError(
                    _("The Vehicle Number '%s' is already added in the ITC Permits.") % self.vehicle_no.name)

        # Check the permit end date before updating the status. If its already expired or not.
        if self.permit_end_date:
            permit_end_date = datetime.strptime(self.permit_end_date, "%Y-%m-%d")
            actual_due_date = permit_end_date.strftime("%Y-%m-%d")
            if actual_due_date < current_date:
                self.write({'state': 'expired'})
            else:
                self.write({'state': 'done'})

        # # Sending the mail to Accounts team to inform that the vehicle's ITC Permit is confirmed.
        # users_groups = self.env.ref('bbis_itc_permits.group_itc_mail_users').users
        # partners_ids = users_groups.mapped('partner_id.id')
        # if users_groups and partners_ids:
        #     body = "<p>Dear Accounts Team,</p>"
        #     body += "<p>This is to notify you that ITC permit is confirmed for the vehicle %s by %s." % (
        #         self.vehicle_no.name, self.env.user.name)
        #     body += "<p>ITC Number - %s." % self.name
        #     # body += "<p> Permit Start Date - %s ." % self.permit_start_date
        #     # body += "<p> Permit End Date - %s." % self.permit_end_date
        #     body += "<p>Thank you.</p>"
        #     subject = "ITC Permit Confirmation"
        #     self.message_post(body=body, subject=subject, message_type='comment', subtype='mt_comment',
        #                       partner_ids=partners_ids)

    # Sending the mail to account advisor if the ITC will expire after one week.
    def itc_expired_mail(self):
        now = datetime.now()
        next_month = now + relativedelta(months=1)
        first_day = next_month.replace(day=1, hour=0)
        last_day = next_month + relativedelta(day=31)

        users_groups = self.env.ref('bbis_itc_permits.group_itc_mail_users').users.ids
        user = self.env['res.users'].browse(self.env.uid)
        from_email = 'itcpermit@fms-tech.com'

        # prepare ITC Permits.
        itc_permits = self.env['itc.permit'].search([('state', '=', 'done'), ('permit_end_date', '>=', first_day),
                                                     ('permit_end_date', '<=', last_day)], order="permit_end_date")

        itc_permits_count = 0
        permits_html = ''
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')

        for permits in itc_permits:
            itc_permits_count += 1

            permits_html += "<tr>"
            permits_html += "<td>" + str(itc_permits_count) + "</td>"
            permits_html += "<td>" + str(permits.name) + "</td>"
            permits_html += "<td>" + permits.partner_id.name + "</td>"
            permits_html += "<td>" + permits.vehicle_no.name + "</td>"
            permits_html += "<td>" + permits.device_no + "</td>"
            permits_html += "<td>" + permits.permit_end_date + "</td>"
            permits_html += "<td><a href=" + base_url + "/web#id=" + str(
                permits.id) + "&amp;view_type=form&amp;model=itc.permit " \
                              "style=background-color: " \
                              "#2c286c; border: 10px solid " \
                              "#2c286c; text-decoration: " \
                              "none; color: #fff; font-size: " \
                              "14px;>View Details</a></td>"
            permits_html += "</tr>"

        permits_html += '</table>'

        if users_groups and itc_permits_count:
            # Find out one finance user from the account advisor group.
            users = self.env['res.users'].search([('id', 'in', users_groups), ('id', '!=', 1)])
            emails = users.mapped('partner_id').mapped('email')
            user_mail = '%s' % ",".join(emails)

            if user_mail:
                # Preparing the mail content for sending.
                body_html = """
                    <div style="font-family:Arial;font-size:10pt;">
                    <p>Dear Team,</p>
                    <p>This is to inform you that the below mentioned ITC Permits will be expiring on %s.
                    </p>
                    <table style="border-collapse:collapse; font-family:Arial;font-size:10pt; 
                    margin-top:10px; text-align:left" cellpadding="5" border="1">
                    <tr>
                        <th style="background-color:#2c286c; color:white">SN</th>
                        <th style="background-color:#2c286c; color:white;">Permit Number</th>
                        <th style="background-color:#2c286c; color:white;">Client Name</th>
                        <th style="background-color:#2c286c; color:white;">Vehicle Number</th>
                        <th style="background-color:#2c286c; color:white;">Device Number</th>
                        <th style="background-color:#2c286c; color:white;">Expiry Date</th>
                        <th style="background-color:#2c286c; color:white;"></th>
                    </tr>
                    """ % next_month.strftime("%B %Y")
                body_html += permits_html
                body_html += '''<br/><br/><p>Thank You,</p>'''
                body_html += '''<p style="margin:0; color:#F05A29"><b>%s</b></p>''' % user.company_id.name
                body_html += '''<p style="color: #808080; margin:0;"><small>This is a system generated mail. 
                No need of sending replies.</small></p>'''

                template_obj = self.env['mail.mail']

                template_data = {
                    'subject': 'ITC Permit Expiration Reminder on %s ' % next_month.strftime("%B %Y"),
                    'body_html': body_html,
                    'email_from': from_email,
                    'email_to': user_mail,
                }

                template_id = template_obj.create(template_data)
                template_id.send()

    # Cancel button function
    def action_cancel(self):
        if self.cancel_reason:
            self.write({'state': 'cancel'})
        else:
            raise UserError(_('Please enter the reason for Canceling.'))

    # Onchange added for sale subscription for getting the subscription date from the chosen Subscription.
    @api.onchange('sale_subscription_id')
    def onchange_subscription(self):
        subscription = self.env['sale.order'].search([('id', '=', self.sale_subscription_id.id), ('is_subscription', '=', True)])
        self.subscription_end_date = subscription.date

    # Delete inherit. Only the draft stage entries are possible to delete.
    def unlink(self):
        login_user = self.env.user.has_group('account.group_account_manager')
        for record in self:
            if record.state != 'draft':
                raise UserError(_('You cannot delete this record. Only Pending records can delete.'))
            else:
                if not login_user:
                    raise UserError(_('You have no permission to delete this record.'))

        result = super(ITCPermit, self).unlink()
        return result

    # Function to Reset the ITC Permit entry only in Cancel State.
    def action_reset(self):
        if self.state == 'cancel':
            self.write({'state': 'draft'})

    # Add onchange for setting the value of lot name from new device_id to old device_no
    @api.onchange('device_id')
    def device_id_onchange(self):
        if self.device_id:
            self.device_no = self.device_id.name

    # Scheduler function. Update Multiple ITC to confirm.
    def itc_multiple_confirm(self):
        now = datetime.now()
        current_date = now.strftime("%Y-%m-%d")

        users_groups = self.env.ref('bbis_itc_permits.group_itc_mail_users').users.ids
        user = self.env['res.users'].browse(self.env.uid)
        from_email = user.company_id.email
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        sale_orders = []
        # Mail send to Accounts team - List of vehicles that ITC Permit confirmed.
        # Selecting the selected ids using active ids.
        itc_permit_orders = self.env['itc.permit'].search([('id', 'in', self._context.get('active_ids'))],
                                                          order='sale_order_id asc')
        for sale_order in itc_permit_orders:
            if sale_order.sale_order_id not in sale_orders:
                sale_orders.append(sale_order.sale_order_id)

        for sale_order in sale_orders:
            itc_permit_det = ''
            itc_count = 0
            itc_permit_selected = self.env['itc.permit'].search([('id', 'in', self._context.get('active_ids')),
                                                                 ('sale_order_id', '=', sale_order.id)],
                                                                order='id asc')

            for itc in itc_permit_selected:
                # Updating the status as Confirmed.
                # Check there is ITC permit number before confirming.
                if not itc.name:
                    raise UserError(_('Please fill out the ITC Permit Number before confirming.'))
                # Check the Permit Start and End dates are filled.
                if not itc.permit_start_date or not itc.permit_end_date:
                    raise UserError(_('Please fill out the ITC Permit Start and End Dates before confirming.'))
                # Checking whether the Permit End date lesser than the Permit Start Date.
                if itc.permit_end_date < itc.permit_start_date:
                    raise UserError(_('The Permit End Date is lesser than Permit Start Date. Please update the dates.'))
                # Check the given ITC Permit number already exists.
                itc_permit_no = self.env['itc.permit'].search([('name', '=', itc.name), ('state', '=', 'done'),
                                                               ('id', '!=', itc.id)], limit=1)
                if itc_permit_no:
                    raise UserError(
                        _('This ITC number already exists. Please cancel existing record if you want to proceed.'))

                # Check if the vehicle is already in the ITC Permit having pending or running state.
                if itc.vehicle_no:
                    itc_vehicles = self.env['itc.permit'].search([('vehicle_no', '=', itc.vehicle_no.name),
                                                                  ('state', '=', 'done'), ('id', '!=', itc.id)],
                                                                 limit=1)
                    for vehicle in itc_vehicles:
                        if vehicle.vehicle_no:
                            raise UserError(
                                _("The Vehicle Number '%s' is already added in the ITC Permits.") % vehicle.vehicle_no.name)

                # Check the permit end date before updating the status. If its already expired or not.
                if itc.permit_end_date:
                    permit_end_date = datetime.strptime(itc.permit_end_date, "%Y-%m-%d")
                    actual_due_date = permit_end_date.strftime("%Y-%m-%d")
                    if actual_due_date < current_date:
                        self.write({'state': 'expired'})
                    else:
                        self.write({'state': 'done'})

                mail_start_date = datetime.strftime(datetime.strptime(itc.permit_start_date, "%Y-%m-%d"), "%d-%m-%Y")
                mail_end_date = datetime.strftime(datetime.strptime(itc.permit_end_date, "%Y-%m-%d"), "%d-%m-%Y")
                #  Mail code for sending the mails for selected ITC Prmit
                itc_count += 1
                itc_permit_det += "<tr>"
                itc_permit_det += "<td style='text-align:center'>" + str(itc_count) + "</td>"
                itc_permit_det += "<td style='text-align:center'>" + str(itc.name) + "</td>"
                itc_permit_det += "<td>" + itc.partner_id.name + "</td>"
                itc_permit_det += "<td style='text-align:center'>" + itc.vehicle_no.name + "</td>"
                itc_permit_det += "<td style='text-align:center'>" + itc.device_no + "</td>"
                itc_permit_det += "<td style='text-align:center'>" + mail_start_date + "</td>"
                itc_permit_det += "<td style='text-align:center'>" + mail_end_date + "</td>"
                itc_permit_det += "<td style='text-align:center'>" + str(itc.sale_order_id.name) + "</td>"
                itc_permit_det += "<td style='text-align:center'>" + str(itc.po_number) + "</td>"
                itc_permit_det += "<td style='text-align:center'><a href=" + base_url + "/web#id=" + str(
                    itc.id) + "&amp;view_type=form&amp;model=itc.permit&action=979 " \
                              "style=background-color: " \
                              "#2c286c; border: 10px solid " \
                              "#2c286c; text-decoration: " \
                              "none; color: #fff; font-size: " \
                              "14px;>View Details</a></td>"
                itc_permit_det += "</tr>"

            itc_permit_det += '</table>'

            if users_groups and itc_count:
                # Find out one finance user from the account advisor group.
                users = self.env['res.users'].search([('id', 'in', users_groups), ('id', '!=', 1)])
                emails = users.mapped('partner_id').mapped('email')
                user_mail = '%s' % ",".join(emails)

                if user_mail:
                    # Preparing the mail content for sending.
                    body_html = """
                                               <div style="font-family:Arial;font-size:10pt;">
                                               <p>Dear Accounts Team,</p>
                                               <p>Please see below list of ITC Permits confirmed against corresponding Sale Orders:.
                                               </p>
                                               <table style="border-collapse:collapse; font-family:Arial;font-size:10pt; 
                                               margin-top:10px; text-align:left" cellpadding="5" border="1">
                                               <tr>
                                                   <th style="background-color:#2c286c; text-align:center; color:white">SN</th>
                                                   <th style="background-color:#2c286c; text-align:center; color:white;">Permit Number</th>
                                                   <th style="background-color:#2c286c; text-align:center; color:white;">Client Name</th>
                                                   <th style="background-color:#2c286c; text-align:center; color:white;">Vehicle Number</th>
                                                   <th style="background-color:#2c286c; text-align:center; color:white;">Device Number</th>
                                                   <th style="background-color:#2c286c; text-align:center; color:white;">Create Date</th>
                                                   <th style="background-color:#2c286c; text-align:center; color:white;">Expiry Date</th>
                                                   <th style="background-color:#2c286c; text-align:center; color:white;">Sale Order</th>
                                                   <th style="background-color:#2c286c; text-align:center; color:white;">Purchase Order</th>
                                                   <th style="background-color:#2c286c; text-align:center; color:white;"></th>
                                               </tr>
                                               """
                    body_html += itc_permit_det
                    body_html += '''<br/><br/><p>Thank You,</p>'''
                    body_html += '''<p style="margin:0; color:#f05a28"><b>%s</b></p>''' % user.company_id.name
                    body_html += '''<p style="color: #808080; margin:0;"><small>This is a system generated mail. 
                               No need of sending replies.</small></p>'''

                    template_obj = self.env['mail.mail']
                    template_data = {
                        'subject': 'Confirmed ITC Permit List',
                        'body_html': body_html,
                        'email_from': from_email,
                        'email_to': user_mail
                    }

                    template_id = template_obj.create(template_data)
                    template_id.send()

    # Function for mark as expired.
    def action_mark_expired(self):
        self.write({'state': 'expired'})

    # Function for applied.
    def action_applied(self):
        self.write({'state': 'applied'})
