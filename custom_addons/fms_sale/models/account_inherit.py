from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from odoo import api, exceptions, fields, models, _
from odoo.exceptions import UserError, AccessError
from odoo.addons import decimal_precision as dp


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.model
    def _get_default_journal(self):
        ''' Get the default journal.
        It could either be passed through the context using the 'default_journal_id' key containing its id,
        either be determined by the default type.
        '''
        move_type = self._context.get('default_move_type', 'entry')
        if move_type in self.get_sale_types(include_receipts=True):
            journal_types = ['sale']
        elif move_type in self.get_purchase_types(include_receipts=True):
            journal_types = ['purchase']
        else:
            journal_types = self._context.get('default_move_journal_types', ['general'])

        if self._context.get('default_journal_id'):
            journal = self.env['account.journal'].browse(self._context['default_journal_id'])

            if move_type != 'entry' and journal.type not in journal_types:
                raise UserError(_(
                    "Cannot create an invoice of type %(move_type)s with a journal having %(journal_type)s as type.",
                    move_type=move_type,
                    journal_type=journal.type,
                ))
        else:
            journal = self._search_default_journal(journal_types)

        return journal
    
    # @api.multi
    def action_post(self):
        if self.env.user.has_group('purchase.group_purchase_manager') or self.env.user.has_group('account.group_account_invoice'):
            res = super(AccountMove, self).action_post()
            return res
        else:
            raise UserError(_("Invoice must be Validated by Manager."))
    
    # @api.one
    @api.depends('inclusive_invoice_line.price_subtotal', 'currency_id')
    def _compute_amount_inclusive(self):
        for rec in self:
            amount_untaxed1 = 0
            round_currr = rec.currency_id.round
            amount_untaxed1 += sum(line.price_subtotal for line in rec.inclusive_invoice_line)
            rec.amount_untaxed1 = amount_untaxed1
            rec.amount_total1 = amount_untaxed1
    
    purchase_order_no = fields.Char("PO #")
    purchase_order_date = fields.Date("PO Date")
    client_ref = fields.Char("Ref #")
    sale_type = fields.Selection([('cash', 'Walk In/Cash Sale'),
                                  ('purchase', 'Unit Sale'),
                                  ('lease', 'Lease Sale'),
                                  ('rental', 'Rental Sale'),
                                  ('pilot', 'Renewal Sale'),
                                  ], string='Sale Type')
    inclusive_invoice_line = fields.One2many('inclusive.invoice.line', 'invoice_id', string="Inclusive Invoice Products")
    amount_untaxed1 = fields.Monetary(string='Untaxed Amount',
        store=True, readonly=True, compute='_compute_amount_inclusive', track_visibility='always')   
    amount_total1 = fields.Monetary(string='Total',
        store=True, readonly=True, compute='_compute_amount_inclusive')

    vehicle_detail_ids = fields.One2many("invoice.vehicle.details", 'invoice_id', string="Vehicle Details")
    bill_start_date = fields.Datetime(string="Billing Start Date")
    bill_end_date = fields.Datetime(string="Billing End Date")
    is_reseller = fields.Boolean("Reseller", default=False, store=True, related='partner_id.is_reseller')
    journal_id = fields.Many2one('account.journal', string='Journal', required=True, readonly=True,
                                 states={'draft': [('readonly', False)]},
                                 check_company=True, domain="[('company_id', '=', company_id)]",
                                 default=_get_default_journal)


class InclusiveInvoiceProduct(models.Model):
    _name = "inclusive.invoice.line"

    invoice_id = fields.Many2one('account.move', 'Account Move')
    name = fields.Text(string='Description')
    price_unit = fields.Monetary('Unit Price', default=0.0)
    currency_id = fields.Many2one(related='invoice_id.currency_id', store=True, string='Currency', readonly=True)
    price_subtotal = fields.Monetary(string='Subtotal', compute='compute_price_subtotal')
    product_id = fields.Many2one('product.product', string='Product')
    product_uom_qty = fields.Integer(string='Quantity')
    product_uom = fields.Many2one('uom.uom', string='Unit of Measure')
    discount = fields.Float(string='Discount (%)', digits=dp.get_precision('Discount'),
                            default=0.0)

    # @api.one
    @api.depends('product_uom_qty', 'price_unit')
    def compute_price_subtotal(self):
        for rec in self:
            rec.price_subtotal = (rec.product_uom_qty * rec.price_unit) * (1 - (rec.discount or 0.0) / 100.0)

    @api.onchange('product_id')
    def onchange_product_details(self):
        if self.product_id:
            self.update({
                'price_unit': self.product_id.lst_price if self.product_id.lst_price else 0,
                'product_uom': self.product_id.uom_id if self.product_id.uom_id else False,
                'name': self.product_id.description if self.product_id.description else '',
            })


class ProductProduct(models.Model):
    _inherit = 'product.product'

    stock_value = fields.Float('Values', compute='_compute_stock_value', digits=(14, 3))
    qty_at_date = fields.Float('Quantity', compute='_compute_stock_value', digits=(12, 0))


class InvoiceVehicleDetails(models.Model):
    _name = "invoice.vehicle.details"

    invoice_id = fields.Many2one('account.move', string="Invoice")
    serial_no_id = fields.Many2one("stock.lot", string="Device Serial No")
    device_id = fields.Many2one("product.product", string="Device Name")
    vehicle_id = fields.Many2one('vehicle.master', string="Vehicle Reg No")
    installation_date = fields.Date('Installation Date')
    status = fields.Selection([('active', 'Active'), ('in_active', 'In Active')], string='Status')
