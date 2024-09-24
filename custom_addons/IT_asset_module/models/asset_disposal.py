from odoo import models, fields, api, _, exceptions


class AssetDisposal(models.Model):
    _name = 'asset.disposal'

    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="ID", readonly=True, copy=False, index=True, default=lambda self: self.env['ir.sequence'].next_by_code('asset.disposal') or _('Dispose'))

    search_asset = fields.Char(string="Search")

    asset_id = fields.Many2one('account.asset.asset', string="Asset", required=True, domain=[('asset_status', '=', 'damaged')])

    dispose_location = fields.Many2one('stock.location', string="Dispose Location")

    disposal_mtd = fields.Selection([('writeoff', "Write-off"), ('sell', "For Sell")],
                                    default='writeoff', string='Disposal Method')

    state = fields.Selection([('draft', "Draft"),
                              ('submitted', "Submitted"),
                              ('approved', "Approved"),
                              ('writeoff', "Write Off"), ('sold', "Sold"), ('close', 'Closed')
                              ], track_visibility='always', default='draft')

    asset_qty = fields.Float(string="Stock Qty", default=1.00)

    asset_net_value = fields.Float(string="Asset Net Value", related='asset_id.value_residual')

    selling_cost = fields.Float(string="Selling Cost")

    profit_cost = fields.Float(string="Profit/Loss", compute='calculate_profit_loss')

    partner_id = fields.Char(string="Customer")

    comments = fields.Text(string="Memo/Reference")

    @api.onchange('search_asset')
    def search_get_asset(self):
        search = self.env['account.asset.asset'].search([('asset_number', '=', self.search_asset),
                                                         ('state', '=', 'open'), ('asset_status', '=', 'damaged')])

        if search:
            self.asset_id = search.id
        elif not search:
            self.asset_id = ''

    @api.depends('asset_net_value', 'selling_cost')
    def calculate_profit_loss(self):
        # if self.asset_net_value and self.selling_cost:
        self.profit_cost = self.asset_net_value - self.selling_cost

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
    def action_selloff(self):
        self.state = 'sold'

    #@api.multi
    def action_writeoff(self):
        self.state = 'writeoff'

    #@api.multi
    def action_close(self):
        dispose = self.env['account.asset.asset'].search([('asset_number', '=', self.asset_id.asset_number)])
        dispose.asset_status = 'disposed'

        xyz = self.env['asset.movement.history'].create({
            'name': self.asset_id.id,
            'location_from': self.asset_id.location.id,
            'location_to': self.dispose_location.id,
            'asset_status': self.asset_id.asset_status
        })
        dispose.state = 'close'
        self.state = 'close'

    #@api.multi
    def return_back(self):
        self.state = 'writeoff'
