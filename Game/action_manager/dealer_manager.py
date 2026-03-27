from typing import *


class Platform:
    """
    this class is for dealing with the rotating platform the dealer sits on
    """

    def __init__(self, pin_num: int):
        self.pin_num = pin_num

    def turn(self, degrees: int):
        """
        will make the platform turn {degrees} degrees
        :param degrees:
        :return:
        """
        pass


class Thrower:
    """
    this class is for dealing with the card thrower
    """

    def __init__(self, pin_num: int):
        self.pin_num = pin_num

    def spin(self):
        """
        will make the card thrower spin. 0 for backwards, 1 for forwards
        :return:
        """
        pass


class Separator:
    def __init__(self, pin_num: int):
        self.pin_num = pin_num

    def separate(self):
        """
        separates the top card from the dealer's stack
        :return:
        """
        pass


class Dealer_Manager:
    """
    the mechanical manager for the dealer.
    assumes there is a class Player with position attribute based on angle from itself.
    assumes there is a class Dealer of the game attributes of the dealer
    with an attribute of the number of cards on the dealer's main stack.
    """
    def __init__(self, platform_pin: int, thrower_pin: int, seperator_pin: int):
        self.platform = Platform(platform_pin)
        self.thrower = Thrower(thrower_pin)
        self.seperator = Separator(seperator_pin)

    def give_card(self, player: Player):
        self.platform.turn(player.angle)
        self.seperator.separate()
        self.thrower.spin()

    def deal(self, players: List[Player], num_of_cards: int, dealer_stack_size: int):
        """
        deals the cards from the dealer's stack
        :param players:
        :param num_of_cards:
        :return: number of cards left in the dealer's stack
        """
        def inner_give_loop(players):
            for player in players:
                self.give_card(player)
        if num_of_cards > 0:
            while stack_size > 0:
                inner_give_loop(players)
                stack_size -= 1
        else:
            for i in range(num_of_cards):
                inner_give_loop(players)
        return stack_size - len(players)*num_of_cards if num_of_cards > 0 else 0