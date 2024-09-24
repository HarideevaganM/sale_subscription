from odoo import api, fields, models, _
from odoo.exceptions import UserError, AccessError
import csv
import base64
from odoo.tools.float_utils import float_compare, float_is_zero


class StockPickingInherit(models.Model):
    _inherit = "stock.picking"
    
    job_card_id = fields.Many2one("job.card", "Job Card Reference")
    po_number = fields.Char("PO #")
    po_date = fields.Date("PO Date")
    technician = fields.Many2one("res.users", "Assigned Engineer")

    # @api.multi
    def check_picking_type(self):
        picking_type = self.env["stock.picking.type"].search([("id", "=", self.picking_type_id.id)])
        sale_id = self.env["sale.order"].search([("name", "=", self.origin)])
        if sale_id.sale_type == 'lease' and self.picking_type_id.sequence_code != 'LW':
            
            raise UserError(_("You Should Select Operation Type As Lease Warehouse or Create Operation Type As Lease Warehouse with Code as 'LW'"))
        
        elif sale_id.sale_type == 'rental' and self.picking_type_id.sequence_code != 'RW':
            
            raise UserError(_("You Should Select Operation Type As Rental Warehouse or Create Operation Type As Rental Warehouse with Code as 'RW'"))
        elif sale_id.sale_type == 'pilot' and self.picking_type_id.sequence_code != 'PW':
            raise UserError(_("You Should Select Operation Type As Pilot Warehouse or Create Operation Type As Pilot Warehouse with Code as 'PW'"))
            
    # @api.multi
    def button_validate(self):
        res = super(StockPickingInherit, self).button_validate()
        return res


class StockLocationInherit(models.Model):
    _inherit = "stock.location"

    location_code = fields.Char("Code")


class StockPickingTypeInherit(models.Model):
    _inherit = "stock.picking.type"

    picking_code = fields.Char("Code")


class StockMoveInherit(models.Model):
    _inherit = "stock.move"
    
    lot_upload = fields.Binary(string='Lot File')
    file_name = fields.Char('Filename')

    # @api.multi
    def lot_update(self):
        move_line = self.env['stock.move.line']
        for move in self.filtered(lambda x: x.picking_code == 'incoming'):
            self.env.cr.execute("""delete from stock_move_line where move_id =%s """%(move.id))
            location_dest_id = move.location_dest_id._get_putaway_strategy(move.product_id) or move.location_dest_id
            if not location_dest_id:
                return False
            if not move.lot_upload:
                return False
            lot_list = base64.b64decode(move.lot_upload).decode("utf-8", "ignore")
            reader = csv.DictReader(lot_list.split('\n'))
            for line in reader:
                vals = {
                    'move_id': move.id,
                    'product_id': move.product_id.id,
                    'product_uom_id': move.product_uom.id,
                    'location_id': move.location_id.id,
                    'location_dest_id': location_dest_id and location_dest_id.id,
                    'picking_id': move.picking_id.id,
                    'lot_name': line.get('Lot'),
                    'qty_done': 1,
                    'product_uom_qty': 1,
                    }
                move_line |= self.env['stock.move.line'].create(vals)
            if move_line:
                attachment_ids = self.env['ir.attachment'].sudo().create({
                    'name': move.file_name,
                    'datas_fname': move.file_name,
                    'datas': move.lot_upload,
                    'res_model': 'stock.picking',
                    'res_id': move.picking_id and move.picking_id.id,
                    'res_name': move.file_name,
                    'public' : True
                })
                self.env['mail.message'].sudo().create({
                    'body': _('<p>Attached files : </p>'),
                    'model': 'stock.picking',
                    'message_type': 'comment',
                    'no_auto_thread': False,
                    'res_id': move.picking_id.id,
                    'attachment_ids': [(6, 0, attachment_ids.ids)],
                })
    # @api.multi
    # def lot_update(self):
    #     self.env.cr.execute("""delete from stock_move_line where move_id =%s """%(self.id))
    #     location_dest_id = self.location_dest_id.get_putaway_strategy(self.product_id).id or self.location_dest_id.id
    #     move_line_obj = self.env['stock.move.line']
    #     lot_list = base64.b64decode(self.lot_upload).decode("utf-8", "ignore")
    #     reader = csv.DictReader(lot_list.split('\n'))
    #     for line in reader:
    #         vals = {
    #             'move_id': self.id,
    #             'product_id': self.product_id.id,
    #             'product_uom_id': self.product_uom.id,
    #             'location_id': self.location_id.id,
    #             'location_dest_id': location_dest_id,
    #             'picking_id': self.picking_id.id,
    #             'lot_name': line['Lot'],
    #             'qty_done': 1,
    #             'product_uom_qty': 1,
    #             }
    #         move_line_obj.create(vals)


class StockMoveLineInherit(models.Model):
    _inherit = "stock.move.line"
    
    lot_id = fields.Many2one('stock.lot', 'Device Serial No')
    lot_name = fields.Char('Device Serial No')    

