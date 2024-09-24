# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class UpdateSoPoInvoiceStatusWizard(models.TransientModel):
    _name = 'bbis.update.po.so.invoice.status'
    _description = 'BBIS Update SO/PO Invoice Status'

    sale_order_id = fields.Many2one('sale.order', readonly=True)
    so_invoice_status = fields.Selection([('upselling', 'Upselling Opportunity'), ('invoiced', 'Fully Invoiced'),
                                          ('to invoice', 'To Invoice'), ('no', 'Nothing to Invoice')],
                                         string="SO Invoice Status")
    purchase_order_id = fields.Many2one('purchase.order', readonly=True)
    po_invoice_status = fields.Selection([('no', 'Nothing to Bill'), ('to invoice', 'Waiting Bills'),
                                          ('invoiced', 'No Bill to Receive')], string="PO Invoice Status")
    model_type = fields.Selection([('sale', 'Sale Order'), ('purchase', 'Purchase Order')], readonly=True)
    reason = fields.Text(required=True)

    def update_invoice_status(self):
        # print("Update")
        if not self.model_type:
            raise ValidationError("Sorry, you need to select Model Type.")

        if self.model_type == 'sale':
            if not self.sale_order_id:
                raise ValidationError("Sorry, you need to select sale order.")

            self.sale_order_id.write({'invoice_status': self.so_invoice_status,
                                      'invoice_status_change': self.reason})

        if self.model_type == 'purchase':
            if not self.purchase_order_id:
                raise ValidationError("Sorry, you need to select purchase order.")
            # print(self.po_invoice_status)
            self.purchase_order_id.write({'invoice_status': self.po_invoice_status,
                                          'invoice_status_change': self.reason})
