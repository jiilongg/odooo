# -*- coding: utf-8 -*-
{
    'name': "Face Recognition Attendance",

    'summary': "Automated attendance system using face recognition technology.",

    'description': """
        This module provides a seamless attendance tracking system that uses face recognition technology 
        powered by OpenCV. Employees can check in and check out simply by scanning their faces, ensuring 
        secure and efficient attendance logging.
    """,

    'author': "Your Company Name",
    'website': "https://www.yourcompany.com",

    'category': 'Human Resources',
    'version': '1.0',

    # Modules required for this module to work
    'depends': ['base'],

    # Data files always loaded
    'data': [
        # Security
        'security/ir.model.access.csv',
        
        'views/student_information_view.xml',
        'views/face_recognition_view.xml',
        'views/student_attendance_view.xml',
        'views/study_session_view.xml',
        
        'views/actions.xml',
        'views/menu_items.xml',
    ],

    # Technical details
    'installable': True,
    'application': True,
    'auto_install': False,
}
