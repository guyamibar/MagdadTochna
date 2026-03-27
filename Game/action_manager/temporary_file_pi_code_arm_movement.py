import math
import lgpio
import time
import numpy as np

CHIP = 0
SERVO1_PIN = 23  # GPIO18
SERVO2_PIN = 18
FREQ = 50
X_OFFSET = 0.7
Y_OFFSET = 0.4

p0 = (-9.6, 10.0)
p1 = (9.6, 16.8)

s_l = (0.0, 0.0)
s_r = (3.5, 0.0)

a = 12
b = 12


# -------------------------------------

def __distance(a_pt, b_pt):
    return math.hypot(a_pt[0] - b_pt[0], a_pt[1] - b_pt[1])


def __alpha_beta(p, s_l, s_r, a, b):
    d_l = __distance(p, s_l)
    term_l = (d_l ** 2 + a ** 2 - b ** 2) / (2 * a * d_l)
    term_l = max(-1.0, min(1.0, term_l))
    alpha = math.atan2(p[1] - s_l[1], p[0] - s_l[0]) + math.acos(term_l)

    d_r = __distance(p, s_r)
    term_r = (d_r ** 2 + a ** 2 - b ** 2) / (2 * a * d_r)
    term_r = max(-1.0, min(1.0, term_r))
    beta = math.atan2(p[1] - s_r[1], p[0] - s_r[0]) - math.acos(term_r)

    return alpha, beta


# Sample

h = lgpio.gpiochip_open(CHIP)
lgpio.gpio_claim_output(h, SERVO1_PIN)
lgpio.gpio_claim_output(h, SERVO2_PIN)


def __set_servo_angle(angle, servo_pin):
    angle = angle / math.pi * 180
    duty = 2.5 + (angle / 180.0) * 6
    print(f"Motor: {servo_pin}, Angle: {angle}, duty: {duty}")
    lgpio.tx_pwm(h, servo_pin, FREQ, duty)


def __set_output_angle(angle, servo_side):
    if servo_side == "r":
        theta_servo = -2 / 3 * angle + 2 / 3 * math.pi
    elif servo_side == "l":
        theta_servo = -2 / 3 * angle + math.pi
    else:
        print("unknown servo")
        return
    servo_pin = SERVO1_PIN if servo_side == 'r' else SERVO2_PIN
    __set_servo_angle(theta_servo, servo_pin)


def __corrected(p):
    if p[0] >2.4:
        x_mltp = -1
    elif p[0] < -2.4:
        x_mltp = 1
    else:
        x_mltp = 0
    if p[1] < 4.8:
        y_mltp = 0
    else:
        y_mltp = -1
    return p[0]+x_mltp*X_OFFSET, p[1] + y_mltp*Y_OFFSET


try:
    __set_output_angle(math.pi / 2, 'l')
    __set_output_angle(math.pi / 2, 'r')
    time.sleep(1)
    alpha, beta = __alpha_beta(p0, s_l, s_r, a, b)
    __set_output_angle(alpha, 'l')
    __set_output_angle(beta, 'r')
    time.sleep(1)
    alpha, beta = __alpha_beta(__corrected(p1), s_l, s_r, a, b)
    __set_output_angle(alpha, 'l')
    __set_output_angle(beta, 'r')
    time.sleep(1)
finally:
    lgpio.tx_pwm(h, SERVO1_PIN, 0, 0)
    lgpio.tx_pwm(h, SERVO2_PIN, 0, 0)
    lgpio.gpiochip_close(h)
