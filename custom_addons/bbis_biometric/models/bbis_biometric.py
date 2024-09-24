# -*- coding: utf-8 -*-

from odoo import models, fields, api
from zk import ZK, const
from odoo.exceptions import ValidationError
import requests


class BiometricDevice(models.Model):
    _name = 'biometric.device'
    _description = 'Biometric Device'

    name = fields.Char(string="Device Name")
    firmware = fields.Char(string="Firmware Version")
    branch = fields.Many2one('hr.working.branch')
    ip_address = fields.Char()
    port = fields.Integer()
    password = fields.Integer()

    def show_attendance(self):
        return {
            'name': 'Biometric Device Attendance',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'biometric.device.attendance',
            'domain': [('biometric_device', '=', self.id)],
            'context': {'search_default_group_name': 1}
        }

    def show_download_wizard(self):
        return {
            'name': 'Biometric Attendance',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'biometric.attendance.wizard',
            'target': 'new'
        }

    def upload_attendance(self):
        self.ensure_one()
        bio_attendance = self.env['biometric.device.attendance'].search([('biometric_device', '=', self.id)])
        hr_emp_obj = self.env['hr.employee']
        temp_attendance_obj = self.env['bbis.attendance.temp']
        exclude_import = self.env['hr.attendance.exclude.import']

        # first make sure that there's no name in biometric not in odoo
        for b in bio_attendance:
            exclude = exclude_import.search(['|', ('name', '=', b.name), ('user_id', '=', b.user_id)])
            if exclude:
                continue
            emp = hr_emp_obj.search([('name', '=', b.name)])
            if not emp:
                raise ValidationError("Sorry! Biometric user '{}' doesn't exist in Odoo HR Employees. Please make sure "
                                      "name is exactly the same between Biometric and Odoo.".format(b.name))

        # now we are sure to delete all records and add biometric devices
        temp_attendance_obj.truncate_attendances()

        for b in bio_attendance:
            exclude = exclude_import.search(['|', ('name', '=', b.name), ('user_id', '=', b.user_id)])
            if exclude:
                continue

            emp = hr_emp_obj.search([('name', '=', b.name)])

            temp_attendance_obj.create({'name': emp.id,
                                        'date_time': b.date_time,
                                        'branch': self.branch.id,
                                        'month': b.month,
                                        'year': b.year})

        temp_attendance_obj.compute_time_in_out(bio_attendance[0].month, bio_attendance[0].year,
                                                self.branch, biometric=True)

        return {
            'type': 'ir.actions.act_window',
            'name': 'Temporary Attendances',
            'view_type': 'form',
            'res_model': 'bbis.attendance.temp',
            'view_mode': 'tree,form',
            'view_id': False,
            'target': 'current',
            'context': {'search_default_employee': 1}
        }

    def download_attendance(self, selected_month, selected_year):
        self.ensure_one()
        conn = None
        # create ZK instance
        zk = ZK(self.ip_address, port=self.port, timeout=5, password=0, force_udp=False, ommit_ping=False)

        try:
            # connect to device
            conn = zk.connect()

            # get all users
            bio_users = conn.get_users()
            users = {}
            for user in bio_users:
                if user not in users:
                    users[user.user_id] = user.name

            attendances = conn.get_attendance()

            # truncate table so that you get fresh data
            self.env.cr.execute('TRUNCATE only biometric_device_attendance RESTART IDENTITY')

            if not len(attendances):
                raise ValidationError("Sorry! No records found!")

            for att in attendances:
                """
                Fields: uid, user_id, timestamp, status, punch
                """

                month = int(att.timestamp.strftime("%m"))
                year = int(att.timestamp.strftime("%Y"))

                if month == selected_month and year == selected_year:

                    self.env['biometric.device.attendance'].create({
                        'name': users[att.user_id] if att.user_id in users else att.user_id,
                        'biometric_device': self.id,
                        'uid': att.uid,
                        'user_id': att.user_id,
                        'date_time': att.timestamp,
                        'month': month,
                        'year': year,
                    })
        except Exception as e:
            raise ValidationError("Sorry! Unable to process : {}".format(e))
        finally:
            if conn:
                conn.disconnect()

    def check_connection(self):
        self.ensure_one()

        conn = None
        ip_address = self.ip_address
        password = self.password

        # if there's no ip, we can get the public ip dynamically
        if not self.ip_address:
            ip_address = requests.get('https://checkip.amazonaws.com').text.strip()
            self.ip_address = ip_address

        if not self.password:
            password = 0

        # create ZK instance
        zk = ZK(ip_address, port=self.port, timeout=5, password=password, force_udp=False, ommit_ping=False)
        try:
            # connect to device
            conn = zk.connect()
            device_name = conn.get_device_name()
            firmware = conn.get_firmware_version()

            self.name = device_name
            self.firmware = firmware

        except Exception as e:
            raise ValidationError("Sorry! Unable to process : {}".format(e))
        finally:
            if conn:
                conn.disconnect()

                # add success message
                message = "Your connection to {} Biometric Device is successful. You can proceed " \
                          "downloading attendance.".format(self.branch.name)
                message_id = self.env['bbis.message.wizard'].create({'message': message})

                return {
                    'name': 'Connection Successful!',
                    'type': 'ir.actions.act_window',
                    'view_mode': 'form',
                    'res_model': 'bbis.message.wizard',
                    'res_id': message_id.id,
                    'target': 'new'
                }


class BiometricDeviceAttendance(models.Model):
    _name = 'biometric.device.attendance'
    _description = 'Biometric Device Attendance'

    name = fields.Char()
    uid = fields.Integer(string="Biometric ID")
    user_id = fields.Integer(string="Biometric User ID")
    biometric_device = fields.Many2one('biometric.device')
    date_time = fields.Datetime()
    month = fields.Integer()
    year = fields.Integer()


class ExcludeAttendanceImport(models.Model):
    _name = 'hr.attendance.exclude.import'
    _description = 'Exclude Attendance Import'

    name = fields.Char()
    user_id = fields.Integer(string="User ID")
    branch_id = fields.Many2one('hr.working.branch', required=1)
