import utils.utils as eutils
import utils.gestures_json as gjutils
from libemg_realtime_prediction import predicator
from control.interface_control import InterfaceControl

from multiprocessing.connection import Connection
from multiprocessing import Lock, Process, Pipe
from config import *
import time
from collections import deque, Counter
from statistics import mean

eutils.set_logging()

USE_GUI = True

POLL_SLEEP_DELAY = 0.001  # Sleep time to prevent busy waiting when polling for data
PREDICTOR_DELAY = 0.01 # Changes the frequency of predictions
PREDICTOR_TIMEOUT_DELAY = 0.5 # Timeout for waiting for new predictions

# Controller-side smoothing buffer
SMOOTH_WINDOW = 1 # Set to 1 to disable smoothing (always use latest value)
SMOOTH_METHOD = 'mode' # 'mode' recommended for categorical gestures; 'mean' for numeric smoothing


# PREDICTOR
def run_predicator_process(conn: Connection=None):
    predicator(use_gui=USE_GUI, conn=conn, delay=PREDICTOR_DELAY, timeout_delay=PREDICTOR_TIMEOUT_DELAY)


# COMMUNICATOR
def run_controller_process(conn: Connection=None):
    try:
        
        comm_controller = InterfaceControl(hand_type="psyonic")
        comm_controller.connect()
        
        gestures_dict = gjutils.get_gestures_dict(MEDIA_PATH)
        images = gjutils.get_images_list(MEDIA_PATH)
        
        # Main loop to read input from stdin
        print("Communicator waiting for data...")
        recent = deque(maxlen=SMOOTH_WINDOW)

        while True:
            # Read input from stdin
            if conn is None:
                input_data = input()
            else:
                # Drain the pipe buffer and collect any pending predictions
                input_data = None
                any_received = False
                while conn.poll():  # Check if data is available without blocking
                    try:
                        d = conn.recv()
                        any_received = True
                        input_data = d  # keep last for backwards-compat
                        timestamp = input_data["timestamp"]
                        # extract numeric prediction if present and append to recent
                        try:
                            p = int(d.get("prediction", 0))
                        except Exception:
                            p = None
                        if p is not None:
                            recent.append(p)
                    except EOFError:
                        print("Connection closed")
                        return

                # If no data available, wait briefly and continue
                if not any_received:
                    time.sleep(POLL_SLEEP_DELAY)  # sleep to prevent busy waiting
                    continue

                # Compute smoothed prediction (if smoothing window > 1 and buffer has data)
                if len(recent) == 0:
                    # nothing to do, continue
                    continue
                if SMOOTH_WINDOW > 1:
                    if SMOOTH_METHOD == 'mode':
                        counts = Counter(recent)
                        most_common = counts.most_common()
                        top_count = most_common[0][1]
                        candidates = [val for val, cnt in most_common if cnt == top_count]
                        # if tie, pick the most recent candidate
                        for v in reversed(recent):
                            if v in candidates:
                                smoothed_pred = v
                                break
                    elif SMOOTH_METHOD == 'mean':
                        smoothed_pred = int(round(mean(recent)))
                    else:
                        smoothed_pred = recent[-1]
                else:
                    smoothed_pred = recent[-1]

                # reconstruct input_data as a dict similar to what the GUI sent
                input_data = {
                    "prediction": smoothed_pred, "timestamp": timestamp
                }

            # Exit the loop if no more input is received
            if input_data is None or input_data == "":
                print("NO INPUT RECEIVED")
                continue
           
            # print("Communicator Received input:", input_data)
            if input_data == "exit":
                break

            # Process the input 
            try:
                input_pred = int(input_data["prediction"])
                # timestamp = input_data["timestamp"]
                if int(input_pred) not in range(NUM_CLASSES): 
                    input_pred = 0
                gesture = gjutils.get_label_from_index(input_pred, images, gestures_dict)

                print(f"Input: pred({input_pred})  gest[{gesture}]: {input_data}" + " "*10 + "... received data /  sending gesture ...")
            
            except Exception as e:
                print("Invalid input. Error: ", e)
                continue

            # Send the gesture to the hand
            comm_controller.send_gesture(gesture)
            print("="*50)
            
    except Exception as e:
        print(f"Error communicator: {e}")
    finally:
        comm_controller.disconnect()
        print("Communicator Exiting...")


# CONNECTION HANDLER

def run_process(target, conn: Connection):
    try:
        target(conn)
    except Exception as e:
        print(f"An error occurred in a subprocess: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    try:
            parent_conn, child_conn = Pipe()
            
            p1 = Process(target=run_process, args=(run_predicator_process, parent_conn))
            p2 = Process(target=run_process, args=(run_controller_process, child_conn))
            
            p1.start()
            p2.start()
            
            p1.join()
            p2.join()
    except Exception as e:
        print(f"An error occurred in the main process: {e}")
    finally:
        parent_conn.close()
        child_conn.close()

        if p1.is_alive():
            p1.terminate()
        if p2.is_alive():
            p2.terminate()
