
import threading
from libemg.data_handler import OnlineDataHandler
from libemg.emg_predictor import EMGClassifier, OnlineEMGClassifier
from libemg.feature_extractor import FeatureExtractor
from libemg.streamers import emager_streamer
from libemg.filtering import Filter

import models.models as etm
import utils.utils as eutils
from visualization.realtime_gui import RealTimeGestureUi, update_labels_process
import utils.gestures_json as gjutils

import time
import torch
import numpy as np
from multiprocessing import Lock
from multiprocessing.connection import Connection
from config import *

eutils.set_logging()


def predicator(use_gui:bool=True, conn:Connection | None = None, delay:float=0.01):

    # Create data handler and streamer
    p, smi = emager_streamer()
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
        model.eval()
    except RuntimeError as e:
        print(f"Error loading model: {e}")

    classi = EMGClassifier(model)
    classi.add_majority_vote(MAJORITY_VOTE)

    # Ensure OnlineEMGClassifier is correctly set up for data handling and inference
    smm_items=[
            ["classifier_output", (100,4), np.double, Lock()], #timestamp, class prediction, confidence, velocity
            ['classifier_input', (100, 1 + 64), np.double, Lock()], # timestamp <- features ->
        ]
    oclassi = OnlineEMGClassifier(classi, WINDOW_SIZE, WINDOW_INCREMENT, odh, fg, std_out=False, smm=True, smm_items=smm_items)


    # Create GUI
    files = gjutils.get_images_list(MEDIA_PATH)
    print("Files: ", files)
    print("Creating GUI...")
    gui = RealTimeGestureUi(files)
    
    stop_event = threading.Event()
    updateLabelProcess = threading.Thread(target=update_labels_process, args=(stop_event, gui, conn, delay))

    try:
        print("Starting classification...")
        oclassi.run(block=False)
        print("Starting process thread...")
        updateLabelProcess.start()
        print("Starting GUI...")
        if use_gui:
            gui.run()
        else:
            while True:
                time.sleep(1)
        
    except Exception as e:
        print(f"Error during classification: {e}")

    finally :
        if conn is not None:
            conn.send("exit")
        stop_event.set()
        oclassi.stop_running()
        
        print("Exiting")


if __name__ == "__main__":
    predicator(use_gui=True, conn=None, delay=0.01)