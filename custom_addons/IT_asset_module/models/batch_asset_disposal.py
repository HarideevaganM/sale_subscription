from odoo import models, fields, api, _, exceptions


class BatchAssetDisposalLine(models.Model):
    _name = 'batch.asset.disposal.line'

    name = fields.Many2one('account.asset.asset', string="Asset", domain="[('asset_status', '=', 'damaged')]")

    asset_net_value = fields.Float(string="Asset Net Value", related='name.value_residual')

    batch_asset_id = fields.Many2one('batch.asset.disposal')

    asset_number = fields.Char("Asset Number", related='name.asset_number')

    disposal_mtd = fields.Selection([('writeoff', "Write-off"), ('sell', "For Sell")],
                                    default='sell', string='Disposal Method')

    selling_cost = fields.Float(string="Selling Cost")

    profit_cost = fields.Float(string="Profit/Loss", compute='calculate_profit_loss')

    @api.depends('asset_net_value', 'selling_cost')
    def calculate_profit_loss(self):
        for record in self:
            record.profit_cost = record.asset_net_value - record.selling_cost


class BatchAssetDisposal(models.Model):
    _name = 'batch.asset.disposal'

    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="ID", readonly=True, copy=False, index=True, default=lambda self: self.env['ir.sequence'].next_by_code('batch.asset.disposal') or _('Dispose'))

    batch_disposal_line = fields.One2many('batch.asset.disposal.line', 'batch_asset_id', string="Approve Requests")

    dispose_location = fields.Many2one('stock.location', string="Dispose Location")

    partner_id = fields.Char(string="Customer")

    state = fields.Selection([('draft', "Draft"),
                              ('submitted', "Submitted"),
                              ('approved', "Approved"),
                              ('close', 'Closed')
                              ], track_visibility='always', default='draft')

    comments = fields.Text(string="Memo/Reference")

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
    def action_close(self):
        for record in self.batch_disposal_line:
            dispose = self.env['account.asset.asset'].search([('asset_number', '=', record.name.asset_number)])
            dispose.asset_status = 'disposed'

            xyz = self.env['asset.movement.history'].create({
                'name': record.name.id,
                'location_from': record.name.location.id,
                'location_to': self.dispose_location.id,
                'asset_status': record.name.asset_status
            })
            dispose.state = 'close'
            self.state = 'close'

