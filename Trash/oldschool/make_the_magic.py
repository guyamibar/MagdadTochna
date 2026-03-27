import os
import cv2
import time
import sys
from collections import defaultdict
import math
from discover_cards_frames import discover_cards,pixel_to_camera
from april_tags_frames import detect_apriltags
import numpy as np
# Setup folders
os.makedirs("results/photos", exist_ok=True)
os.makedirs("results/texts", exist_ok=True)
os.makedirs("results/marked", exist_ok=True)

# RUN ID SYSTEM
RUN_FILE = "run_id.txt"

# Create file if missing
if not os.path.exists(RUN_FILE):
    with open(RUN_FILE, "w") as f:
        f.write("0")

# Increment run ID
with open(RUN_FILE, "r") as f:
    RUN_ID = int(f.read().strip()) + 1

with open(RUN_FILE, "w") as f:
    f.write(str(RUN_ID))

print(f"Starting RUN #{RUN_ID}")

# our digital camera calibration data
K = [
    [1.39561099e+03, 0.00000000e+00, 8.85690305e+02],
    [0.00000000e+00, 1.38830766e+03, 5.04754597e+02],
    [0.00000000e+00, 0.00000000e+00, 1.00000000e+00],
]
D = [-0.07011441, 0.24724181, 0.00124205, -0.00364551, -0.27059026]

fx = K[0][0]
fy = K[1][1]
cx = K[0][2]
cy = K[1][2]

camera_params = [fx, fy, cx, cy]
tag_id_for_depth = 1

# ----------------------------------------------------
# every frames goes to both functions
# ----------------------------------------------------


def distance(first_location, second_location):
    deltax=first_location[0] - second_location[0]
    deltay=first_location[1] - second_location[1]
    return math.sqrt(deltax**2 + deltay**2)

def find_closest(april_poses, card_poses, found_cards, num_of_cards, tag_id=1):
    if(tag_id not in april_poses.keys()):
        print("couldnt find the tag")
        sys.exit()
    if not found_cards:
        return [], []
    if(len(found_cards)<=num_of_cards):
        num_of_cards = len(found_cards)
    cards=[]
    dis=[]
    found_cards_copy=found_cards.copy()
    for i in range(num_of_cards):
        j = 0
        for card in found_cards_copy:
            if j==0:
                j+=1
                closest_card =card
                closest_dis = distance(april_poses[tag_id], card_poses[closest_card])
            temp_dis = distance(april_poses[tag_id], card_poses[card])
            if(closest_dis > temp_dis):
                closest_dis= temp_dis
                closest_card = card
        cards.append(closest_card)
        dis.append(closest_dis)
        found_cards_copy.remove(closest_card)

    return cards,dis

def distance_for_hand(card_position,april_position,num_frames=30):
    print("move in x " + str(math.abs(april_position[0]-card_position[0])))
    print("move in y " + str(math.abs(april_position[1]-card_position[1])))

def take_a_pic(num_of_cards,num_dealer,agent):
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        raise Exception("Could not open camera.")
    frame_id = 0
    number_of_images=0
    my_cards={}
    dealer_cards={}
    while number_of_images!=100:
        ret, frame = cap.read()
        if not ret:
            break
        # detect AprilTags (and draw them)
        frame_for_tags = frame.copy()
        frame_with_tags, april_poses, found_tags = detect_apriltags(frame_for_tags, camera_params)

        # run YOLO card detection
        annotated_frame, card_poses, found_cards= discover_cards(
            frame,  # use frame WITH TAG drawings
            frame_id,
            RUN_ID,
        )
        card_poses_3d = {}  # card_poses_3d[label] = [X, Y, Z] in meters
        if tag_id_for_depth in april_poses:
            Z_ref = april_poses[tag_id_for_depth][2]  # z of the tag in meters
            for label, (u, v) in card_poses.items():
                X, Y, Z = pixel_to_camera(u, v, Z_ref, fx, fy, cx, cy)
                card_poses_3d[label] = [X, Y, Z]
        else:
            card_poses_3d = {}

        for card in card_poses_3d.keys():
            distance = distance(card_poses_3d[card], april_poses[2])

        # Show the LIVE annotated view
        cv2.imshow("Magic: Cards", annotated_frame)
        cards, _ = find_closest(april_poses, card_poses_3d, found_cards, num_of_cards)
        dealer_card,_=find_closest(april_poses, card_poses_3d, found_cards, num_dealer, tag_id=0)
        for card in cards:
            try:
                my_cards[card]+=1
            except:
                my_cards[card]=1
        for card in dealer_card:
            try:
                dealer_cards[card]+=1
            except:
                dealer_cards[card]=1

        for card in found_cards:
            agent.update_count(card)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
        number_of_images+=1

    my_cards = sorted(my_cards.items(), key=lambda x: x[1], reverse=True)
    dealer_cards=sorted(dealer_cards.items(), key=lambda x: x[1], reverse=True)
    cards=[]
    j=0
    for card in my_cards:
        if j<num_of_cards:
            cards.append(card[0])
        j+=1
    j=0
    dealer_card=[]
    for card in dealer_cards:
        if num_dealer>j:
            dealer_card.append(card[0])
        j+=1
    cap.release()
    cv2.destroyAllWindows()
    return dealer_card,cards


def distance_checker_multi(num_frames=30):
    """
    Capture many frames and produce reliable:
      - card list
      - april tags
      - 3D card coordinates
      - distances between each card and each AprilTag

    Returns:
        distances, april_poses_3d, card_poses_3d
    """

    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        raise Exception("Could not open camera.")

    # stores many detections
    card_seen_count = defaultdict(int)
    card_xyz_list = defaultdict(list)

    april_xyz_list = defaultdict(list)

    frame_id = 0

    while frame_id < num_frames:
        ret, frame = cap.read()
        if not ret:
            break

        # 1) Detect AprilTags
        frame_for_tags = frame.copy()
        frame_with_tags, april_poses, found_tags = detect_apriltags(
            frame_for_tags,
            camera_params
        )

        # store AprilTag 3D poses (multiple samples)
        for tag_id, pose3d in april_poses.items():
            april_xyz_list[tag_id].append(pose3d)

        # 2) Detect cards (YOLO)
        annotated, card_poses, found_cards = discover_cards(
            frame_with_tags,
            output_id=frame_id,
            RUN_ID=RUN_ID,
            save_outputs=False
        )

        # 3) Convert each card pixel → 3D using AprilTag depth
        if tag_id_for_depth in april_poses:
            Z_ref = april_poses[tag_id_for_depth][2]

            for label, (u, v) in card_poses.items():
                X, Y, Z = pixel_to_camera(u, v, Z_ref, fx, fy, cx, cy)
                card_xyz_list[label].append([X, Y, Z])
                card_seen_count[label] += 1

        frame_id += 1
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

    # 4) Aggregate AprilTag positions (median)
    april_poses_3d = {
        tag_id: np.median(np.array(samples), axis=0).tolist()
        for tag_id, samples in april_xyz_list.items()
    }

    # 5) Aggregate card positions (median)
    card_poses_3d = {
        card: np.median(np.array(samples), axis=0).tolist()
        for card, samples in card_xyz_list.items()
        if card_seen_count[card] >= 3   # must appear in >=3 frames
    }

    # 6) Compute distances
    distances = {}
    for card, card_xyz in card_poses_3d.items():
        distances[card] = {}

        for tag_id, tag_xyz in april_poses_3d.items():
            dx = card_xyz[0] - tag_xyz[0]
            dy = card_xyz[1] - tag_xyz[1]
            dist = math.sqrt(dx*dx + dy*dy)
            distances[card][tag_id] = dist

    for card_label, tag_distances in distances.items():
        print(card_label, tag_distances)






