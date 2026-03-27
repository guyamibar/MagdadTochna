from game_env import Deck, utility, hand_value
from bj_player import Agent
from make_the_magic import take_a_pic


def dealer_play(agent,num_of_cards, dealer_card,dealer_num=2):
    dealer_card , my_cards = take_a_pic(num_of_cards,2, agent)
    while hand_value(dealer_card) <17:
        dealer_num+=1
        print("dealer: hit me")
        input("i am waiting")
        dealer_card, my_cards = take_a_pic(num_of_cards,dealer_num , agent)
        print(dealer_card)
    if hand_value(dealer_card)<=21:
        print("i stand")
    else:
        print("i busted")
        print((hand_value(dealer_card)))
    return dealer_card, my_cards



def play_round(agent, deck,num_of_cards):

    units = agent.allocate_units()
    print(f"i bet {units} dollars")
    input("deal the cards")
    # Environment + dealer upcard
    dealer_card , my_cards = take_a_pic(num_of_cards,1, agent)
    print("dealer " )
    print(dealer_card)
    print("mine " )
    print(my_cards)
    # Allocate units (abstract weight)

    # 5. Agent’s hit/stand loop
    while True:
        print("its my turn")
        action = agent.decide_action(my_cards, deck, dealer_card)
        if action == "stand":
            break

        input("hit me")
        num_of_cards+=1
        _, my_cards = take_a_pic(num_of_cards,1, agent)

        if hand_value(my_cards) > 21:
            print("i lost")
            break

    # 6. Dealer finishes hand
    print("open my second card")
    input("is it open?")
    dealer_hand,my_cards = dealer_play(agent,num_of_cards, dealer_card)
    # 7. Compute abstract result & update resources
    print(dealer_hand)
    print(my_cards)
    result = utility(my_cards, dealer_hand)   # -1 / 0 / +1
    agent.resources += result * units     # scale by units

    return "played"


def main():
    deck = Deck()
    agent = Agent()

    num_rounds = 1000
    for round_idx in range(num_rounds):
        # Shuffle when deck low, reset count (new shoe)
        num_of_cards = 2
        if deck.size() < 20:
            deck = Deck()
            agent.running_count = 0

        outcome = play_round(agent, deck,num_of_cards)

        # Only print when we actually played, to avoid spam
        if outcome == "played":
            print(f"Round {round_idx+1:04d}: {outcome}, "
                  f"count={agent.running_count}, "
                  f"resources={agent.resources:.2f}")


if __name__ == "__main__":
    main()
