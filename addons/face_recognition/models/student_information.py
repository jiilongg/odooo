import cv2
import dlib
import base64
import io
import os
import numpy as np
from PIL import Image
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime
import pytz

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

# Set timezone
DEFAULT_TIMEZONE = 'Asia/Phnom_Penh'


class StudentInformation(models.Model):
    _name = 'student.information'
    _description = 'Student Information'

    name = fields.Char(string="Student Name", required=True)
    studentid = fields.Char(string="Student ID", required=True, unique=True)
    email = fields.Char(string="Email")
    phone = fields.Char(string="Phone")
    date_of_birth = fields.Date(string="Date of Birth")
    gender = fields.Selection([('male', 'Male'), ('female', 'Female')], string="Gender")
    address = fields.Char(string="Address")
    city = fields.Char(string="City")
    zip = fields.Char(string="Postal Code")
    enrollment_date = fields.Date(string="Enrollment Date")
    face_image = fields.Binary(string="Face Image", attachment=True, help="Captured face image of the student.")
    internal_note = fields.Text('Internal Note')
    shift_id = fields.Many2one('study.session', string="Assigned Shift")

    def capture_and_train_face(self):
        """
        Start the camera feed and allow the user to manually capture the image.
        Ensures that the captured frame does not include any overlaid messages.
        """
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            raise UserError(_("Cannot access the camera. Please check if it's connected."))

        try:
            # Configure the camera feed
            cv2.namedWindow('Face Capture', cv2.WND_PROP_FULLSCREEN)
            cv2.setWindowProperty('Face Capture', cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

            captured_frame = None  # Store the frame when the user captures an image

            while True:
                ret, frame = cap.read()
                if not ret:
                    raise UserError(_("Unable to read from the camera."))

                # Detect faces in the current frame
                faces = face_detector(frame)

                if len(faces) > 0:
                    message = "Face detected! Press 'c' to capture."
                    message_color = (0, 255, 0)  # Green
                else:
                    message = "No face detected. Adjust position!"
                    message_color = (0, 0, 255)  # Red

                # Show the message on the frame for live preview
                preview_frame = frame.copy()  # Create a copy for overlay
                self._display_message_on_frame(preview_frame, message, color=message_color)

                # Show the preview frame
                cv2.imshow('Face Capture', preview_frame)

                key = cv2.waitKey(1) & 0xFF
                if key == ord('c'):  # Capture the frame on pressing 'c'
                    if len(faces) > 0:
                        captured_frame = frame.copy()  # Capture the frame without overlay
                        break
                    else:
                        raise UserError(_("No face detected! Please adjust your position and try again."))
                elif key == ord('q'):  # Quit on pressing 'q'
                    break

            if captured_frame is not None:
                self._save_full_frame(captured_frame)
                # raise UserError(_("Image captured successfully and saved!"))

        finally:
            cap.release()
            cv2.destroyAllWindows()

    def _save_full_frame(self, frame):
        """
        Encode and save the captured frame to the database.
        """
        _, frame_buffer = cv2.imencode('.jpg', frame)
        frame_encoded = base64.b64encode(frame_buffer).decode('utf-8')

        self.write({'face_image': frame_encoded})

    @staticmethod
    def _display_message_on_frame(frame, message, color=(255, 255, 255)):
        """
        Overlay a message on the video frame for live preview.
        This does not affect the saved frame.
        """
        cv2.putText(frame, message, (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)


    @staticmethod
    def _get_local_time():
        """
        Get the current local time in the configured timezone.
        """
        try:
            local_tz = pytz.timezone(DEFAULT_TIMEZONE)
        except pytz.UnknownTimeZoneError:
            local_tz = pytz.utc  # Fallback to UTC

        now = datetime.now(pytz.utc).astimezone(local_tz)
        return now

    @api.onchange('face_image')
    def _check_image_clarity(self):
        """
        Validate the clarity of the uploaded image.
        """
        if self.face_image:
            image_data = base64.b64decode(self.face_image)
            image = np.array(Image.open(io.BytesIO(image_data)))

            # Convert to grayscale for clarity check
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()

            # Define a threshold for image clarity
            blur_threshold = 100.0
            if laplacian_var < blur_threshold:
                raise UserError(_("The uploaded image is too blurry. Please upload a clearer image!"))
