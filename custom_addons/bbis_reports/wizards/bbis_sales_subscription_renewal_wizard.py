from odoo import fields, models, api, _
from datetime import datetime, date, timedelta, time
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError
import tempfile
import binascii
import xlrd


class BBISSalesSubscriptionRenewalUpdate(models.TransientModel):
    _name = 'bbis.sales.subscription.renewal.update'
    _description = 'BBIS Sales Subscription Renewal Update'

    @api.model
    def default_sale_selected(self):
        active_ids = self._context.get('active_ids')
        if active_ids:
            subscription_records = self.env['sale.order'].search([
                ('id', 'in', active_ids),
                ('is_subscription', '=', True)
            ])
            return subscription_records
        return self.env['sale.order']

    sale_subscription_ids = fields.Many2many('sale.order', required=True, default=default_sale_selected, domain=[('is_subscription', '=', True)])
    sale_type = fields.Selection([('cash', 'Walk In/Cash Sale'),
                                  ('purchase', 'Unit Sale'),
                                  ('lease', 'Lease Sale'),
                                  ('rental', 'Rental Sale'),
                                  ('pilot', 'Renewal Sale'),
                                  ], string='Sale Type', track_visibility='onchange')
    auto_bill = fields.Selection([('true', 'True'),
                                  ('false', 'False')])
    sales_tag = fields.Selection([('open', 'Open'),
                                  ('confirmed', 'Confirmed'),
                                  ('qualify', 'Qualify'),
                                  ('reach', 'Reach'),
                                  ('not_renewed', 'Not Renewed'),
                                  ('not_renewed', 'Not Renewed')], string="Sales Tag", track_visibility='onchange')
    sub_status = fields.Selection([('closed', 'Closed'), ('hold', 'Hold'), ('in_progress', 'In Progress')],
                                  string="Subscription Status", track_visibility='onchange', copy=False)
    auto_fls = fields.Selection([('true', 'True'),
                                 ('false', 'False')], string='Auto FLS')
    file = fields.Binary('File')
    file_name = fields.Char("File Name")

    def update_sale_type(self):
        # partner_ids = []
        template_ids = []
        subscriptions = []
        # sale_subscription_list = self.env['sale.order'].browse(self._context.get('active_ids'))

        for subscription in self.sale_subscription_ids:
            if subscription.template_id not in template_ids:
                template_ids.append(subscription.template_id)
            subscriptions.append(subscription.id)

            if self.sale_type:
                subscription.sale_type = self.sale_type

            if self.auto_bill:
                subscription.auto_bill = True if self.auto_bill == 'true' else False

            if self.auto_fls:
                subscription.is_fls = True if self.auto_fls == 'true' else False

            if self.sales_tag:
                subscription.sales_tag = self.sales_tag

            if self.sub_status:
                subscription.sub_status = self.sub_status

        return {
            'type': 'ir.actions.act_window',
            'name': _('Subscriptions'),
            'view_type': 'form',
            'res_model': 'sale.order',
            'view_mode': 'tree,form',
            'view_id': False,
            'target': 'current',
            'domain': [('id', 'in', subscriptions)],
        }

    # Onchange event for calling the import file option while selecting the Excel.
    @api.onchange('file')
    def onchange_file(self):
        for r in self:
            if r.file_name:
                subscriptions = self.import_file()
                self.sale_subscription_ids = subscriptions

    # Code for getting the device numbers from the uploaded Excel.
    #@api.multi
    def import_file(self):
        data_list = []
        subscription_ids = ''
        not_exists = []
        for r in self:
            if r.file_name:
                file_extension = r.file_name.split(".")[-1]
                if file_extension in ('xlsx', 'xls'):
                    fields = []
                    fp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")

                    if not self.file:
                        return False
                    fp.write(binascii.a2b_base64(self.file))
                    fp.seek(0)
                    workbook = xlrd.open_workbook(fp.name)

                    temp_list = []
                    for sheet in workbook.sheets():
                        for row_no in range(sheet.nrows):
                            if row_no <= 0:
                                fields = list(map(lambda row: str(row.value), sheet.row(row_no)))
                            else:
                                lines = list(
                                    map(lambda row: isinstance(row.value, bytes) and row.value.encode('utf-8') or str(
                                        row.value), sheet.row(row_no)))

                                if fields and lines:
                                    list_dict = dict(zip(fields, lines))
                                    temp_list.append(list_dict)

                    for k in temp_list:
                        if k.get('Device Serial'):
                            device_number = k.get('Device Serial').split('.')[0]
                            subscriptions = self.env['sale.order'].search([('serial_no', '=', device_number), ('is_subscription', '=', True)],
                                                                                 limit=1)
                            if subscriptions:
                                data_list.append(subscriptions.id)
                            else:
                                not_exists.append(k.get('Device Serial').split('.')[0])
                    if not_exists:
                        raise ValidationError("These Device Serials %s are not existing in the system" % not_exists)
                    subscription_ids = self.env['sale.order'].search([('id', 'in', data_list),('is_subscription', '=', True)])
        return subscription_ids
