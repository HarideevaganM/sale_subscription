# Wizard for upload the vehicle details for the ITC permits.
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime
import xlrd
import tempfile
import binascii


class ITCPermitReportWizard(models.TransientModel):
    """ Create a wizard for report filter. """
    _name = 'itc.permit.report.wizard'

    # Fields in the wizard for import
    report_type = fields.Selection([('itc_permit', 'ITC Permit Report'), ('so_itc', 'SO With ITC Report'),
                                    ('odoo_sm_comparison', 'Odoo/Smart Mobility Report')], default='itc_permit')
    date_based = fields.Selection([('create', 'Permit Start Date'), ('expiry', 'Expiry Date'),
                                   ('expiry_only', 'Expired Only')],
                                  default='create', copy=False, string='Based On', required=True)
    start_date = fields.Date("Start Date")
    end_date = fields.Date("End Date")
    partner_id = fields.Many2one('res.partner', string='Partner')
    smart_mobility_data = fields.Binary()

    #@api.multi
    def print_xlsx_report(self):
        """ Excel report function."""

        data = {
            'start_date': self.start_date,
            'end_date': self.end_date,
            'partner': self.partner_id.id,
            'date_based': self.date_based
        }

        if self.report_type == 'odoo_sm_comparison':
            excel_data = self.import_file()
            # print(excel_data)
            # return True
            return self.env.ref('bbis_itc_permits.odoo_smart_mobility_report').report_action(self, data={"sm_data": excel_data})
        elif self.report_type == 'so_itc':
            return self.env.ref('bbis_itc_permits.so_with_itc_report').report_action(self, data=data)
        else:
            if not self.start_date or not self.end_date:
                raise ValidationError("Please select the Start and End dates.")

            start_date = datetime.strptime(self.start_date, '%Y-%m-%d')
            end_date = datetime.strptime(self.end_date, '%Y-%m-%d')

            if start_date.year > end_date.year:
                raise ValidationError("Sorry, please select start date not greater then end date.")

            template = 'bbis_itc_permits.vehicle_itc_permit_report'

            return self.env.ref(template).report_action(self, data=data)

    def import_file(self):
        """Function for import the Excel."""
        fields = []
        fp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
        if not self.smart_mobility_data:
            return False
        fp.write(binascii.a2b_base64(self.smart_mobility_data))
        fp.seek(0)
        workbook = xlrd.open_workbook(fp.name)
        sheet = workbook.sheet_by_index(0)
        data_list = []
        for row_no in range(sheet.nrows):
            if row_no <= 0:
                fields = list(map(lambda row: str(row.value), sheet.row(row_no)))
            else:
                lines = list(
                    map(lambda row: isinstance(row.value, bytes) and row.value.encode('utf-8') or str(
                        row.value),
                        sheet.row(row_no)))

                if fields and lines:
                    color_dict = dict(zip(fields, lines))
                    data_list.append(color_dict)

        return data_list
