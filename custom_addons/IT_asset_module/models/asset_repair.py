from odoo import models, fields, api, _, exceptions
from odoo.exceptions import ValidationError
# import datetime
from datetime import datetime


class AssetRepair(models.Model):
    _name = 'asset.repair'

    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="ID", readonly=True, copy=False, index=True, default=lambda self: self.env['ir.sequence'].next_by_code('asset.repair') or _('Repair'))

    search_asset = fields.Char(string="Search")

    asset_id = fields.Many2one('account.asset.asset', string="Asset", required=True,
                               domain=[('asset_status', '=', ['damaged', 'unallocated'])])

    asset_category = fields.Many2one('account.asset.category', string="Asset Category", required=True, related='asset_id.category_id')

    asset_model = fields.Many2one('asset.model', string="Asset Model", required=True, related='asset_id.asset_model')

    transit_location = fields.Many2one('stock.location', string="Transit Location")

    repairer_location = fields.Many2one('stock.location', string="Repairer Location")

    manufacturer_location = fields.Many2one('stock.location', string="Manufacturer Location")

    state = fields.Selection([('draft', "Draft"),
                              ('submitted', "Submitted"),
                              ('escalated', "Escalated"),
                              ('delivered', "Delivered for Repair"),
                              ('received', "Received"),
                              ('done', 'Done')], track_visibility='always', default='draft')
    asset_qty = fields.Float(string="Stock Qty", default=1.00)

    picking_type_id = fields.Many2one('stock.picking.type', string="Picking Type")

    comment = fields.Text(string="Damage Comment")

    warranty = fields.Date(string="Warranty", related='asset_id.end_warranty_date')
    current_date = fields.Date(string="Current Date", default=datetime.now())
    date_difference = fields.Integer(string="Date Difference")

    @api.onchange('search_asset')
    def search_get_asset(self):
        search = self.env['account.asset.asset'].search([('asset_number', '=', self.search_asset),
                                                         ('state', '=', 'open'), ('asset_status', '=', 'damaged')])

        if search:
            self.asset_category = search.category_id.id
            self.asset_model = search.asset_model.id
            self.asset_id = search.id

            asset_comment = self.env['asset.return'].search(
                [('asset_id.asset_number', '=', self.asset_id.asset_number)])
            self.comment = asset_comment.damaged_comment

            if self.asset_id.end_warranty_date <= fields.Date.context_today(self):
                res = {'warning': {
                    'title': _('Warning'),
                    'message': _('Asset is out of warranty, Send for Repair.')
                }}
                return res
            elif self.asset_id.end_warranty_date > fields.Date.context_today(self):
                res = {'warning': {
                    'title': _('Warning'),
                    'message': _('Asset is within warranty, Send to Manufacturer.')
                }}
                return res

        elif not search:
            self.asset_category = ''
            self.asset_model = ''
            self.asset_id = ''

    #@api.multi
    def action_submit(self):
        self.state = 'submitted'

    #@api.multi
    def return_draft(self):
        self.state = 'draft'

    #@api.multi
    def action_escalate(self):
        update = self.env['account.asset.asset'].search([('asset_number', '=', self.asset_id.asset_number)])
        for record in update:
            record.asset_status = "transit"
            record.location = self.transit_location.id

            xyz = self.env['asset.movement.history'].create({
                'name': self.asset_id.id,
                'location_from': self.asset_id.location.id,
                'location_to': self.transit_location.id,
                'asset_status': self.asset_id.asset_status
            })

        self.state = 'escalated'

    #@api.multi
    def action_delivered(self):
        update = self.env['account.asset.asset'].search([('asset_number', '=', self.asset_id.asset_number)])
        if self.repairer_location:
            update.location = self.repairer_location
            update.asset_status = "repair"
            xyz = self.env['asset.movement.history'].create({
                'name': self.asset_id.id,
                'location_from': self.transit_location.id,
                'location_to': self.repairer_location.id,
                'asset_status': self.asset_id.asset_status
            })
        else:
            update.location = self.manufacturer_location
            update.asset_status = "repair"
            xyz = self.env['asset.movement.history'].create({
                'name': self.asset_id.id,
                'location_from': self.transit_location.id,
                'location_to': self.manufacturer_location.id,
                'asset_status': self.asset_id.asset_status
            })
        self.state = 'delivered'

    #@api.multi
    def action_receive(self):
        update = self.env['account.asset.asset'].sudo().search([('asset_number', '=', self.asset_id.asset_number)])
        update.location = self.asset_id.initial_location
        update.asset_status = 'unallocated'
        if self.repairer_location:
            xyz = self.env['asset.movement.history'].sudo().create({
                'name': self.asset_id.id,
                'location_from': self.repairer_location.id,
                'location_to': self.asset_id.initial_location.id,
                'asset_status': self.asset_id.asset_status
            })
        else:
            xyz = self.env['asset.movement.history'].sudo().create({
                'name': self.asset_id.id,
                'location_from': self.manufacturer_location.id,
                'location_to': self.asset_id.initial_location.id,
                'asset_status': self.asset_id.asset_status
            })
        self.state = 'received'

    #@api.multi
    def action_done(self):
        self.state = 'done'

    #@api.multi
    def return_back(self):
        self.state = 'draft'
