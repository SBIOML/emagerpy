if __name__ == "__main__":
    from libemg.data_handler import OnlineDataHandler
    from libemg.datasets import OneSubjectMyoDataset
    from libemg.gui import GUI
    from libemg.streamers import emager_streamer
    import time
    import os
    from config import *
    

    # Create data handler and streamer
    p, smi = emager_streamer()
    print(f"Streamer created: process: {p}, smi : {smi}")
    odh = OnlineDataHandler(shared_memory_items=smi)
    print("Data handler created")

    args = {
        "online_data_handler": odh,
        "media_folder": MEDIA_PATH,
        "data_folder": DATAFOLDER,
        "num_reps": NUM_REPS,
        "rep_time": REP_TIME,
        "rest_time": REST_TIME,
        "auto_advance": True
    }
    
    gui = GUI(odh, args=args, debug=False, width=900, height=800)
    gui.download_gestures(CLASSES, MEDIA_PATH, download_gifs=False)
    gui.start_gui()

    print("Data saved in : " + DATAFOLDER)