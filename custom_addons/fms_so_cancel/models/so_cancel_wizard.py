from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SalesWizard(models.TransientModel):
    _name = 'sale.advance.cancel.inv'
    _description = "so_cancel"

    cancellation_reason = fields.Text('Reason For Cancel')
    order_id = fields.Many2one("sale.order", string="Sale Order")

    @api.model
    def default_get(self, data):
        rec = super(SalesWizard, self).default_get(data)
        context = dict(self._context or {})
        active_model = context.get('active_model')
        active_ids = context.get('active_ids')
        # Checks on context parameters
        if not active_model or not active_ids:
            raise UserError(_("Program error: wizard action executed without active_model or "
                              "active_ids in context."))
        # Checks on received invoice records
        sale = self.env[active_model].browse(active_ids)
        rec.update({
            'order_id': sale.id
        })
        return rec

    # @api.multi
    def update_details(self):
        self.order_id.cancellation_reason = self.cancellation_reason
        self.order_id.write({'state': 'cancel'})
