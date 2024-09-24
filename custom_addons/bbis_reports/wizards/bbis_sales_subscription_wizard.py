from odoo import fields, models, api, _
from datetime import datetime, date, timedelta, time
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError
import tempfile
import binascii
import xlrd


class BBISSalesSubscriptionWizard(models.TransientModel):
    _name = 'bbis.sales.subscription.update'
    _description = 'BBIS Sales Subscription Update'

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

    sale_subscription_ids = fields.Many2many('sale.order', 'bbis_sales_subscription_update_rel',
                                             'subscription_id', 'update_wizard_id', string='Subscriptions',
                                             required=True, default=default_sale_selected, domain=[('is_subscription', '=', True)])
    period_date_start = fields.Date(string="Period Start Date")
    subscription_date_start = fields.Date(string="Subscription Start Date")
    subscription_end_date = fields.Date(string="Subscription End Date")
    store_ending_date = fields.Date(string="End Date")
    renewal_date = fields.Date(string="Renewal Date")
    period_end_date = fields.Date(string="Period End Date")
    recurring_next_date = fields.Date(string="Date of Next Invoice")
    period = fields.Integer(string="Period")
    amount = fields.Float(string="Amount")
    template_id = fields.Many2one('sale.order.template', string='Billing Cycle', required=True,
                                  track_visibility='onchange')
    product_id = fields.Many2one('product.product', string='Product', domain="[('recurring_invoice','=',True)]")
    file = fields.Binary('File')
    file_name = fields.Char("File Name")

    @api.onchange('subscription_date_start', 'period')
    def onchange_date_start(self):
        if self.subscription_date_start and self.period:
            self.period_date_start = self.subscription_date_start
            ending_date = fields.Date.from_string(self.subscription_date_start) + relativedelta(months=self.period)
            self.subscription_end_date = ending_date - relativedelta(days=1)
            self.renewal_date = ending_date

    @api.onchange('period_date_start', 'template_id')
    def onchange_start_date(self):
        if self.period_date_start:
            self.subscription_date_start = self.period_date_start
            ending_date = fields.Date.from_string(self.period_date_start) + relativedelta(months=self.period)
            self.subscription_end_date = ending_date - relativedelta(days=1)
            self.renewal_date = ending_date
        if self.period_date_start and self.template_id:
            periods = {'daily': 'days', 'weekly': 'weeks', 'monthly': 'months', 'yearly': 'years'}
            val = relativedelta(**{periods[self.template_id.recurring_rule_type]: self.template_id.recurring_interval})
            start_date = fields.Date.from_string(self.period_date_start) - timedelta(days=1)
            self.period_end_date = start_date + val

    @api.onchange('template_id')
    def onchange_template_id(self):
        if self.template_id:
            if self.template_id.recurring_rule_type == 'yearly':
                self.period = 12 * self.template_id.recurring_interval
            if self.template_id.recurring_rule_type == 'monthly':
                self.period = self.template_id.recurring_interval

    # Onchange event for calling the import file option while selecting the Excel.
    @api.onchange('file')
    def onchange_file(self):
        for r in self:
            if r.file_name:
                subscriptions = self.import_file()
                self.sale_subscription_ids = subscriptions

    def update_amount(self):
        partner_ids = []
        template_ids = []
        subscriptions = []
        # sale_subscription_list = self.env['sale.order'].browse(self._context.get('active_ids'))
        # sale_subscription_line_list = self.env['sale.order.line'].browse(self._context.get('active_ids'))

        for subscription in self.sale_subscription_ids:
            if subscription.partner_id not in partner_ids:
                partner_ids.append(subscription.partner_id)
            if subscription.template_id not in template_ids:
                template_ids.append(subscription.template_id)
            subscriptions.append(subscription.id)

            if len(partner_ids) > 1:
                raise ValidationError(_('Please select only Subscriptions with the same Client Name.'))
            # if len(template_ids) > 1:
            #     raise ValidationError(_('The Billing Cycle is different for selected items.'))
            if subscription.auto_bill:
                raise ValidationError(_('Auto Bill entry cannot edit.'))
            if subscription.sale_type in ('lease', 'rental'):
                raise ValidationError(_('Cannot edit this file. The Sale Subscription is Lease/Rental.'))

            if len(subscription.recurring_invoice_line_ids) > 1:
                raise ValidationError(_('Please select only Subscriptions having single line entry.'))

            if self.period_date_start:
                if not self.subscription_date_start or not self.period or not self.template_id or not self.subscription_end_date:
                    raise ValidationError(_('Please fill every information properly.'))

                subscription.start_date = self.period_date_start
                subscription.date_start = self.subscription_date_start
                subscription.subscription_period = self.period
                subscription.date = self.subscription_end_date
                subscription.renewal_date = self.renewal_date
                subscription.end_date = self.period_end_date
                subscription.template_id = self.template_id.id

            if self.amount > 0:
                subscription.recurring_invoice_line_ids.price_unit = self.amount
            if self.product_id:
                subscription.recurring_invoice_line_ids.product_id = self.product_id

            if self.recurring_next_date:
                if subscription.recurring_next_date:
                    subscription.message_post(
                        "The Next Invoice Date Changed from " + subscription.recurring_next_date + " to " + self.recurring_next_date)
                else:
                    subscription.message_post("The Next Invoice Date Changed " + self.recurring_next_date)
                subscription.recurring_next_date = self.recurring_next_date

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
                                    map(lambda row: isinstance(row.value, bytes) and row.value.encode(
                                        'utf-8') or str(
                                        row.value), sheet.row(row_no)))

                                if fields and lines:
                                    list_dict = dict(zip(fields, lines))
                                    temp_list.append(list_dict)

                    for k in temp_list:
                        if k.get('Device Serial'):
                            device_number = k.get('Device Serial').split('.')[0]
                            subscriptions = self.env['sale.order'].search([('serial_no', '=', device_number),('is_subscription', '=', True)],
                                                                                 limit=1)
                            if subscriptions:
                                data_list.append(subscriptions.id)
                            else:
                                not_exists.append(k.get('Device Serial').split('.')[0])
                    if not_exists:
                        raise ValidationError(
                            "These Device Serials %s are not existing in the system" % not_exists)
                    subscription_ids = self.env['sale.order'].search([('id', 'in', data_list),('is_subscription', '=', True)])
        return subscription_ids
