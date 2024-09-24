from odoo import models, fields, api, _, exceptions, tools
import random, collections


class AssetHistory(models.Model):
    _name = 'asset.movement.history'
    _order = "id desc"

    name = fields.Many2one('account.asset.asset', string="Asset")

    # movement_id = fields.Many2one('account.asset.asset')

    location_from = fields.Many2one('stock.location')

    location_to = fields.Many2one('stock.location')

    asset_status = fields.Selection([('allocated', 'Allocated'), ('transit', 'Transit'),
                                     ('unallocated', 'Unallocated'),
                                     ('disposed', 'Disposed'),
                                     ('repair', 'Out for Repair'), ('damaged', 'Damaged')], default='unallocated',
                                    string='Asset')

    movement_date = fields.Char("Transfer Date", default=fields.Datetime.now)


class Asset(models.Model):
    _inherit = 'account.asset.asset'

    asset_number = fields.Char("Asset Number")

    do_manage = fields.Boolean(string="To be Managed")

    serial_number = fields.Char("Asset Tag Number")

    date_received = fields.Date("Date Allocated")

    assigned_to = fields.Many2one('hr.employee', string="Assigned To", readonly=True)

    managed_by = fields.Many2one('hr.employee', string="Managed By", readonly=True)

    initial_location = fields.Many2one('stock.location', string="Initial Location", required=True)

    location = fields.Many2one('stock.location', string="Current Location", readonly=True)

    asset_status = fields.Selection([('allocated', 'Allocated'), ('transit', 'Transit'),
                                     ('unallocated', 'Unallocated'),
                                     ('disposed', 'Disposed'),
                                     ('repair', 'Out for Repair'), ('damaged', 'Damaged'),
                                     ('lost', 'Lost'), ('vanished', 'Vanished')],
                                    default='unallocated', string='Asset Status', readonly=True)

    barcode = fields.Char(
        'Barcode', copy=False, oldname='ean13',
        help="International Article Number used for product identification.")

    start_warranty_date = fields.Date("Start Warranty Date", required=True)

    end_warranty_date = fields.Date("End Warranty Date", required=True)

    asset_model = fields.Many2one('asset.model', string="Asset Model")

    image_medium = fields.Binary(
        "Medium-sized image",
        help="Image of the product variant (Medium-sized image of product template if false).")

    asset_history_id = fields.One2many('asset.movement.history', 'name', string="History", copy=True)

    color = fields.Integer(string='Color Index', default=0)

    @api.onchange('category_id')
    def generate_asset_number(self):
        domain = {}
        if self.category_id:
            self.asset_tag_number = "OC" + str(random.randint(100000, 999999))
            self.asset_model = None
            domain['asset_model'] = [('asset_category', '=', self.category_id.name)]
        return {'domain': domain}

    _sql_constraints = [
        ('asset_number_unique', 'UNIQUE(asset_number)', "Asset Number must be unique"),

        ('barcode_unique', 'unique(barcode)', "A barcode can only be assigned to one product !"),

    ]

    #@api.multi
    def set_to_close(self):
        res = super(Asset, self).set_to_close()
        return res


class AssetTag(models.Model):
    _name = 'asset.tag'

    name = fields.Char(sting="Tag Name")

