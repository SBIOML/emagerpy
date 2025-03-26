
import threading
from libemg.data_handler import OnlineDataHandler
from libemg.emg_predictor import EMGClassifier, OnlineEMGClassifier
from libemg.feature_extractor import FeatureExtractor
from libemg.streamers import emager_streamer
from libemg.filtering import Filter
from libemg.shared_memory_manager import SharedMemoryManager

from utils.find_usb import virtual_port
import models.models as etm
import utils.utils as eutils
from visualization import realtime_gui
import utils.gestures_json as gjutils

import os
import torch
import time
import numpy as np
from multiprocessing import Lock, Process

eutils.set_logging()


MODEL_PATH = "C:\GIT\Datasets/Libemg/TestVideo/libemg_torch_cnn_TestVideo_829_24-10-28_21h37.pth"
MEDIA_PATH = "./media-test/"

NUM_CLASSES = 5
WINDOW_SIZE=200
WINDOW_INCREMENT=10
MAJORITY_VOTE=7
SAMPLING = 1010

VIRTUAL = False

def update_labels_process(gui:realtime_gui.RealTimeGestureUi, smm_items:list, stop_event:threading.Event):
    smm = SharedMemoryManager()
    gestures_dict = gjutils.get_gestures_dict(MEDIA_PATH)
    images = gjutils.get_images_list(MEDIA_PATH)
    
    while not stop_event.is_set():
        check = True
        for item in smm_items:
            tag, shape, dtype, lock = item
            if not smm.find_variable(tag, shape, dtype, lock):
                # wait for the variable to be created
                check = False
                break
        if not check:
            continue

        # Read from shared memory
        classifier_output = smm.get_variable("classifier_output")
        # The most recent output is at index 0
        latest_output = classifier_output[0]
        output_data = {
            "timestamp": np.double(latest_output[0]),
            "prediction": int(latest_output[1]),
            "probability": np.double(latest_output[2]),
        }
        print(f"Sending data: ({(output_data['prediction'])}) : {output_data} ")
        index = output_data["prediction"]
        label = gjutils.get_label_from_index(index, images, gestures_dict)

        gui.update_label(label)

        time.sleep(0.45)

def run():

    # Get data port
    if VIRTUAL:
        DATASET_PATH = "C:\GIT\Datasets\EMAGER/"
        PORT = virtual_port(DATASET_PATH)
        print("Data generator thread started")
        time.sleep(3)
    else:
        PORT = None

    # Create data handler and streamer
    p, smi = emager_streamer(specified_port=PORT)
    print(f"Streamer created: process: {p}, smi : {smi}")
    odh = OnlineDataHandler(shared_memory_items=smi)

    filter = Filter(SAMPLING)
    notch_filter_dictionary={ "name": "notch", "cutoff": 60, "bandwidth": 3}
    filter.install_filters(notch_filter_dictionary)
    bandpass_filter_dictionary={ "name":"bandpass", "cutoff": [20, 450], "order": 4}
    filter.install_filters(bandpass_filter_dictionary)
    odh.install_filter(filter)
    print("Data handler created")

    # Choose feature group and classifier
    fe = FeatureExtractor()
    fg = ["MAV"]
    print("Feature group: ", fg)

    # Verify model loading and state dict compatibility
    model = etm.EmagerCNN((4, 16), NUM_CLASSES, -1)
    try:
        model.load_state_dict(torch.load(MODEL_PATH))
    except RuntimeError as e:
        print(f"Error loading model: {e}")
        # Handle error (e.g., exit or attempt a recovery)

    classi = EMGClassifier()
    classi.add_majority_vote(MAJORITY_VOTE)
    classi.classifier = model.eval()

    # Ensure OnlineEMGClassifier is correctly set up for data handling and inference
    smm_items=[["classifier_output", (100,3), np.double, Lock()], #timestamp, class prediction, confidence
                        ["classifier_input", (100,1+64), np.double, Lock()], # timestamp, <- features ->
                        ["adapt_flag", (1,1), np.int32, Lock()],
                        ["active_flag", (1,1), np.int8, Lock()]]
    oclassi = OnlineEMGClassifier(classi, WINDOW_SIZE, WINDOW_INCREMENT, odh, fg, std_out=False, smm=True, smm_items=smm_items)


    # Create GUI
    files = gjutils.get_images_list(MEDIA_PATH)
    print("Files: ", files)
    print("Creating GUI...")
    gui = realtime_gui.RealTimeGestureUi(files)
    
    stop_event = threading.Event()
    updateLabelProcess = threading.Thread(target=update_labels_process, args=(gui, smm_items, stop_event))

    try:
        print("Starting classification...")
        oclassi.run(block=False)
        print("Starting process thread...")
        updateLabelProcess.start()
        print("Starting GUI...")
        gui.run()

        # while True:
        #     time.sleep(1)
        
    except Exception as e:
        print(f"Error during classification: {e}")

    finally :
        stop_event.set()
        oclassi.stop_running()

        print("Exiting")

if __name__ == "__main__":
    run()