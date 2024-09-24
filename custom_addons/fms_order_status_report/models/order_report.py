# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import datetime, date
from odoo.exceptions import UserError, ValidationError
import xlsxwriter
from io import StringIO
import base64
import os
from dateutil import parser

class SaleOrderReport(models.AbstractModel):
    _inherit = 'sale.order'

    filedata = fields.Binary(string='Order Status Report', readonly=True)
    filename = fields.Char('Filename', size=64, readonly=True)
    datafile = fields.Binary(string='Device Status Report', readonly=True)
    namefile = fields.Char('Filename', size=64, readonly=True)

    #@api.multi
    def _get_order_status_report(self):
        output = StringIO()
        url = '/home/support/'
        workbook = xlsxwriter.Workbook(url + 'Order Status.xlsx')
        worksheet = workbook.add_worksheet()

        merge_format1 = workbook.add_format({
            'bold': 1,
            'border': 1,
            'align': 'center',
            'fg_color': '#ffff66',
            'valign': 'vcenter', })

        merge_format2 = workbook.add_format({
            'align': 'left',
            'valign': 'vcenter', })

        merge_format3 = workbook.add_format({
            'align': 'center',
            'bold': 1,
            'border': 1,
            'font_size': 14,
        })

        merge_format4 = workbook.add_format({
            'align': 'right',
            'bold': 1,
            'valign': 'vcenter', })
        format_date = workbook.add_format({
            'num_format': 'd mmm yyyy hh:mm AM/PM',
            'align': 'left',
        })
        today = datetime.today().strftime('%d-%m-%Y')
        worksheet.set_column('A:A', 5)
        worksheet.set_column('B:B', 25)
        worksheet.set_column('C:C', 15)
        worksheet.set_column('D:D', 15)
        worksheet.set_column('E:E', 15)
        worksheet.set_column('F:F', 15)
        worksheet.merge_range('A1:E1', 'Order Status Report', merge_format3)
        worksheet.write(4, 0, 'Sale Order No', merge_format1)
        worksheet.write(4, 1, "Customer", merge_format1)
        worksheet.write(4, 2, "Sale Type", merge_format1)


        worksheet.write(7, 0, "S.No", merge_format1)
        worksheet.write(7, 1, "Device Type", merge_format1)
        worksheet.write(7, 2, "Device Serial No", merge_format1)
        worksheet.write(7, 3, "Engineer", merge_format1)
        worksheet.write(7, 4, "Delivered", merge_format1)
        worksheet.write(7, 5, "Delivery Date", merge_format1)
        worksheet.write(7, 6, "Invoiced", merge_format1)
        worksheet.write(7, 7, "Invoiced Date", merge_format1)
        worksheet.write(7, 8, "Installed", merge_format1)
        worksheet.write(7, 9, "Installed Date", merge_format1)
        worksheet.write(7, 10, "Subscription Created", merge_format1)
        worksheet.write(7, 11, "Subscription Created Date", merge_format1)
        worksheet.write(7, 12, "Subscription Started", merge_format1)
        worksheet.write(7, 13, "Subscription Start Date", merge_format1)
        worksheet.write(7, 14, "Subscription End Date", merge_format1)
        row = 5

        worksheet.write(row, 0, self.name, merge_format4)
        worksheet.write(row, 1, self.partner_id.name, merge_format4)
        self.env.cr.execute(""" SELECT   sum (sol.product_uom_qty) from sale_order so
                                    JOIN sale_order_line sol ON (so.id=sol.order_id)
                                    LEFT JOIN project_project pp ON (pp.sale_order_id=so.id)
                                    LEFT JOIN project_task pt ON (pp.id=pt.project_id)
                                    LEFT JOIN product_product ppt ON (ppt.id=sol.product_id)
                                    LEFT JOIN product_template ptt ON (ptt.id=ppt.product_tmpl_id)

                                    WHERE so.id=%d  and ptt.type='product' """%self.id)
        vals = self.env.cr.fetchone()
        quantity = int(vals[0])
        worksheet.write(row, 3, today, merge_format4)



        if self.sale_type=='cash':
            worksheet.write(row, 2, "Cash Sale", merge_format4)
            worksheet.write(4, 3, "Report Taken On", merge_format1)

            self.env.cr.execute(""" SELECT distinct pt.name as product_name,spl.name as lot_name,
                                sp.id as picking_id,ss.date_start,ss.date,jc.device_serial_number_new_id,
                                rpt.name as user_name,ai.origin,date(sp.date_done) as date_done,ai.date_invoice,jc.installation_date,date(ss.create_date) as create_date from sale_order so
                                JOIN sale_order_line sol ON (so.id=sol.order_id)
                                LEFT JOIN stock_picking sp ON (sp.sale_id=so.id)
                                LEFT JOIN stock_move sm ON (sm.picking_id=sp.id)
                                LEFT JOIN stock_move_line sml ON (sml.move_id=sm.id)
                                LEFT JOIN res_partner rp ON (rp.id=so.partner_id)
                                LEFT JOIN product_product pp ON (pp.id=sol.product_id)
                                LEFT JOIN product_template pt ON (pt.id=pp.product_tmpl_id)
                                JOIN stock_production_lot spl ON (sml.lot_id=spl.id)
                                LEFT JOIN sale_subscription ss ON (ss.serial_no=sml.lot_id)
                                LEFT JOIN account_invoice ai ON (ai.origin=so.name)
                                LEFT JOIN job_card jc ON (jc.sale_order_id=so.id)
                                LEFT JOIN res_users ru ON (ru.id=jc.engineer_id)
                                LEFT JOIN res_partner rpt ON (rpt.id = ru.partner_id) WHERE so.id=%d   and pt.type='product'""" % self.id)
            product_ids = [i for i in self.env.cr.dictfetchall()]
            vals=len(product_ids)
            serial_count = 1
            for obj in product_ids:
                worksheet.write(row+3, 0,serial_count, merge_format4)
                worksheet.write(row+3, 1, obj['product_name'], merge_format4)
                worksheet.write(row+3, 2, obj['lot_name'], merge_format4)
                worksheet.write(row+3, 3,obj['user_name'], merge_format4)

                stock = self.env['stock.picking'].search([('id', '=', obj['picking_id'])])
                if stock.state == 'done':
                    worksheet.write(row + 3, 4, "Yes", merge_format4)
                    worksheet.write(row + 3, 5, obj['date_done'], merge_format4)

                else:
                    worksheet.write(row + 3, 4, "No", merge_format4)
                invoice = self.env['account.move'].search([('origin', '=', obj['origin'])])
                if not invoice:
                    worksheet.write(row + 3, 6, "No", merge_format4)
                for inv in invoice:
                    if inv.state == 'paid':
                        worksheet.write(row + 3, 6, "Yes", merge_format4)
                        worksheet.write(row + 3, 7, obj['date_invoice'], merge_format4)
                    else:
                        worksheet.write(row + 3, 6, "No", merge_format4)
                job_card = self.env['job.card'].search([('sale_order_id', '=', self.id)])
                if not job_card:
                    worksheet.write(row + 3, 8, "No", merge_format4)
                for job in job_card:
                    if job.state == 'done':
                        worksheet.write(row + 3, 8, "Yes", merge_format4)
                        worksheet.write(row + 3, 9, obj['installation_date'], merge_format4)

                    else:

                        worksheet.write(row + 3, 8, "No", merge_format4)
                subscription = self.env['sale.order'].search([('serial_no','=',obj['device_serial_number_new_id']),('sale_order_id','=',self.id),('state','in',('draft','open')), ('is_subscription', '=', True)])
                if subscription:
                    worksheet.write(row + 3, 10, "Yes", merge_format4)
                    worksheet.write(row + 3, 11, obj['create_date'], merge_format4)
                else:
                    worksheet.write(row + 3, 10, "No", merge_format4)
                subscription_start = self.env['sale.order'].search(
                    [('serial_no', '=', obj['device_serial_number_new_id']), ('sale_order_id', '=', self.id), ('is_subscription', '=', True),
                     ('state', '=',  'open')])
                if subscription_start:
                    worksheet.write(row + 3, 12, "Yes", merge_format4)
                else:
                    worksheet.write(row + 3, 12, "No", merge_format4)
                worksheet.write(row + 3, 13, subscription_start.date_start, merge_format4)
                worksheet.write(row + 3, 14,subscription_start.date, merge_format4)
                row += 1
                serial_count += 1
        elif self.purchase_type=='non_project':
            worksheet.write(4, 3, "Report Taken On", merge_format1)
            worksheet.write(row, 2, "Unit Sale - Non Project", merge_format4)
            self.env.cr.execute(""" SELECT pt.name as product_name,spl.name as lot_name,sp.id as picking_id,
                                    ss.date_start,ss.date,jc.device_serial_number_new_id,rpt.name as user_name,
                                    ai.origin,date(sp.date_done) as date_done,ai.date_invoice,jc.installation_date,date(ss.create_date) as create_date from sale_order so
                                    JOIN sale_order_line sol ON (so.id=sol.order_id)
                                    LEFT JOIN stock_picking sp ON (sp.sale_id=so.id)
                                    LEFT JOIN stock_move sm ON (sm.picking_id=sp.id)
                                    LEFT JOIN stock_move_line sml ON (sml.move_id=sm.id)
                                    LEFT JOIN res_partner rp ON (rp.id=so.partner_id)
                                    LEFT JOIN product_product pp ON (pp.id=sol.product_id)
                                    LEFT JOIN product_template pt ON (pt.id=pp.product_tmpl_id)
                                    JOIN stock_production_lot spl ON (sml.lot_id=spl.id)
                                    LEFT JOIN sale_subscription ss ON (ss.serial_no=sml.lot_id)
                                    LEFT JOIN account_invoice ai ON (ai.origin=so.name)
                                    LEFT JOIN job_card jc ON (jc.sale_order_id=so.id)
                                    LEFT JOIN res_users ru ON (ru.id=jc.engineer_id)
                                    LEFT JOIN res_partner rpt ON (rpt.id = ru.partner_id)
                                    WHERE so.id=%d   and pt.type='product'""" % self.id)
            product_ids = [i for i in self.env.cr.dictfetchall()]
            serial_count = 1
            for obj in product_ids:
                worksheet.write(row+3, 0,serial_count, merge_format4)
                worksheet.write(row+3, 1, obj['product_name'], merge_format4)
                worksheet.write(row+3, 2, obj['lot_name'], merge_format4)
                worksheet.write(row+3, 3,obj['user_name'], merge_format4)

                stock = self.env['stock.picking'].search([('id', '=', obj['picking_id'])])
                if stock.state == 'done':
                    worksheet.write(row + 3, 4, "Yes", merge_format4)
                    worksheet.write(row + 3, 5, obj['date_done'], merge_format4)

                else:
                    worksheet.write(row + 3, 4, "No", merge_format4)
                invoice = self.env['account.move'].search([('origin', '=', obj['origin'])])
                if not invoice:
                    worksheet.write(row + 3, 6, "No", merge_format4)
                for inv in invoice:
                    if inv.state == 'paid':
                        worksheet.write(row + 3, 6, "Yes", merge_format4)
                        worksheet.write(row + 3, 7, obj['date_invoice'], merge_format4)
                    else:
                        worksheet.write(row + 3, 6, "No", merge_format4)
                job_card = self.env['job.card'].search([('sale_order_id', '=', self.id)])
                if not job_card:
                    worksheet.write(row + 3, 8, "No", merge_format4)
                for job in job_card:
                    if job.state == 'done':
                        worksheet.write(row + 3, 8, "Yes", merge_format4)
                        worksheet.write(row + 3, 9, obj['installation_date'], merge_format4)

                    else:

                        worksheet.write(row + 3, 8, "No", merge_format4)
                subscription = self.env['sale.order'].search([('serial_no','=',obj['device_serial_number_new_id']),('sale_order_id','=',self.id),('state','in',('draft','open')), ('is_subscription', '=', True)])
                if subscription:
                    worksheet.write(row + 3, 10, "Yes", merge_format4)
                    worksheet.write(row + 3, 11, obj['create_date'], merge_format4)
                else:
                    worksheet.write(row + 3, 10, "No", merge_format4)
                subscription_start = self.env['sale.order'].search(
                    [('serial_no', '=', obj['device_serial_number_new_id']), ('sale_order_id', '=', self.id),
                     ('state', '=',  'open'), ('is_subscription', '=', True)])
                if subscription_start:
                    worksheet.write(row + 3, 12, "Yes", merge_format4)
                else:
                    worksheet.write(row + 3, 12, "No", merge_format4)
                worksheet.write(row + 3, 13, subscription_start.date_start, merge_format4)
                worksheet.write(row + 3, 14,subscription_start.date, merge_format4)
                row += 1
                serial_count += 1
        elif self.sale_type == 'lease':
            worksheet.write(row, 2, "Lease Sale", merge_format4)
            worksheet.write(4, 3, "Total Stock", merge_format1)
            worksheet.write(4, 4, "Unalloted Stock", merge_format1)
            worksheet.write(4, 5, "Report Taken On", merge_format1)
            self.env.cr.execute("""
                             SELECT  ptt.name as product_name ,spl.name as lot_name,
                             ru.name as user_name,ai.origin,
                             smls.lot_id as lot_ids ,sppg.id as pick_id,date(sppg.date_done) as date_done,ai.date_invoice
                              from sale_order so
                            JOIN sale_order_line sol ON (so.id=sol.order_id)
                            LEFT JOIN project_project pp ON (pp.sale_order_id=so.id)
                            LEFT JOIN project_task pt ON (pp.id=pt.project_id)
                            LEFT JOIN product_product ppt ON (ppt.id=sol.product_id)
                            LEFT JOIN product_template ptt ON (ptt.id=ppt.product_tmpl_id)
                            LEFT JOIN  material_purchase_requisition mpl ON (mpl.task_id=pt.id)
                            LEFT JOIN stock_picking sppg ON (mpl.id=sppg.custom_requisition_id )
                            LEFT JOIN stock_move sms ON (sppg.id=sms.picking_id)
                            LEFT JOIN stock_move_line smls ON (smls.move_id=sms.id)
                            LEFT JOIN stock_production_lot spl ON (spl.id=smls.lot_id)
                            LEFT JOIN account_invoice ai ON (ai.origin=so.name)
                            LEFT JOIN hr_employee ru ON (ru.id=mpl.employee_id)
                            WHERE so.id=%d  and ptt.type='product'
                            """ % self.id)
            product_ids = [i for i in self.env.cr.dictfetchall()]
            valuess = len(product_ids)
            quant=quantity-valuess
            worksheet.write(row, 3,quantity, merge_format4)
            worksheet.write(row, 4,quant, merge_format4)
            worksheet.write(row, 5,today, merge_format4)
            serial_count = 1
            for obj in product_ids:
                worksheet.write(row + 3, 0, serial_count, merge_format4)
                worksheet.write(row + 3, 1, obj['product_name'], merge_format4)
                worksheet.write(row + 3, 2, obj['lot_name'], merge_format4)
                worksheet.write(row + 3, 3, obj['user_name'], merge_format4)

                stock = self.env['stock.picking'].search([('id', '=', obj['pick_id'])])
                if stock.state == 'done':
                    worksheet.write(row + 3, 4, "Yes", merge_format4)
                    worksheet.write(row + 3, 5, obj['date_done'], merge_format4)
                else:
                    worksheet.write(row + 3, 4, "No", merge_format4)
                invoice = self.env['account.move'].search([('origin', '=', obj['origin'])])
                if not invoice:
                    worksheet.write(row + 3, 6, "No", merge_format4)
                for inv in invoice:
                    if inv.state == 'paid':
                        worksheet.write(row + 3, 6, "Yes", merge_format4)
                        worksheet.write(row + 3, 7, obj['date_invoice'], merge_format4)
                    else:
                        worksheet.write(row + 3, 6, "No", merge_format4)
                job_card = self.env['job.card'].search([('sale_order_id', '=', self.id),('device_serial_number_new_id','=',obj['lot_ids']),('state','=','done')])
                if job_card:
                    worksheet.write(row + 3, 8, "Yes", merge_format4)
                    worksheet.write(row + 3, 9, job_card.installation_date, merge_format4)

                else:
                    worksheet.write(row + 3, 8, "No", merge_format4)
                subscription = self.env['sale.order'].search(
                    [('serial_no', '=', obj['lot_ids']), ('sale_order_id', '=', self.id),
                     ('state', 'in', ('draft', 'open')), ('is_subscription', '=', True)])
                if subscription:
                    worksheet.write(row + 3, 10, "Yes", merge_format4)
                    cus_date = datetime.strptime(subscription.create_date, "%Y-%m-%d %H:%M:%S").date()
                    worksheet.write(row + 3, 11,str(cus_date), merge_format4)
                else:
                    worksheet.write(row + 3, 10, "No", merge_format4)
                subscription_start = self.env['sale.order'].search(
                    [('serial_no', '=', obj['lot_ids']), ('sale_order_id', '=', self.id),
                     ('state', '=', 'open'), ('is_subscription', '=', True)])
                if subscription_start:
                    worksheet.write(row + 3, 12, "Yes", merge_format4)
                else:
                    worksheet.write(row + 3,12, "No", merge_format4)
                worksheet.write(row + 3, 13, subscription_start.date_start, merge_format4)
                worksheet.write(row + 3, 14, subscription_start.date, merge_format4)
                row += 1
                serial_count += 1
        elif self.sale_type == 'rental':
            worksheet.write(4, 3, "Total Stock", merge_format1)
            worksheet.write(4, 4, "Unalloted Stock", merge_format1)
            worksheet.write(4, 5, "Report Taken On", merge_format1)
            worksheet.write(row, 2, "Rental Sale", merge_format4)
            self.env.cr.execute("""
                             SELECT  ptt.name as product_name ,spl.name as lot_name,
                             ru.name as user_name,ai.origin,
                             smls.lot_id as lot_ids ,sppg.id as pick_id,date(sppg.date_done) as date_done,ai.date_invoice
                              from sale_order so
                            JOIN sale_order_line sol ON (so.id=sol.order_id)
                            LEFT JOIN project_project pp ON (pp.sale_order_id=so.id)
                            LEFT JOIN project_task pt ON (pp.id=pt.project_id)
                            LEFT JOIN product_product ppt ON (ppt.id=sol.product_id)
                            LEFT JOIN product_template ptt ON (ptt.id=ppt.product_tmpl_id)
                            LEFT JOIN  material_purchase_requisition mpl ON (mpl.task_id=pt.id)
                            LEFT JOIN stock_picking sppg ON (mpl.id=sppg.custom_requisition_id )
                            LEFT JOIN stock_move sms ON (sppg.id=sms.picking_id)
                            LEFT JOIN stock_move_line smls ON (smls.move_id=sms.id)
                            LEFT JOIN stock_production_lot spl ON (spl.id=smls.lot_id)
                            LEFT JOIN account_invoice ai ON (ai.origin=so.name)
                            LEFT JOIN hr_employee ru ON (ru.id=mpl.employee_id)
                            WHERE so.id=%d  and ptt.type='product'
                            """ % self.id)
            product_ids = [i for i in self.env.cr.dictfetchall()]
            valuess = len(product_ids)
            quant=quantity-valuess
            worksheet.write(row, 3,quantity, merge_format4)
            worksheet.write(row, 4,quant, merge_format4)
            worksheet.write(row, 5,today, merge_format4)
            serial_count = 1
            for obj in product_ids:
                worksheet.write(row + 3, 0, serial_count, merge_format4)
                worksheet.write(row + 3, 1, obj['product_name'], merge_format4)
                worksheet.write(row + 3, 2, obj['lot_name'], merge_format4)
                worksheet.write(row + 3, 3, obj['user_name'], merge_format4)

                stock = self.env['stock.picking'].search([('id', '=', obj['pick_id'])])
                if stock.state == 'done':
                    worksheet.write(row + 3, 4, "Yes", merge_format4)
                    worksheet.write(row + 3, 5, obj['date_done'], merge_format4)
                else:
                    worksheet.write(row + 3, 4, "No", merge_format4)
                invoice = self.env['account.move'].search([('origin', '=', obj['origin'])])
                if not invoice:
                    worksheet.write(row + 3, 6, "No", merge_format4)
                for inv in invoice:
                    if inv.state == 'paid':
                        worksheet.write(row + 3, 6, "Yes", merge_format4)
                        worksheet.write(row + 3, 7, obj['date_invoice'], merge_format4)
                    else:
                        worksheet.write(row + 3, 6, "No", merge_format4)
                job_card = self.env['job.card'].search([('sale_order_id', '=', self.id),('device_serial_number_new_id','=',obj['lot_ids']),('state','=','done')])
                if job_card:
                    worksheet.write(row + 3, 8, "Yes", merge_format4)
                    worksheet.write(row + 3, 9, job_card.installation_date, merge_format4)

                else:
                    worksheet.write(row + 3, 8, "No", merge_format4)
                subscription = self.env['sale.order'].search(
                    [('serial_no', '=', obj['lot_ids']), ('sale_order_id', '=', self.id),
                     ('state', 'in', ('draft', 'open')), ('is_subscription', '=', True)])
                if subscription:
                    worksheet.write(row + 3, 10, "Yes", merge_format4)
                    cus_date = datetime.strptime(subscription.create_date, "%Y-%m-%d %H:%M:%S").date()
                    worksheet.write(row + 3, 11,str(cus_date), merge_format4)
                else:
                    worksheet.write(row + 3, 10, "No", merge_format4)
                subscription_start = self.env['sale.order'].search(
                    [('serial_no', '=', obj['lot_ids']), ('sale_order_id', '=', self.id),
                     ('state', '=', 'open'), ('is_subscription', '=', True)])
                if subscription_start:
                    worksheet.write(row + 3, 12, "Yes", merge_format4)
                else:
                    worksheet.write(row + 3,12, "No", merge_format4)
                worksheet.write(row + 3, 13, subscription_start.date_start, merge_format4)
                worksheet.write(row + 3, 14, subscription_start.date, merge_format4)
                row += 1
                serial_count += 1
        elif self.purchase_type == 'project':
            worksheet.write(4, 3, "Total Stock", merge_format1)
            worksheet.write(4, 4, "Unalloted Stock", merge_format1)
            worksheet.write(4, 5, "Report Taken On", merge_format1)
            worksheet.write(row, 2, "Unit Sale - Project", merge_format4)
            self.env.cr.execute("""
                             SELECT  ptt.name as product_name ,spl.name as lot_name,
                             ru.name as user_name,ai.origin,
                             smls.lot_id as lot_ids ,sppg.id as pick_id,sppg.date_done,ai.date_invoice
                              from sale_order so
                            JOIN sale_order_line sol ON (so.id=sol.order_id)
                            LEFT JOIN project_project pp ON (pp.sale_order_id=so.id)
                            LEFT JOIN project_task pt ON (pp.id=pt.project_id)
                            LEFT JOIN product_product ppt ON (ppt.id=sol.product_id)
                            LEFT JOIN product_template ptt ON (ptt.id=ppt.product_tmpl_id)
                            LEFT JOIN  material_purchase_requisition mpl ON (mpl.task_id=pt.id)
                            LEFT JOIN stock_picking sppg ON (mpl.id=sppg.custom_requisition_id )
                            LEFT JOIN stock_move sms ON (sppg.id=sms.picking_id)
                            LEFT JOIN stock_move_line smls ON (smls.move_id=sms.id)
                            LEFT JOIN stock_production_lot spl ON (spl.id=smls.lot_id)
                            LEFT JOIN account_invoice ai ON (ai.origin=so.name)
                            LEFT JOIN hr_employee ru ON (ru.id=mpl.employee_id)
                            WHERE so.id=%d  and ptt.type='product'
                            """ % self.id)
            product_ids = [i for i in self.env.cr.dictfetchall()]
            valuess = len(product_ids)
            quant=quantity-valuess
            worksheet.write(row, 3,quantity, merge_format4)
            worksheet.write(row, 4,quant, merge_format4)
            worksheet.write(row, 5,today, merge_format4)
            serial_count = 1
            for obj in product_ids:
                worksheet.write(row + 3, 0, serial_count, merge_format4)
                worksheet.write(row + 3, 1, obj['product_name'], merge_format4)
                worksheet.write(row + 3, 2, obj['lot_name'], merge_format4)
                worksheet.write(row + 3, 3, obj['user_name'], merge_format4)

                stock = self.env['stock.picking'].search([('id', '=', obj['pick_id'])])
                if stock.state == 'done':
                    worksheet.write(row + 3, 4, "Yes", merge_format4)
                    worksheet.write(row + 3, 5, obj['date_done'], merge_format4)
                else:
                    worksheet.write(row + 3, 4, "No", merge_format4)
                invoice = self.env['account.move'].search([('origin', '=', obj['origin'])])
                if not invoice:
                    worksheet.write(row + 3, 6, "No", merge_format4)
                for inv in invoice:
                    if inv.state == 'paid':
                        worksheet.write(row + 3, 6, "Yes", merge_format4)
                        worksheet.write(row + 3, 7, obj['date_invoice'], merge_format4)
                    else:
                        worksheet.write(row + 3, 6, "No", merge_format4)
                job_card = self.env['job.card'].search([('sale_order_id', '=', self.id),('device_serial_number_new_id','=',obj['lot_ids']),('state','=','done')])
                if job_card:
                    worksheet.write(row + 3, 8, "Yes", merge_format4)
                    worksheet.write(row + 3, 9, job_card.installation_date, merge_format4)

                else:
                    worksheet.write(row + 3, 8, "No", merge_format4)
                subscription = self.env['sale.order'].search(
                    [('serial_no', '=', obj['lot_ids']), ('sale_order_id', '=', self.id),
                     ('state', 'in', ('draft', 'open')), ('is_subscription', '=', True)])
                if subscription:
                    worksheet.write(row + 3, 10, "Yes", merge_format4)
                    cus_date = datetime.strptime(subscription.create_date, "%Y-%m-%d %H:%M:%S").date()
                    worksheet.write(row + 3, 11,str(cus_date), merge_format4)
                else:
                    worksheet.write(row + 3, 10, "No", merge_format4)
                subscription_start = self.env['sale.order'].search(
                    [('serial_no', '=', obj['lot_ids']), ('sale_order_id', '=', self.id),
                     ('state', '=', 'open'), ('is_subscription', '=', True)])
                if subscription_start:
                    worksheet.write(row + 3, 12, "Yes", merge_format4)
                else:
                    worksheet.write(row + 3,12, "No", merge_format4)
                worksheet.write(row + 3, 13, subscription_start.date_start, merge_format4)
                worksheet.write(row + 3, 14, subscription_start.date, merge_format4)
                row += 1
                serial_count += 1
        workbook.close()
        fo = open(url + 'Order Status.xlsx', "rb+")
        data = fo.read()
        out = base64.encodestring(data)
        self.write({'filedata': out, 'filename': 'Order Status.xlsx'+'-'+today})

    #@api.multi
    def _get_assigned_report(self):

        output = StringIO()
        url = '/home/support/'
        today = datetime.today().strftime('%d-%m-%Y')
        workbook = xlsxwriter.Workbook(url + 'Assigned Devices.xlsx')
        worksheet = workbook.add_worksheet()

        merge_format1 = workbook.add_format({
            'bold': 1,
            'border': 1,
            'align': 'center',
            'fg_color': '#ffff66',
            'valign': 'vcenter', })

        merge_format2 = workbook.add_format({
            'align': 'left',
            'valign': 'vcenter', })

        merge_format3 = workbook.add_format({
            'align': 'center',
            'bold': 1,
            'border': 1,
            'font_size': 14,
        })

        merge_format4 = workbook.add_format({
            'align': 'right',
            'bold': 1,
            'valign': 'vcenter', })
        format_date = workbook.add_format({
            'num_format': 'd mmm yyyy hh:mm AM/PM',
            'align': 'left',
        })
        worksheet.set_column('A:A', 5)
        worksheet.set_column('B:B', 25)
        worksheet.set_column('C:C', 15)
        worksheet.set_column('D:D', 15)
        worksheet.set_column('E:E', 15)
        worksheet.merge_range('A1:E1', 'Assigned Status Report', merge_format3)
        worksheet.write(4, 0, 'Sale Order No', merge_format1)
        worksheet.write(4, 1, "Customer", merge_format1)
        worksheet.write(4, 2, "Sale Type", merge_format1)
        worksheet.write(4, 3, "Report Taken On", merge_format1)
        worksheet.write(7, 0, "S.No", merge_format1)
        worksheet.write(7, 1, "Device Type", merge_format1)
        worksheet.write(7, 2, "Device Serial No", merge_format1)
        worksheet.write(7, 3, "Engineer", merge_format1)
        row = 5

        worksheet.write(row, 0, self.name, merge_format4)
        worksheet.write(row, 1, self.partner_id.name, merge_format4)
        worksheet.write(row, 2, self.sale_type, merge_format4)
        worksheet.write(row, 3, today, merge_format4)

        if self.sale_type == 'cash' or self.purchase_type == 'non_project':
            self.env.cr.execute("""SELECT  ptt.name as product_name , spl.name as lot_name,
                                        rp.name as user_name from sale_order so
                                        JOIN sale_order_line sol ON (so.id=sol.order_id)
                                        JOIN stock_picking sp ON (sp.sale_id=so.id)
                                        JOIN stock_move sm ON (sm.picking_id=sp.id)
                                        JOIN stock_move_line sml ON (sml.move_id=sm.id)
                                        JOIN product_product ppt ON (ppt.id=sol.product_id)
                                        JOIN job_card jc ON (jc.sale_order_id=so.id)
                                        JOIN product_template ptt ON (ptt.id=ppt.product_tmpl_id)
                                        JOIN stock_production_lot spl ON (spl.id=sml.lot_id)
                                        JOIN res_users ru ON (ru.id=jc.engineer_id)
                                        JOIN res_partner rp ON (rp.id=ru.partner_id)
                                         WHERE so.id=%d and sp.state='done' and ptt.type='product'

                                        """%self.id)
            assigned=self.env.cr.dictfetchall()
            if assigned:
                serial_count = 1
                for assign in assigned:
                    worksheet.write(row + 3, 0, serial_count, merge_format4)
                    worksheet.write(row + 3, 1, assign['product_name'], merge_format4)
                    worksheet.write(row + 3, 2, assign['lot_name'], merge_format4)
                    worksheet.write(row + 3, 3, assign['user_name'], merge_format4)
                    row += 1
                    serial_count += 1
            else:
                raise ValidationError("No Records Found")
        elif self.sale_type == 'rental' or self.sale_type == 'lease' or self.purchase_type == 'project':
            self.env.cr.execute("""SELECT  ru.name as partner_name,spl.name as lot_name, ptt.name as product_name from sale_order so
                                    JOIN sale_order_line sol ON (so.id=sol.order_id)
                                    JOIN product_product ppt ON (ppt.id=sol.product_id)
                                    JOIN product_template ptt ON (ptt.id=ppt.product_tmpl_id)
                                    JOIN project_project pp ON (pp.sale_order_id=so.id)
                                    JOIN project_task pt ON (pt.project_id=pp.id)
                                    JOIN material_purchase_requisition mpl ON (mpl.task_id=pt.id)
                                    JOIN stock_picking sp ON (sp.custom_requisition_id=mpl.id)
                                    JOIN stock_move sm ON (sm.picking_id=sp.id)
                                    JOIN stock_move_line sml ON (sml.move_id=sm.id)
                                    JOIN stock_production_lot spl ON (spl.id=sml.lot_id)
                                    JOIN hr_employee ru ON (ru.id=mpl.employee_id)
                                    WHERE so.id=%d and sp.state='done' and ptt.type='product'"""%self.id)
            vals=self.env.cr.dictfetchall()
            if vals:
                serial_count = 1
                for val in vals:
                    worksheet.write(row + 3, 0, serial_count, merge_format4)
                    worksheet.write(row + 3, 1, val['product_name'], merge_format4)
                    worksheet.write(row + 3, 2, val['lot_name'], merge_format4)
                    worksheet.write(row + 3, 3, val['partner_name'], merge_format4)
                    row += 1
                    serial_count += 1
            else:
                raise ValidationError("No Records Found")

        workbook.close()
        fo = open(url + 'Assigned Devices.xlsx', "rb+")
        data = fo.read()
        out = base64.encodestring(data)
        self.write({'datafile': out, 'namefile': 'Assigned Devices.xlsx'+'-'+today})
