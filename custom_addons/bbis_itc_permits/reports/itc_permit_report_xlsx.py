from odoo import models
import math
from datetime import datetime


class BbisITCPermitReport(models.AbstractModel):
    _name = 'report.bbis_itc_permits.vehicle_itc_permit_report'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, orders):
        start_date = data['start_date']
        end_date = data['end_date']
        partner = data['partner']
        date_based = data['date_based']

        # Domain create for different type dates based.
        if date_based == 'create':
            domain = [('permit_start_date', '>=', start_date), ('permit_start_date', '<=', end_date)]
        elif date_based == 'expiry':
            domain = [('permit_end_date', '>=', start_date), ('permit_end_date', '<=', end_date)]
        else:
            domain = [('permit_end_date', '>=', start_date), ('permit_end_date', '<=', end_date),
                      ('state', '=', 'expired')]

        order = 'vehicle_no, partner_id asc'
        # Partner id included in the domain if partner ID is choosed.
        if partner:
            domain.append(('partner_id', '=', partner))
            itc_permits = self.env['itc.permit'].search(domain, order=order)
        else:
            itc_permits = self.env['itc.permit'].search(domain, order=order)

        # Formats
        title_format = workbook.add_format({'bold': True, 'border': True, 'align': 'center', 'valign': 'vcenter',
                                            'font_size': 14})
        header_format = workbook.add_format({'bold': True, 'border': True, 'font_size': 9, 'align': 'center',
                                             'valign': 'vcenter', 'bg_color': '#f05a29', 'font_color': 'white'})
        cell_format_center = workbook.add_format({'valign': 'vcenter', 'border': True, 'font_size': 9,
                                                  'align': 'center', 'text_wrap': True})
        cell_format_left = workbook.add_format(
            {'valign': 'vcenter', 'border': True, 'font_size': 9, 'align': 'left', 'text_wrap': True})

        start_date_1 = datetime.strptime(start_date, '%Y-%m-%d')
        end_date_1 = datetime.strptime(end_date, '%Y-%m-%d')
        from_to_date = '{} - {}'.format(start_date_1.strftime('%b %d, %Y'), end_date_1.strftime('%b %d, %Y'))
        sheet_title = 'ITC Permit Report from {}'.format(from_to_date)

        sheet_sales = workbook.add_worksheet('ITC Permit Report')
        row, col = 0, 0
        sheet_sales.merge_range('A1:K1', sheet_title, title_format)
        sheet_sales.set_row(row, 30)
        sheet_sales.freeze_panes(2, 2)

        row += 1

        # Header of the Excel Report Declaration.
        sheet_sales.write(row, col, "Partner", header_format)
        col += 1
        sheet_sales.write(row, col, "Sale Order", header_format)
        # col += 1
        # sheet_sales.write(row, col, "Request No", header_format)
        col += 1
        sheet_sales.write(row, col, "ITC Permit No", header_format)
        col += 1
        sheet_sales.write(row, col, "Vehicle Number", header_format)
        col += 1
        sheet_sales.write(row, col, "Chassis No", header_format)
        col += 1
        sheet_sales.write(row, col, "Device No", header_format)
        col += 1
        sheet_sales.write(row, col, "Sim Card No", header_format)
        col += 1
        sheet_sales.write(row, col, "ITC Permit History", header_format)
        col += 1
        sheet_sales.write(row, col, "Invoice No", header_format)
        col += 1
        sheet_sales.write(row, col, "Invoice Date", header_format)
        col += 1
        sheet_sales.write(row, col, "Current Status", header_format)

        col = 0
        # Adjust the column width.
        sheet_sales.set_column(col, col, 40)  # Partner
        col += 1
        sheet_sales.set_column(col, col, 11)  # Sale Order
        # col += 1
        # sheet_sales.set_column(col, col, 28)  # Request No
        col += 1
        sheet_sales.set_column(col, col, 27)  # ITC Permit No
        col += 1
        sheet_sales.set_column(col, col, 22)  # Vehicle Number
        col += 1
        sheet_sales.set_column(col, col, 18)  # Chassis No
        col += 1
        sheet_sales.set_column(col, col, 15)  # Device No
        col += 1
        sheet_sales.set_column(col, col, 15)  # Sim Card No
        col += 1
        sheet_sales.set_column(col, col, 70)  # ITC Permit Info
        col += 1
        sheet_sales.set_column(col, col, 17)  # Invoice No
        col += 1
        sheet_sales.set_column(col, col, 10)  # Invoice Date
        col += 1
        sheet_sales.set_column(col, col, 10)  # Current Status

        row += 1
        col = 0
        vehicles = []
        # For loop for getting all the vehicle details.
        for permit in itc_permits:
            itc_line_entries = ""
            # Checking if the vehicle is added in the excel. Compare with an array(Vehicles)
            if permit.vehicle_no.name not in vehicles:
                sheet_sales.write(row, 0, permit.partner_id.name, cell_format_center)
                sheet_sales.write(row, 1, permit.sale_order_id.name, cell_format_center)
                #sheet_sales.write(row, 2, permit.request_number, cell_format_center)
                sheet_sales.write(row, 2, permit.name, cell_format_center)
                sheet_sales.write(row, 3, permit.vehicle_no.name, cell_format_center)
                sheet_sales.write(row, 4, permit.chassis_no if permit.chassis_no else '', cell_format_center)
                sheet_sales.write(row, 5, permit.device_no if permit.device_no else '', cell_format_center)
                sheet_sales.write(row, 6, permit.sim_card_no if permit.sim_card_no else '', cell_format_center)

                itc_details = self.env['itc.permit'].search([('vehicle_no', '=', permit.vehicle_no.id)], order='permit_start_date')
                # For loop for the ITC permit history of vehicle.
                status = False
                for itc_entries in itc_details:
                    permit_no = itc_entries.name
                    start_date = itc_entries.permit_start_date
                    end_date = itc_entries.permit_end_date
                    status = dict(itc_entries._fields['state'].selection).get(itc_entries.state)
                    itc_line_entries += 'Permit No:{} / From: {} To: {} @ Status: {} \n'.format(permit_no, start_date, end_date, status)

                sheet_sales.write(row, 7, itc_line_entries[:-1], cell_format_left)
                sheet_sales.write(row, 8, permit.invoice_no.number, cell_format_center)
                if permit.invoice_no.date_invoice:
                    sheet_sales.write(row, 9, datetime.strftime(datetime.strptime(permit.invoice_no.date_invoice,'%Y-%m-%d'), '%d-%m-%Y'), cell_format_center)
                else:
                    sheet_sales.write(row, 9, permit.invoice_no.date_invoice, cell_format_center)
                sheet_sales.write(row, 10, status, cell_format_center)
                # Appending the already added vehicle details to array.
                vehicles.append(permit.vehicle_no.name)
                row += 1
