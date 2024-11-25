from odoo import fields, models, api
 
class StudySession(models.Model):
    _name = 'study.session'
    _description = 'Study Session / Shift'

    name = fields.Char(string="Session Name", required=True, help="Name of the study session or shift")
    start_time = fields.Float(string="Start Time", required=True, help="Start time of the session (in 24-hour format, e.g., 9.5 for 9:30 AM)")
    end_time = fields.Float(string="End Time", required=True, help="End time of the session (in 24-hour format, e.g., 17.0 for 5:00 PM)")
    description = fields.Text(string="Session Description", help="Additional details about the session or shift")
    
    check_in_grace_period = fields.Integer(string="Check-in Grace Period (Minutes)", default=5, help="Allowed grace period in minutes for students to be late for check-in")
    check_out_grace_period = fields.Integer(string="Check-out Grace Period (Minutes)", default=5, help="Allowed grace period in minutes for students to check out early")
    
    session_type = fields.Selection([
        ('regular', 'Regular Term'), 
        ('short_course', 'Short Course'),
        ('summer_course', 'Summer Course'),
        ('intensive', 'Intensive Program'),
        ('workshop', 'Workshop'),
        ('seminar', 'Seminar'),
        ('special_program', 'Special Program')], 
        string="Session Type", 
        help="Type of session, such as regular term classes, short courses, summer courses, intensive programs, workshops, seminars, or special programs.")
