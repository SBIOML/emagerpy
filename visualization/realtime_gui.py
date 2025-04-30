from PyQt6 import QtWidgets
from PyQt6.QtCore import *
from PyQt6.QtWidgets import *
from PyQt6.QtGui import QPixmap
import os
import sys
import threading
import utils.gestures_json as gjutils

class RealTimeGestureUi(QWidget):
    labelChanged = pyqtSignal(int)  # Define a signal for changing labels

    def __init__(self, images:list):
        self.app = QApplication([])

        super().__init__()

        self.images_path = images

        # Get the gestures dictionary
        self.images_folder = gjutils.get_images_folder(self.images_path)
        self.gestures_dict = gjutils.get_gestures_dict(self.images_folder)

        self.images_name = ""
        self.img_label = 1
        self.img_index = 0
        self.label_text = "Label Text"
        self.timer = QTimer(self)
        self.timer.timeout.connect(lambda: self.setImg(self.img_index))
        

        self.pixmaps = [QPixmap(img) for img in self.images_path]   
        self.pixmaps = [pm.scaled(QSize(400, 400)) for pm in self.pixmaps]
        self.setWindowTitle('RealTime Gesture Recognition')

        layout = QGridLayout()

        self.labelText = QtWidgets.QLabel(self, alignment=Qt.AlignmentFlag.AlignCenter)
        self.labelText.setText(self.label_text)
        layout.addWidget(self.labelText, 0, 0)

        self.gestureImage = QtWidgets.QLabel(self)  # alignment=Qt.AlignCenter
        self.gestureImage.setPixmap(self.pixmaps[self.img_index])
        layout.addWidget(self.gestureImage, 1, 0)

        self.setLayout(layout)

        self.labelChanged.connect(self.setImg)

    

    @pyqtSlot(int)
    def setImg(self, index):
        # Set the image and label
        self.label_text = self.images_name
        self.label_text = f"(label : {self.img_label})   {self.label_text}   [class : {self.img_index}] "
        self.labelText.setText(self.label_text)
        self.gestureImage.setPixmap(self.pixmaps[self.img_index])

    def update_label(self, label:int):
        # Get images path and index
        self.images_name = self.gestures_dict[str(label)]
        self.img_index = gjutils.get_index_from_label(label, self.images_path, self.gestures_dict)
        if self.img_index is None:
            self.img_index = 0
            return
        self.img_label = label
        self.labelChanged.emit(self.img_index)

    def update_index(self, index:int):
        # Get images path and index
        self.img_index = index
        if self.gestures_dict is not None:
            self.img_label = gjutils.get_label_from_index(index, self.images_path, self.gestures_dict)
            self.images_name = self.gestures_dict[str(self.img_label)]
        else:
            self.images_name = self.images_path[index].split("/")[-1].split(".")[0]
        if self.img_label is None:
            self.img_label = -1
            return
        self.labelChanged.emit(self.img_index)

    def run(self):
        self.show()
        self.timer.start(1000)
        self.app.aboutToQuit.connect(self.stop)
        self.app.exec()

    def stop(self):
        self.timer.stop()


from libemg.environments.controllers import ClassifierController
from multiprocessing.connection import Connection
import time
from config import *

def update_labels_process(stop_event:threading.Event, gui:RealTimeGestureUi, conn:Connection | None = None, delay:float=0.01):
    '''
    Update the labels of the gui and send the data to the controller via conn if it is not None
    stop_event: threading.Event = threading.Event()
    gui: RealTimeGestureUi = RealTimeGestureUi()
    conn: Connection | None = None, delay:float=0.01
    conn ouputs:
        output_data = {
            "prediction": int(predictions[0]),
            "timestamp": time.time()
        }
    '''
    gestures_dict = gjutils.get_gestures_dict(MEDIA_PATH)
    images = gjutils.get_images_list(MEDIA_PATH)
    ctrl = ClassifierController('predictions', NUM_CLASSES)
    
    # Run thread until stop event
    while not stop_event.is_set():
        
        # Get predictions using the controller
        predictions = ctrl.get_data(['predictions'])
        action = ctrl._get_action()
        # print(f"{predictions} (predictions)")
        # print(f"action: {action}")
        if predictions is None:
            time.sleep(delay)  # Wait a bit if no data
            continue
        
        output_data = {
            "prediction": int(predictions[0]),
            "timestamp": time.time()
        }
        if output_data is None:
            time.sleep(delay)
            continue
        
        index = int(predictions[0])
        label = gjutils.get_label_from_index(index, images, gestures_dict)

        gui.update_label(label)

        if conn is not None:
            print(f"Output : pred({predictions[0]})  gest[{label}] {output_data}" + " "*10,"... sending data ...")
            conn.send(output_data)

        time.sleep(delay)