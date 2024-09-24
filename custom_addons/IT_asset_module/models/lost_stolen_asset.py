from odoo import models, fields, api, _, exceptions


class LostStolenAsset(models.Model):
    _name = 'lost.asset'

    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="ID", readonly=True, copy=False, index=True,
                       default=lambda self: self.env['ir.sequence'].next_by_code('lost.asset') or _('Lost Asset'))

    employee = fields.Many2one('hr.employee', string="Employee")

    asset_id = fields.Many2one('account.asset.asset', string="Asset", required=True)

    stolen_location = fields.Many2one('stock.location', string="Stolen Location", domain=[('scrap_location', '=', True)])

    evidence = fields.Binary(string="Evidence of Loss", required=True)

    state = fields.Selection([('draft', "Draft"),
                              ('submitted', "Submitted"),
                              ('approved', 'Approved')], track_visibility='always', default='draft')

    @api.onchange('employee')
    def onchange_employee_asset(self):
        domain = {}
        if self.employee:
            assets = self.env['account.asset.asset']
            self.asset_id = None
            domain['asset_id'] = [('assigned_to', 'in', self.employee.name), ('state', '=', 'open')]
        return {'domain': domain}

    #@api.multi
    def action_submit(self):
        self.state = 'submitted'

    #@api.multi
    def action_approve_lost(self):
        lost_asset = self.env['account.asset.asset'].search([('asset_number', '=', self.asset_id.asset_number)])
        lost_asset.asset_status = 'lost'
        lost_asset.location = self.stolen_location.id

        xyz = self.env['asset.movement.history'].create({
            'name': self.asset_id.id,
            'location_from': self.employee.stock_location.id,
            'location_to': self.stolen_location.id,
            'asset_status': ''
        })
        lost_asset.state = 'close'
        self.state = 'approved'
