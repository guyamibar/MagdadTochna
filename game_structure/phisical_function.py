import numpy as np
from typing import Union, Tuple
from arduino_control import moveitmoveit
import cv2
import time
try:
    from picamera2 import Picamera2
except ImportError:
    Picamera2 = None
from pathlib import Path
import arduino_control.dealer_communication as dealer
from game_structure.models import Point2D
from game_structure.card_classification import CardClassifier
from game_structure.gsd import Gsd
from main.take_image import HighResCamera
from main.board_layout import get_group
# Dealer position
DEALER_X = 360
DEALER_Y = 125
SAFE_POS = (24,16)
angle = {0: -25, 1: 0, 2: 25}
K: list[list[float]] = [
    [1.39561099e03, 0.00000000e00, 8.85690305e02],
    [0.00000000e00, 1.38830766e03, 5.04754597e02],
    [0.00000000e00, 0.00000000e00, 1.00000000e00],
]

# Distortion coefficients [k1, k2, p1, p2, k3] from calibration
D: list[float] = [-0.07011441, 0.24724181, 0.00124205, -0.00364551, -0.27059026]

# Extract camera intrinsic parameters
fx: float = K[0][0]  # Focal length x
fy: float = K[1][1]  # Focal length y
cx: float = K[0][2]  # Principal point x
cy: float = K[1][2]  # Principal point y

# Camera parameters tuple for AprilTag detection [fx, fy, cx, cy]
camera_params: list[float] = [fx, fy, cx, cy]
# --- ALIGNMENT BASKET PLACEHOLDERS ---
def put_card_in_basket(card_position: Tuple[float, float], card_orientation: int):
    """Takes a grabbed card and drops it into the physical alignment basket."""
    #TODO check, but its done
    moveitmoveit.put_card_in_rotator(card_position, card_orientation)


def align_basket(target_angle: int):
    """Rotates the basket mechanism to the requested angle."""
    #TODO check, but its done
    moveitmoveit.rotator_rotate(target_angle)
    print(f"⚙️ [Basket] Basket mechanism turning card to exactly {target_angle} degrees.")


def grab_from_basket(target_position: Tuple[float, float], target_orientation: float):
    """Retrieves the card from the basket after alignment and flipping is done."""
    #TODO check, but its done
    print(f"🧺 [Basket] Arm returning to basket to GRAB the processed card.")
    moveitmoveit.take_card_from_rotator(target_position, target_orientation)

def move_to_safe_position():
    """Moves the arm to a safe distance so the flip mechanism can operate without collision."""
    #TODO check, but its done
    print(f"🦾 [Arm] Retreating to SAFE_POS (safe distance).")
    moveitmoveit.move_to(SAFE_POS)


# --- DEALER & VISION PLACEHOLDERS ---
def dealer_shoot(player:int, number_of_cards = 1):
    #TODO check, but its done
    print("🤖 [Dealer] Firing a card to the player.")
    dealer.shoot_cards(number_of_cards, angle[player], dealer.high_power)
    dealer.move_stepper(0)


def take_and_analyze_shot_card() -> Tuple[Tuple[float, float], float]:
    #TODO SABAG THIS ON YOU
    """Takes a picture to find where the dealer shot the card."""
    print("📸 [Vision] Snapping photo of the table...")
    print("🔍 [Vision] Locating new card coordinates and angle.")
    frame = HighResCamera().take_image()
    gsd = Gsd(camera_params=camera_params)
    res = gsd.process([frame])
    all_cards = res.open_cards + res.face_down_cards
    real = []
    for card in all_cards:
        if get_group(card.center) == "PICKUP":
            real.append(card)

    if len(real) == 0:
        print("No cards detected for pickup.")
        return ((0, 0), 0)
    card = real[0]

    return ((card.center.x, card.center.y), card.get_angle())  # Placeholder data


def deal_cards(num_players: int, cards_per_player: int) -> None:
    #TODO check, but its done
    """
    Physical dealing sequence (Black Box Placeholder).
    This function will be used to trigger the physical hardware sequence.
    """
    print(f"\n🃏 [Physical] Deal Sequence Triggered:")
    print(f"   👥 Players: {num_players}")
    print(f"   🎴 Cards per Player: {cards_per_player}")
    for player in range(num_players):
        dealer.shoot_cards(cards_per_player,angle[player],dealer.mid_power)
    print("   ✅ Hardware sequence complete (Simulated).\n")
    dealer.move_stepper(0)

# --- ARM MOVEMENT PLACEHOLDERS ---
def pixels_to_physical(pixel_x, pixel_y):
    #TODO check, but its done
    ROOT_DIR = Path(__file__).parent.parent
    H_PATH = ROOT_DIR / "data" / "H_cam_to_arm.npy"

    H_cam_to_arm = None
    if H_PATH.exists():
        H_cam_to_arm = np.load(H_PATH)
        print(f"✅ Loaded calibration matrix from {H_PATH}")
    else:
        print(f"⚠️ Warning: Calibration matrix not found at {H_PATH}")

    if H_cam_to_arm is None: return (0, 0)
    pt = np.array([(pixel_x, pixel_y)], dtype=np.float32).reshape(-1, 1, 2)
    transformed = cv2.perspectiveTransform(pt, H_cam_to_arm)
    return (float(transformed[0][0][0]), float(transformed[0][0][1]))



def move_player(point_coordinate: Tuple[float,float]) -> None:
    #TODO check, but its done
    """Moves the robotic arm/player to a specific point coordinate."""
    if isinstance(point_coordinate, Point2D):
        pos = (point_coordinate.x, point_coordinate.y)
    else:
        pos = point_coordinate
    moveitmoveit.move_to(pos)


def grab() -> None:
    #TODO check, but its done
    """Triggers the grab mechanism."""
    print("🦾 [Arm] GRAB triggered.")
    moveitmoveit.grab()


def drop() -> None:
    #TODO check, but its done
    """Triggers the drop/release mechanism."""
    print("🦾 [Arm] DROP triggered.")
    moveitmoveit.grabber_release()
    moveitmoveit.grabber_rest()


def flip(card_pos:Tuple[float,float], angle:int, target_pos) -> None:
    #TODO LAHAV
    """Triggers the flipping mechanism for a card inside the basket."""
    put_card_in_basket(card_pos, angle)
    move_to_safe_position()
    moveitmoveit.send_command(5,0,0)
    time.sleep(2)
    grab_from_basket(target_pos,0)
    move_to_safe_position()
    moveitmoveit.send_command(8,0,0)
    print("🔄 [Mechanism] FLIPPING card over inside the basket.")
    # Future code: trigger physical flip servo


def look_at_card() -> str:
    #TODO check, but its done
    """Uses the camera to identify the card currently held in the basket."""
    print("👁 [Vision] Scanning face-up card in the basket...")
    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    suits = {
        "H" : "Hearts",
        "D" : "Diamonds",
        "C" : "Clubs",
        "S" : "Spades"
    }
    card = CardClassifier().infere(frame)
    rank = card["rank"]
    suit = suits[card['suit']]
    return f"{rank} of {suit}"