# Wizard for upload the vehicle details for the ITC permits.
from odoo import api, fields, models, _
import xlrd
import tempfile
import binascii
from odoo.exceptions import ValidationError, UserError
from datetime import datetime


# Create a wizard window for upload the vehicle details for itc permit.
class ITCPermitWizard(models.TransientModel):
    _name = 'itc.permit.wizard'

    def _default_sale_order(self):
        return self.env.context.get('active_id')

    # Fields in the wizard for import
    file = fields.Binary('Select File')
    order_id = fields.Integer(string='Sales Order')
    permit_wizard_line_ids = fields.One2many('itc.permit.wizard.line', 'permit_wizard_id', string='Permit Wizard Lines')
    sale_order_id = fields.Integer(string='Sales Orer', default=_default_sale_order)
    permit_count = fields.Integer(compute="compute_permit_count")

    # Onchange method. Fill the data from Excel and check there is request number matching with request no in ITC.
    @api.onchange('file')
    def onchange_file(self):
        permit_status = self.env.context.get('permit_status')
        itc = self.env['itc.permit']
        if permit_status != 'permit_applied':
            permit_wizard_line = self.env['itc.permit.wizard.line'].search([])
            permit_wizard_line.unlink()
            for r in self:
                if r.file:
                    data_list = self.import_file()
                    for k in data_list:
                        req_no = k.get('Request Number')
                        permit_no = k.get('Permit No.')
                        record = itc.search([('request_number', '=', req_no), ('state', '=', 'applied')])

                        if len(record) > 1:
                            raise ValidationError("%s has more than 1 record under the application stage. Please make sure to add only 1 record." % req_no)

                        if record:
                            state = dict(record._fields['state'].selection).get(record.state)
                            permit_wizard_line.create({
                                'request_no': record.request_number,
                                'permit_no': permit_no or record.name,
                                'partner': record.partner_id.name,
                                'sale_order_no': record.sale_order_id.name,
                                'vehicle_no': record.vehicle_no.name,
                                'current_status': state,
                                'portal_status': k.get('Status'),
                            })
                    data_records = self.env['itc.permit.wizard.line'].search([])
                    self.permit_wizard_line_ids = data_records
            return {'type': 'ir.actions.act_window_refresh'}

    @api.depends('permit_wizard_line_ids')
    def compute_permit_count(self):
        for rec in self:
            rec.permit_count = len(rec.permit_wizard_line_ids) if rec.permit_wizard_line_ids else 0

    def import_file(self):
        """Function for import the Excel."""
        for r in self:
            fields = []
            fp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
            if not self.file:
                return False
            fp.write(binascii.a2b_base64(self.file))
            fp.seek(0)
            workbook = xlrd.open_workbook(fp.name)
            sheet = workbook.sheet_by_index(0)
            data_list = []
            for row_no in range(sheet.nrows):
                if row_no <= 0:
                    fields = list(map(lambda row: str(row.value), sheet.row(row_no)))
                else:
                    lines = list(
                        map(lambda row: isinstance(row.value, bytes) and row.value.encode('utf-8') or str(
                            row.value),
                            sheet.row(row_no)))

                    if fields and lines:
                        color_dict = dict(zip(fields, lines))
                        data_list.append(color_dict)
            return data_list

    def upload_applied_permits(self):
        """Update draft itc permits that were inserted during sales order confirmation."""

        if not self.file:
            raise ValidationError("Please select file to upload.")

        data_list = self.import_file()
        active_id = self.env.context.get('active_id')
        itc = self.env['itc.permit']
        sale_order = self.env['sale.order'].search([('id', '=', active_id)])
        records = itc.search([('sale_order_id', '=', active_id), ('state', '=', 'draft'), ('name', '=', 'Draft')])
        final_length = len(records)
        if not records:
            ordered_itc = sale_order.order_line.filtered(lambda l: l.product_id.is_itc_product).mapped('product_uom_qty')
            all_itc = itc.search([('sale_order_id', '=', active_id)])
            final_length = (sum(ordered_itc) - len(all_itc))

        i = 0
        for line in data_list[0: int(final_length)]:

            field_data = self.get_fields(line, sale_order)
            vehicles = field_data['vehicles']
            devices = field_data['devices']
            permit_create_date = field_data['start_date']
            permit_expiry_date = field_data['expiry_date']

            if records:
                records[i].update({
                    'name': line.get('ITC Permit No.'),
                    'request_number': line.get('Request No.'),
                    'sale_order_id': sale_order.id,
                    'traffic_code_no': line.get('Traffic Code No').split('.')[0] if line.get('Traffic Code No') else '',
                    'chassis_no': vehicles.chassis_no if vehicles.chassis_no else line.get('Chassis No.'),
                    'vehicle_no': vehicles.id,
                    'device_id': devices.id,
                    'device_no': devices.name,
                    'sim_card_no': line.get('Sim Card No.').split('.')[0] if line.get('Sim Card No.') else '',
                    'trailer_no': line.get('Trailer No.').split('.')[0] if line.get('Trailer No.') else '',
                    'trailer_chassis_no': line.get('Trailer Chassis No.').split('.')[0] if line.get(
                        'Trailer Chassis No.') else '',
                    'permit_start_date': permit_create_date,
                    'permit_end_date': permit_expiry_date,
                    'vehicle_status': line.get('Vehicle Status'),
                    'remarks': line.get('Remarks'),
                    'state': 'applied',
                })
            else:
                self.create_itc_permits(line, sale_order, field_data)
            i += 1

        for line in data_list:
            free_permit = line.get('Free Permit')
            if free_permit and free_permit.lower() == 'yes':

                field_data = self.get_fields(line, sale_order)
                self.create_itc_permits(line, sale_order, field_data, free_permit)

        # Open the ITC permit tree view with filter of the created SO Number.
        return {
            'type': 'ir.actions.act_window',
            'name': _('ITC Permits'),
            'view_type': 'form',
            'res_model': 'itc.permit',
            'view_mode': 'tree,form',
            'view_id': False,
            'target': 'current',
            'domain': [('sale_order_id', '=', self.env.context.get('active_id'))],
            'context': {'default_sale_order_id': active_id}
        }

    def create_itc_permits(self, line, sale_order, field_data, free_permit=False):
        """ Create TIC Permits """

        itc = self.env['itc.permit']
        vehicles = field_data['vehicles']
        devices = field_data['devices']
        permit_create_date = field_data['start_date']
        permit_expiry_date = field_data['expiry_date']

        itc.create({
            'name': line.get('ITC Permit No.'),
            'request_number': line.get('Request No.'),
            'sale_order_id': sale_order.id,
            'traffic_code_no': line.get('Traffic Code No').split('.')[0] if line.get('Traffic Code No') else '',
            'chassis_no': vehicles.chassis_no if vehicles.chassis_no else line.get('Chassis No.'),
            'vehicle_no': vehicles.id,
            'device_id': devices.id,
            'device_no': devices.name,
            'sim_card_no': line.get('Sim Card No.').split('.')[0] if line.get('Sim Card No.') else '',
            'trailer_no': line.get('Trailer No.').split('.')[0] if line.get('Trailer No.') else '',
            'trailer_chassis_no': line.get('Trailer Chassis No.').split('.')[0] if line.get(
                'Trailer Chassis No.') else '',
            'permit_start_date': permit_create_date,
            'permit_end_date': permit_expiry_date,
            'vehicle_status': line.get('Vehicle Status'),
            'remarks': line.get('Remarks'),
            'state': 'applied',
            'free_permit': free_permit,
        })

    def _get_fields(self, line, sale_order):
        vehicle_name = line.get('Vehicle No.')
        if not vehicle_name:
            raise UserError(_('Vehicle Number not exist in the file.'))
        # Selecting from the database if there is same vehicle details available in the database
        vehicles = self.env['vehicle.master'].search([('name', '=', line.get('Vehicle No.'))], limit=1)
        if not vehicles:
            raise UserError(_('This Vehicle ' + line.get('Vehicle No.') + ' not in the Vehicle Master list.'))

        # If vehicle is available in the database again checking that this vehicle have already entry in ITC Permit.
        if vehicles:
            itc_vehicles = self.env['itc.permit'].search([('vehicle_no', '=', vehicles.id),
                                                          ('sale_order_id.id', '=', sale_order.id),
                                                          ('state', 'in', ('draft', 'done'))], limit=1)
            if itc_vehicles:
                raise UserError(_("The vehicle %s has already an existing ITC entry in this Sale Order. "
                                  "Please cancel it if you want to proceed.") % line.get('Vehicle No.'))

        device_name = line.get('Device No.').split('.')[0] if line.get('Device No.') else ''
        devices = False

        if device_name:
            devices = self.env['stock.lot'].search([('name', '=', device_name)])
            if not devices:
                raise UserError(_('This Device ' + device_name + ' not in the Device list.'))

        if line.get('ITC Permit No.'):
            itc_permit_no = self.env['itc.permit'].search([('name', '=', line.get('ITC Permit No.')),
                                                           ('state', '=', 'done')])
            if itc_permit_no:
                raise UserError(
                    _('This ITC Number: %s already exists. Mark it as expired for using the same.' % itc_permit_no.name))

        if line.get('Request No.'):
            request_no = self.env['itc.permit'].search([('name', '=', line.get('ITC Request No.')),
                                                        ('state', '=', 'done')])
            if request_no:
                raise UserError(_('This Request Number %s already exists.' % request_no.request_number))

        permit_create_date = ''
        permit_expiry_date = ''
        create_date = line.get('Permit Create Date').split('.')[0] if line.get('Permit Create Date') else ''
        expiry_date = line.get('Permit Expiry Date').split('.')[0] if line.get('Permit Expiry Date') else ''
        if create_date:
            permit_create_date = datetime.fromordinal(datetime(1900, 1, 1).toordinal() + int(create_date) - 2)
        if expiry_date:
            permit_expiry_date = datetime.fromordinal(datetime(1900, 1, 1).toordinal() + int(expiry_date) - 2)

        return {
            "start_date": permit_create_date,
            "expiry_date": permit_expiry_date,
            "vehicles": vehicles,
            "devices": devices,
        }

    def update_permit_status(self):
        """ Update the new status of itc with the ITC Portal Excel file """
        now = datetime.now()
        current_date = now.strftime("%Y-%m-%d")
        users_groups = self.env.ref('bbis_itc_permits.group_itc_mail_users').users.ids
        user = self.env['res.users'].browse(self.env.uid)
        from_email = user.company_id.email
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        itc_permit_ids = []

        wizard_lines = self.env['itc.permit.wizard.line'].search([])
        for line in wizard_lines:
            itc_permit = self.env['itc.permit'].search([('request_number', '=', line.request_no), ('state', '=', 'applied')], limit=1)
            if itc_permit:
                if line.portal_status.lower() == 'permit issued' and line.permit_issued:
                    state = 'done'
                elif 'permit expired' in line.portal_status.lower() or line.portal_status.lower() == 'auto closed':
                    state = 'expired'
                elif 'permit cancelled' in line.portal_status.lower():
                    state = 'cancel'
                else:
                    state = 'applied'

                if state != 'applied':
                    itc_permit_ids.append(itc_permit.id)
                    itc_permit.update({'state': state})

                    if itc_permit.name != line.permit_no:
                        itc_permit.update({'name': line.permit_no})

        # Sending mail function.
        sale_orders = []
        itc_permits = self.env['itc.permit'].search([('id', 'in', itc_permit_ids)], order='sale_order_id asc')
        for sale_order in itc_permits:
            if sale_order.sale_order_id not in sale_orders:
                sale_orders.append(sale_order.sale_order_id)

        for sale_order in sale_orders:
            itc_permit_det = ''
            itc_count = 0
            itc_permit_selected = self.env['itc.permit'].search([('id', 'in', itc_permit_ids), ('state', '=', 'done'),
                                                                 ('sale_order_id', '=', sale_order.id)],
                                                                order='id asc')

            for itc in itc_permit_selected:
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
                       <p>Please see below list of ITC Permits confirmed.</p>
                       <table style="border-collapse:collapse; font-family:Arial;font-size:10pt; margin-top:10px; text-align:left" cellpadding="5" border="1">
                       <tr>
                           <th style="background-color:#2c286c; text-align:center; color:white">SN</th>
                           <th style="background-color:#2c286c; text-align:center; color:white;">Permit Number</th>
                           <th style="background-color:#2c286c; text-align:center; color:white;">Client Name</th>
                           <th style="background-color:#2c286c; text-align:center; color:white;">Vehicle Number</th>
                           <th style="background-color:#2c286c; text-align:center; color:white;">Device Number</th>
                           <th style="background-color:#2c286c; text-align:center; color:white;">Start Date</th>
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
                        'subject': 'Confirmed ITC Permit List For %s' % itc.sale_order_id.name,
                        'body_html': body_html,
                        'email_from': from_email,
                        'email_to': user_mail
                    }
                    template_id = template_obj.create(template_data)
                    template_id.send()

        # Open the ITC permit tree view.
        return {
            'type': 'ir.actions.act_window',
            'name': _('ITC Permits'),
            'view_type': 'form',
            'res_model': 'itc.permit',
            'view_mode': 'tree,form',
            'view_id': False,
            'target': 'current',
            'domain': [('id', 'in', itc_permit_ids)],
        }

class ITCPermitWizardLine(models.TransientModel):
    """Create a wizard window for update the vehicle details for itc permit."""
    _name = 'itc.permit.wizard.line'

    permit_wizard_id = fields.Many2one('itc.permit.wizard', string='Wizard Reference', store=True)
    request_no = fields.Char(string="Request No.")
    permit_no = fields.Char(string="Permit No.")
    sale_order_no = fields.Char(string="Sale Order")
    partner = fields.Char(string="Client")
    vehicle_no = fields.Char(string="Vehicle No.")
    current_status = fields.Char()
    portal_status = fields.Char()
    permit_issued = fields.Boolean()
