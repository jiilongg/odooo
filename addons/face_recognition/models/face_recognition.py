import cv2
import dlib
import base64
import io, os
import numpy as np
from PIL import Image
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
import pytz

# Function to get path of component
def get_model_path(filename):
    """
    Resolve the full path of the file dynamically.
    Ensures the file exists and handles errors gracefully.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))  # Current script's directory
    file_path = os.path.join(base_dir, filename)

    if not os.path.isfile(file_path):
        raise UserError(_("Model file not found: %s") % file_path)
    return file_path

try:
    # Load Dlib models
    shape_predictor = dlib.shape_predictor(get_model_path('shape_predictor_68_face_landmarks.dat'))
    face_recognition_model = dlib.face_recognition_model_v1(get_model_path('dlib_face_recognition_resnet_model_v1.dat'))
    face_detector = dlib.get_frontal_face_detector()
except Exception as e:
    raise UserError(_("Error loading face recognition models: %s") % str(e))

class FaceRecognition(models.Model):
    _name = 'face.recognition'
    _description = 'Face Recognition Attendance'

    def log_attendance(self, student, status, shift):
        """Helper function to log check-in or check-out"""
        now = fields.Datetime.now()
        if status == 'checked_in':
            self.env['student.attendance'].sudo().create({
                'student_id': student.id,
                'shift_id': shift.id,
                'check_in': now,
                'status': 'checked_in',
            })
        elif status == 'checked_out':
            attendance = self.env['student.attendance'].sudo().search(
                [('student_id', '=', student.id), ('status', '=', 'checked_in')],
                order="check_in desc", limit=1
            )
            if attendance:
                attendance.sudo().write({
                    'check_out': now,
                    'status': 'checked_out',
                })

    def encode_known_faces(self, students):
        """Encodes known faces from the student records."""
        known_face_encodings = []
        known_face_ids = []
        missing_images = []  # Track students with missing face images

        for student in students:
            if student.face_image:
                image_data = base64.b64decode(student.face_image)
                image = Image.open(io.BytesIO(image_data))
                image_np = np.array(image)

                gray_image = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
                faces = face_detector(gray_image)
                if len(faces) > 0:
                    face = faces[0]
                    shape = shape_predictor(image_np, face)
                    face_encoding = np.array(face_recognition_model.compute_face_descriptor(image_np, shape))
                    known_face_encodings.append(face_encoding)
                    known_face_ids.append(student.id)
                else:
                    missing_images.append(student.name)
            else:
                missing_images.append(student.name)

        if missing_images:
            missing_list = ", ".join(missing_images)
            raise UserError(_("The following students have no valid face images: %s") % missing_list)

        return known_face_encodings, known_face_ids

    def recognize_faces_in_frame(self, frame, known_face_encodings, known_face_ids):
        """Recognizes faces in the given frame."""
        rgb_frame = frame[:, :, ::-1]  # Convert from BGR to RGB
        faces = face_detector(rgb_frame)
        if len(faces) == 0:
            print("No faces detected in the frame.")
            return None

        for face in faces:
            shape = shape_predictor(frame, face)
            face_encoding = np.array(face_recognition_model.compute_face_descriptor(frame, shape)) 
            face_distances = np.linalg.norm(known_face_encodings - face_encoding, axis=1)
            """
                Calculate to find match point incase that we want it more accuracy decrease 
                the value that have used to set condition.
            """
            best_match_index = np.argmin(face_distances)
              
            if face_distances[best_match_index] < 0.6:  # Threshold for face similarity in case that best match smaller than 0.6 it found student.
                student_id = known_face_ids[best_match_index]
                return student_id, face

        raise UserError(_("No matching face detected for any student."))

    def time_to_float(self, time):
        """Convert datetime.time object to float value representing hours."""
        return time.hour + time.minute / 60.0

    def start_camera_and_recognize(self):
        """Start the camera and recognize student faces with a full-screen feed."""
        students = self.env['student.information'].search([])
        known_face_encodings, known_face_ids = self.encode_known_faces(students)

        # Open the camera
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            raise UserError("Cannot access the camera. Please check if it's connected.")

        # Variables for message delay
        message = ""
        message_display_time = None
        message_duration = 3  # Duration to show messages

        try:
            # Set OpenCV window to full screen
            cv2.namedWindow('Face Recognition', cv2.WND_PROP_FULLSCREEN)
            cv2.setWindowProperty('Face Recognition', cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

            while True:
                ret, frame = cap.read()
                if not ret:
                    raise UserError("Unable to read from the camera.")

                if message_display_time and (datetime.now() - message_display_time).total_seconds() > message_duration:
                    message = ""  # Clear the message
                    message_display_time = None

                result = self.recognize_faces_in_frame(frame, known_face_encodings, known_face_ids)
                if result:
                    student_id, face = result
                    student = self.env['student.information'].browse(student_id)

                    # Get the student's shift
                    shift = student.shift_id
                    if not shift:
                        raise UserError("No active shift found for this time.")

                    # Log attendance and show a message
                    latest_attendance = self.env['student.attendance'].sudo().search(
                        [('student_id', '=', student_id)], order="check_in desc", limit=1
                    )
                    now = datetime.now()
                    one_minute_ago = now - timedelta(minutes=1)

                    if latest_attendance and (
                        latest_attendance.check_in and latest_attendance.check_in > one_minute_ago or
                        latest_attendance.check_out and latest_attendance.check_out > one_minute_ago
                    ):
                        message = f"{student.name} already scanned within the last minute"
                        message_display_time = datetime.now()
                        continue

                    if not latest_attendance:
                        self.log_attendance(student, 'checked_in', shift)
                        message = f"{student.name} successfully checked in to {shift.name}"
                    elif latest_attendance.status == 'checked_out':
                        self.log_attendance(student, 'checked_in', shift)
                        message = f"{student.name} successfully checked in to {shift.name}"
                    else:
                        self.log_attendance(student, 'checked_out', shift)
                        message = f"{student.name} successfully checked out of {shift.name}"

                    message_display_time = datetime.now()

                if message:
                    cv2.putText(frame, message, (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

                cv2.imshow('Face Recognition', frame)

                if cv2.waitKey(1) & 0xFF == ord('c'):  # Exit on 'c'
                    break

        finally:
            cap.release()
            cv2.destroyAllWindows()

    def close_camera(self):
        """Close the camera"""
        try:
            cv2.destroyAllWindows()
        except Exception as e:
            raise UserError(f"Error closing camera: {str(e)}")
