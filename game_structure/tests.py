import time

import cv2

from game_structure.detecting_functions import is_card_backside
from game_structure.gsd import Gsd
from main.phisical_function import move_card, shoot_card

K = [
    [1.39561099e03, 0.00000000e00, 8.85690305e02],
    [0.00000000e00, 1.38830766e03, 5.04754597e02],
    [0.00000000e00, 0.00000000e00, 1.00000000e00],
]
D = [-0.07011441, 0.24724181, 0.00124205, -0.00364551, -0.27059026]

fx = K[0][0]
fy = K[1][1]
cx = K[0][2]
cy = K[1][2]
camera_params = [fx, fy, cx, cy]


def sort_by_number():
    Gsd(camera_params)
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open video source.")
        exit()

    while True:
        frames = []
        for i in range(5):
            ret, frame = cap.read()
            if not ret:
                break
            frames.append(frame)

        img, open_cards, upside_down_cards = Gsd.process(frames)
        cv2.imshow("Detection Debug", img)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

        cards_to_move = []
        for card in open_cards:
            if card[0][0] < 800 and card[0][0] > 200:
                cards_to_move.append(card)

        for card in cards_to_move:
            if card[3][0] == "2":
                move_card(card[0], pos_2)
            elif card[3][0] == "3":
                move_card(card[0], pos_3)
            elif card[3][1] == "4":
                move_card(card[0], pos_4)
            elif card[3][1] == "5":
                move_card(card[0], pos_5)
            elif card[3][1] == "6":
                move_card(card[0], pos_6)
            elif card[3][1] == "7":
                move_card(card[0], pos_7)

        if len(cards_to_move) == 0:
            shoot_card(0, 40)

        time.sleep(2)

    cap.release()


def sort_by_suit():
    Gsd(camera_params)
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open video source.")
        exit()

    while True:
        frames = []
        for i in range(5):
            ret, frame = cap.read()
            if not ret:
                break
            frames.append(frame)
        img, open_cards, upside_down_cards = Gsd.process(frame)
        cv2.imshow("Detection Debug", img)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

        cards_to_move = []
        for card in open_cards:
            if card[0][0] < 800 and card[0][0] > 200:
                cards_to_move.append(card)

        for card in cards_to_move:
            if card[3][1] == "H":
                move_card(card[0], pos_H)
            elif card[3][1] == "D":
                move_card(card[0], pos_D)
            elif card[3][1] == "S":
                move_card(card[0], pos_S)
            elif card[3][1] == "C":
                move_card(card[0], pos_C)

        if len(cards_to_move) == 0:
            shoot_card(0, 40)

        time.sleep(2)

    cap.release()


def test():
    img = cv2.imread("data/img1.jpg")
    gsd = Gsd(camera_params)
    img, open_cards, upside_down_cards = gsd.process([img])
    for card in open_cards + upside_down_cards:
        if is_card_backside(card[2]):
            cv2.imshow("Backside", card[2])
        else:
            cv2.imshow("Frontside", card[2])
        cv2.waitKey(0)


test()


def get_greater_card(rank1, rank2):
    """
    Compares two card ranks (strings) and returns the greater one.
    Returns 'Equal' if they are the same value.
    """
    # 1. Define the hierarchy (Ace is usually high = 14)
    rank_values = {
        "2": 2,
        "3": 3,
        "4": 4,
        "5": 5,
        "6": 6,
        "7": 7,
        "8": 8,
        "9": 9,
        "10": 10,
        "J": 11,
        "Q": 12,
        "K": 13,
        "A": 14,
    }

    # 2. Normalize input to uppercase to handle 'a' vs 'A'
    r1 = rank1.upper().strip()
    r2 = rank2.upper().strip()

    # 3. Get integer values (default to 0 if invalid input)
    val1 = rank_values.get(r1, 0)
    val2 = rank_values.get(r2, 0)

    # 4. Compare
    if val1 > val2:
        return rank1
    elif val2 > val1:
        return rank2
    else:
        return "Equal"


def war():
    gsd = Gsd(camera_params)
    did_turn = False
    while True:
        take_picture()
        im = cv2.imread("pic")
        img, open_cards, upside_down_cards = gsd.process([im])
        cards = []
        for card in open_cards:
            if card[0][0] < 700 and card[0][0] > 300:
                cards.append(card)

        if len(cards) < 2:
            if not did_turn:
                move_card((800, 350), (500, 200))
                did_turn = True
            continue
        else:
            my_card = cards[0]
            other_card = cards[1]
            if cards[1][0][1] > cards[0][0][1]:
                my_card = cards[1]
                other_card = cards[0]
            pos_discard = (200, 200)
            winning = get_greater_card(my_card[3][0], other_card[3][0])
            if winning == my_card[3][0]:
                print("i win")
                move_card(other_card[0], pos_discard)
                move_card(my_card[0], pos_discard)
                print("War!")
            elif winning == other_card[3][0]:
                print("you win")
                time.sleep(1)
                continue
            else:
                print("everyone loses because i said so")
                return
