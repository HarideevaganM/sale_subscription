from odoo import api, fields, models, _
from odoo.exceptions import UserError, AccessError, ValidationError
from dateutil.relativedelta import relativedelta
import tempfile
import binascii
import xlrd


class GenerateSubscriptionWizarInherit(models.TransientModel):
    _inherit = 'generate.subscription.wizard'

    file = fields.Binary('File')
    file_name = fields.Char("File Name")

    # Onchange event for calling the import file option while selecting the Excel.
    @api.onchange('file')
    def onchange_file(self):
        for r in self:
            if r.file_name:
                subscriptions = self.import_file()
                partner = subscriptions.mapped('partner_id')
                reseller_id = partner.mapped('reseller_id')
                if len(partner.ids) == 1:
                    self.update({'partner_id': partner and partner.id})
                else:
                    if len(reseller_id.ids) == 1:
                        self.update({'reseller_id': reseller_id and reseller_id.id, 'is_reseller': True})
                self.update({'subscription_ids': subscriptions})
        return

    #@api.multi
    def create_quotation(self):
        if self.file_name:
            subscriptions = self.import_file()
            self.subscription_ids = subscriptions
        sub_vals = []
        vehicle_vals = []
        sale_order_obj = self.env['sale.order']
        # set vehicle
        partner_id = self.subscription_ids.mapped('partner_id')
        if self.is_reseller:
            partner_id = partner_id.mapped('reseller_id')
            if len(partner_id.ids) > 1:
                raise UserError(_('Reseller must be same for generate of quote'))
            if self.reseller_id != partner_id:
                raise UserError(_('Reseller must be one of subscription'))
        else:
            if len(partner_id.ids) > 1:
                raise UserError(_('Partner must be same for generate of quote'))
            if self.partner_id != partner_id:
                raise UserError(_('Partner must be same in subscription'))
        if not self.partner_id and not self.reseller_id:
            raise UserError(_('Partner or reseller not define'))
        # subscribtion
        for line in self.subscription_ids.filtered(lambda x: x.vehicle_number):
            sub_start_date = fields.Date.from_string(line.end_date)
            if not sub_start_date:
                raise UserError(_('Please define period end date "%s".') % (line.display_name,))
            periods = {'daily': 'days', 'weekly': 'weeks', 'monthly': 'months', 'yearly': 'years'}
            subscription_period = relativedelta(**{periods['monthly']: line.subscription_period})
            start_date = fields.Date.from_string(line.date)
            start_period = start_date + relativedelta(days=1)
            sub_end_period = start_period + subscription_period
            end_period = sub_end_period - relativedelta(days=1)
            veh_vals = {
                'serial_no_id': line.vehicle_number.device_serial_number_id and line.vehicle_number.device_serial_number_id.id,
                'device_id': line.vehicle_number.device_id and line.vehicle_number.device_id.id,
                'vehicle_id': line.vehicle_number.id,
                'partner_id': line.partner_id and line.partner_id.id,
                'installation_date': line.vehicle_number.installation_date,
                'start_date': start_period,
                'num_of_period': line.subscription_period,
                'end_date': end_period,
                'status': line.subscription_status if line.subscription_status else 'active',
            }
            vehicle_vals.append((0, 0, veh_vals))
        # set lines
        for line in self.subscription_ids.mapped('recurring_invoice_line_ids').filtered(
                lambda x: x.analytic_account_id.vehicle_number):
            vec_name = line.analytic_account_id.vehicle_number.name
            dev_name = line.analytic_account_id.vehicle_number.device_serial_number_id and line.analytic_account_id.vehicle_number.device_serial_number_id.name
            line_vals = {
                'product_id': line.product_id.id,
                'name': "%s -- %s -- %s" % (line.product_id.display_name, vec_name, dev_name),
                'product_uom_qty': line.quantity,
                'product_uom': line.uom_id and line.uom_id.id,
                'price_unit': line.price_unit,
                'subscription_id': line.analytic_account_id and line.analytic_account_id.id,
            }
            sub_vals.append((0, 0, line_vals))
        # sale order
        sale_order = sale_order_obj.create({
            'partner_id': partner_id and partner_id.id,
            'user_id': partner_id.user_id and partner_id.user_id.id or self.env.user and self.env.user.id,
            'sale_type': 'pilot',
            'pricelist_id': partner_id.property_product_pricelist and partner_id.property_product_pricelist.id,
            'payment_term_id': partner_id.property_payment_term_id and partner_id.property_payment_term_id.id,
            'order_line': sub_vals,
            'vehicle_number_ids': vehicle_vals,
        })
        # return
        return {
            'type': 'ir.actions.act_window',
            'name': 'Sale Order (%s)' % sale_order.name,
            'res_id': sale_order.id,
            'views': [[False, 'form']],
            'res_model': 'sale.order',
            'view_mode': 'tree,form',
        }
        # Inherit the default get for getting the uploaded subscription ids.


    # Code for getting the device numbers from the uploaded Excel.
    #@api.multi
    def import_file(self):
        data_list = []
        not_exists = []
        subscription_ids = ''
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
                            subscriptions = self.env['sale.order'].search([('serial_no', '=', device_number),('is_subscription', '=', True)],
                                                                                 limit=1)
                            if subscriptions:
                                data_list.append(subscriptions.id)
                            else:
                                not_exists.append(k.get('Device Serial').split('.')[0])
                    if not_exists:
                        raise ValidationError("These Device Serials %s are not existing in the system" % not_exists)
                    subscription_ids = self.env['sale.order'].search([('id', 'in', data_list),('is_subscription', '=', True)])
        return subscription_ids
