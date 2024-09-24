from odoo import fields, models, api, _


class BBISVehicleMasterInherit(models.Model):
    _name = "vehicle.master"
    _inherit = ['vehicle.master', 'mail.thread', 'mail.activity.mixin']

    # Inherit the vehicle master for adding the track visibility.
    name = fields.Char('Vehicle No', track_visibility='onchange')
    vehicle_name = fields.Char('Vehicle Name', track_visibility='onchange')
    device_serial_number_id = fields.Many2one("stock.lot", "Device Serial No", track_visibility='onchange')
    device_id = fields.Many2one("product.product", "Device Type", track_visibility='onchange')
    partner_id = fields.Many2one('res.partner', 'Customer Name', track_visibility='onchange')

