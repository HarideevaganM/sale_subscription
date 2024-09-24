# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from openerp.exceptions import ValidationError, Warning
import requests
import json
from datetime import datetime
import logging
_logger = logging.getLogger("Device")

class VehicleMaster(models.Model):
    _inherit='vehicle.master'

    def _get_domain(self):
        domain = []
        company_id = self.env.user.company_id
        predicate = fields.Date.today()
        sign = company_id.sign
        if company_id.predicate:
            predicate = company_id.predicate
        if company_id.filters:
            domain.append({"Display": company_id.filters, "Predicate": ("%s'%s'")%(sign,predicate)})
        return domain

    def _find_product(self, product, product_code):
        product_id = self.env['product.product'].search([('name', '=', product), ('default_code', '=', product_code)], limit=1)
        # if product_id:
        #     _logger.info('============= Finding Product  ====================== %s - %s', product,product_code)
        # else:
        #     _logger.info('============= Product Not Found   ====================== %s - %s', product, product_code)
        if not product_id:
            _logger.info('============= Product Not Found   ====================== %s - %s', product, product_code)
        return product_id

    def _get_product_job_cart(self, so_name, job_no):
        job_id = self.env['job.card']
        if so_name and job_no:
            sale_id =  self.env['sale.order'].search([('name', '=', so_name)], limit=1)
            if sale_id:
                job_id = self.env['job.card'].search([('sale_order_id', '=', sale_id.id), ('name', '=', job_no), ('device_status', 'in', ('in_active', False))], limit=1)
                # if not job_id:
                #     _logger.info('============= Job Card Already Processed ==================== %s', job_no)
            return job_id
        else:
            _logger.info('============= No Such Sale Order or Job Card  ====================== %s', job_no)
        return False

    def _find_partner(self, company):
        partner_id = self.env['res.partner'].search([('name', '=', company)], limit=1)
        if partner_id:
            _logger.info('============= Finding Partner ======================')
        else:
            _logger.info('============= Partner Not Found ======================')
        return partner_id

    def send_response_to_user(self, serial, product, product_code, sale_order, job_id):
        if sale_order and serial and product:
            # sale_id =  self.env['sale.order'].search([('name', '=', sale_order)], limit=1)
            if job_id:
                message = "<span> Serial not available in stock location for product </span> " + product_code + "<span> - </span>" + product + "<span> and serial </span>" + serial
                job_id.sudo().message_post(body=message, subject="Serial not available in stock location")

    def _lot_exist(self, serial, product, product_code, sale_order, job_id):
        lot_id = self.env['stock.lot']
        company_id = self.env.user.company_id
        warehouse_id = self.env['stock.warehouse'].search([('company_id', '=', company_id.id)], limit=1)
        lot_stock_id = warehouse_id.lot_stock_id if warehouse_id else False
        if serial and product and product_code and sale_order:
            product_id = self._find_product(product, product_code)
            if not product_id:
                return True
            else:
                lot_id = self.env['stock.lot'].search([('name', '=', serial), ('product_id', '=', product_id.id)], limit=1)
                if lot_id:
                    if lot_stock_id:
                        quants = lot_id.quant_ids.filtered(lambda x: x.location_id == lot_stock_id)
                        if quants and sum(quants.mapped('quantity')) >= 1:
                            _logger.info('============= Serial Available in Stock Location ====================== %s - %s', product, serial)
                        else:
                            lot_id = False
                            _logger.info('============= Serial Not Available in Stock Location ====================== %s - %s', product, serial)
                # else:
                #     _logger.info('============= Serial Not Exist ====================== %s - %s', product, serial)
                if not lot_id:
                    self.send_response_to_user(serial, product, product_code, sale_order, job_id)
        return lot_id

    def _get_data(self, company_id):
        try:
            if not company_id:
                company_id = self.env.user.company_id
            header = {'Authorization': 'Bearer ' + company_id.token}
            result_url = company_id.result_url
            req_fields = ["SaleOrder","JobOrderNo","Vehicle","Serial","ActivationDate","InstallationDate"]
            send_data = {
                "EntityName":"OdooMaster",
                "Fields": req_fields,
                "Filter":[],
                "Parameter": company_id.param,
                "OrderBy": company_id.order_by,
                "TopClause": company_id.topclause
                }
            response = requests.post(result_url, json=send_data, headers=header, verify=False)
            _logger.info('============= Response ====================== : %s', response)
            data = response.json()
            if not data.get('result'):
                message = "<p>Job Card API Result is empty.</p>" \
                          "<p>Please check if the token is updated or there's something wrong with the " \
                          "configurations. Otherwise, please ignore this email.</p>"
                _logger.info('============= Job Card API Result is empty ============= : %s', response)
                message += "<p>Response Status: %s </p>" % response.status_code
                subject = "Job Card API Result is Empty"
                self.send_unsuccessful_fms_api(subject, message)
                return []
            if data and data.get('result'):
                data_list = []
                exist_list = []
                exist_dict = {}
                result_list = data.get('result').split('\r\n')
                if result_list:
                    keys = result_list[0].split(',')
                    values = result_list[1].split(',')
                    job_id = self.env['job.card']
                    product = self.env['product.product']
                    for i in result_list[1:]:
                        values = i.split(',')
                        column_dict = dict(zip(keys, values))
                        serial = column_dict.get('Serial')
                        sale_order = column_dict.get('SaleOrder')
                        job_no = column_dict.get('JobOrderNo')
                        if sale_order and job_no:
                            job_id = self._get_product_job_cart(sale_order, job_no)
                        if not job_id:
                            continue
                        else:
                            product = job_id.device_id and job_id.device_id.name
                            product_code = job_id.device_id.default_code
                        if serial and product and product_code:
                            exist_dict = dict(zip([serial], [product]))
                            if exist_dict in exist_list:
                                continue
                            exist_list.append(exist_dict)
                            if not self._lot_exist(serial, product, product_code, sale_order, job_id):
                                continue
                        data_list.append(column_dict)
                    return data_list
        except Exception as e:
            message = "Method get_data has some issues. %s" % e
            _logger.info('============= %s ======================', message)
            subject = "Job Card API Failed"
            self.send_unsuccessful_fms_api(subject, message)
            return []
  
    def _create_vehicle_master(self, company):
        try:
            installation_date = False
            activation_date = False
            vehicle_id = self.env['vehicle.master']
            lot_id = self.env['stock.lot']
            partner_id = self.env['res.partner']
            product_id = self.env['product.product']
            responsive_data = self._get_data(company)
            for rec in responsive_data:
                _logger.info('============= Responsive Data ====================== %s', rec)
                sale_order = rec.get('SaleOrder')
                job_order = rec.get('JobOrderNo')
                if sale_order and sale_order:
                    job_id = self._get_product_job_cart(sale_order, job_order)
                    if job_id:
                        _logger.info('============= Job Card Found ==================== %s', job_id.name)
                        partner_id = job_id.reseller_id if job_id.reseller_id else job_id.company_id
                        product_id = job_id.device_id
                    if partner_id and product_id:
                        vehicle = rec.get('Vehicle')
                        serial = rec.get('Serial')
                        date_installation = rec.get('InstallationDate') and rec.get('InstallationDate').split(' ')
                        date_activation = rec.get('ActivationDate') and rec.get('ActivationDate').split(' ')
                        installation_date = datetime.strptime(date_installation[0], '%m/%d/%Y') if date_installation else False
                        activation_date = datetime.strptime(date_activation[0], '%m/%d/%Y') if date_activation else False
                        if serial:
                            lot_id = self._lot_exist(serial, product_id.name, product_id.default_code, sale_order, job_id)
                        if vehicle and lot_id:
                            vehicle_id = self.env['vehicle.master'].create({
                                'name' : vehicle,
                                'vehicle_name': vehicle,
                                'partner_id': partner_id.id,
                                'device_id': product_id.id,
                                'device_serial_number_id': lot_id.id,
                                'installation_date': installation_date,
                                'activation_date': activation_date,
                            })
                            _logger.info('============= New Vehicle %s : is Created ======================', vehicle)
                        if job_id and vehicle_id:
                            job_id.write({
                                'device_serial_number_new_id': lot_id and lot_id.id,
                                'vehicle_number': vehicle_id and vehicle_id.id,
                                'installation_date': installation_date,
                                'activation_date': activation_date,
                                'device_status': 'active',
                            })
                            job_id.to_configured()
                            job_id.to_installed()
                            job_id.submit_job_card()
                            job_id.close_job_card()
                            _logger.info('============= Job Card %s : is Updated ======================', job_id.name)
        except Exception as e:
            _logger.info('============= Something went wrong in creation vehicle master method ====================== %s', e)
            return False
        return True

    def import_vehicle_master(self):
        company = self.env.user.company_id
        if company and company.token and company.result_url:
            self._create_vehicle_master(company)
        else:
            message = "Company or Token or Data Url Are Missing"
            subject = "Job Card API Failed"
            _logger.info('============= %s ======================', message)
            self.send_unsuccessful_fms_api(subject, message)
        return True

    def send_unsuccessful_fms_api(self, subject, body):
        template_obj = self.env['mail.mail']
        company = self.env['res.company'].browse(1)
        email_to = self.env['ir.config_parameter'].get_param('fms_api_email_notify')

        template_data = {
            'subject': "%s - %s" % (subject, company.name),
            'body_html': body,
            'email_from': company.email,
            'email_to': email_to
        }

        template_id = template_obj.create(template_data)
        template_id.send()
