import xlwt
# import cStringIO
from io import BytesIO
import base64
from odoo import models, api, fields, _
import string


class AssetReport(models.TransientModel):
    _name = 'all.asset.report'

    name = fields.Char(string='Name', required=True)
    xls_output = fields.Boolean(string='Excel Output', help='Tick if you want to output of report in excel sheet')

    #@api.multi
    def render_header(self, ws, fields, first_row=0):
        header_style = xlwt.easyxf('font: name Helvetica,bold on')
        col = 1
        for hdr in fields:
            ws.write(first_row, col, hdr, header_style)
            col += 1
        return first_row + 2

    #@api.multi
    def print_report(self, data):
        """
         To get the date and print the report
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param context: A standard dictionary
         @return: return report
        """

        # data = self.read(['assets'])
        context = (self._context or {})
        datas = {'ids': context.get('active_ids', [])}

        asset_record = self.env['account.asset.asset'].search([])

        res = self.read()
        res = res and res[0] or {}
        datas.update({'form': res})
        if datas['form'].get('xls_output', False):
            workbook = xlwt.Workbook()
            sheet = workbook.add_sheet('Asset Report')
            sheet.row(0).height = 256 * 3
            title_style = xlwt.easyxf('font: name Times New Roman,bold on, italic on, height 600')
            al = xlwt.Alignment()
            al.horz = xlwt.Alignment.HORZ_CENTER
            title_style.alignment = al

            sheet.write_merge(0, 0, 2, 5, 'Asset Report', title_style)
            row = self.render_header(sheet,
                                     ['Asset Name'] + ['Asset Category'] + ['Asset Model'] +
                                     ['Asset Number'] + ['Asset State'] + ['Current Location'],
                                     first_row=2)
            value_style = xlwt.easyxf('font: name Helvetica,bold on', num_format_str='#,##0.00')
            cell_count = 0
            for record in asset_record:
                cell_count += 1
                sheet.write(row + cell_count, 1, record.name, value_style)
                sheet.write(row + cell_count, 2, record.category_id.name, value_style)
                sheet.write(row + cell_count, 3, record.asset_model.name, value_style)
                sheet.write(row + cell_count, 4, record.asset_number, value_style)
                sheet.write(row + cell_count, 5, string.capwords(record.asset_status), value_style)
                if record.location:
                    sheet.write(row + cell_count, 6, record.location.name, value_style)
                else:
                    sheet.write(row + cell_count, 6, record.initial_location.name, value_style)
            stream = BytesIO
            workbook.save(stream)
            ir_attachment = self.env['ir.attachment'].create({
                'name': self.name + '.xls',
                'datas': base64.encodestring(stream.getvalue()),
                'datas_fname': self.name + '.xls'}).id

            actid = self.env.ref('base.action_attachment')[0]
            myres = actid.read()[0]
            myres['domain'] = "[('id','in',[" + ','.join(map(str, [ir_attachment])) + "])]"
            return myres


class AllocatedAssetReport(models.TransientModel):
    _name = 'allocated.asset.report'

    name = fields.Char(string='Name', required=True)
    xls_output = fields.Boolean(string='Excel Output', help='Tick if you want to output of report in excel sheet')

    #@api.multi
    def render_header(self, ws, fields, first_row=0):
        header_style = xlwt.easyxf('font: name Helvetica,bold on,height 200')
        col = 1
        for hdr in fields:
            ws.write(first_row, col, hdr, header_style)
            col += 1
        return first_row + 2

    #@api.multi
    def allocated_print_report(self, data):
        """
         To get the date and print the report
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param context: A standard dictionary
         @return: return report
        """

        # data = self.read(['assets'])
        context = (self._context or {})
        datas = {'ids': context.get('active_ids', [])}

        asset_record = self.env['account.asset.asset'].search([('assigned_to', '!=', False)])

        res = self.read()
        res = res and res[0] or {}
        datas.update({'form': res})
        if datas['form'].get('xls_output', False):
            workbook = xlwt.Workbook()
            sheet = workbook.add_sheet('Allocated Asset Report')
            sheet.row(0).height = 256 * 3
            title_style = xlwt.easyxf('font: name Times New Roman,bold on, italic on, height 600')
            al = xlwt.Alignment()
            al.horz = xlwt.Alignment.HORZ_CENTER
            title_style.alignment = al

            sheet.write_merge(0, 0, 2, 9, 'Allocated Asset Report', title_style)
            row = self.render_header(sheet,
                                     ['Asset Name'] + ['Asset Category'] + ['Asset Model'] +
                                     ['Asset Number'] + ['Allocated To'] + ['Current Location'],
                                     first_row=2)
            value_style = xlwt.easyxf('font: name Helvetica,bold on', num_format_str='#,##0.00')
            cell_count = 0
            for record in asset_record:
                if record.assigned_to:
                    cell_count += 1
                    sheet.write(row + cell_count, 1, record.name, value_style)
                    sheet.write(row + cell_count, 2, record.category_id.name, value_style)
                    sheet.write(row + cell_count, 3, record.asset_model.name, value_style)
                    sheet.write(row + cell_count, 4, record.asset_number, value_style)
                    sheet.write(row + cell_count, 5, record.assigned_to.name, value_style)
                    sheet.write(row + cell_count, 6, record.location.name, value_style)

            stream = cStringIO.StringIO()
            workbook.save(stream)
            ir_attachment = self.env['ir.attachment'].create({
                'name': self.name + '.xls',
                'datas': base64.encodestring(stream.getvalue()),
                'datas_fname': self.name + '.xls'}).id

            actid = self.env.ref('base.action_attachment')[0]
            myres = actid.read()[0]
            myres['domain'] = "[('id','in',[" + ','.join(map(str, [ir_attachment])) + "])]"
            return myres