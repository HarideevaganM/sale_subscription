from odoo import api, fields, models, _


class ItcSaleOrderInherit(models.Model):
    _inherit = 'sale.order'

    # Add two fields for ITC.
    show_itc_product = fields.Boolean(string='Show ITC Product', default=False)
    itc_count = fields.Integer(string='ITC Count', compute="compute_itc_count")
    itc_permit_ids = fields.One2many("itc.permit", 'sale_order_id', string="Permit Details")
    itc_notes = fields.Text(string='ITC Notes')

    def create_itc_permit(self):
        """Function for open the wizard when clicking the ITC permit from sale order."""

        return {
            'name': _('Vehicle ITC Permits'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'itc.permit.wizard',
            'target': 'new',
            'context': {'permit_status': 'permit_applied', 'hide_button_related': True}
        }

    @api.onchange('order_line')
    def onchange_product_id(self):
        """Function used to show the ITC Button if selecting the ITC product only from the grid."""

        for rec in self.order_line:
            if rec.product_id:
                product = self.env['product.product'].search([('id', '=', rec.product_id.id)])
                product_temp = self.env['product.template'].search([('id', '=', product.product_tmpl_id.id)])
                if product_temp.is_itc_product:
                    self.show_itc_product = True

    def compute_itc_count(self):
        """ITC count compute function against one sale order."""
        for rec in self:
            itc_ids = self.env['itc.permit'].search([('sale_order_id', '=', rec.id)])
            rec.itc_count = len(itc_ids.ids)

    def show_itc_entries(self):
        """Opening the ITC screen (tree view) while clicking the smart button ITC Permit in SO."""
        return {
            'name': _('ITC Permits'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'itc.permit',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('sale_order_id', '=', self.id)],
            'context': {'default_sale_order_id': self.id},
        }

    #@api.multi
    def action_confirm(self):
        """ Create ITC Permit on Sale Order """

        res = super(ItcSaleOrderInherit, self).action_confirm()

        for line in self.order_line:
            if line.product_id.is_itc_product:
                for qty in range(int(line.product_uom_qty)):
                    self.env['itc.permit'].create({
                        "name": "Draft",
                        "sale_order_id": self.id,
                        "state": "draft",
                    })

        return res

    def _get_itc_order_lines(self):
        orders = self.search([('state', '=', 'sale')])
        itc_data = orders.filtered(lambda x: x.product_id.is_itc_product)
        has_itc = []
        for r in itc_data:
            lines = r.order_line.filtered(lambda l: l.product_id.id == r.product_id.id).mapped('id')
            has_itc += lines

        return has_itc

    #@api.multi
    def _prepare_invoice(self):
        invoice_vals = super(ItcSaleOrderInherit, self)._prepare_invoice()

        permit_lines = []
        for line in self.itc_permit_ids.filtered(lambda l: l.state in ('done', 'applied')):
            if not line.invoice_no and line.free_permit == False:
                permit_vals = {
                    'permit_id': line.id,
                }
                permit_lines.append((0, 0, permit_vals))

        invoice_vals.update({'itc_permit_ids': permit_lines})

        return invoice_vals
