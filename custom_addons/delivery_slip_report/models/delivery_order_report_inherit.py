from odoo import api, fields, models, _


class DeliveryReport(models.AbstractModel):
    _name = 'report.stock.report_deliveryslip'
    _description = "delivery_slip"

    def line_item(self, data):
        self.env.cr.execute(""" select sml.lot_name as lot,sml.qty_done as qty, pt.name as pname,
                                    spl.name as name from stock_move_line sml join stock_picking sp
                                    on sp.id=sml.picking_id join stock_production_lot spl
                                    on spl.id=sml.lot_id join product_product proname
                                    on proname.id=spl.product_id join product_template pt
                                    on pt.id=proname.product_tmpl_id where sp.id=%s group by pname,qty,lot,spl.name""" % (data.id))
        lot_obj = self.env.cr.dictfetchall()
        # for product in lot_obj:
        #     vals.append({
        #                 'product_name'    : product['pname']
        #                 })

        products = []
        for product in lot_obj:
            if not product['pname'] in products:
                products.append(product['pname'])
        final_prod = []
        for prod in products:
            tot_seriel = []
            for obj in lot_obj:
                if prod == obj['pname']:
                    tot_seriel.append(obj['name'])
            final_prod.append({
                'product_name': prod,
                'lots': tot_seriel
            })
        return final_prod


    @api.model
    def _get_report_values(self, docids, data=None):
        delivery_obj = self.env["stock.picking"].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': "stock.picking",
            'docs': delivery_obj,
            'data': data,
            'line_item': self.line_item,

        }


