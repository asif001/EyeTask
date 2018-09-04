import cv2
import dlib
import imutils
import numpy as np
from keras.models import load_model


class GazeDetector:
    def __init__(self):
        self.model_left = load_model('inputs\\lefteyemodel.h5')
        self.model_left.compile(loss='categorical_crossentropy', optimizer='rmsprop', metrics=['accuracy'])

        self.model_right = load_model('inputs\\righteyemodel.h5')
        self.model_right.compile(loss='categorical_crossentropy', optimizer='rmsprop', metrics=['accuracy'])

        cascPath = 'inputs\\haarcascade_frontalface_default.xml'
        PREDICTOR_PATH = 'inputs\\shape_predictor_68_face_landmarks.dat'

        self.RIGHT_EYE_POINTS = list(range(36, 42))
        self.RIGHT_EYEBROW_POINTS = list(range(17, 22))

        self.LEFT_EYE_POINTS = list(range(42, 48))
        self.LEFT_EYEBROW_POINTS = list(range(22, 27))

        self.faceCascade = cv2.CascadeClassifier(cascPath)
        self.predictor = dlib.shape_predictor(PREDICTOR_PATH)
        # cap = cv2.VideoCapture(0)

    def processImage(self, image):
        ret = {
            "gazedirection": None,
            "img": None,
            "gazeleft": None,
            "gazeright": None,
            "blink": "none"
        }
        faces = self.faceCascade.detectMultiScale(
            image,
            scaleFactor=1.05,
            minNeighbors=5,
            minSize=(100, 100),
            flags=cv2.CASCADE_SCALE_IMAGE
        )
        roi1 = None
        roi2 = None

        # print("Found {0} faces!".format(len(faces)))
        for (x, y, w, h) in faces:
            cv2.rectangle(image, (x, y), (x + w, y + h), (0, 255, 0), 2)
            # Converting the OpenCV rectangle coordinates to Dlib rectangle
            dlib_rect = dlib.rectangle(int(x), int(y), int(x + w), int(y + h))

            landmarks = np.matrix([[p.x, p.y]
                                   for p in self.predictor(image, dlib_rect).parts()])

            landmarks_display_right = landmarks[self.RIGHT_EYE_POINTS + self.RIGHT_EYEBROW_POINTS]
            # for idx, point in enumerate(landmarks_display_right):
            #     pos = (point[0, 0], point[0, 1])
            (x, y, w, h) = cv2.boundingRect(landmarks_display_right)
            roi1 = image[y:y + h, x:x + w]
            roi1 = imutils.resize(roi1, width=250, height=250, inter=cv2.INTER_CUBIC)

            landmarks_display_left = landmarks[self.LEFT_EYE_POINTS + self.LEFT_EYEBROW_POINTS]
            # for idx, point in enumerate(landmarks_display_left):
            #     pos = (point[0, 0], point[0, 1])
            (x, y, w, h) = cv2.boundingRect(landmarks_display_left)
            roi2 = image[y:y + h, x:x + w]
            roi2 = imutils.resize(roi2, width=250, height=250, inter=cv2.INTER_CUBIC)

        if roi1 is not None:
            cv2.imwrite('temp_right.jpg', roi1)
            img = cv2.imread('temp_right.jpg')
            img = cv2.resize(img, (64, 64))
            img = np.reshape(img, [1, 64, 64, 3])
            classes_r82 = self.model_right.predict(img)
            roi1 = cv2.flip(roi1, 1)
            ret["gazeleft"] = roi1

        if roi2 is not None:
            cv2.imwrite('temp_left.jpg', roi2)
            img = cv2.imread('temp_left.jpg')
            img = cv2.resize(img, (64, 64))
            img = np.reshape(img, [1, 64, 64, 3])
            classes_l81 = self.model_left.predict(img)
            roi2 = cv2.flip(roi2, 1)
            ret["gazeright"] = roi2

        image = cv2.flip(image, 1)
        ret["img"] = image

        if roi1 is not None or roi2 is not None:
            self.percent(classes_l81, classes_r82, ret)
        return ret

    def percent(self, values_left, values_right, ret):
        x_l = values_left.item(0)
        y_l = values_left.item(1)
        z_l = values_left.item(2)
        b_l = values_left.item(3)

        x_r = values_right.item(0)
        y_r = values_right.item(1)
        z_r = values_right.item(2)
        b_r = values_right.item(3)

        total_l = b_l + x_l + y_l + z_l
        total_r = b_r + x_r + y_r + z_r

        x_l = float("{0:.2f}".format(x_l / total_l))
        y_l = float("{0:.2f}".format(y_l / total_l))
        z_l = float("{0:.2f}".format(z_l / total_l))
        b_l = float("{0:.2f}".format(b_l / total_l))

        x_r = float("{0:.2f}".format(x_r / total_r))
        y_r = float("{0:.2f}".format(y_r / total_r))
        z_r = float("{0:.2f}".format(z_r / total_r))
        b_r = float("{0:.2f}".format(b_r / total_r))

        x = (x_l + x_r) / 2
        y = (y_l + y_r) / 2
        z = (z_l + z_r) / 2
        b = (b_l + b_r) / 2
        # print("Prob of Class 0 is : ", x, "\nProb of Class 1 is : ", y, "\nProb of Class 2 is : ", z,
        #       "\nProb of Class 3 is : ", b)

        if x >= 0.80:
            cv2.putText(ret["img"], "Blink", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 2, 155, thickness=3)
            ret["blink"] = "both"
        elif x_l >= 0.80 and x_r <= 0.50:
            cv2.putText(ret["img"], "LEFT Blink", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 2, 255, thickness=3)
            ret["blink"] = "left"
        elif x_l <= 0.50 and x_r >= 0.80:
            cv2.putText(ret["img"], "RIGHT Blink", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 2, 255, thickness=3)
            ret["blink"] = "right"
        else:
            ret["blink"] = "none"
        if y >= 0.80:
            cv2.putText(ret["img"], "LEFT", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 2, 255, thickness=3)
            ret["gazedirection"] = "gazeleft"
        elif z >= 0.80:
            cv2.putText(ret["img"], "Middle", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 2, 130, thickness=3)
            ret["gazedirection"] = "gazecenter"
        elif b >= 0.80:
            cv2.putText(ret["img"], "RIGHT", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 2, 255, thickness=3)
            ret["gazedirection"] = "gazeright"
        else:
            ret["gazedirection"] = "gazenone"
