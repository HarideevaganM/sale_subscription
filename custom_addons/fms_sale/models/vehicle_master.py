from odoo import api, fields, models, _


class VehicleMaster(models.Model):
    _name = 'vehicle.master'

    name = fields.Char('Vehicle No')
    vehicle_name = fields.Char('Vehicle Name')
    chassis_no = fields.Char('Chassis No')
    satellite_imei_no = fields.Char('Satellite IMEI No')
    gsm_no = fields.Char('GSM No')
    gsm_imei_no = fields.Char('GSM IMEI No')
    device_serial_number_id = fields.Many2one("stock.lot", "Device Serial No")
    device_id = fields.Many2one("product.product", "Device Type")
    installation_location_id = fields.Many2one('installation.location', 'Installation Location')
    installation_date = fields.Date("Installation Date")
    activation_date = fields.Date("Activation Date")
    partner_id = fields.Many2one('res.partner', 'Customer Name')
    device_duplicate = fields.Char('Device Type')
    serial_no = fields.Char('Import Device Serial No')
    model = fields.Char('Model/Year')
    reseller_id = fields.Many2one("res.partner", "Reseller")
    device_status = fields.Selection([('active', 'Active'), ('in_active', 'Inactive')], string='Device Status')
