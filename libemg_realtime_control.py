import utils.utils as eutils
import utils.gestures_json as gjutils
from libemg_realtime_prediction import predicator
from control.interface_control import InterfaceControl

from multiprocessing.connection import Connection
from multiprocessing import Lock, Process, Pipe
from config import *

eutils.set_logging()

USE_GUI = True


# PREDICTOR
def run_predicator_process(conn: Connection=None):
    predicator(use_gui=USE_GUI, conn=conn, delay=0.01)


# COMMUNICATOR
def run_controller_process(conn: Connection=None):
    try:
        
        comm_controller = InterfaceControl(hand_type="psyonic")
        comm_controller.connect()
        
        # Main loop to read input from stdin
        print("Communicator waiting for data...")
        while True:
            # Read input from stdin
            if conn is None:
                input_data = input()
            else:
                input_data = conn.recv()

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
                timestamp = input_data["timestamp"]
                if int(input_pred) not in range(NUM_CLASSES): 
                    input_pred = 0
                gesture = gjutils.get_label_from_index(input_pred, MEDIA_PATH)

                print(f"Input: pred({input_pred})  gest[{gesture}]: {input_data}" + " "*10 + "... received data /  sending gesture ...")
            
            except Exception as e:
                print("Invalid input. Error: ", e)
                continue

            # Send the gesture to the hand
            comm_controller.send_gesture(gesture)
            
            
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
