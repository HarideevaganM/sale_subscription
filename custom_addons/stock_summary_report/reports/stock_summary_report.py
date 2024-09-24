# -*- coding: utf-8 -*-

from odoo import models, fields, _
import datetime
from datetime import datetime, timedelta, date
import dateutil.parser
import pytz


class StockSummaryReportXls(models.AbstractModel):
    _name = 'report.stock_summary_report.stock_summary_report.xlsx'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, lines):
        if data['form']['parent_location'] or data['form']['all_locations']:
            sheet2 = workbook.add_worksheet('Stock Main Location')
            self.get_product_with_main_location(data, workbook, sheet2)
        else:
            sheet = workbook.add_worksheet('Stock Summary')
            self.print_header(data, workbook, sheet)
            self.get_product_with_category(data, workbook, sheet)

    def print_header(self, data, workbook, sheet):
        format_header = workbook.add_format(
            {'border': True, 'font_name': 'Arial', 'font_size': 9, 'align': 'center', 'bold': True,
             'bg_color': '#2c286c', 'font_color': 'white'})
        format_header_no_bg = workbook.add_format(
            {'font_name': 'Arial', 'font_size': 10, 'align': 'center', 'bold': True})
        format_header_string = workbook.add_format(
            {'font_name': 'Arial', 'font_size': 10, 'align': 'center', 'bold': False})
        format_header_title = workbook.add_format(
            {'font_name': 'Arial', 'font_size': 18, 'align': 'center', 'bold': True})
        company = self.env['res.company'].search([('id', '=', data['form']['company_id'])])
        user = self.env.user.name
        tz = pytz.timezone(self.env.user.tz) if self.env.user.tz else pytz.timezone("Asia/Kathmandu")
        time = pytz.utc.localize(datetime.now()).astimezone(tz)
        if data['form']['show_cost']:
            colmns = 'A{}:G{}'
        else:
            colmns = 'A{}:F{}'
        sheet.merge_range(colmns.format(1, 1), 'STOCK SUMMARY REPORT', format_header_title)
        sheet.merge_range(colmns.format(2, 2), company.name, format_header_no_bg)
        sheet.merge_range(colmns.format(3, 3), 'Location: ' + str(data['location']), format_header_string)
        sheet.merge_range(colmns.format(4, 4),
                          'Generated On : ' + str(time.strftime("%d/%m/%Y, %I:%M:%S %p")) + "\t \t \t By:  " + str(
                              user), format_header_string)

        sheet.write('C6', 'From', format_header_no_bg)
        sheet.write('C7', data['form']['start_date'], format_header_no_bg)
        sheet.write('F6', 'To', format_header_no_bg)
        sheet.write('F7', data['form']['end_date'], format_header_no_bg)
        sheet.write('A8', 'Particulars', format_header)
        sheet.write('B8', 'UOM', format_header)
        sheet.write('C8', 'Opening Stock', format_header)
        sheet.write('D8', 'Inwards', format_header)
        sheet.write('E8', 'Outwards', format_header)
        sheet.write('F8', 'Closing Stock', format_header)
        if data['form']['show_cost']:
            sheet.write('G8', 'Closing Value', format_header)

        col = 0
        # Adjust the column width.
        sheet.set_column(col, col, 45)  # Particulars
        col += 2
        sheet.set_column(col, col, 15)  # Opening Balance
        col += 1
        sheet.set_column(col, col, 10)  # Inwards
        col += 1
        sheet.set_column(col, col, 10)  # Outwards
        col += 1
        sheet.set_column(col, col, 15)  # Closing Balance
        col += 1
        sheet.set_column(col, col, 15)  # Closing Value

    def _get_records(self, data, location=None, product_id=None):
        """
        @param start_date: start date
        @param end_date: end date
        @param location_id: location ID
        @param product_id: Product IDs
        @returns: recordset
        """

        domains = []
        domains += [
            ('date', '>=', data['form']['start_date']),
            ('date', '<=', data['form']['end_date']),
            ('state', '=', 'done'),
            ('product_id.id', '=', product_id),
            '|',
            ('location_id.id', '=', location),
            ('location_dest_id.id', '=', location)
        ]
        records = self.env['stock.move.line'].search(domains, order='date asc')
        product_id = self.env['product.product'].search([('id', '=', product_id), ('type', '=', 'product')])
        location_name = self.env['stock.location'].search([('id', '=', location)]).display_name
        opening_date = datetime.strptime(data['form']['start_date'], "%Y-%m-%d").date() + timedelta(days=-1)
        closing_date = datetime.strptime(data['form']['end_date'], "%Y-%m-%d").date()
        opening = product_id.with_context({'to_date': str(opening_date), 'location': location}).qty_available
        # opening_value = product_id.with_context({'to_date': str(opening_date), 'location': location}).stock_value
        closing = product_id.with_context({'to_date': str(closing_date), 'location': location}).qty_available
        product_closing_date = datetime.strptime(data['form']['end_date'], "%Y-%m-%d").date() + timedelta(days=+1)

        if closing_date:
            # closing_value = product_id.get_history_price(
            #     self.env.user.company_id.id,
            #     date=datetime.strftime(product_closing_date, "%Y-%m-%d %H:%M:%S"))
            closing_value = product_id.standard_price
        closing_value = closing_value * closing

        # Find out the Opening Quantities without the sum of Sub Locations.
        total_sub_opening = 0
        location_child_ids = self.env['stock.location'].search([('location_id', '=', location)])
        if location_child_ids:
            for sub_loc in location_child_ids:
                sub_opening = product_id.with_context(
                    {'to_date': str(opening_date), 'location': sub_loc.id}).qty_available
                total_sub_opening = total_sub_opening + sub_opening
        opening = opening - total_sub_opening

        # Find out the Closing Quantities without the sum of Sub Locations.
        total_sub_closing = 0
        location_child_ids = self.env['stock.location'].search([('location_id', '=', location)])
        if location_child_ids:
            for sub_loc in location_child_ids:
                sub_closing = product_id.with_context(
                    {'to_date': str(closing_date), 'location': sub_loc.id}).qty_available
                total_sub_closing = total_sub_closing + sub_closing
        closing = closing - total_sub_closing

        total_in = 0
        total_in_value = 0
        for record in (records.filtered(lambda r: r.location_dest_id.id == location)):
            total_in += record.product_uom_id._compute_quantity(record.qty_done, record.product_id.uom_id)
            total_in_value += record.qty_done
        total_out = 0
        total_out_value = 0
        for record in (records.filtered(lambda r: r.location_id.id == location)):
            total_out += record.product_uom_id._compute_quantity(record.qty_done, record.product_id.uom_id)
            total_out_value += record.qty_done
        summary = {
            'product': product_id,
            'product_code': product_id.default_code,
            'product_name': product_id.name,
            'product_uom': product_id.uom_id.name,
            'opening': opening,
            'closing': closing,
            'total_in': total_in,
            'total_out': total_out,
            'closing_value': closing_value,
        }
        return summary

    def _get_product_with_category(self, data, workbook, sheet):
        # format of Cells according to data type and categories
        format_total_string = workbook.add_format(
            {'font_name': 'Arial', 'font_size': 9, 'align': 'center', 'bold': True, 'bg_color': 'silver'})
        format_string = workbook.add_format(
            {'border': True, 'font_name': 'Arial', 'font_size': 9, 'align': 'left', 'bold': False})
        format_string_center = workbook.add_format(
            {'border': True, 'font_name': 'Arial', 'font_size': 9, 'align': 'center', 'bold': False})
        format_numeric = workbook.add_format(
            {'border': True, 'font_name': 'Arial', 'font_size': 9, 'num_format': '#,##0.00', 'bold': False})

        category_name_format = workbook.add_format(
            {'border': True, 'font_name': 'Arial', 'font_size': 9, 'align': 'left', 'bold': True,
             'bg_color': '#ddebf7'})

        location = data['form']['location_id']
        products = self.env['product.product'].search(
            [('type', '=', 'product'), ('location_id.id', '=', data['form']['location_id'])])
        categories = list(set([product.categ_id.id for product in products]))
        categ_records = self.env['product.category'].search([('id', 'in', categories)])
        row = 8
        for category in categ_records:
            if data['form']['show_cost']:
                sheet.merge_range('A{}:G{}'.format(row + 1, row + 1), category.name, category_name_format)
            else:
                sheet.merge_range('A{}:F{}'.format(row + 1, row + 1), category.name, category_name_format)
            cate_products = self.env['product.product'].search(
                [('categ_id.id', '=', category.id), ('type', '=', 'product'),
                 ('location_id.id', '=', data['form']['location_id'])])
            for product in cate_products:
                row += 1
                summary = self.get_records(data, location=data['form']['location_id'], product_id=product.id)
                if summary['product_code']:
                    sheet.write(row, 0, summary['product_code'] + ' - ' + summary['product_name'], format_string)
                else:
                    sheet.write(row, 0, summary['product_name'], format_string)
                sheet.write(row, 1, summary['product_uom'], format_string_center)
                sheet.write(row, 2, summary['opening'], format_numeric)

                sheet.write(row, 3, summary['total_in'], format_numeric)

                sheet.write(row, 4, summary['total_out'], format_numeric)

                sheet.write(row, 5, summary['closing'], format_numeric)
                if data['form']['show_cost']:
                    sheet.write(row, 6, summary['closing_value'], format_numeric)

            row += 1

    # Function for getting the closing quantity of each product in each location.
    def _get_all_location_data(self, data, location=None, product_id=None):
        total_sub_closing = 0
        closing_date = datetime.strptime(data['form']['end_date'], "%Y-%m-%d").date()
        product_id = self.env['product.product'].search([('id', '=', product_id), ('type', '=', 'product')])
        closing = product_id.with_context({'to_date': str(closing_date), 'location': location}).qty_available
        product_closing_date = datetime.strptime(data['form']['end_date'], "%Y-%m-%d").date() + timedelta(days=+1)

        # Summarize the quantities by avoiding the adding of quantities in sub location.
        main_location_name = ''
        location_child_ids = self.env['stock.location'].search([('location_id', '=', location)])
        if location_child_ids:
            for sub_loc in location_child_ids:
                sub_closing = product_id.with_context(
                    {'to_date': str(closing_date), 'location': sub_loc.id}).qty_available
                total_sub_closing = total_sub_closing + sub_closing
        closing = closing - total_sub_closing
        if closing_date:
            # closing_value = product_id.get_history_price(
            #     self.env.user.company_id.id,
            #     date=datetime.strftime(product_closing_date, "%Y-%m-%d %H:%M:%S"))
            closing_value = product_id.standard_price

        all_location = {
            'product': product_id,
            'product_name': product_id.name,
            'product_uom': product_id.uom_id.name,
            'closing': closing,
            'closing_value': closing_value,
        }
        return all_location

    # Function for generating the excel having all the products in every location with closing quantity.
    def _get_product_with_main_location(self, data, workbook, sheet2):
        sheet2.freeze_panes(1, 1)
        sheet2.set_column('A:A', 50)
        sheet2.set_column('B:BZ', 20)

        format_location = workbook.add_format({'font_name': 'Arial', 'font_size': 9, 'align': 'center', 'bold': True,
                                               'bg_color': '#00B050', 'font_color': 'white', 'valign': 'vcenter',
                                               'text_wrap': True, 'border': True})
        format_string_product = workbook.add_format(
            {'font_name': 'Arial', 'font_size': 8, 'align': 'left', 'bold': False,
             'border': True, 'text_wrap': True, 'valign': 'vcenter', 'bg_color': '#EEECE1'})
        format_product_header = workbook.add_format(
            {'font_name': 'Arial', 'font_size': 9, 'align': 'center', 'bold': True,
             'bg_color': 'orange', 'font_color': 'white', 'valign': 'vcenter',
             'text_wrap': True, 'border': True})
        format_string_qty = workbook.add_format(
            {'font_name': 'Arial', 'font_size': 9, 'align': 'right', 'bold': False,
             'border': True, 'text_wrap': True, 'valign': 'vcenter'})

        products = self.env['product.product'].search([('type', '=', 'product')])
        locations = self.env['stock.location'].search([])

        row = 0
        first_row = 0
        loc_col = 0
        column = 0
        location_list = []
        sheet2.write(row, column, 'PRODUCT LIST', format_product_header)

        for product in products:
            row = row + 1
            if product.default_code:
                sheet2.write(row, column, str(product.default_code) + ' - ' + str(product.name), format_string_product)
            else:
                sheet2.write(row, column, str(product.name), format_string_product)

            total_qty = 0
            for sub_location in locations:
                if not data['form']['all_locations']:
                    if sub_location.location_id.id == data['form']['parent_location'] and sub_location.usage != 'view':
                        loc_col = loc_col + 1
                        if sub_location.name not in location_list:
                            sheet2.write(first_row, loc_col, sub_location.name, format_location)
                            location_list.append(sub_location.name)

                        summary = self.get_all_location_data(data, location=sub_location.id, product_id=product.id)
                        if summary:
                            sheet2.write(row, loc_col, summary['closing'], format_string_qty)
                            total_qty = total_qty + summary['closing']
                            sheet2.write(row, loc_col + 1, total_qty, format_string_qty)
                else:
                    if sub_location.usage == 'internal':
                        loc_col = loc_col + 1
                        if sub_location.location_id:
                            main_location = self.env['stock.location'].search([('id', '=', sub_location.location_id.id)])
                        if main_location:
                            sheet2.write(first_row, loc_col, main_location.name + '/' + sub_location.name,
                                         format_location)
                        else:
                            sheet2.write(first_row, loc_col, sub_location.name, format_location)

                        summary = self.get_all_location_data(data, location=sub_location.id, product_id=product.id)
                        if summary:
                            sheet2.write(row, loc_col, summary['closing'], format_string_qty)
                            total_qty = total_qty + summary['closing']
                            sheet2.write(row, loc_col + 1, total_qty, format_string_qty)
                            if data['form']['show_cost']:
                                sheet2.write(row, loc_col + 2, total_qty * summary['closing_value'], format_string_qty)
            sheet2.write(first_row, loc_col + 1, 'TOTAL', format_product_header)
            if data['form']['show_cost']:
                sheet2.write(first_row, loc_col + 2, 'Closing Value', format_product_header)

            loc_col = 0
