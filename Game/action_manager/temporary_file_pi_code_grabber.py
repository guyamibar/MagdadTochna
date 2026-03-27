import lgpio as lg
import time

CHIP = 0
PIN = 12

h = lg.gpiochip_open(CHIP)
lg.gpio_claim_output(h, PIN)

# ==== YOUR REAL NEUTRAL ====
NEUTRAL = 7.16

# choose symmetric speeds around neutral
DUTY_FWD  = NEUTRAL + 2   # example = 9.265%
DUTY_BACK = NEUTRAL - 2  # example = 5.265%

L_FWD  = 6.8   # cm moved in 1 sec forward (example)
L_BACK = 5   # cm moved in 1 sec backward (example)

V_FWD  = L_FWD
V_BACK = L_BACK

def __set_speed(duty):
    lg.tx_pwm(h, PIN, 50, duty)

def __stop():
    __set_speed(NEUTRAL)

def __move_distance(dist_cm):
    if dist_cm == 0:
        return

    if dist_cm > 0:
        # forward
        t = dist_cm / V_FWD
        __set_speed(DUTY_FWD)
        time.sleep(t)
    else:
        # backward
        t = (-dist_cm) / V_BACK
        __set_speed(DUTY_BACK)
        time.sleep(t)
    __stop()

# Test
__move_distance(5.3)    # forward 5 cm
time.sleep(1)
__move_distance(-2)   # backward 5 cm
time.sleep(20)
__move_distance(-4)   # backward 5 cm


__stop()
lg.gpiochip_close(h)