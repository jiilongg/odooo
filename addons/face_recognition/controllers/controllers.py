# -*- coding: utf-8 -*-
# from odoo import http


# class FaceRecognition(http.Controller):
#     @http.route('/face_recognition/face_recognition', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/face_recognition/face_recognition/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('face_recognition.listing', {
#             'root': '/face_recognition/face_recognition',
#             'objects': http.request.env['face_recognition.face_recognition'].search([]),
#         })

#     @http.route('/face_recognition/face_recognition/objects/<model("face_recognition.face_recognition"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('face_recognition.object', {
#             'object': obj
#         })

