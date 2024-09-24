from odoo import models, fields, api, _, exceptions
from odoo.exceptions import ValidationError
from urllib.parse import urljoin
from urllib.parse import urlencode


class AssetRequest(models.Model):
    _name = 'asset.request'
    _description = 'Asset Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="ID", readonly=True, copy=False, index=True, default=lambda self: self.env['ir.sequence'].next_by_code('asset.request') or _('Request'))

    search_asset = fields.Char(string="Search")

    asset_location = fields.Many2one('stock.location', string="Asset Location")

    asset_id = fields.Many2one('account.asset.asset', string="Asset", required=True)

    asset_category = fields.Many2one('account.asset.category', string="Asset Category", required=True)

    asset_model = fields.Many2one('asset.model', string="Asset Model", required=True)

    employee = fields.Many2one('hr.employee', string="Employee", required=True)

    partner_id = fields.Many2one('res.partner', string="Partner", related='employee.address_home_id')

    employee_branch = fields.Many2one('asset.branch', string="Branch", related='employee.branch')

    regional_warehouse_manager = fields.Many2one('res.users', string="Regional WH Manager",
                                                 related='employee.branch.regional_wh_manager')

    service_number_ticket = fields.Char(string="Service Number Ticket", required=True)

    state = fields.Selection([('draft', "Draft"),
                              ('submitted', "Submitted"),
                              ('approved', "Approved"),
                              ('allocated', "Allocated"),
                              ('received', 'Received')], track_visibility='always', default='draft')

    asset_qty = fields.Float(string="Stock Qty", default=1.00)

    picking_type_id = fields.Many2one('stock.picking.type', string="Picking Type")

    comment = fields.Text(string="Comment")
    other_info = fields.Text(string="Other Information")
    request_date = fields.Date(string="Request Date", default=fields.Datetime.now)

    asset_approval = fields.Many2one('res.users', string="Approval", required=True,
                                     domain=lambda self: [
                                         ("groups_id", "=", self.env.ref("IT_asset_module.group_approval_manager").id)])

    @api.onchange('asset_location', 'search_asset')
    def search_get_asset(self):
        search = self.env['account.asset.asset'].search([('asset_number', '=', self.search_asset),
                                                         ('state', '=', 'open'), ('initial_location', '=', self.asset_location.name or str(self.asset_location.location_id.name)+ '/' + str(self.asset_location.name)),
                                                         ('asset_status', '=', 'unallocated')])

        if search and self.asset_location:
            self.asset_category = search.category_id.id
            self.asset_model = search.asset_model.id
            self.asset_id = search.id
        elif not search and not self.asset_location or not search:
            self.asset_category = ''
            self.asset_model = ''
            self.asset_id = ''

    #@api.multi
    def action_approve(self):
        if self.asset_approval.id == self.env.user.id:
            mail_mail = self.env['mail.mail']
            body = "<p>Dear " + str(self.regional_warehouse_manager.name) + ",</p> <p>" \
                   + " Asset " + self.asset_id.name + "for " + str(self.employee.name) + " is  waiting for allocation.</p>"\
                   +"<p><a href="+ self.build_url() + " >Click Here to allocate</a></p> <p>Thanks</p>" \
                   + "<p>Asset MGT team.</p>"

            mail_values = {
                'auto_delete': True,
                'body_html': body,
                'email_cc': False,
                'email_from': self.asset_approval.login,
                'email_to': str(self.regional_warehouse_manager.login),
                'mail_server_id': False,
                'model': 'asset.request',
                'subject': "Dear Pending Approval."
            }
            msg_id = mail_mail.sudo().create(mail_values)
            msg_id.sudo().send()
            self.state = 'approved'
        else:
            raise ValidationError(_('Error! You Do Not Have Permission to Approve.'))

    #@api.multi
    def action_allocate(self):
        mail_mail = self.env['mail.mail']
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')

        body = "<p>Dear " + str(self.employee.name) + ",</p> <p>" \
               + str(self.asset_id.name) + " has been allocated to you. The request ID is " + self.name +" </p>" "<p><a href=" \
               + base_url + '/confirm' + " >Click Here to receive in good condition</a></p>" \
               +"<p>Thanks</p>" + "<p>Asset MGT team.</p>"

        mail_values = {
            'auto_delete': True,
            'body_html': body,
            'email_cc': False,
            'email_from': self.regional_warehouse_manager.login,
            'email_to': str(self.employee.work_email),
            'mail_server_id': False,
            'model': 'asset.request',
            'subject': "Pending Asset."
        }
        msg_id = mail_mail.sudo().create(mail_values)
        msg_id.sudo().send()

        self.state = 'allocated'

    #@api.multi
    def action_wh(self):
        update = self.env['account.asset.asset'].search([('asset_number', '=', self.asset_id.asset_number)])
        update.assigned_to = self.employee.id
        update.location = self.employee.stock_location.id
        update.date_received = fields.Date.context_today(self)
        update.asset_status = "allocated"

        xyz = self.env['asset.movement.history'].create({
            'name': self.asset_id.id,
            'location_from': self.asset_id.initial_location.id,
            'location_to': self.employee.stock_location.id,
            'asset_status': self.asset_id.asset_status
        })
        self.state = 'received'

    #@api.multi
    def action_submit(self):
        if self.asset_id.assigned_to:
            raise ValidationError(_('Error! Asset Has Already Been Allocated.'))
        else:
            mail_mail = self.env['mail.mail']
            # notification_body = "<p>Dear " + str(self.employee.name) + ",</p> <p>" \
            #                     + " Asset request for " + str(self.asset_id.name) + " has being placed on your behalf. " \
            #                                                                         "Kindly visit the warehouse to receive." \
            #                     + "<p>Thanks</p>" \
            #                     + "<p>Asset MGT team.</p>"
            #
            # notification_body_mail_values = {
            #     'auto_delete': True,
            #     'body_html': notification_body,
            #     'email_cc': False,
            #     'email_from': str(self.asset_approval.login),
            #     'email_to': str(self.employee.work_email),
            #     'mail_server_id': False,
            #     'model': 'asset.request',
            #     'subject': "Asset Request."
            # }
            #
            # notification_id = mail_mail.sudo().create(notification_body_mail_values)
            # notification_id.sudo().send()

            approval_body = "<p>Dear " + str(self.asset_approval.name) + ",</p> <p>" \
                            + " Asset request for " + str(
                self.employee.name) + " is waiting for your Approval.</p>" "<p><a href=" \
                            + self.build_url() + " >Click Here to approve</a></p> <p>Thanks</p>" \
                            + "<p>Asset MGT team.</p>"

            approval_body_mail_values = {
                'auto_delete': True,
                'body_html': approval_body,
                'email_cc': False,
                'email_from': str(self.employee.work_email),
                'email_to': str(self.asset_approval.login),
                'mail_server_id': False,
                'model': 'asset.request',
                'subject': "Asset Request."
            }
            msg_id = mail_mail.sudo().create(approval_body_mail_values)
            msg_id.sudo().send()
            self.state = 'submitted'

    #@api.multi
    def return_draft(self):
        self.state = 'draft'

    #@api.multi
    def return_back(self):
        self.state = 'allocated'

    @api.onchange('asset_category')
    def onchange_category(self):
        domain = {}
        if self.asset_category and not self.asset_location:
            self.asset_model = None
            domain['asset_model'] = [('asset_category', '=', self.asset_category.name)]
        return {'domain': domain}

    @api.onchange('asset_category', 'asset_model')
    def _get_asset(self):
        domain = {}
        if self.asset_category and self.asset_model and not self.asset_location:
            self.asset_id = None
            domain['asset_id'] = [('category_id', '=', self.asset_category.name),
                                  ('asset_model', '=', self.asset_model.name),
                                  ('state', '=', 'open'), ('asset_status', '=', 'unallocated')]
        return {'domain': domain}

    @api.onchange('employee')
    def check_asset_with_employee(self):
        all_asset = self.env['account.asset.asset'].search([('assigned_to.name', '=', self.employee.name)])
        if self.employee.name in [asset_list.assigned_to.name for asset_list in all_asset]:
            res = {'warning': {
                'title': _('Warning'),
                'message': _('%s already has assets %s.'
                             % (tuple(list(set([emp_name.assigned_to.name.encode("utf-8") for emp_name in all_asset]))),
                                tuple([asset.name.encode("utf-8") for asset in all_asset])))
            }}
            return res

    #@api.multi
    def build_url(self):
        fragment = {}
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        action_id = self.env['ir.model.data'].get_object_reference('IT_asset_module', 'asset_request_action')[1]
        menu_id = self.env['ir.model.data'].get_object_reference('IT_asset_module', 'menu_asset_request')[1]
        fragment['view_type'] = 'form'
        fragment['menu_id'] = menu_id
        fragment['model'] = 'asset.request'
        fragment['id'] = self.id
        fragment['action'] = action_id
        query = {'db': self._cr.dbname}
        res = urljoin(base_url + '/web', "?%s#%s" % (urlencode(query), urlencode(fragment)))
        return res



