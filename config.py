
# hand_close, hand_open, index extension, ok, thumbs up
CLASSES = [2,3,30,14,18]
NUM_CLASSES = 5
NUM_REPS = 5
REP_TIME = 5
REST_TIME = 1

WINDOW_SIZE = 200
WINDOW_INCREMENT = 10
EPOCH = 10
SAMPLING = 1010
MAJORITY_VOTE=50
SAMPLING=1010
FILTER = False
VIRTUAL = False
PORT = None

BASE_PATH = "./Datasets/"
SESSION = "D0"

import utils.find_models as futils
# MODEL_NAME = "libemg_torch_cnn_D0_974_25-10-20_15h03.pth"
MODEL_NAME = futils.find_last_model(BASE_PATH, SESSION)

MEDIA_PATH = "./media-test/"
MODEL_PATH = f"{BASE_PATH}{SESSION}/{MODEL_NAME}"
DATAFOLDER = f"{BASE_PATH}{SESSION}/"
DATASETS_PATH = f"{BASE_PATH}{SESSION}/"
SAVE_PATH = f"{BASE_PATH}{SESSION}/"