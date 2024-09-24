from odoo import models, fields, api, _, exceptions


class InternalTransferLine(models.Model):
    _name = 'internal.transfer.line'

    name = fields.Many2one('account.asset.asset', string="Asset", domain="[('asset_status', '=', 'unallocated')]")

    transfer_id = fields.Many2one('internal.transfer.request')

    asset_qty = fields.Float(string="Stock Qty", default=1.00, readonly=True)

    asset_number = fields.Char("Asset Number", related='name.asset_number')


class InternalTransferRequest(models.Model):
    _name = 'internal.transfer.request'

    _inherit = ['mail.thread', 'mail.activity.mixin']

    regional_manager = fields.Many2one('res.users', string="Regional Manager")

    source_location = fields.Many2one('stock.location', string="Source Location")

    transit_location = fields.Many2one('stock.location', string="Transit Location", required=True)

    destination_location = fields.Many2one('stock.location', string="Destination Location")

    approve_requests_line = fields.One2many('internal.transfer.line', 'transfer_id', string="Approve Requests")

    name = fields.Char(string="ID", readonly=True, copy=False, index=True, default=lambda self: self.env['ir.sequence'].next_by_code('internal.transfer.request') or _('Internal'))

    state = fields.Selection([('draft', "Draft"),
                              ('submitted', "Submitted"),
                              ('approved', "Approved"),
                              ('allocated', "Allocated/Transit"), ('received', "Received"),
                              ('close', 'Close')], track_visibility='always', default='draft')

    #@api.multi
    def action_submit(self):
        self.state = 'submitted'

    #@api.multi
    def return_draft(self):
        self.state = 'draft'

    #@api.multi
    def action_approve(self):
        self.state = 'approved'

    #@api.multi
    def action_allocate(self):
        for record in self.approve_requests_line:
            transit = self.env['account.asset.asset'].search([('asset_number', '=', record.name.asset_number)])
            transit.asset_status = "transit"
            transit.date_received = fields.Date.context_today(self)
            transit.location = self.transit_location.id

        for record in self.approve_requests_line:
            xyz = self.env['asset.movement.history'].create({
                'name': record.name.id,
                'location_from': record.name.initial_location.id,
                'location_to': self.transit_location.id,
                'asset_status': record.name.asset_status
            })
        self.state = 'allocated'

    #@api.multi
    def action_receive(self):
        for record in self.approve_requests_line:
            transit = self.env['account.asset.asset'].search([('asset_number', '=', record.name.asset_number)])
            transit.asset_status = "unallocated"
            # transit.location = self.regional_manager
            transit.date_received = fields.Date.context_today(self)
            transit.location = self.destination_location.id

        for record in self.approve_requests_line:
            xyz = self.env['asset.movement.history'].create({
                'name': record.name.id,
                'location_from': record.name.location.id,
                'location_to': self.destination_location.id,
                'asset_status': record.name.asset_status
            })
        self.state = 'received'

    #@api.multi
    def action_close(self):
        self.state = 'close'
