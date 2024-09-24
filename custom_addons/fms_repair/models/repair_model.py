from odoo import api, fields, models, _
from odoo.exceptions import UserError, AccessError,ValidationError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from datetime import datetime, timedelta, date
from dateutil import parser
# from openerp import api, fields, models
import re


class RepairOrder(models.Model):
    _inherit = "repair.order"

    name = fields.Char(
        'Device Maintenance Reference',
        default=lambda self: self.env['ir.sequence'].next_by_code('repair.order'),
        copy=False, required=True,
        states={'confirmed': [('readonly', True)]}, readonly=True)
    rep_history_line = fields.One2many('new.repair.order', 'new_id', string="History")
    lot_id = fields.Many2one(
        'stock.lot', 'Device Serial No',
        domain="[('product_id','=', product_id)]",
        help="Products repaired are all belonging to this lot", oldname="prodlot_id")
    picking_id = fields.Many2one('stock.picking',"DO Number", store=True)
    delivery_count = fields.Integer('Count', compute='compute_delivery_count')
    location_src_id = fields.Many2one('stock.location', "Location", store=True)
    location_des_id = fields.Many2one('stock.location', "Destination Location", store=True)
    is_invoice = fields.Boolean('Is Invoice')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('cancel', 'Cancelled'),
        ('confirmed', 'Confirmed'),
        ('under_repair', 'Under Maintainance'),
        ('ready', 'Ready'),
        ('2binvoiced', 'To be Invoiced'),
        ('invoice_except', 'Invoice Exception'),
        ('invoiced','Invoiced'),
        ('done', 'Done'),
        ('assigned','Assigned')], string='Status',
        copy=False, default='draft', readonly=True, track_visibility='onchange',
        help="* The \'Draft\' status is used when a user is encoding a new and unconfirmed repair order.\n"
             "* The \'Confirmed\' status is used when a user confirms the repair order.\n"
             "* The \'Ready to Repair\' status is used to start to repairing, user can start repairing only after repair order is confirmed.\n"
             "* The \'To be Invoiced\' status is used to generate the invoice before or after repairing done.\n"
             "* The \'Done\' status is set when repairing is completed.\n"
             "* The \'Cancelled\' status is used when user cancel repair order.")
    partner_id = fields.Many2one(comodel_name="res.partner", string="Customer", required=True)
    ticket_id = fields.Many2one("website.support.ticket" , "Ticket")
    amount_untaxed = fields.Float('Untaxed Amount', compute='_amount_untaxed', store=True, digits=(16,3))
    amount_tax = fields.Float('Taxes', compute='_amount_tax', store=True, digits=(16,3))
    amount_total = fields.Float('Total', compute='_amount_total', store=True, digits=(16,3))
    product_id = fields.Many2one('product.product', string='Product', readonly=True, required=True, states={'draft': [('readonly', False)]})
    version_number = fields.Char("Version")
    product_firmware_id = fields.Many2one('product.product',"Product")
    firmware_lot_id = fields.Many2one('stock.lot', 'Serial No', domain="[('product_id','=', product_firmware_id)]")

    # @api.multi
    def action_invoice_create_maintainance(self, group=False):
        """ Creates invoice(s) for repair order.
        @param group: It is set to true when group invoice is to be generated.
        @return: Invoice Ids.
        """
        self.env.cr.execute("""SELECT mpl.product_id,mpl.name,mpl.product_uom_qty,mpl.price_unit FROM repair_order mr
                           JOIN repair_line mpl ON (mr.id=mpl.repair_id) WHERE mr.id=%d and mpl.type='add'""" % self.id)
        repair_invoice = self.env.cr.dictfetchall()
        if repair_invoice != []:
            self.state = 'invoiced'
            res = dict.fromkeys(self.ids, False)
            invoices_group = {}
            InvoiceLine = self.env['account.move.line']
            Invoice = self.env['account.move']
            for repair in self.filtered(lambda repair: repair.state not in ('draft', 'cancel') and not repair.invoice_id):
                if not repair.partner_id.id and not repair.partner_invoice_id.id:
                    raise UserError(_('You have to select a Partner Invoice Address in the repair form!'))
                comment = repair.quotation_notes
                if repair.invoice_method != 'none':
                    if group and repair.partner_invoice_id.id in invoices_group:
                        invoice = invoices_group[repair.partner_invoice_id.id]
                        invoice.write({
                            'name': invoice.name + ', ' + repair.name,
                            'origin': invoice.origin + ', ' + repair.name,
                            'comment': (comment and (invoice.comment and invoice.comment + "\n" + comment or comment)) or (
                            invoice.comment and invoice.comment or ''),
                        })
                    else:
                        if not repair.partner_id.property_account_receivable_id:
                            raise UserError(_('No account defined for partner "%s".') % repair.partner_id.name)
                        invoice = Invoice.create({
                            'name': repair.name,
                            'invoice_origin': repair.name,
                            'move_type': 'out_invoice',
                            'account_id': repair.partner_id.property_account_receivable_id.id,
                            'partner_id': repair.partner_invoice_id.id or repair.partner_id.id,
                            'currency_id': repair.pricelist_id.currency_id.id,
                            'comment': repair.quotation_notes,
                            'fiscal_position_id': repair.partner_id.property_account_position_id.id
                        })
                        invoices_group[repair.partner_invoice_id.id] = invoice
                    repair.write({'invoiced': True, 'invoice_id': invoice.id})

                    for operation in repair.operations:
                        if operation.type == 'add':
                            if group:
                                name = repair.name + '-' + operation.name
                            else:
                                name = operation.name

                            if operation.product_id.property_account_income_id:
                                account_id = operation.product_id.property_account_income_id.id
                            elif operation.product_id.categ_id.property_account_income_categ_id:
                                account_id = operation.product_id.categ_id.property_account_income_categ_id.id
                            else:
                                raise UserError(_('No account defined for product "%s".') % operation.product_id.name)

                            invoice_line = InvoiceLine.create({
                                'move_id': invoice.id,
                                'name': name,
                                'origin': repair.name,
                                'account_id': account_id,
                                'quantity': operation.product_uom_qty,
                                'tax_ids': [(6, 0, [x.id for x in operation.tax_id])],
                                'uom_id': operation.product_uom.id,
                                'price_unit': operation.price_unit,
                                'price_subtotal': operation.product_uom_qty * operation.price_unit,
                                'product_id': operation.product_id and operation.product_id.id or False
                            })
                            operation.write({'invoiced': True, 'invoice_line_id': invoice_line.id})
                    for fee in repair.fees_lines:
                        if group:
                            name = repair.name + '-' + fee.name
                        else:
                            name = fee.name
                        if not fee.product_id:
                            raise UserError(_('No product defined on Fees!'))

                        if fee.product_id.property_account_income_id:
                            account_id = fee.product_id.property_account_income_id.id
                        elif fee.product_id.categ_id.property_account_income_categ_id:
                            account_id = fee.product_id.categ_id.property_account_income_categ_id.id
                        else:
                            raise UserError(_('No account defined for product "%s".') % fee.product_id.name)

                        invoice_line = InvoiceLine.create({
                            'move_id': invoice.id,
                            'name': name,
                            'origin': repair.name,
                            'account_id': account_id,
                            'quantity': fee.product_uom_qty,
                            'tax_ids': [(6, 0, [x.id for x in fee.tax_id])],
                            'uom_id': fee.product_uom.id,
                            'product_id': fee.product_id and fee.product_id.id or False,
                            'price_unit': fee.price_unit,
                            'price_subtotal': fee.product_uom_qty * fee.price_unit
                        })
                        fee.write({'invoiced': True, 'invoice_line_id': invoice_line.id})
                    invoice.compute_taxes()
                    res[repair.id] = invoice.id
                    return res
        else:
            raise ValidationError("Please Add Line For Product in Parts")

    # @api.multi
    def action_invoice_create_maintainance_before(self, group=False):
        """ Creates invoice(s) for repair order.
        @param group: It is set to true when group invoice is to be generated.
        @return: Invoice Ids.
        """
        self.env.cr.execute("""SELECT mpl.product_id,mpl.name,mpl.product_uom_qty,mpl.price_unit FROM repair_order mr
                               JOIN repair_line mpl ON (mr.id=mpl.repair_id) WHERE mr.id=%d and mpl.type='add'""" % self.id)
        repair_invoice = self.env.cr.dictfetchall()
        if repair_invoice != []:
            self.state = 'invoiced'
            res = dict.fromkeys(self.ids, False)
            invoices_group = {}
            InvoiceLine = self.env['account.move.line']
            Invoice = self.env['account.move']
            for repair in self.filtered(
                    lambda repair: repair.state not in ('draft', 'cancel') and not repair.invoice_id):
                if not repair.partner_id.id and not repair.partner_invoice_id.id:
                    raise UserError(_('You have to select a Partner Invoice Address in the repair form!'))
                comment = repair.quotation_notes
                if repair.invoice_method != 'none':
                    if group and repair.partner_invoice_id.id in invoices_group:
                        invoice = invoices_group[repair.partner_invoice_id.id]
                        invoice.write({
                            'name': invoice.name + ', ' + repair.name,
                            'origin': invoice.origin + ', ' + repair.name,
                            'comment': (comment and (
                            invoice.comment and invoice.comment + "\n" + comment or comment)) or (
                                           invoice.comment and invoice.comment or ''),
                        })
                    else:
                        if not repair.partner_id.property_account_receivable_id:
                            raise UserError(_('No account defined for partner "%s".') % repair.partner_id.name)
                        invoice = Invoice.create({
                            'name': repair.name,
                            'invoice_origin': repair.name,
                            'move_type': 'out_invoice',
                            'account_id': repair.partner_id.property_account_receivable_id.id,
                            'partner_id': repair.partner_invoice_id.id or repair.partner_id.id,
                            'currency_id': repair.pricelist_id.currency_id.id,
                            'comment': repair.quotation_notes,
                            'fiscal_position_id': repair.partner_id.property_account_position_id.id
                        })
                        invoices_group[repair.partner_invoice_id.id] = invoice
                    repair.write({'invoiced': True, 'invoice_id': invoice.id})

                    for operation in repair.operations:
                        if operation.type == 'add':
                            if group:
                                name = repair.name + '-' + operation.name
                            else:
                                name = operation.name

                            if operation.product_id.property_account_income_id:
                                account_id = operation.product_id.property_account_income_id.id
                            elif operation.product_id.categ_id.property_account_income_categ_id:
                                account_id = operation.product_id.categ_id.property_account_income_categ_id.id
                            else:
                                raise UserError(_('No account defined for product "%s".') % operation.product_id.name)

                            invoice_line = InvoiceLine.create({
                                'move_id': invoice.id,
                                'name': name,
                                'origin': repair.name,
                                'account_id': account_id,
                                'quantity': operation.product_uom_qty,
                                'tax_ids': [(6, 0, [x.id for x in operation.tax_id])],
                                'uom_id': operation.product_uom.id,
                                'price_unit': operation.price_unit,
                                'price_subtotal': operation.product_uom_qty * operation.price_unit,
                                'product_id': operation.product_id and operation.product_id.id or False
                            })
                            operation.write({'invoiced': True, 'invoice_line_id': invoice_line.id})
                    for fee in repair.fees_lines:
                        if group:
                            name = repair.name + '-' + fee.name
                        else:
                            name = fee.name
                        if not fee.product_id:
                            raise UserError(_('No product defined on Fees!'))

                        if fee.product_id.property_account_income_id:
                            account_id = fee.product_id.property_account_income_id.id
                        elif fee.product_id.categ_id.property_account_income_categ_id:
                            account_id = fee.product_id.categ_id.property_account_income_categ_id.id
                        else:
                            raise UserError(_('No account defined for product "%s".') % fee.product_id.name)

                        invoice_line = InvoiceLine.create({
                            'move_id': invoice.id,
                            'name': name,
                            'origin': repair.name,
                            'account_id': account_id,
                            'quantity': fee.product_uom_qty,
                            'tax_ids': [(6, 0, [x.id for x in fee.tax_id])],
                            'uom_id': fee.product_uom.id,
                            'product_id': fee.product_id and fee.product_id.id or False,
                            'price_unit': fee.price_unit,
                            'price_subtotal': fee.product_uom_qty * fee.price_unit
                        })
                        fee.write({'invoiced': True, 'invoice_line_id': invoice_line.id})
                    invoice.compute_taxes()
                    res[repair.id] = invoice.id
                    return res
        else:
            raise ValidationError("Please Add Line For Product in Parts")

    def action_repair_invoice_create(self):
        for repair in self:
            repair.action_invoice_create_maintainance()
            if repair.invoice_method == 'b4repair':
                repair.action_repair_ready()
            elif repair.invoice_method == 'after_repair':
                repair.write({'state': 'done'})
        return True

    @api.model
    def compute_delivery_count(self):
        for res in self:
            res.delivery_count = len(self.env['stock.picking'].search([('repair_id', '=', res.id)]))

    #Assigning to R&D Team
    # @api.multi
    def assign_to_research(self):
        self.write({'state': 'assigned'})

    #Confirming the repair order
    # @api.multi
    def action_repair_confirm(self):
        """ Repair order state is set to 'To be invoiced' when invoice method
        is 'Before repair' else state becomes 'Confirmed'.
        @param *arg: Arguments
        @return: True
        """
        if self.filtered(lambda repair: repair.state != 'draft'):
            raise UserError(_("Can only confirm draft repairs."))
        before_repair = self.filtered(lambda repair: repair.invoice_method == 'b4repair')
        before_repair.write({'state': 'confirmed'})
        self.state='confirmed'
        return True

    #Onchange For Lot_id
    @api.onchange('lot_id')
    def onchange_lot_id(self):
        if self.lot_id:
            self.env.cr.execute("""SELECT *  from stock_quant sq
                JOIN stock_location sl ON (sq.location_id=sl.id) where sq.lot_id=%d and sq.quantity=1 and sl.location_code='WH/S'"""%self.lot_id.id)
            location = self.env.cr.dictfetchall()
            if not location:
                stock = self.env['stock.move.line'].search([('lot_id', '=', self.lot_id.id)])

                # sale=self.env['sale.order'].search([('serial_no','=',self.lot_id.id),('state','=','open')])
                # for sto in stock:
                #     if sto.picking_id and sto.picking_id.state=='done':
                #         self.picking_id = sto.picking_id.id
                #         self.location_src_id = sto.picking_id.location_id.id
                #         self.location_des_id = sto.picking_id.location_dest_id.id
                #         warranty_date = parser.parse(sto.picking_id.date_done).date()
                #         expiry_date = warranty_date + timedelta(days=365)
                #         self.guarantee_limit = expiry_date
                #     else:
                #         raise ValidationError("Please Check Whether the Delivery Order for selected lot in done state")
            else:
                raise ValidationError("Invalid Lot.Please select the lot which is not in main location")

    #Device History For Lot
    # @api.depends("lot_id")
    def device_history(self):
        if self.lot_id:
            stock = self.env['stock.move.line'].search([('lot_id','=',self.lot_id.id)])
            history = []
            for sto in stock:
                if sto.picking_id:
                    self.env.cr.execute("""SELECT mp.id as id ,mp.name,mp.product_id,mp.product_qty,mp.partner_id,mp.guarantee_limit,mp.amount_total
                                            FROM repair_order mp
                                            JOIN stock_production_lot spl ON (spl.id=mp.lot_id) WHERE spl.id=%d and mp.state='done' group by mp.id"""%(self.lot_id.id))
                    history = self.env.cr.dictfetchall()
            for mrp_history in history:
                values = ({
                        'new_id': self.id,
                        'name': mrp_history['name'],
                        'product_id': mrp_history['product_id'],
                        'product_qty': mrp_history['product_qty'],
                        'partner_id': mrp_history['partner_id'],
                        'guarantee_limit': mrp_history['guarantee_limit'],
                        'amount_total': mrp_history['amount_total']
                            })
                self.env['new.repair.order'].create(values)

    #Delivery Order for Receipts
    # @api.multi
    def action_repair_start_delivery(self):
        """ Writes repair order state to 'Under Repair'
        @return: True
        """
        if self.filtered(lambda repair: repair.state not in ['confirmed', 'assigned']):
            raise UserError(_("Repair must be confirmed before starting reparation."))
        self.mapped('operations').write({'state': 'confirmed'})
        self.location_move_stock()
        self.device_history()
        if self.invoice_method == 'b4repair':
            self.state = 'ready'
        else:
            self.write({'state': 'ready'})

    # Delivery Order for Stockable product and  repaired product send to customer
    # @api.multi
    def action_repair_end_delivery(self):
        stock = self.env['stock.picking'].search([('repair_id', '=', self.id), ('state', '!=', 'done')])
        if stock:
            raise ValidationError("Some transfer picking sill not processed")
        else:
            self.state = 'done'
            self.component_move_customer()

    #Used in action repair start function to create delivery order Customer to Stock Location

    # @api.multi
    def location_move_stock(self):
        for repair in self:
            picking_type_id = self.env["stock.picking.type"]
            dest_location = self.env["stock.location"]
            source_location = self.env["stock.location"]
            if repair.picking_id:
                dest_location = repair.picking_id.location_id
                source_location = repair.picking_id.location_dest_id
                picking_type_id = repair.picking_id.picking_type_id and repair.picking_id.picking_type_id.return_picking_type_id
            if not picking_type_id:
                picking_type_id = self.env["stock.picking.type"].search([('picking_code', '=', 'RE')], limit=1)
            if not dest_location:
                dest_location = self.env["stock.location"].search([('location_code', '=', 'WH/S')], limit=1)
            if not source_location:
                picking_loc_id = self.env['stock.quant'].search([('lot_id', '=', repair.lot_id.id), ('product_id', '=', repair.product_id.id), ('quantity', '=', 1)], limit=1)
                if picking_loc_id:
                    source_location = picking_loc_id.location_id
            if source_location and dest_location and picking_type_id:
                vals = {
                    'repair_id': repair.id,
                    'partner_id': repair.partner_id.id,
                    'origin': repair.name,
                    'scheduled_date': datetime.now().date(),
                    'location_id': source_location.id,
                    'location_dest_id': dest_location.id,
                    'picking_type_id': picking_type_id.id,
                    'product_lots_id':repair.lot_id.id,
                    # 'delivery_id': repair.picking_id and repair.picking_id.id,
                    'job_id': repair.job_id and repair.job_id.id

                }
                picking_id = self.env['stock.picking'].create(vals)
                line_value = {
                    'product_id': repair.product_id.id,
                    'name': repair.product_id.name,
                    'product_uom_qty': 1,
                    'product_uom': repair.product_id.uom_id.id,
                    'location_id': source_location.id,
                    'location_dest_id': dest_location.id,
                    'picking_id': picking_id.id,
                }
                self.env['stock.move'].create(line_value)
                picking_id.action_assign()

    # @api.multi
    def component_move_customer(self):
        if self.picking_id:
            dest_location = self.picking_id.location_dest_id
            picking_type_obj = self.picking_id.picking_type_id
            location_id = self.picking_id.location_id
            if not picking_type_obj:
                picking_type_obj = self.env["stock.picking.type"].search([('picking_code', '=', 'DO')], limit=1)
                if not location_id:
                    location_id = picking_type_obj.default_location_src_id if picking_type_obj else False
            if not dest_location:
                dest_location = self.env["stock.location"].search([('location_code', '=', 'CUS')], limit=1)
            if dest_location and location_id and picking_type_obj:
                for comp in self.operations:
                    vals = {
                        'repair_id': self.id,
                        'origin': self.name,
                        'partner_id': self.partner_id.id,
                        'scheduled_date': datetime.now().date(),
                        'location_id': location_id.id,
                        'location_dest_id': dest_location.id,
                        'picking_type_id': picking_type_obj.id,
                        'job_id': self.job_id and self.job_id.id,
                        'product_lots_id': comp.lot_id and comp.lot_id.id
                        # 'delivery_id': self.picking_id and self.picking_id.id,
                    }
                    picking_id = self.env['stock.picking'].create(vals)
                    line_value = {
                        'product_id': comp.product_id.id,
                        'name': comp.name,
                        'product_uom_qty': comp.product_uom_qty,
                        'product_uom': comp.product_uom and comp.product_uom.id,
                        'location_id': location_id.id,
                        'location_dest_id': dest_location.id,
                        'picking_id': picking_id.id,
                    }
                    self.env['stock.move'].create(line_value)
                    picking_id.action_assign()
                    if self.job_id and comp.lot_id and self.job_id.device_serial_number_new_id and self.job_id.device_serial_number_new_id != comp.lot_id:
                        self.job_id.device_serial_number_old_id = self.job_id.device_serial_number_new_id and self.job_id.device_serial_number_new_id.id
                        if self.job_id.device_serial_number_old_id:
                            vehicle_master_id = self.env['vehicle.master'].search([('device_serial_number_id', '=', self.job_id.device_serial_number_old_id.id)], limit=1)
                            if vehicle_master_id:
                                vehicle_master_id.device_serial_number_id = comp.lot_id and comp.lot_id.id
                        self.job_id.device_serial_number_new_id = comp.lot_id and comp.lot_id.id

    #View for delivery order
    # @api.multi
    def action_delivery_view(self):
        if self._context is None:
            context = {}
        obj = self.env.ref('stock.action_picking_tree_all')
        obj['context'] = self._context
        stock = self.env["stock.picking"].search([('repair_id', '=', self.id)]).ids
        obj['domain'] = [('id', 'in', stock)]
        return obj

    def action_repair_ready(self):
        self.mapped('operations').write({'state': 'confirmed'})
        return self.write({'state': 'invoiced'})


class NewRepairOrder(models.Model):
    _name = "new.repair.order"

    new_id = fields.Many2one("repair.order", string="repaired",store=True)
    fee_id = fields.Many2one("repair.fee", string="Operation")
    name = fields.Char('Name')
    product_id = fields.Many2one('product.product', string='Product Repaired')
    product_qty = fields.Float('Quantity')
    partner_id = fields.Many2one('res.partner', string="Partner")
    lot_id = fields.Many2one('stock.lot', string="Lot")
    guarantee_limit = fields.Date(string="Warranty")
    amount_total = fields.Float('Amount')


class StockPickingInherit(models.Model):
    _inherit = 'stock.picking'

    repair_id = fields.Many2one("repair.order", "Repair")
    delivery_id = fields.Many2one("repair.delivery", "Delivery")
    product_lots_id = fields.Many2one("stock.lot", "Lot")
    job_id = fields.Many2one("job.card", "Job Card Reference")
    partner_id = fields.Many2one('res.partner', 'Customer', states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})

    def button_validate(self):
        res = super(StockPickingInherit, self).button_validate()
        if self.product_lots_id:
            if self.move_line_ids:
                self.move_line_ids.write({'lot_id': self.product_lots_id.id})
        return res

    # @api.multi
    # def button_validate(self):
    #     if self.product_lots_id:
    #         if self.move_line_ids:
    #             self.move_line_ids.write({'lot_id': self.product_lots_id.id})
    #         else:
    #             for move in self.move_lines:
    #                 vals = {
    #                         'move_id': move.id,
    #                         'product_id': move.product_id.id,
    #                         'product_uom_id': move.product_uom.id,
    #                         'location_id': move.location_id.id,
    #                         'location_dest_id': move.location_dest_id.id,
    #                         'picking_id': move.picking_id.id,
    #                         'lot_id': self.product_lots_id and self.product_lots_id.id,
    #                         'qty_done': 1,
    #                         'product_uom_qty': 1,
    #                         }
    #                 self.env['stock.move.line'].create(vals)
    #         self.ensure_one()
    #         if not self.move_lines and not self.move_line_ids:
    #             raise UserError(_('Please add some lines to move'))
    #
    #         # If no lots when needed, raise error
    #         picking_type = self.picking_type_id
    #         precision_digits = self.env['decimal.precision'].precision_get('Product Unit of Measure')
    #         no_quantities_done = all(
    #             float_is_zero(move_line.qty_done, precision_digits=precision_digits) for move_line in self.move_line_ids)
    #         no_reserved_quantities = all(
    #             float_is_zero(move_line.product_qty, precision_rounding=move_line.product_uom_id.rounding) for move_line in
    #             self.move_line_ids)
    #         if no_reserved_quantities and no_quantities_done:
    #             raise UserError(_(
    #                 'You cannot validate a transfer if you have not processed any quantity. You should rather cancel the transfer.'))
    #
    #         if picking_type.use_create_lots or picking_type.use_existing_lots:
    #             lines_to_check = self.move_line_ids
    #             if not no_quantities_done:
    #                 lines_to_check = lines_to_check.filtered(
    #                     lambda line: float_compare(line.qty_done, 0,
    #                                                precision_rounding=line.product_uom_id.rounding)
    #                 )
    #
    #             for line in lines_to_check:
    #                 product = line.product_id
    #                 if product and product.tracking != 'none':
    #                     if not line.lot_name and not line.lot_id:
    #                         raise UserError(_('You need to supply a lot/serial number for %s.') % product.display_name)
    #
    #         if no_quantities_done:
    #             view = self.env.ref('stock.view_immediate_transfer')
    #             wiz = self.env['stock.immediate.transfer'].create({'pick_ids': [(4, self.id)]})
    #             return {
    #                 'name': _('Immediate Transfer?'),
    #                 'type': 'ir.actions.act_window',
    #                 # 'view_type': 'form',
    #                 'view_mode': 'form',
    #                 'res_model': 'stock.immediate.transfer',
    #                 'views': [(view.id, 'form')],
    #                 'view_id': view.id,
    #                 'target': 'new',
    #                 'res_id': wiz.id,
    #                 'context': self.env.context,
    #             }
    #
    #         if self._get_overprocessed_stock_moves() and not self._context.get('skip_overprocessed_check'):
    #             view = self.env.ref('stock.view_overprocessed_transfer')
    #             wiz = self.env['stock.overprocessed.transfer'].create({'picking_id': self.id})
    #             return {
    #                 'type': 'ir.actions.act_window',
    #                 # 'view_type': 'form',
    #                 'view_mode': 'form',
    #                 'res_model': 'stock.overprocessed.transfer',
    #                 'views': [(view.id, 'form')],
    #                 'view_id': view.id,
    #                 'target': 'new',
    #                 'res_id': wiz.id,
    #                 'context': self.env.context,
    #             }
    #
    #         # Check backorder should check for other barcodes
    #         if self._check_backorder():
    #             return self.action_generate_backorder_wizard()
    #         self.action_done()
    #         return
    #     else:
    #         # self.ensure_one()
    #         if not self.move_lines and not self.move_line_ids:
    #             raise UserError(_('Please add some lines to move'))
    #
    #         # If no lots when needed, raise error
    #         picking_type = self.picking_type_id
    #         precision_digits = self.env['decimal.precision'].precision_get('Product Unit of Measure')
    #         no_quantities_done = all(
    #             float_is_zero(move_line.qty_done, precision_digits=precision_digits) for move_line in
    #             self.move_line_ids)
    #         no_reserved_quantities = all(
    #             float_is_zero(move_line.product_qty, precision_rounding=move_line.product_uom_id.rounding) for move_line
    #             in
    #             self.move_line_ids)
    #         if no_reserved_quantities and no_quantities_done:
    #             raise UserError(_(
    #                 'You cannot validate a transfer if you have not processed any quantity. You should rather cancel the transfer.'))
    #
    #         if picking_type.use_create_lots or picking_type.use_existing_lots:
    #             lines_to_check = self.move_line_ids
    #             if not no_quantities_done:
    #                 lines_to_check = lines_to_check.filtered(
    #                     lambda line: float_compare(line.qty_done, 0,
    #                                                precision_rounding=line.product_uom_id.rounding)
    #                 )
    #
    #             for line in lines_to_check:
    #                 product = line.product_id
    #                 if product and product.tracking != 'none':
    #                     if not line.lot_name and not line.lot_id:
    #                         raise UserError(_('You need to supply a lot/serial number for %s.') % product.display_name)
    #
    #         if no_quantities_done:
    #             view = self.env.ref('stock.view_immediate_transfer')
    #             wiz = self.env['stock.immediate.transfer'].create({'pick_ids': [(4, self.id)]})
    #             return {
    #                 'name': _('Immediate Transfer?'),
    #                 'type': 'ir.actions.act_window',
    #                 # 'view_type': 'form',
    #                 'view_mode': 'form',
    #                 'res_model': 'stock.immediate.transfer',
    #                 'views': [(view.id, 'form')],
    #                 'view_id': view.id,
    #                 'target': 'new',
    #                 'res_id': wiz.id,
    #                 'context': self.env.context,
    #             }
    #
    #         if self._get_overprocessed_stock_moves() and not self._context.get('skip_overprocessed_check'):
    #             view = self.env.ref('stock.view_overprocessed_transfer')
    #             wiz = self.env['stock.overprocessed.transfer'].create({'picking_id': self.id})
    #             return {
    #                 'type': 'ir.actions.act_window',
    #                 # 'view_type': 'form',
    #                 'view_mode': 'form',
    #                 'res_model': 'stock.overprocessed.transfer',
    #                 'views': [(view.id, 'form')],
    #                 'view_id': view.id,
    #                 'target': 'new',
    #                 'res_id': wiz.id,
    #                 'context': self.env.context,
    #             }
    #
    #         # Check backorder should check for other barcodes
    #         if self._check_backorder():
    #             return self.action_generate_backorder_wizard()
    #         self.action_done()
    #         return


class RepairDelivery(models.Model):
    _name = 'repair.delivery'
    _rec_name = 'partner_id'

    state = fields.Selection(string="State", selection=[('draft', 'Draft'), ('confirmed', 'Confirmed'), ('delivery', 'Delivery')], required=False, default="draft")
    partner_id = fields.Many2one("res.partner", string="Customer")
    delivery_line = fields.One2many('delivery.line', 'delivery_id', 'Delivery')
    count_delivery = fields.Integer("Delivery", compute="compute_count_delivery")

    #DELIVERY order count
    # @api.multi
    def compute_count_delivery(self):
        for rec in self:
            rec.count_delivery = len(self.env['stock.picking'].search([('delivery_id','=',self.id)]))

    # @api.multi
    def action_delivery_view(self):
        if self._context is None:
            context = {}
        # obj = self.env["ir.actions.act_window"].for_xml_id("stock", 'action_picking_tree_all')
        obj = self.env.ref('stock.action_picking_tree_all')
        obj['context'] = self._context
        stock = self.env["stock.picking"].search([('delivery_id', '=', self.id)]).ids
        obj['domain'] = [('id', 'in', stock)]
        return obj

    #BULK DELIVERY FOR REPAIR ORDER
    # @api.multi
    def confirm_delivery(self):
        self.env.cr.execute("""SELECT mp.id as repair_id,mp.lot_id,mp.picking_id,mp.product_id FROM repair_order mp WHERE mp.state='ready' and mp.partner_id=%d""" % self.partner_id.id)
        values = self.env.cr.dictfetchall()
        if values:
            self.env.cr.execute('''DELETE FROM delivery_line WHERE delivery_id=%d''' % self.id)
            self.state = 'confirmed'
            for vals in values:
                delivery = {'delivery_id': self.id,
                            'repair_id': vals['repair_id'],
                            'lot_id': vals['lot_id'],
                            'product_id': vals['product_id'],
                            'picking_id': vals['picking_id']}
                self.env['delivery.line'].create(delivery)
        else:
            raise ValidationError("No Records Found For Selected Partner")

    #DELIVERY ORDER CREATION
    # @api.multi
    def create_delivery(self):
        self.env.cr.execute("""SELECT dl.repair_id,dl.lot_id,dl.product_id,dl.picking_id,pt.name,pt.uom_id FROM repair_delivery rd
                                JOIN delivery_line dl ON (rd.id=dl.delivery_id)
                                JOIN product_product pp ON (pp.id=dl.product_id)
                                JOIN product_template pt ON (pp.product_tmpl_id=pt.id) where check_type=True and rd.id=%d"""%(self.id))
        confirmed = self.env.cr.dictfetchall()

        if confirmed:
            self.state = 'delivery'
            vals = {
                # 'repair_id': self.id,
                'delivery_id': self.id,
                'partner_id': self.partner_id.id,
                'scheduled_date': datetime.now().date(),
                'location_id': 15,
                'location_dest_id': 9,
                'picking_type_id': 3,

            }
            stock = self.env['stock.picking'].create(vals)
            stock_existing_id = self.env['stock.picking'].search([('delivery_id', '=', self.id)])
            stock_move = self.env['stock.move'].search([('delivery_id', '=', stock_existing_id.id)])

            # for line_val in stock_move:
            for con in confirmed:
                line_value = {
                    'product_id': con['product_id'],
                    'name': con['name'],
                    'product_uom_qty':1,
                    'product_uom': con['uom_id'],
                    'location_id': 15,
                    'location_dest_id': 9,
                    'picking_id': stock.id,
                }

                self.env['stock.move'].create(line_value)

            self.env.cr.execute("""
                UPDATE repair_order set state='assigned' where id in


                (SELECT dl.repair_id FROM delivery_line dl

                JOIN repair_order ro ON (ro.id=dl.repair_id)

                JOIN repair_delivery rd ON (rd.id=dl.delivery_id) where dl.check_type=True and rd.id=%d)""" % self.id)
        else:
            raise ValidationError("Please select the repair")


class RepairDeliveryLine(models.Model):
    _name = 'delivery.line'

    delivery_id = fields.Many2one("repair.delivery")
    check_type = fields.Boolean(string="Check")
    repair_id = fields.Many2one("repair.order","Repair")
    product_id = fields.Many2one("product.product", string="Product")
    lot_id = fields.Many2one("stock.lot","Device Serial No")
    picking_id = fields.Many2one("stock.picking",'Picking')


class StockMove(models.Model):
    _inherit = 'stock.move'

    delivery_id = fields.Many2one("repair.delivery")


class WebsiteSupport(models.Model):
    _inherit = 'website.support.ticket'

    states = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('under_repair', 'In Progress'),
        ('cancel', 'Cancelled'),
        ('done', 'Done'),
        ('invoiced', 'Invoiced')
       ], string='Status',
        copy=False, default='draft', readonly=True, track_visibility='onchange',
        help="* The \'Draft\' status is used when a user is encoding a new and unconfirmed repair order.\n"
             "* The \'Confirmed\' status is used when a user confirms the repair order.\n"
             "* The \'Ready to Repair\' status is used to start to repairing, user can start repairing only after repair order is confirmed.\n"
             "* The \'To be Invoiced\' status is used to generate the invoice before or after repairing done.\n"
             "* The \'Done\' status is set when repairing is completed.\n"
             "* The \'Cancelled\' status is used when user cancel repair order.")
    repair_count = fields.Integer("Work Order",compute='compute_job_order_count')
    job_card_count = fields.Integer("Job Card",compute='compute_job_card_count')
    file_attachment = fields.Binary("Attachment")
    partner_id = fields.Many2one('res.partner', string="Customer")
    user_id = fields.Many2one('res.users', string="Ticket Held By")
    person_name = fields.Char(string='Point Of Contact')
    phone_number = fields.Char(string='Phone')
    invoice_count = fields.Integer("Invoice",compute='compute_invoice_count')
    is_invoice = fields.Boolean('Is Invoice')
    # ticket_line = fields.One2many("website.support.line", "support_id", string="Vehicle Details")
    create_date_dup = fields.Datetime('Create Date')
    # support_idss= fields.Many2one('job.card', string='Support')

    sup_id = fields.Many2one('job.card', string='support')

    support_id = fields.Many2one("website.support.ticket", string="Ticket")
    vehicle_id = fields.Many2one("vehicle.master", string="Vehicle")
    device_id = fields.Many2one("stock.lot", "Serial No")
    product_id = fields.Many2one("product.product", "Product")
    job_id = fields.Many2one("job.card", "Job Card")
    installated_city = fields.Many2one("installation.location", "Installed Location")
    installation_city = fields.Many2one("installation.location", "Installing Location")
    warranty_expiration = fields.Date("Warranty Expiry")
    # NEW FIELDS ADDED
    vehicle_name = fields.Char('Vehicle Name', store=True)
    chassis_no = fields.Char('Chassis No', store=True)
    satellite_imei_no = fields.Char('Satellite IMEI No')
    gsm_no = fields.Char('GSM No', store=True)
    gsm_imei_no = fields.Char('GSM IMEI No')
    # partner_id = fields.Many2one('res.partner', 'Customer Name', related='vehicle_id.partner_id')
    device_duplicate = fields.Many2one('product.product', 'Device', related='vehicle_id.device_id', store=True)
    serial_no = fields.Many2one('stock.lot', 'Serial Number', related='vehicle_id.device_serial_number_id', store=True)

    elapsed_time = fields.Float("Elapsed Time", compute='calculate_elapsed_time', store=True)
    schedule_time = fields.Datetime("Schedule Date")
    # job_stage = fields.Char( string='Job Card Status')
    job_stage = fields.Selection([('open','Open'),
                            ('configured','Configured'),
                            ('installed','Installed'),
                            ('submitted','Submitted'),
                            ('done','Done')], string='Job Card Status', compute='get_job_card_status')
    bool_field = fields.Boolean('Same text', default=False)

    # @api.depends('job_stage')
    def _get_job_card_status(self):
        for rec in self:
            job_card_obj = self.env['job.card'].search([('support_id', '=', rec.id)], limit=1)
            if job_card_obj.state:
                rec.job_stage = job_card_obj.state
            else:
                rec.job_stage = 'open'

    @api.onchange('vehicle_id')
    def onchange_vehicle(self):
        if self.vehicle_id:
            self.product_id = self.vehicle_id.device_id.id
            self.partner_id = self.vehicle_id.partner_id.id
            self.device_id = self.vehicle_id.device_serial_number_id.id
            self.installated_city = self.vehicle_id.installation_location_id.id
            self.vehicle_name = self.vehicle_id.vehicle_name
            self.chassis_no = self.vehicle_id.chassis_no
            self.satellite_imei_no = self.vehicle_id.satellite_imei_no
            self.gsm_no = self.vehicle_id.gsm_no
            self.gsm_imei_no = self.vehicle_id.gsm_imei_no
            self.env.cr.execute("""SELECT jc.id, date(sp.date_done) as end_date from job_card jc
                                   JOIN  stock_picking sp ON (sp.job_card_id=jc.id)
                                   JOIN sale_subscription ss ON (jc.device_serial_number_new_id=ss.serial_no) where ss.vehicle_number=%s and sp.state='done'and ss.stage_category='progress' and ss.subscription_status='active' and jc.state='done'""" % self.vehicle_id.id)

            vals = self.env.cr.dictfetchall()
            for jobs in vals:
                self.job_id = jobs['id']
                self.warranty_expiration = jobs['end_date'] + timedelta(days=365)\


    # @api.multi
    def compute_invoice_count(self):
        for rec in self:
            rec.invoice_count = len(self.env['account.move'].search([('job_id', '=', self.id)]))

    @api.depends('close_time', 'create_date')
    def calculate_elapsed_time(self):
        for pair in self:
            if pair.close_time:
                start_date = datetime.combine(fields.Date.from_string(pair.create_date), datetime.min.time())
                end_date = datetime.combine(fields.Date.from_string(pair.close_time), datetime.max.time())
                time_inter = (end_date - start_date).total_seconds()
                pair.elapsed_time = abs((time_inter / 3600)) + 1

    # @api.multi
    def compute_job_order_count(self):
        for rec in self:
            rec.repair_count = len(self.env['project.task'].search([('support_id', '=', rec.id)]))

    # @api.multi
    def compute_job_card_count(self):
        for rec in self:
            rec.job_card_count = len(self.env['job.card'].search([('support_id', '=', self.id)]))

            # CONFIRM TICKET BY VEHICLE NUMBER
    # @api.multi
    # def update_date(self):
    #     ticket_obj = self.env['website.support.ticket'].search([])
    #     for obj in ticket_obj:
    #         print('dateeeeeeeeeeeeeeeeee',self.create_date_dup)
    #         self.env.cr.execute('''update website_support_ticket set create_date ='%s' '''%(self.create_date_dup))

    # @api.multi
    # def confirm_repair_order(self):
    #     if self.states == 'draft' and self.partner_id:
    #
    #         if self.job_id and self.warranty_expiration:
    #             self.write({'states': 'confirmed'})
    #         else:
    #             self.write({'states': 'confirmed'})

    # @api.multi
    def confirm_repair_order(self):
        self.write({'states': 'confirmed'})
        subject = 'Confirm Repair Order'
        body = """<p>Dear %s,</p>
                          <br/>
                          <p>Your request Confirmation of Repai Order is Done</p>
                          <p>Sincerely,<br/>
                             Admin</p>""" % (self.user_id.name)
        message_body = body
        template_data = {
            'subject': subject,
            'body_html': message_body,
            'email_from': self.env.user.company_id.email,
            'email_to': self.user_id.name,
        }
        self.message_post(body=message_body, subject=subject)
        template_id = self.env['mail.mail'].sudo().create(template_data)
        template_id.sudo().send()


 #~ # REPAIR CREATION
    #~ @api.multi
    #~ def create_job_order(self):
        #~ if self.states == 'confirmed':
                #~ work = self.env['ir.sequence'].next_by_code('work.order')
                #~ self.states = 'under_repair'
                #~ vals={'support_id': self.id,
                      #~ 'name': work,
                      #~ 'work_order': work
                    #~ }

                #~ self.env['project.task'].create(vals)
        #~ else:
            #~ raise ValidationError("Please check the Vehicle Number")


    # JOB CARD CREATION
    # @api.multi
    def create_job_card(self):

        if not self.vehicle_id:
            raise ValidationError("Please Add Vehicle Details to create job card")

        if self.states == 'confirmed':
            self.states = 'under_repair'
            vals = {
                'support_id': self.id,
                'job_card_type': 'support',
                'company_id': self.partner_id.id,
                'vehicle_number': self.vehicle_id.id,
                'gsm_number':  self.gsm_no,
                }

            self.env['job.card'].create(vals)
            self.bool_field = True

    # @api.multi
    # def _prepare_invoice(self):
    #    res = super(WebsiteSupportInherit, self)._prepare_invoice()
    #    res.update({
    #     'sale_type': self.sale_type
    # })
    #    return res

    # @api.multi
    def action_project_view(self):
        if self._context is None:
            context = {}
        # obj = self.env["ir.actions.act_window"].for_xml_id("project", 'act_project_project_2_project_task_all')
        obj = self.env.ref('project.act_project_project_2_project_task_all')
        obj['context'] = self._context
        ticket = self.env["project.task"].search([('support_id', '=', self.id)]).ids
        obj['domain'] = [('id', 'in', ticket)]
        return obj
        # INVOICE VIEW

    # @api.multi
    def action_invoice_view(self):
        if self._context is None:
            context = {}
        # obj = self.env["ir.actions.act_window"].for_xml_id("account", 'action_invoice_tree1')
        obj = self.env.ref('account.action_move_out_invoice_type')
        obj['context'] = self._context
        account = self.env["account.move"].search([('job_id', '=', self.id)]).ids
        obj['domain'] = [('id', 'in', account)]
        return obj

    # JOB CARD VIEW
    # @api.multi
    def action_job_card_views(self):
        if self._context is None:
            context = {}
        obj = self.env.ref('fms_sale.job_order_action')
        job = self.env["job.card"].search([('support_id', '=', self.id)]).ids
        obj['domain'] = [('id', 'in', job)]
        return obj

    # @api.multi
    def action_invoice_create(self):
        """ Creates invoice(s) for repair order.
        @param group: It is set to true when group invoice is to be generated.
        @return: Invoice Ids.
        """
        invoice = self.env['account.move']
        vals = {'partner_id': self.partner_id.id, 'account_id': self.partner_id.property_account_receivable_id.id}

        self.env.cr.execute("""SELECT jc.product_id,jc.name FROM website_support_ticket wst
                                JOIN repair_order jc ON (wst.id=jc.support_id)
                                WHERE jc.state='done'""")
        values = self.env.cr.dictfetchall()
        if values == []:
            raise ValidationError("""Can Not Create Invoice For This Ticket
                                    * Added Stock Delivery Order Must Be Validated
                                    * Service must in done stage
                                    * Subscription for serial number must be open stage 
                                """)
        invoice = self.env['account.move'].create(vals)
        # for account_invoice_line in values:
        #      if account_invoice_line.get('product_id'):
        #         product = self.env['product.product'].browse(account_invoice_line.get('product_id'))
        #         invoice_line_create = {
        #             'invoice_id': invoice.id,
        #             'product_id': product.id,
        #             'name': product.display_name,
        #             'quantity': 1,
        #             'account_id': 17,
        #             'price_unit': product.standard_price
        #         }
        #         self.env['account.move.line'].create(invoice_line_create)
        self.states = 'invoiced'

        # remove device
        removes = self.env['job.card'].search([('repair_job_type', '=', 'removal'), ('support_id', '=', self.id)], limit=1)
        if removes:
            vals.update({'job_id': removes.id})
            if removes.invoice != 'chargeable':
                raise ValidationError("You can not create invoice because job card is not set as chargeable")

            self.env.cr.execute("""SELECT jc.device_serial_number_old_id,jc.device_id FROM website_support_ticket wst
                                    JOIN job_card jc ON (wst.id=jc.support_id)
                                    JOIN stock_picking so ON (so.job_id=jc.id)
                                    JOIN sale_subscription ss ON (ss.serial_no=jc.device_serial_number_old_id)
                                    JOIN product_product pp ON (pp.id=jc.device_id)
                                    WHERE jc.job_card_type='support' and jc.state='done' and jc.repair_job_type='removal'  and so.state='done' and ss.state='open'""")
            remove = self.env.cr.dictfetchall()
            if remove == []:
                raise ValidationError("""Invoice Creation For Removal Stock
                                        * Delivery Order For Old Serial Number Must Be Validated
                                        * New Job Card must in done stage
                                        * Subscription for old serial number must be open stage 
                                    """)
            invoice = self.env['account.move'].create(vals)
            for invoice_line in remove:
                if invoice_line.get('device_id'):
                    product = self.env['product.product'].browse(invoice_line.get('device_id'))
                    invoice_line_create = {
                        'move_id': invoice.id,
                        'product_id': product.id,
                        'name': product.display_name,
                        'quantity': 1,
                        'account_id': 17,
                        'price_unit': product.lst_price
                    }
                    self.env['account.move.line'].create(invoice_line_create)
            self.states = 'invoiced'

        # device replaced
        device_replacement = self.env['job.card'].search([('repair_job_type', '=', 'defective_device_replacement'), ('support_id', '=', self.id)], limit=1)
        if device_replacement:
            vals.update({'job_id': device_replacement.id})
            if device_replacement.invoice != 'chargeable':
                raise ValidationError("You can not create invoice because job card is not set as chargeable")

            self.env.cr.execute("""SELECT jc.device_serial_number_new_id,jc.device_id FROM website_support_ticket wst
                                    JOIN job_card jc ON (wst.id=jc.support_id)
                                    JOIN stock_picking so ON (so.job_id=jc.id)
                                    JOIN sale_subscription ss ON (ss.serial_no=jc.device_serial_number_new_id)
                                    JOIN product_product pp ON (pp.id=jc.device_id)
                                    WHERE jc.job_card_type='support' and jc.state='done' and jc.repair_job_type='defective_device_replacement' and jc.device_status='active' and so.state='done'and ss.state='open'""")
            replace = self.env.cr.dictfetchall()
            if replace == []:
                raise ValidationError("""Invoice Creation For Device Replacement
                                        * Stock Delivery Order For New Serial Number Must Be Validated
                                        * New Job Card  must in done stage
                                        * Subscription for New serial number must be open stage 
                                    """)
            invoice = self.env['account.move'].create(vals)
            for replace_line in replace:
                if replace_line.get('device_id'):
                    product = self.env['product.product'].browse(replace_line.get('device_id'))
                    invoice_line_create = {
                        'move_id': invoice.id,
                        'product_id': product.id,
                        'name': product.display_name,
                        'quantity': 1,
                        'account_id': 17,
                        'price_unit': product.lst_price
                    }
                    self.env['account.move.line'].create(invoice_line_create)
            self.states = 'invoiced'   
        return invoice


class WebsiteCloseInherit(models.TransientModel):
    _inherit = 'website.support.ticket.close'

    # TICKET CLOSURE
    def close_ticket(self):
        self.ticket_id.close_time = datetime.now()
        self.ticket_id.states = 'done'
        #Also set the date for gamification
        self.ticket_id.close_date = datetime.now().date()

        diff_time = datetime.strptime(self.ticket_id.close_time, DEFAULT_SERVER_DATETIME_FORMAT) - datetime.strptime(self.ticket_id.create_date, DEFAULT_SERVER_DATETIME_FORMAT)
        self.ticket_id.time_to_close = diff_time.seconds

        # closed_state = self.env['ir.model.data'].sudo().get_object('website_support', 'website_ticket_state_staff_closed')
        closed_state = self.env.ref('website_support.website_ticket_state_staff_closed')

        #We record state change manually since it would spam the chatter if every 'Staff Replied' and 'Customer Replied' gets recorded
        message = "<ul class=\"o_mail_thread_message_tracking\">\n<li>State:<span> " + self.ticket_id.state.name + " </span><b>-></b> " + closed_state.name + " </span></li></ul>"
        self.ticket_id.message_post(body=message, subject="Ticket Closed by Staff")

        self.ticket_id.close_comment = re.compile(r'<[^>]+>').sub('', self.message)
        self.ticket_id.closed_by_id = self.env.user.id
        self.ticket_id.state = closed_state.id
        self.ticket_id.sla_active = False

        #Auto send out survey
        setting_auto_send_survey = self.env['ir.default'].get('website.support.settings', 'auto_send_survey')
        if setting_auto_send_survey:
            self.ticket_id.send_survey()


class RepairLine(models.Model):
    _inherit = 'repair.line'

    @api.onchange('product_id', 'product_uom_qty')
    def onchange_product_id(self):
        res = super(RepairLine, self).onchange_product_id()
        if self.type == 'add' and self.product_id:
            self.name = self.product_id.name
            self.product_uom = self.product_id.uom_id.id
            self.env.cr.execute("""
            select sum(quantity)  from stock_quant sq
            JOIN stock_location sl ON (sq.location_id=sl.id) where sl.location_code='WH/S' and sq.product_id=%d""" %self.product_id.id)
            vals = self.env.cr.dictfetchall()
            for quant in vals:
                if quant.get('sum') and quant.get('sum') <= 0.00:
                    raise ValidationError("Insuffient Quantity for selected product %s" % self.name)
                elif quant.get('sum') and quant.get('sum') < self.product_uom_qty:
                    raise ValidationError("Insuffient Quantity  for selected product %s" % self.name)
        else:
            self.name = self.product_id.name
            self.product_uom = self.product_id.uom_id.id
        return res


class AccountMove(models.Model):
    _inherit = 'account.move'

    repair_id = fields.Many2one("repair.order", "Maintenance")
    job_id = fields.Many2one("job.card", "Job Card")
    sale_subscription_id = fields.Many2one("sale.order", "Subscription",  domain=[('is_subscription', '=', True)])

