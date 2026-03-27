import math
from typing import *
import lgpio as lg
import time
import numpy as np

from game_structure.card import Card

position = Tuple[float, float]


class Arm_Motor:
    """
    this is the class for a single motor for easy interaction
    """
    CHIP = 0
    SERVO_R_PIN = 23  # GPIO18
    SERVO_L_PIN = 18
    FREQ = 50
    X_OFFSET = 0.7
    Y_OFFSET = 0.4

    s_l = (0.0, 0.0)
    s_r = (3.5, 0.0)

    a = 12
    b = 12

    def __init__(self, pin_num: int):
        self.pin_num = pin_num

    def __distance(self,a_pt, b_pt):
        return math.hypot(a_pt[0] - b_pt[0], a_pt[1] - b_pt[1])

    def __alpha_beta(self,p, s_l, s_r, a, b):
        d_l = self.__distance(p, s_l)
        term_l = (d_l ** 2 + a ** 2 - b ** 2) / (2 * a * d_l)
        term_l = max(-1.0, min(1.0, term_l))
        alpha = math.atan2(p[1] - s_l[1], p[0] - s_l[0]) + math.acos(term_l)

        d_r = self.__distance(p, s_r)
        term_r = (d_r ** 2 + a ** 2 - b ** 2) / (2 * a * d_r)
        term_r = max(-1.0, min(1.0, term_r))
        beta = math.atan2(p[1] - s_r[1], p[0] - s_r[0]) - math.acos(term_r)

        return alpha, beta

    def get_angles(self, pos):
        return self.__alpha_beta(self.corrected(pos),self.s_l,self.s_r,self.a,self.b)

    def __corrected(self,p):
        if p[0] > 2.4:
            x_mltp = -1
        elif p[0] < -2.4:
            x_mltp = 1
        else:
            x_mltp = 0
        if p[1] < 4.8:
            y_mltp = 0
        else:
            y_mltp = -1
        return p[0] + x_mltp * Arm_Motor.X_OFFSET, p[1] + y_mltp * Arm_Motor.Y_OFFSET

    def __set_inner_angle(self,angle, servo_pin,h):
        angle = angle / math.pi * 180
        duty = 2.5 + (angle / 180.0) * 6
        print(f"Motor: {servo_pin}, Angle: {angle}, duty: {duty}")
        lg.tx_pwm(h, servo_pin, Arm_Motor.FREQ, duty)

    def set_angle(self,angle,h):
        servo_side = 'r' if self.pin_num == Arm_Motor.SERVO_R_PIN else 'l'
        if servo_side == "r":
            theta_servo = -2 / 3 * angle + 2 / 3 * math.pi
        elif servo_side == "l":
            theta_servo = -2 / 3 * angle + math.pi
        else:
            print("unknown servo")
            return
        self.__set_inner_angle(theta_servo, self.pin_num,h)


class Grabber:
    """
    this is the grabber that sits at the end of the arms
    and goes up and down to grab the cards.
    """
    CHIP = 0
    NEUTRAL = 7.16
    PIN = 12
    # choose symmetric speeds around neutral
    DUTY_FWD = NEUTRAL + 2  # example = 9.265%
    DUTY_BACK = NEUTRAL - 2  # example = 5.265%

    L_FWD = 6.8  # cm moved in 1 sec forward (example)
    L_BACK = 5  # cm moved in 1 sec backward (example)

    V_FWD = L_FWD
    V_BACK = L_BACK

    def __init__(self):
        self.pin_num = Grabber.PIN

    def __set_speed(self, duty, h):
        lg.tx_pwm(h, Grabber.PIN, 50, duty)

    def __stop(self, h):
        self.__set_speed(Grabber.NEUTRAL, h)

    def __move_distance(self, dist_cm, h):
        if dist_cm == 0:
            return

        if dist_cm > 0:
            # forward
            t = dist_cm / Grabber.V_FWD
            self.__set_speed(Grabber.DUTY_FWD, h)
            time.sleep(t)
        else:
            # backward
            t = (-dist_cm) / Grabber.V_BACK
            self.__set_speed(Grabber.DUTY_BACK, h)
            time.sleep(t)
        self.__stop(h)

    def grab(self):
        """
        goes down, grabs the card and goes up a little
        :return:
        """
        h = lg.gpiochip_open(Grabber.CHIP)
        lg.gpio_claim_output(h, self.pin_num)
        self.__move_distance(5.3, h)  # forward 5 cm
        time.sleep(1)
        self.__move_distance(-2, h)
        self.__stop(h)
        lg.gpiochip_close(h)

    def let_go(self):
        """
        should come after grab, goes up a little more
        and makes the card hit the ring and fall.
        :return:
        """
        h = lg.gpiochip_open(Grabber.CHIP)
        lg.gpio_claim_output(h, self.pin_num)
        self.__move_distance(-4, h)
        time.sleep(1)
        self.__move_distance(2, h)
        self.__stop(h)
        lg.gpiochip_close(h)


class Arm_System:
    DEFAULT_POS = (0, 10)

    def __init__(self):
        self.right_motor = Arm_Motor(Arm_Motor.SERVO_R_PIN)
        self.left_motor = Arm_Motor(Arm_Motor.SERVO_L_PIN)
        self.grabber = Grabber()

    def move_to(self, pos: position):
        alpha, beta = Arm_Motor.get_angles(pos)
        h = lg.gpiochip_open(Arm_Motor.CHIP)
        lg.gpio_claim_output(h, self.right_motor.pin_num)
        lg.gpio_claim_output(h, self.left_motor.pin_num)
        self.right_motor.set_angle(beta,h)
        self.left_motor.set_angle(alpha,h)
        time.sleep(1)
        lg.tx_pwm(h, self.right_motor.pin_num, 0, 0)
        lg.tx_pwm(h, self.left_motor.pin_num, 0, 0)
        lg.gpiochip_close(h)
    def move_card(self, card: Card, target_pos: position):
        self.move_to(card.pos)
        self.grabber.grab()
        self.move_to(target_pos)
        self.grabber.let_go()
        self.move_to(Arm_System.DEFAULT_POS)

