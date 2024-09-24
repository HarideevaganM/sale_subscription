from odoo import api, fields, models, _


class PurchaseRequisitionInherit(models.Model):
    _inherit = "purchase.requisition"
    
    sale_id = fields.Many2one('sale.order', 'Sale Reference')


class PurchaseOrderInherit(models.Model):
    _inherit = "purchase.order"
    
    sale_id = fields.Many2one('sale.order', 'Sale Reference')
    make_vendor_readonly = fields.Boolean("vendor")
    state = fields.Selection([
        ('draft', 'RFQ'),
        ('sent', 'RFQ Sent'),
        ('to approve', 'To Approve'),
        ('awaiting_approval',"Awaiting Approval"),
        ('manager_approved',"Manager Approved"),
        ('purchase', 'Purchase Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'),
        ], string='Status', readonly=True, index=True, copy=False, default='draft', track_visibility='onchange')
    
    instructions = fields.Text('Instructions')
    warranty = fields.Char('Warranty')

    #
    # @api.multi
    def update_sale(self):
        if self.sale_id:
            purchase_line_obj = self.env['purchase.order.line'].search([('order_id', '=', self.id)])
            for line in purchase_line_obj:
                self.env.cr.execute("""update sale_order_line set price_unit = %s 
                where order_id= %s and product_id =%s""" % (line.price_unit, self.sale_id.id, line.product_id.id))
    
    # @api.multi
    def submit_order(self):
        self.write({'state': 'awaiting_approval'})
    
    # @api.multi
    def manager_approval(self):
        self.write({'state': 'manager_approved'})
        
    # @api.multi
    def button_confirm(self):
        for order in self:
            if order.state not in ['draft', 'sent', 'awaiting_approval', 'manager_approved']:
                continue
            order._add_supplier_to_product()
            # Deal with double validation process
            if order.company_id.po_double_validation == 'one_step'\
                    or (order.company_id.po_double_validation == 'two_step'\
                        and order.amount_total < self.env.user.company_id.currency_id.compute(order.company_id.po_double_validation_amount, order.currency_id))\
                    or order.user_has_groups('purchase.group_purchase_manager'):
                order.button_approve()
            else:
                order.write({'state': 'to approve'})
        return True   


class MaterialPurchaseRequisitionInherit(models.Model):
    _inherit = "material.purchase.requisition"

    partner_id = fields.Many2one("res.partner", string="Customer", required=False, related='task_id.partner_id', store=True)
    
          
