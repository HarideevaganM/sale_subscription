from odoo import models, fields, api, _, exceptions
from odoo.exceptions import ValidationError


class AssetReturn(models.Model):
    _name = 'asset.return'

    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="ID", readonly=True, copy=False, index=True, default=lambda self: self.env['ir.sequence'].next_by_code('asset.return') or _('Return'))

    employee = fields.Many2one('hr.employee', string="Employee")

    asset_id = fields.Many2one('account.asset.asset', string="Asset", required=True)

    asset_current_location = fields.Many2one('stock.location', related='asset_id.location')

    asset_condition = fields.Selection([('functioning', "Still Functioning"),
                                        ('damaged', "Damaged")], default='functioning')

    damages_location = fields.Many2one('stock.location', string="Dispose Location", related='asset_id.location', readonly=1)

    return_location = fields.Many2one('stock.location', string="Return Location", related='asset_id.location', readonly=1)

    damaged_comment = fields.Text(string="Comment")

    state = fields.Selection([('draft', "Draft"),
                              ('return', "Returned"),
                              ('damaged', 'Damaged'), ('done', 'Done')], track_visibility='always', default='draft')

    @api.onchange('employee')
    def onchange_employee_asset(self):
        domain = {}
        if self.employee:
            domain['asset_id'] = ['|', ('assigned_to', 'in', self.employee.name), ('managed_by', 'in', self.employee.name), ('state', '=', 'open')]
        return {'domain': domain or False}

    #@api.multi
    def action_safe_return(self):
        if not self.employee:
            raise ValidationError(_('Error! You must select an employee.'))
        else:
            self.state = 'return'

    #@api.multi
    def action_damage_return(self):
        self.state = 'damaged'

    #@api.multi
    def action_done(self):
        update = self.env['account.asset.asset'].search([('asset_number', '=', self.asset_id.asset_number)])
        if update.do_manage is True:
            update.managed_by = ''
        else:
            update.assigned_to = ''

        if self.asset_condition == 'damaged':
            update.asset_status = 'damaged'
            update.location = self.damages_location.id

            xyz = self.env['asset.movement.history'].create({
                'name': self.asset_id.id,

                'location_from': self.employee.stock_location.id,
                'location_to': self.damages_location.id,
                'asset_status': self.asset_id.asset_status
            })

        else:
            update.location = self.return_location.id
            update.asset_status = 'unallocated'

            xyz = self.env['asset.movement.history'].create({
                'name': self.asset_id.id,
                'location_from': self.employee.stock_location.id,
                'location_to': self.return_location.id,
                'asset_status': self.asset_id.asset_status
            })

        self.state = 'done'

