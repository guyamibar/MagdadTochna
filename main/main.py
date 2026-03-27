import sys
from pathlib import Path
from time import sleep

# Add project root and game_structure to sys.path
root = Path(__file__).parent.parent
sys.path.append(str(root))
sys.path.append(str(root / "game_structure"))
from take_image import take_image
import cv2
import numpy as np

from game_structure.gsd import Gsd, camera_params
from game_structure.models import Point2D
from game_structure.phisical_function import move_player, grab, drop, flip, shoot

# Arbitrary constants for group center locations
GROUP_LOCATIONS = {
    "MYOPEN": (500, 867),
    "MYCLOSED": (500, 1072),
    "MYDECK": (500, 662),
    "PUBPILE_1": (286, 272),
    "PUBPILE_2": (500, 272),
    "PUBPILE_3": (713, 272),
    "PUBPILE_4": (286, 467),
    "PUBPILE_5": (500, 467),
    "PUBPILE_6": (713, 467),
    "DECKPLAYER_1": (90, 75),
    "OPENPLAYER_1": (90, 480),
    "DECKPLAYER_2": (910, 75),
    "OPENPLAYER_2": (910, 480),
}


def move_card_between_groups(source_group: str, dest_group: str):
    """
    Moves a card from the source group to the destination group using physical functions.
    """
    source_pos = GROUP_LOCATIONS.get(source_group)
    dest_pos = GROUP_LOCATIONS.get(dest_group)

    if source_pos is None or dest_pos is None:
        print(f"Error: Missing location for group(s) {source_group} or {dest_group}")
        return

    print(f"Moving card from {source_group} to {dest_group}")
    move_player(source_pos)
    grab()
    move_player(dest_pos)
    drop()


groups = (
    ["MYOPEN", "MYCLOSED", "MYDECK"] +
    [f"PUBPILE_{i}" for i in range(1, 7)] +
    [f"DECKPLAYER_{i}" for i in range(1, 6)] +
    [f"OPENPLAYER_{i}" for i in range(1, 6)]
)


def get_group(p: Point2D) -> str:
    # Table Layout (1000x1200 units for 50x60cm)
    # Card size: 127x178 units.

    # 1. Side Players (Columns: 0-180 and 820-1000)
    if 0 <= p.x < 180:
        if 0 <= p.y < 150: return "DECKPLAYER_1"
        if 160 <= p.y < 800: return "OPENPLAYER_1"
        return "UNKNOWN"
    
    if 820 <= p.x <= 1000:
        if 0 <= p.y < 150: return "DECKPLAYER_2"
        if 160 <= p.y < 800: return "OPENPLAYER_2"
        return "UNKNOWN"

    # 2. Center Column (180-820, Width = 640)
    if 180 <= p.x < 820:
        # Public Area - Row 1 (Y: 180-365)
        if 180 <= p.y < 365:
            col = int((p.x - 180) // 213.3)
            if col == 0: return "PUBPILE_1"
            if col == 1: return "PUBPILE_2"
            if col == 2: return "PUBPILE_3"
        
        # Public Area - Row 2 (Y: 375-560)
        if 375 <= p.y < 560:
            col = int((p.x - 180) // 213.3)
            if col == 0: return "PUBPILE_4"
            if col == 1: return "PUBPILE_5"
            if col == 2: return "PUBPILE_6"
        
        # MYDECK (Y 570-755)
        if 570 <= p.y < 755:
            if 435 <= p.x < 565: return "MYDECK"
            return "UNKNOWN"

    # 3. My Hand Rows (Bottom Area)
    # MYOPEN (Y 775-960)
    if 775 <= p.y < 960:
        if 180 <= p.x < 820: return "MYOPEN"
    
    # MYCLOSED (Y 980-1165)
    if 980 <= p.y < 1165:
        if 180 <= p.x < 820: return "MYCLOSED"

    return "UNKNOWN"


def visualize_groups():
    """
    Creates a 1000x1200 image coloring each area by its group name
    and adding labels + a reference card for scale.
    """
    # Using the updated TABLE_HEIGHT
    vis_img = np.zeros((1200, 1000, 3), dtype=np.uint8)
    
    # Unique colors
    all_possible_groups = groups + ["UNKNOWN"]
    np.random.seed(42)
    group_colors = {g: np.random.randint(50, 255, 3).tolist() for g in all_possible_groups}
    group_colors["UNKNOWN"] = [20, 20, 20]
    
    # Draw background
    step = 5
    for y in range(0, 1200, step):
        for x in range(0, 1000, step):
            group = get_group(Point2D(x, y))
            cv2.rectangle(vis_img, (x, y), (x + step, y + step), group_colors.get(group, [0,0,0]), -1)

    # Reference Card
    ref_card_x, ref_card_y = 435, 10
    cv2.rectangle(vis_img, (ref_card_x, ref_card_y), (ref_card_x + 127, ref_card_y + 178), (255, 255, 255), 2)
    cv2.putText(vis_img, "CARD REF", (ref_card_x + 10, ref_card_y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255,255,255), 1)

    # Public labels
    cv2.putText(vis_img, "P1", (230, 270), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255,255,255), 1)
    cv2.putText(vis_img, "P2", (450, 270), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255,255,255), 1)
    cv2.putText(vis_img, "P3", (660, 270), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255,255,255), 1)
    cv2.putText(vis_img, "P4", (230, 470), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255,255,255), 1)
    cv2.putText(vis_img, "P5", (450, 470), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255,255,255), 1)
    cv2.putText(vis_img, "P6", (660, 470), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255,255,255), 1)

    # Others
    cv2.putText(vis_img, "MYDECK", (445, 660), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 1)
    cv2.putText(vis_img, "MY_OPEN ROW (5 Cards)", (350, 870), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 1)
    cv2.putText(vis_img, "MY_CLOSED ROW (5 Cards)", (350, 1070), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 1)

    cv2.imwrite("Expanded Row-Based Layout (1000x1200).jpg", vis_img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


if __name__ == "__main__":
    filename1 = "main_run1.jpg"
    filename2 = "main_run2.jpg"
    img = take_image()
    cv2.imwrite(filename1, img)
    res = Gsd(camera_params=camera_params).process([img])
    cv2.imwrite(filename2, res.annotated_image)

def do_turn():
    gsd = Gsd(camera_params=camera_params)
    image = take_image()
    res = gsd.process([image])
    cards = []
    for open_card in res.open_cards:
        group = get_group(open_card.center)
        cards.append((group, open_card))
    for closed_card in res.face_down_cards:
        group = get_group(closed_card.center)
        cards.append((group, closed_card))