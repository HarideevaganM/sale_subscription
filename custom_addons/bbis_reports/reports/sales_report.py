from odoo import models
import math
from datetime import datetime


class BbisSalesReportXlsx(models.AbstractModel):
    _name = 'report.bbis_reports.sales_report_xlsx'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, orders):
        start_date = data['start_date']
        end_date = data['end_date']
        sales_person = data['sales_person']

        domain = [('confirmation_date', '>=', start_date), ('confirmation_date', '<=', end_date), ('state', 'in', ('sale', 'done'))]
        if sales_person:
            domain.append(('user_id', 'in', sales_person))
        order = 'partner_id asc'
        main_orders = self.env['sale.order'].search(domain, order=order)

        # Formats
        title_format = workbook.add_format({'bold': True, 'border': True, 'align': 'center', 'valign': 'vcenter', 'font_size': 14})
        header_format = workbook.add_format({'bold': True, 'border': True, 'font_size': 9, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#f05a29', 'font_color': 'white'})
        sub_header_format = workbook.add_format({'bold': True, 'border': True, 'font_size': 9, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#F2F2F2', 'font_color': 'black'})
        total_format_currency = workbook.add_format({'bold': True, 'border': True, 'font_size': 9, 'align': 'center', 'bg_color': '#f05a29', 'font_color': 'white', 'num_format': '#,##0.00'})
        cell_format = workbook.add_format({'valign': 'vcenter', 'border': True, 'font_size': 9, 'text_wrap': True})
        cell_format_bold = workbook.add_format({'bold': True, 'valign': 'vcenter', 'border': True, 'font_size': 9, 'text_wrap': True})
        cell_format_center = workbook.add_format({'valign': 'vcenter', 'border': True, 'font_size': 9, 'align': 'center', 'text_wrap': True})
        cell_format_description = workbook.add_format({'valign': 'vcenter', 'border': True, 'font_size': 9, 'text_wrap': True})
        cell_format_currency = workbook.add_format({'valign': 'vcenter', 'border': True, 'font_size': 9, 'num_format': '#,##0.00'})
        cell_format_currency_bold = workbook.add_format({'valign': 'vcenter', 'border': True, 'font_size': 9, 'num_format': '#,##0.00', 'bold': True})

        start_date_1 = datetime.strptime(start_date, '%Y-%m-%d')
        end_date_1 = datetime.strptime(end_date, '%Y-%m-%d')
        from_to_date = '{} - {}'.format(start_date_1.strftime('%b %d, %Y'), end_date_1.strftime('%b %d, %Y'))
        sheet_title = 'BBIS Sales Report from {}'.format(from_to_date)

        sheet_sales = workbook.add_worksheet('Sales Report')
        row, col = 0, 0
        sheet_sales.merge_range('A1:N1', sheet_title, title_format)
        sheet_sales.set_row(row, 30)
        sheet_sales.freeze_panes(2, 3)

        row += 1

        sheet_sales.write(row, col, "Quarter", header_format)
        col += 1
        sheet_sales.write(row, col, "Month", header_format)
        col += 1
        sheet_sales.write(row, col, "SO No.", header_format)
        col += 1
        sheet_sales.write(row, col, "Confirm Date", header_format)
        col += 1
        sheet_sales.write(row, col, "PO No.", header_format)
        col += 1
        sheet_sales.write(row, col, "PO Date", header_format)
        col += 1
        sheet_sales.write(row, col, "Customer/Client Name", header_format)
        col += 1
        sheet_sales.write(row, col, "Description", header_format)
        col += 1
        sheet_sales.write(row, col, "Unit Device Qty", header_format)
        col += 1
        sheet_sales.write(row, col, "New Installation", header_format)
        col += 1
        sheet_sales.write(row, col, "Renewal", header_format)
        col += 1
        sheet_sales.write(row, col, "Other Services", header_format)
        col += 1
        sheet_sales.write(row, col, "Total Amount", header_format)
        # col += 1
        # sheet_sales.write(row, col, "No. of Vehicles", header_format)
        col += 1
        sheet_sales.write(row, col, "Sales Person", header_format)

        col = 0
        # Adjust the column width.
        sheet_sales.set_column(col, col, 7)  # Quarter
        col += 1
        sheet_sales.set_column(col, col, 7)  # Month
        col += 1
        sheet_sales.set_column(col, col, 10)  # SO No.
        col += 1
        sheet_sales.set_column(col, col, 10)  # Confirm Date
        col += 1
        sheet_sales.set_column(col, col, 15)  # PO No.
        col += 1
        sheet_sales.set_column(col, col, 10)  # PO Date
        col += 1
        sheet_sales.set_column(col, col, 40)  # Customer/Client Name
        col += 1
        sheet_sales.set_column(col, col, 50)  # Description
        col += 1
        sheet_sales.set_column(col, col, 13)  # Unit Device Qty
        col += 1
        sheet_sales.set_column(col, col, 13)  # New Installation
        col += 1
        sheet_sales.set_column(col, col, 10)  # Renewal
        col += 1
        sheet_sales.set_column(col, col, 12)  # Other Services
        col += 1
        sheet_sales.set_column(col, col, 11)  # Total Amount
        # col += 1
        # sheet_sales.set_column(col, col, 12)  # No. of Vehicles
        col += 1
        sheet_sales.set_column(col, col, 18)  # Sales Person

        row += 1

        for order in main_orders:
            confirmation_date = datetime.strptime(order.confirmation_date, '%Y-%m-%d %H:%M:%S') if order.confirmation_date else ''
            confirmation_date_str = confirmation_date.strftime('%Y-%m-%d') if confirmation_date else ''
            quarter = 'Q{}'.format(math.ceil(float(confirmation_date.month) / 3)) if confirmation_date else ''
            month = confirmation_date.strftime('%b').upper() if quarter else ''

            # Order Lines
            line_items = ""
            unit_device = 0
            new_installation = 0
            renewal = 0
            other_services = 0
            category_ids = []

            # check if it is renewal
            if order.sale_type == 'pilot':
                so_lines = self.env['sale.order.line'].read_group([('order_id', '=', order.id)], ['product_id', 'price_subtotal', 'product_uom_qty'], ['product_id', 'price_subtotal'])
                for so_line in so_lines:
                    quantity = int(so_line['product_uom_qty'])
                    product_name = so_line['product_id'][1]
                    price = '%.2f' % (float(so_line['price_subtotal']))
                    line_items += '({}) {} @ {} \n'.format(quantity, product_name, price)

                    # check if product category is renewal or not
                    prod_id = so_line['product_id'][0]
                    product = self.env['product.product'].browse(prod_id)
                    category = product.categ_id.name
                    category_id = product.categ_id.id

                    if 'renewal' in category.lower():
                        renewal += float(so_line['price_subtotal'])
                    else:
                        # check product category
                        if category_id == 18:
                            unit_device += quantity
                            new_installation += float(so_line['price_subtotal'])
                        else:
                            other_services += float(so_line['price_subtotal'])

            else:
                for line in order.order_line:
                    quantity = int(line.product_uom_qty)
                    price = '%.2f' % float(line.price_subtotal)
                    line_items += '({}) {} @ {} \n'.format(quantity, line.product_id.name, price)

                    # check product category
                    category = line.product_id.categ_id.name
                    category_id = line.product_id.categ_id.id

                    if 'renewal' in category.lower():
                        renewal += float(line.price_subtotal)
                    else:
                        if category_id == 18:
                            unit_device += quantity
                            new_installation += float(line.price_subtotal)
                        else:
                            other_services += float(line.price_subtotal)

            col = 0
            sheet_sales.write(row, col, quarter, cell_format_center)
            col += 1
            sheet_sales.write(row, col, month, cell_format_center)
            col += 1
            sheet_sales.write(row, col, order.name or '', cell_format_center)
            col += 1
            sheet_sales.write(row, col, confirmation_date_str or '', cell_format_center)
            col += 1
            sheet_sales.write(row, col, order.purchase_order_no or '', cell_format_center)
            col += 1
            sheet_sales.write(row, col, order.purchase_order_date or '', cell_format_center)
            col += 1
            sheet_sales.write(row, col, order.partner_id.name, cell_format_description)
            col += 1
            sheet_sales.write(row, col, line_items[:-1], cell_format_description)
            col += 1
            sheet_sales.write(row, col, unit_device or '', cell_format_center)
            col += 1
            sheet_sales.write(row, col, new_installation or '', cell_format_currency)
            col += 1
            sheet_sales.write(row, col, renewal or '', cell_format_currency)
            col += 1
            sheet_sales.write(row, col, other_services or '', cell_format_currency)
            col += 1
            sheet_sales.write(row, col, order.amount_untaxed, cell_format_currency_bold)
            # col += 1
            # sheet_sales.write(row, col, len(order.vehicle_number_ids), cell_format_center)
            col += 1
            sheet_sales.write(row, col, order.user_id.name, cell_format_center)

            row += 1

        col = 7
        sheet_sales.write(row, col, 'Total', header_format)
        col += 1
        sheet_sales.write(row, col, '=SUM(I{}:I{})'.format(3, row), header_format)
        col += 1
        sheet_sales.write(row, col, '=SUM(J{}:J{})'.format(3, row), total_format_currency)
        col += 1
        sheet_sales.write(row, col, '=SUM(K{}:K{})'.format(3, row), total_format_currency)
        col += 1
        sheet_sales.write(row, col, '=SUM(L{}:L{})'.format(3, row), total_format_currency)
        col += 1
        sheet_sales.write(row, col, '=SUM(M{}:M{})'.format(3, row), total_format_currency)

        """Per Salesperson sheet"""
        user_sales_person = sales_person or []
        if not sales_person:
            all_sales_person = self.env['sale.order'].read_group([('confirmation_date', '>=', start_date),
                                                                  ('confirmation_date', '<=', end_date),
                                                                  ('state', 'in', ('sale', 'done')),
                                                                  ('user_id', '!=', False)],
                                                                 ['user_id'], ['user_id'])
            for user in all_sales_person:
                user_sales_person.append(user['user_id'][0])

        # print(user_sales_person, sales_person)
        users = self.env['res.users'].search([('id', 'in', user_sales_person)])
        for user in users:
            domain = [('confirmation_date', '>=', start_date), ('confirmation_date', '<=', end_date),
                      ('user_id', '=', user.id), ('state', 'in', ('sale', 'done'))]
            user_orders = self.env['sale.order'].search(domain)

            if user_orders:
                sheet_user = workbook.add_worksheet(user.name)
                row, col = 0, 0
                sheet_user.merge_range('A1:M1', sheet_title + ' | {}'.format(user.name), title_format)
                sheet_user.set_row(row, 30)
                sheet_user.freeze_panes(2, 3)

                row += 1

                sheet_user.write(row, col, "Quarter", header_format)
                col += 1
                sheet_user.write(row, col, "Month", header_format)
                col += 1
                sheet_user.write(row, col, "SO No.", header_format)
                col += 1
                sheet_user.write(row, col, "Confirm Date", header_format)
                col += 1
                sheet_user.write(row, col, "PO No.", header_format)
                col += 1
                sheet_user.write(row, col, "PO Date", header_format)
                col += 1
                sheet_user.write(row, col, "Customer/Client Name", header_format)
                col += 1
                sheet_user.write(row, col, "Description", header_format)
                col += 1
                sheet_user.write(row, col, "Unit Device Qty", header_format)
                col += 1
                sheet_user.write(row, col, "New Installation", header_format)
                col += 1
                sheet_user.write(row, col, "Renewal", header_format)
                col += 1
                sheet_user.write(row, col, "Other Services", header_format)
                col += 1
                sheet_user.write(row, col, "Total Amount", header_format)
                # col += 1
                # sheet_user.write(row, col, "No. of Vehicles", header_format)
                # col += 1
                # sheet_user.write(row, col, "Sales Person", header_format)

                col = 0
                # Adjust the column width.
                sheet_user.set_column(col, col, 7)  # Quarter
                col += 1
                sheet_user.set_column(col, col, 7)  # Month
                col += 1
                sheet_user.set_column(col, col, 10)  # SO No.
                col += 1
                sheet_user.set_column(col, col, 10)  # Confirm Date
                col += 1
                sheet_user.set_column(col, col, 15)  # PO No.
                col += 1
                sheet_user.set_column(col, col, 10)  # PO Date
                col += 1
                sheet_user.set_column(col, col, 40)  # Customer/Client Name
                col += 1
                sheet_user.set_column(col, col, 50)  # Description
                col += 1
                sheet_user.set_column(col, col, 13)  # Unit Device Qty
                col += 1
                sheet_user.set_column(col, col, 13)  # New Installation
                col += 1
                sheet_user.set_column(col, col, 10)  # Renewal
                col += 1
                sheet_user.set_column(col, col, 12)  # Other Services
                col += 1
                sheet_user.set_column(col, col, 11)  # Total Amount
                # col += 1
                # sheet_user.set_column(col, col, 12)  # No. of Vehicles
                # col += 1
                # sheet_user.set_column(col, col, 18)  # Sales Person

                row += 1

                for order in user_orders:
                    confirmation_date = datetime.strptime(order.confirmation_date, '%Y-%m-%d %H:%M:%S') if order.confirmation_date else ''
                    confirmation_date_str = confirmation_date.strftime('%Y-%m-%d') if confirmation_date else ''
                    quarter = math.ceil(float(confirmation_date.month) / 3) if confirmation_date else ''
                    month = confirmation_date.strftime('%b').upper() if quarter else ''

                    # Order Lines
                    line_items = ""
                    unit_device = 0
                    new_installation = 0
                    renewal = 0
                    other_services = 0
                    category_ids = []

                    # check if it is renewal
                    if order.sale_type == 'pilot':
                        so_lines = self.env['sale.order.line'].read_group([('order_id', '=', order.id)],
                                                                          ['product_id', 'price_subtotal',
                                                                           'product_uom_qty'],
                                                                          ['product_id', 'price_subtotal'])
                        for so_line in so_lines:
                            quantity = int(so_line['product_uom_qty'])
                            product_name = so_line['product_id'][1]
                            price = '%.2f' % (float(so_line['price_subtotal']))
                            line_items += '({}) {} @ {} \n'.format(quantity, product_name, price)

                            # check if product category is renewal or not
                            prod_id = so_line['product_id'][0]
                            product = self.env['product.product'].browse(prod_id)
                            category = product.categ_id.name
                            category_id = product.categ_id.id

                            if 'renewal' in category.lower():
                                renewal += float(so_line['price_subtotal'])
                            else:
                                # check product category
                                if category_id == 18:
                                    unit_device += quantity
                                    new_installation += float(so_line['price_subtotal'])
                                else:
                                    other_services += float(so_line['price_subtotal'])
                    else:
                        for line in order.order_line:
                            quantity = int(line.product_uom_qty)
                            price = '%.2f' % float(line.price_subtotal)
                            line_items += '({}) {} @ {} \n'.format(quantity, line.product_id.name, price)

                            # check product category
                            category = line.product_id.categ_id.name
                            category_id = line.product_id.categ_id.id

                            if 'renewal' in category.lower():
                                renewal += float(line.price_subtotal)
                            else:
                                if category_id == 18:
                                    unit_device += quantity
                                    new_installation += float(line.price_subtotal)
                                else:
                                    other_services += float(line.price_subtotal)

                    col = 0

                    sheet_user.write(row, col, quarter, cell_format_center)
                    col += 1
                    sheet_user.write(row, col, month, cell_format_center)
                    col += 1
                    sheet_user.write(row, col, order.name, cell_format_center)
                    col += 1
                    sheet_user.write(row, col, confirmation_date_str, cell_format_center)
                    col += 1
                    sheet_user.write(row, col, order.purchase_order_no or '', cell_format_center)
                    col += 1
                    sheet_user.write(row, col, order.purchase_order_date or '', cell_format_center)
                    col += 1
                    sheet_user.write(row, col, order.partner_id.name, cell_format_description)
                    col += 1
                    sheet_user.write(row, col, line_items[:-1], cell_format_description)
                    col += 1
                    sheet_user.write(row, col, unit_device or '', cell_format_center)
                    col += 1
                    sheet_user.write(row, col, new_installation or '', cell_format_currency)
                    col += 1
                    sheet_user.write(row, col, renewal or '', cell_format_currency)
                    col += 1
                    sheet_user.write(row, col, other_services or '', cell_format_currency)
                    col += 1
                    sheet_user.write(row, col, order.amount_untaxed, cell_format_currency_bold)
                    # col += 1
                    # sheet_user.write(row, col, len(order.vehicle_number_ids), cell_format_center)
                    # col += 1
                    # sheet_user.write(row, col, order.user_id.name, cell_format_center)

                    row += 1

                col = 7
                sheet_user.write(row, col, 'Total', header_format)
                col += 1
                sheet_user.write(row, col, '=SUM(I{}:I{})'.format(3, row), header_format)
                col += 1
                sheet_user.write(row, col, '=SUM(J{}:J{})'.format(3, row), total_format_currency)
                col += 1
                sheet_user.write(row, col, '=SUM(K{}:K{})'.format(3, row), total_format_currency)
                col += 1
                sheet_user.write(row, col, '=SUM(L{}:L{})'.format(3, row), total_format_currency)
                col += 1
                sheet_user.write(row, col, '=SUM(M{}:M{})'.format(3, row), total_format_currency)

        """combined summary sheet"""
        # get the end date year
        end_date_year = datetime.strptime(end_date, '%Y-%m-%d').year
        start_date_year = datetime.strptime(start_date, '%Y-%m-%d').year
        combined_domain = [('confirmation_date', '>=', '{}-01-01'.format(end_date_year)),
                           ('confirmation_date', '<=', '{}-12-31'.format(end_date_year)),
                           ('state', 'in', ('sale', 'done'))]
        if sales_person:
            combined_domain.append(('user_id', 'in', sales_person))
        combined_orders = self.env['sale.order'].search(combined_domain)

        use_in_combined_orders = combined_orders

        # check if year is not the same.
        if end_date_year != start_date_year:
            use_in_combined_orders = main_orders

        combined_summary = {}

        for order in use_in_combined_orders:
            confirmation_date = datetime.strptime(order.confirmation_date,
                                                  '%Y-%m-%d %H:%M:%S') if order.confirmation_date else ''
            quarter = 'Q{}'.format(math.ceil(float(confirmation_date.month) / 3)) if confirmation_date else ''
            month = confirmation_date.strftime('%b').upper() if quarter else ''

            unit_device = 0
            new_installation = 0
            renewal = 0
            other_services = 0
            category_ids = []

            if quarter not in combined_summary:
                combined_summary[quarter] = {}

            if month not in combined_summary[quarter]:
                combined_summary[quarter][month] = {'unit_device': [], 'new_installation': [], 'other_services': [],
                                                    'renewal': [], 'amount_untaxed': []}

            # check if it is renewal
            if order.sale_type == 'pilot':
                so_lines = self.env['sale.order.line'].read_group([('order_id', '=', order.id)],
                                                                  ['product_id', 'price_subtotal',
                                                                   'product_uom_qty'],
                                                                  ['product_id', 'price_subtotal'])
                # check if product category is renewal or not
                for so_line in so_lines:
                    quantity = int(so_line['product_uom_qty'])
                    prod_id = so_line['product_id'][0]
                    product = self.env['product.product'].browse(prod_id)
                    category = product.categ_id.name
                    category_id = product.categ_id.id

                    if 'renewal' in category.lower():
                        renewal += float(so_line['price_subtotal'])
                    else:
                        # check product category
                        if category_id == 18:
                            unit_device += quantity
                            new_installation += float(so_line['price_subtotal'])
                        else:
                            other_services += float(so_line['price_subtotal'])
            else:
                for line in order.order_line:
                    quantity = int(line.product_uom_qty)

                    # check product category
                    category = line.product_id.categ_id.name
                    category_id = line.product_id.categ_id.id

                    if 'renewal' in category.lower():
                        renewal += float(line.price_subtotal)
                    else:
                        if category_id == 18:
                            unit_device += quantity
                            new_installation += float(line.price_subtotal)
                        else:
                            other_services += float(line.price_subtotal)

                # if 18 in category_ids:
                #     new_installation = order.amount_untaxed
                # else:
                #     other_services = order.amount_untaxed

            if unit_device:
                combined_summary[quarter][month]['unit_device'].append(unit_device)
            if new_installation:
                combined_summary[quarter][month]['new_installation'].append(new_installation)

            combined_summary[quarter][month]['amount_untaxed'].append(order.amount_untaxed)
            combined_summary[quarter][month]['renewal'].append(renewal)
            combined_summary[quarter][month]['other_services'].append(other_services)

        sheet_combined = workbook.add_worksheet('Combined Summary')
        row, col = 0, 0
        if end_date_year != start_date_year:
            sheet_combined.merge_range('A1:N1', 'Combined Summary Report | {}'.format(from_to_date), title_format)
        else:
            sheet_combined.merge_range('A1:N1', 'Combined Summary Report {}'.format(end_date_year), title_format)
        sheet_combined.set_row(row, 30)

        row += 1

        sheet_combined.merge_range('A{}:A{}'.format(row + 1, row + 2), 'Particular', header_format)
        sheet_combined.merge_range('B{}:D{}'.format(row + 1, row + 1), 'Quarter 1', header_format)
        sheet_combined.merge_range('E{}:G{}'.format(row + 1, row + 1), 'Quarter 2', header_format)
        sheet_combined.merge_range('H{}:J{}'.format(row + 1, row + 1), 'Quarter 3', header_format)
        sheet_combined.merge_range('K{}:M{}'.format(row + 1, row + 1), 'Quarter 4', header_format)
        sheet_combined.merge_range('N{}:N{}'.format(row + 1, row + 2), 'Total', header_format)

        sheet_combined.set_column(col, col, 18)  # Particular
        sheet_combined.set_column(1, 12, 10)  # months
        sheet_combined.set_column(13, 13, 12)  # Total
        month_name = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']
        m_index = 0
        row += 1

        for m in month_name:
            m_index += 1
            sheet_combined.write(row, m_index, m.capitalize(), sub_header_format)

        quarter_keys = combined_summary.keys()

        row += 1
        sheet_combined.write(row, 0, 'Unit Device', sub_header_format)
        sheet_combined.write(row + 1, 0, 'New Installation', sub_header_format)
        sheet_combined.write(row + 2, 0, 'Renewal', sub_header_format)
        sheet_combined.write(row + 3, 0, 'Other Services', sub_header_format)
        sheet_combined.write(row + 4, 0, 'Total Amount Monthly', sub_header_format)
        # sheet_combined.write(row + 5, 0, 'Total Amount Quarterly', sub_header_format)

        if quarter_keys:
            for q_key in quarter_keys:
                m_index = 0
                for m in month_name:
                    m_index += 1
                    m_quarter = math.ceil(float(m_index) / 3)
                    q_quarter = q_key.replace('Q', '')
                    if m in combined_summary[q_key].keys():
                        sum_unit_device = sum(combined_summary[q_key][m]['unit_device'])
                        sheet_combined.write(row, m_index, sum_unit_device, cell_format_center)

                        sum_new_installation = sum(combined_summary[q_key][m]['new_installation'])
                        sheet_combined.write(row + 1, m_index, sum_new_installation, cell_format_currency)

                        sum_renewal = sum(combined_summary[q_key][m]['renewal'])
                        sheet_combined.write(row + 2, m_index, sum_renewal, cell_format_currency)

                        sum_other_services = sum(combined_summary[q_key][m]['other_services'])
                        sheet_combined.write(row + 3, m_index, sum_other_services, cell_format_currency)

                        sum_total_untaxed = sum(combined_summary[q_key][m]['amount_untaxed'])
                        sheet_combined.write(row + 4, m_index, sum_total_untaxed, cell_format_currency_bold)
                    else:
                        if m_quarter == q_quarter:
                            sheet_combined.write(row, m_index, 0, cell_format_center)
                            sheet_combined.write(row + 1, m_index, 0, cell_format_currency)
                            sheet_combined.write(row + 2, m_index, 0, cell_format_currency)
                            sheet_combined.write(row + 3, m_index, 0, cell_format_currency)
                            sheet_combined.write(row + 4, m_index, 0, cell_format_currency)

        sheet_combined.write(row, 13, '=SUM(B{}:M{})'.format(row + 1, row + 1), cell_format_currency_bold)  # total unit devices
        row += 1
        sheet_combined.write(row, 13, '=SUM(B{}:M{})'.format(row + 1, row + 1), cell_format_currency_bold)  # total new installation
        row += 1
        sheet_combined.write(row, 13, '=SUM(B{}:M{})'.format(row + 1, row + 1), cell_format_currency_bold)  # total renewals
        row += 1
        sheet_combined.write(row, 13, '=SUM(B{}:M{})'.format(row + 1, row + 1), cell_format_currency_bold)  # total other services
        row += 1
        sheet_combined.write(row, 13, '=SUM(B{}:M{})'.format(row + 1, row + 1), cell_format_currency_bold)  # total untaxed amount

        sheet_combined.conditional_format('A1:N' + str(row + 1), {'type': 'cell',
                                                                  'criteria': '>=',
                                                                  'value': 0,
                                                                  'format': cell_format_center})
        row += 2
        sheet_combined.write(row, 0, '', header_format)
        sheet_combined.write(row, 1, 'Quarter 1', header_format)
        sheet_combined.write(row, 2, 'Quarter 2', header_format)
        sheet_combined.write(row, 3, 'Quarter 3', header_format)
        sheet_combined.write(row, 4, 'Quarter 4', header_format)
        row += 1
        sheet_combined.write(row, 0, 'Total Amount Quarterly', sub_header_format)
        sheet_combined.write(row, 1, '=B{}+C{}+D{}'.format(8, 8, 8), cell_format_currency_bold)  # total q1
        sheet_combined.write(row, 2, '=E{}+F{}+G{}'.format(8, 8, 8), cell_format_currency_bold)  # total q2
        sheet_combined.write(row, 3, '=H{}+I{}+J{}'.format(8, 8, 8), cell_format_currency_bold)  # total q3
        sheet_combined.write(row, 4, '=K{}+L{}+M{}'.format(8, 8, 8), cell_format_currency_bold)  # total q2
        # sheet_combined.merge_range('B{}:D{}'.format(row + 1, row + 1), '=B{}+C{}+D{}'.format(row, row, row), cell_format_currency_bold)
        # sheet_combined.merge_range('E{}:G{}'.format(row + 1, row + 1), '=E{}+F{}+G{}'.format(row, row, row), cell_format_currency_bold)
        # sheet_combined.merge_range('H{}:J{}'.format(row + 1, row + 1), '=H{}+I{}+J{}'.format(row, row, row), cell_format_currency_bold)
        # sheet_combined.merge_range('K{}:M{}'.format(row + 1, row + 1), '=K{}+L{}+M{}'.format(row, row, row), cell_format_currency_bold)

        row += 4
        # united device bar chart
        unit_device_chart = workbook.add_chart({'type': 'line'})

        # Configure the data series for the primary chart.
        unit_device_chart.add_series({
            'name': 'Unit Device',
            'categories': "='Combined Summary'!$B$2:$M$3",
            'values': "='Combined Summary'!$B$4:$M$4",
            'marker': {
                'type': 'diamond',
                'size': 5,
                'border': {'color': 'black'},
                'fill': {'color': 'red'},
            },
        })

        unit_device_chart.set_legend({'none': True})
        unit_device_chart.set_title({'name': 'Monthly Unit Devices Sold'})

        sheet_combined.insert_chart('B{}'.format(row), unit_device_chart)

        # new installation sales bar chart
        new_installation_chart = workbook.add_chart({'type': 'column'})

        # Configure the data series for the primary chart.
        new_installation_chart.add_series({
            'name': 'New Installation',
            'categories': "='Combined Summary'!$B$2:$M$3",
            'values': "='Combined Summary'!$B$5:$M$5",
        })

        new_installation_chart.set_legend({'none': True})
        new_installation_chart.set_title({'name': 'Monthly New Installation Report'})

        sheet_combined.insert_chart('I{}'.format(row), new_installation_chart)

        row += 16
        # monthly sales bar chart
        monthly_sales_chart = workbook.add_chart({'type': 'column'})

        # Configure the data series for the primary chart.
        monthly_sales_chart.add_series({
            'name': 'Total Amount',
            'categories': "='Combined Summary'!$B$2:$M$3",
            'values': "='Combined Summary'!$B$8:$M$8",
        })

        monthly_sales_chart.set_legend({'none': True})
        monthly_sales_chart.set_title({'name': 'Monthly Sales Report'})

        sheet_combined.insert_chart('B{}'.format(row), monthly_sales_chart)

        # quarterly sales bar chart
        quarterly_sales_chart = workbook.add_chart({'type': 'column'})

        # Configure the data series for the primary chart.
        quarterly_sales_chart.add_series({
            'name': 'Total Amount',
            'categories': "='Combined Summary'!$B$10:$E$10",
            'values': "='Combined Summary'!$B$11:$E$11",
        })

        quarterly_sales_chart.set_y_axis({'min': 1})
        quarterly_sales_chart.set_legend({'none': True})
        quarterly_sales_chart.set_title({'name': 'Quarterly Sales Report'})

        sheet_combined.insert_chart('I{}'.format(row), quarterly_sales_chart)
