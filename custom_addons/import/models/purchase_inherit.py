from odoo import models, fields, api, _
import csv
import base64


class StockImport(models.TransientModel):
    _name = 'import.stock'

    name = fields.Char("Name")
    csv_file = fields.Binary(string='CSV File', required=True)  

    # @api.multi
    def import_csv(self):
        rec = self._context.get('active_ids')
        rec = rec[0]
        lot_list = base64.b64decode(self.csv_file).decode("utf-8", "ignore")
        reader = csv.DictReader(lot_list.split('\n'))
       
        for row in reader:         
            inventory = self.env['stock.inventory'].search([('id', '=', rec)])
            for inventory_list in inventory:

                self.env.cr.execute(""" 
                                      select pp.id as pp_id,pt.id as pt_id,pt.name,pt.uom_po_id as po_uom_id
                                      from product_product as pp join product_template as pt on (pt.id=pp.product_tmpl_id)
                                      where pt.name ='%s' and pt.type='product'""" % row['Product/Name'])
                obj = self.env.cr.dictfetchall()
                for inventory_create in obj:
                    lot_obj = self.env['stock.lot'].search([('name', '=', row['Lot/Serial Number'])])
                    inventory_list.line_ids.create({
                                        'inventory_id': inventory.id,
                                        'product_id': str(inventory_create['pp_id']),
                                        'product_uom_id': int(inventory_create['po_uom_id']),
                                        'location_id': int(row['location_id']),
                                        'prod_lot_id': lot_obj.id,
                                        'product_qty': int(row['product_qty'])
                                        })
