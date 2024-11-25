import pytz
from datetime import datetime, timedelta
from odoo import models, fields, api

# Define default timezone for the system
DEFAULT_TIMEZONE = 'Asia/Phnom_Penh'


class StudentAttendance(models.Model):
    _name = 'student.attendance'
    _description = 'Student Attendance'

    name = fields.Char(string="Attendance Name", compute='_compute_name', store=True, readonly=True)
    student_id = fields.Many2one('student.information', string="Student", required=True)
    shift_id = fields.Many2one('study.session', string="Shift", required=True)
    check_in = fields.Datetime(string='Check In', readonly=True)
    check_out = fields.Datetime(string='Check Out', readonly=True)
    status = fields.Selection(
        [('checked_in', 'Checked In'), ('checked_out', 'Checked Out')],
        string='Status', readonly=True
    )
    check_in_status = fields.Selection(
        [('early', 'Early'), ('on_time', 'On Time'), ('late', 'Late')],
        string="Check In Status", compute='_compute_check_in_status', store=True, readonly=True
    )
    check_out_status = fields.Selection(
        [('early', 'Early'), ('on_time', 'On Time'), ('late', 'Late')],
        string="Check Out Status", compute='_compute_check_out_status', store=True, readonly=True
    )

    @api.depends('check_in', 'check_out', 'student_id')
    def _compute_name(self):
        """
        Generate a human-readable name for the attendance record.
        Handles missing check-in or check-out gracefully.
        """
        for record in self:
            # Format check-in and check-out timestamps
            check_in_str = (
                self._convert_to_local_time(record.check_in).strftime('%Y-%m-%d %H:%M:%S')
                if record.check_in else 'N/A'
            )
            check_out_str = (
                self._convert_to_local_time(record.check_out).strftime('%Y-%m-%d %H:%M:%S')
                if record.check_out else 'N/A'
            )

            # Generate attendance name
            record.name = f"{record.student_id.name or 'Unknown'} - {check_in_str} | {check_out_str}"

    @api.depends('check_in', 'shift_id.start_time', 'shift_id.check_in_grace_period')
    def _compute_check_in_status(self):
        """Compute the check-in status based on shift start time and grace period."""
        for record in self:
            if record.check_in and record.shift_id:
                record.check_in_status = self._evaluate_attendance_status(
                    record.check_in, record.shift_id.start_time, record.shift_id.check_in_grace_period, 'check_in'
                )
            else:
                record.check_in_status = False

    @api.depends('check_out', 'shift_id.end_time', 'shift_id.check_out_grace_period')
    def _compute_check_out_status(self):
        """Compute the check-out status based on shift end time and grace period."""
        for record in self:
            if record.check_out and record.shift_id:
                record.check_out_status = self._evaluate_attendance_status(
                    record.check_out, record.shift_id.end_time, record.shift_id.check_out_grace_period, 'check_out'
                )
            else:
                record.check_out_status = False

    def _evaluate_attendance_status(self, attendance_time, shift_time, grace_period_minutes, status_type):
        """
        Evaluate attendance status (on time, early, late) based on shift timings.
        Handles missing shift time gracefully.
        """
        if not shift_time:
            return 'N/A'

        # Convert attendance time to local timezone
        attendance_time = self._convert_to_local_time(attendance_time)

        # Calculate the expected time in local timezone
        expected_time = self._get_expected_time(attendance_time.date(), shift_time)

        # Convert grace period to timedelta
        grace_period = timedelta(minutes=grace_period_minutes or 0)

        if status_type == 'check_in':
            if attendance_time <= expected_time:
                return 'on_time'
            elif attendance_time > expected_time + grace_period:
                return 'late'
            else:
                return 'early'
        elif status_type == 'check_out':
            if attendance_time <= expected_time - grace_period:
                return 'early'
            elif attendance_time >= expected_time:
                return 'on_time'
            else:
                return 'late'

    def _get_expected_time(self, date, time_float):
        """
        Convert float time (e.g., 9.5 for 9:30 AM) into a datetime object in the local timezone.
        Handles missing time_float gracefully.
        """
        if time_float is None:
            return None

        hours = int(time_float)
        minutes = int((time_float - hours) * 60)
        expected_time = datetime.combine(date, datetime.min.time()) + timedelta(hours=hours, minutes=minutes)
        return self._convert_to_local_time(expected_time)

    @staticmethod
    def _convert_to_local_time(utc_datetime):
        """
        Convert a UTC datetime to the local timezone.
        """
        if not utc_datetime:
            return None

        local_tz = pytz.timezone(DEFAULT_TIMEZONE)
        if not utc_datetime.tzinfo:
            utc_datetime = pytz.utc.localize(utc_datetime)

        return utc_datetime.astimezone(local_tz)
