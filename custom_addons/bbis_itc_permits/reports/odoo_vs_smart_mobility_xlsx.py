from odoo import models


class OdooVsSmartMobilityReport(models.AbstractModel):
    _name = 'report.bbis_itc_permits.odoo_smart_mobility_report'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, itc):
        sheet = workbook.add_worksheet()

        title_format = workbook.add_format({'bold': True, 'border': True, 'align': 'center', 'valign': 'vcenter', 'font_size': 14})
        header_format = workbook.add_format({'bold': True, 'border': True, 'font_size': 11, 'align': 'center',
                                             'valign': 'vcenter', 'bg_color': '#f05a29', 'font_color': 'white'})
        cell_format_center = workbook.add_format({'valign': 'vcenter', 'border': True, 'font_size': 9,
                                                  'align': 'center', 'text_wrap': True})

        sm_serials = [x['Device'][0:-2] for x in data['sm_data']]
        row = 0

        sheet.merge_range('A1:E1', "Active in Odoo but missing in Smart Mobility", title_format)
        row += 1

        sheet.write(row, 0, "Device No.", header_format)
        sheet.write(row, 1, "Vehicle", header_format)
        sheet.write(row, 2, "Permit", header_format)
        sheet.write(row, 3, "Device Type", header_format)
        sheet.write(row, 4, "Company Name", header_format)
        row += 1

        sheet.set_column(0, 0, 15)
        sheet.set_column(1, 1, 30)
        sheet.set_column(2, 2, 40)
        sheet.set_column(3, 3, 25)
        sheet.set_column(4, 4, 40)

        for permit in itc.search([('state', '=', 'done')]):
            if permit.device_no and permit.device_no not in sm_serials:

                device_type = False
                serial_obj = self.env['stock.lot'].search([('name', '=', permit.device_no)], limit=1)
                if serial_obj:
                    device_type = serial_obj.product_id.name

                sheet.write(row, 0, permit.device_no, cell_format_center)
                sheet.write(row, 1, permit.vehicle_no.name, cell_format_center)
                sheet.write(row, 2, permit.name, cell_format_center)
                sheet.write(row, 3, device_type, cell_format_center)
                sheet.write(row, 4, permit.partner_id.name, cell_format_center)
                row += 1

        # Report 2
        row = 0

        sheet = workbook.add_worksheet()
        sheet.merge_range('A1:F1', "Not Active in Odoo but existing in Smart Mobility", title_format)
        row += 1

        sheet.write(row, 0, "Device No.", header_format)
        sheet.write(row, 1, "Vehicle", header_format)
        sheet.write(row, 2, "Permit", header_format)
        sheet.write(row, 3, "Device Type", header_format)
        sheet.write(row, 4, "Company Name", header_format)
        sheet.write(row, 5, "Status", header_format)
        row += 1

        sheet.set_column(0, 0, 15)
        sheet.set_column(1, 1, 30)
        sheet.set_column(2, 2, 40)
        sheet.set_column(3, 3, 25)
        sheet.set_column(4, 4, 40)
        sheet.set_column(5, 5, 10)

        active_permits = itc.search([('state', '=', 'done')]).mapped('device_no')
        for permit in itc.search([('state', 'in', ('expired', 'cancel'))], order='device_no'):
            if permit.device_no and permit.device_no not in active_permits and permit.device_no in sm_serials:

                device_type = False
                serial_obj = self.env['stock.lot'].search([('name', '=', permit.device_no)], limit=1)
                if serial_obj:
                    device_type = serial_obj.product_id.name

                status = dict(permit._fields['state'].selection).get(permit.state)

                sheet.write(row, 0, permit.device_no, cell_format_center)
                sheet.write(row, 1, permit.vehicle_no.name, cell_format_center)
                sheet.write(row, 2, permit.name, cell_format_center)
                sheet.write(row, 3, device_type, cell_format_center)
                sheet.write(row, 4, permit.partner_id.name, cell_format_center)
                sheet.write(row, 5, status, cell_format_center)
                row += 1

        # Report 3
        row = 0

        sheet = workbook.add_worksheet()
        sheet.merge_range('A1:D1', "Existing in Smart Mobility but not in Odoo", title_format)
        row += 1

        sheet.write(row, 0, "Device No.", header_format)
        sheet.write(row, 1, "Vehicle", header_format)
        sheet.write(row, 2, "Company Name", header_format)
        sheet.write(row, 3, "Device Type", header_format)
        row += 1

        sheet.set_column(0, 0, 15)
        sheet.set_column(1, 1, 30)
        sheet.set_column(2, 2, 40)
        sheet.set_column(3, 3, 25)

        odoo_serials = itc.search([]).mapped('device_no')

        for line in data['sm_data']:
            l_serial = line['Device'][0:-2]
            if l_serial not in odoo_serials:

                device_type = False
                serial_obj = self.env['stock.lot'].search([('name', '=', l_serial)], limit=1)
                if serial_obj:
                    device_type = serial_obj.product_id.name

                sheet.write(row, 0, line['Device'][0:-2], cell_format_center)
                sheet.write(row, 1, line['Vehicle'], cell_format_center)
                sheet.write(row, 2, line['Company'], cell_format_center)
                sheet.write(row, 3, device_type, cell_format_center)
                row += 1
