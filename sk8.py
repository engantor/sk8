# SK8 - v7.1 (Logging, Late Shuvits & New Cards Update)

import random
import os
import time
import logging
from pathlib import Path
from collections import Counter
from itertools import combinations

# --- Game Data & Configuration ---

# A dictionary holding the original, unmodified difficulty values for every trick.
BASE_DIFFICULTIES = {
    'ollie': 2, 'kickflip': 3, 'heelflip': 4, 'treflip': 5,
    'varial_kickflip': 4, 'varial_heelflip': 4, 'hardflip': 5, 'inward_heelflip': 5,
    'bs_180': 2, 'fs_180': 3, 'bs_360': 3, 'fs_360': 4, 'fifty_fifty': 3,
    'five_o': 4, 'boardslide': 3, 'lipslide': 6, 'noseslide': 4, 'tailslide': 5,
    'nose_grind': 5, 'crooked_grind': 6, 'feeble_grind': 6, 'salad_grind': 6,
    'willy_grind': 5, 'blunt_slide': 6, 'tall_ledge': 3, 'hubba': 4, 'flat_bar': 3,
    'round_rail': 4, 'down_rail': 4, 'kicker_ramp': 2, '3_stair': 3, '5_stair': 3,
    'pop_shuvit': 2, 'fs_pop_shuvit': 3, 'bs_pop_shuvit': 3,
    # New 360 Shuvits, replacing the generic one.
    'bs_360_pop_shuvit': 4, 'fs_360_pop_shuvit': 5,
}
# Card Categories
FLIP_TRICKS = {'kickflip', 'heelflip', 'treflip', 'varial_kickflip', 'varial_heelflip', 'hardflip', 'inward_heelflip'}
SHUVIT_TRICKS = {'pop_shuvit', 'fs_pop_shuvit', 'bs_pop_shuvit', 'bs_360_pop_shuvit', 'fs_360_pop_shuvit'}
STANCES = {'nollie': 3, 'fakie': 2, 'switch': 2}
SPIN_TRICKS = {'bs_180', 'fs_180', 'bs_360', 'fs_360'}
GRINDS_SLIDES = {'fifty_fifty', 'five_o', 'boardslide', 'lipslide', 'noseslide', 'tailslide', 'nose_grind', 'crooked_grind', 'feeble_grind', 'salad_grind', 'willy_grind', 'blunt_slide'}
OBSTACLES = {'tall_ledge', 'hubba', 'flat_bar', 'round_rail', 'down_rail', 'kicker_ramp', '3_stair', '5_stair'}
STAIRS = {'3_stair', '5_stair'}
GRIND_SURFACES = {'tall_ledge', 'hubba', 'flat_bar', 'round_rail', 'down_rail'}

# Core Trick Set (for validation)
CORE_TRICKS = FLIP_TRICKS | SHUVIT_TRICKS | GRINDS_SLIDES | SPIN_TRICKS | {'ollie'}

# The main database of tricks used by the game
TRICKS_DATABASE = {k: max(1, (v - 1)) if k in FLIP_TRICKS else v for k, v in BASE_DIFFICULTIES.items()}
SPECIAL_CARDS = {
    'wax': {'description': 'Play with a Grind/Slide combo to reduce its difficulty by 2.'},
    'thrasher_magazine': {'description': 'Shuffle your hand (except Ollie) and draw 7 new cards.'},
    'focus': {'description': 'If you fail to match a trick, play this to re-roll your dice once.'},
    'pro_model_deck': {'description': 'Play this card to ignore your skater\'s negative ability for this turn.'},
    'sponsors': {'description': 'Draw 2 cards. You must use them this turn or they are discarded.'},
    'bail': {'description': 'Force an opponent to re-roll a successful trick-setting roll.'}
}
ALL_CATEGORIES = {"Flips": FLIP_TRICKS, "Shuvits": SHUVIT_TRICKS, "Grinds": GRINDS_SLIDES, "Spins": SPIN_TRICKS, "Obstacles": OBSTACLES}

class Skater:
    """Represents a skater with their unique set of abilities."""
    def __init__(self, name, passive_desc, passive_ability, activated_desc, activated_ability, trade_desc, negative_desc, negative_ability):
        self.name, self.passive_desc, self.passive_ability, self.activated_desc, self.activated_ability, self.trade_desc, self.negative_desc, self.negative_ability = name, passive_desc, passive_ability, activated_desc, activated_ability, trade_desc, negative_desc, negative_ability

# Defines the different playable characters and their unique traits.
SKATERS = [
    Skater(name="Flip Pro", passive_desc="[PASSIVE] Flip Tricks are -1 difficulty.",
           passive_ability={'type': 'difficulty_modifier', 'category': FLIP_TRICKS, 'amount': -1},
           activated_desc="Use Main Ability (Discard 2 to find a Flip Trick)",
           activated_ability={'type': 'activated', 'action': 'search_deck', 'cost': 2, 'category': FLIP_TRICKS},
           trade_desc="Use Trade Ability (Discard 1 Flip Trick for another card type)",
           negative_desc="[-] Grind & Slide tricks are +1 difficulty.",
           negative_ability={'type': 'difficulty_modifier', 'category': GRINDS_SLIDES, 'amount': 1}),
    Skater(name="Grind Specialist", passive_desc="[PASSIVE] Grind & Slide tricks are -1 difficulty.",
           passive_ability={'type': 'difficulty_modifier', 'category': GRINDS_SLIDES, 'amount': -1},
           activated_desc="Use Main Ability (Discard 2 to find a Grind/Slide)",
           activated_ability={'type': 'activated', 'action': 'search_deck', 'cost': 2, 'category': GRINDS_SLIDES},
           trade_desc="Use Trade Ability (Discard 1 Grind/Slide for another card type)",
           negative_desc="[-] Flip tricks are +1 difficulty.",
           negative_ability={'type': 'difficulty_modifier', 'category': FLIP_TRICKS, 'amount': 1}),
    Skater(name="Spot Finder", passive_desc="[PASSIVE] Obstacle cards are -1 difficulty.",
           passive_ability={'type': 'difficulty_modifier', 'category': OBSTACLES, 'amount': -1},
           activated_desc="Use Main Ability (Discard 2 to find an Obstacle)",
           activated_ability={'type': 'activated', 'action': 'search_deck', 'cost': 2, 'category': OBSTACLES},
           trade_desc="Use Trade Ability (Discard 1 Obstacle for another card type)",
           negative_desc="[-] Spin tricks are +1 difficulty.",
           negative_ability={'type': 'difficulty_modifier', 'category': SPIN_TRICKS, 'amount': 1}),
]
# Game constants
LETTERS, STARTING_HAND_SIZE, MAX_LETTERS = "SK8", 8, len("SK8")

def setup_logging():
    """Configures logging to a file named sk8.log in the script's directory."""
    try:
        script_dir = Path(__file__).parent.resolve()
        log_file = script_dir / 'sk8.log'
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s',
            filename=log_file,
            filemode='w'
        )
        print(f"Logging is active. Log file will be saved to: {log_file}")
        logging.info("--- SK8 Game Log Started ---")
        return True
    except Exception as e:
        print(f"Error setting up logging: {e}. Logging will be disabled.")
        return False

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def roll_dice(with_advantage=False):
    if with_advantage:
        rolls = sorted([random.randint(1, 8) for _ in range(3)])
        result = sum(rolls[1:])
        logging.debug(f"Rolling with advantage. Rolls: {rolls}. Dropped: {rolls[0]}. Result: {result}")
        print(f"(Rolled {rolls[0]}, {rolls[1]}, {rolls[2]} and dropped a {rolls[0]})")
        return result
    roll1 = random.randint(1, 8)
    roll2 = random.randint(1, 8)
    result = roll1 + roll2
    logging.debug(f"Standard roll. Rolls: [{roll1}, {roll2}]. Result: {result}")
    return result

def get_combo_display_name_single(card, count):
    if count <= 1: return card.replace('_', ' ').title()
    prefixes = {2: "Double", 3: "Triple", 4: "Quad"}
    return f"{prefixes.get(count, f'{count}x')} {card.replace('_', ' ').title()}"

def get_combo_display_name(combo):
    """Generates a full display name for a trick combo, handling special cases like Late Flips based on order."""
    if not any(c in TRICKS_DATABASE or c in STANCES for c in combo):
        return "a basic move"
    combo_worklist = list(combo)
    display_parts = []
    
    # 1. Stanced Late Flip / Stanced Late Shuvit
    if len(combo_worklist) >= 3 and combo_worklist[0] in STANCES and combo_worklist[1] == 'ollie':
        stance, next_trick = combo_worklist[0], combo_worklist[2]
        late_type = None
        if next_trick in FLIP_TRICKS: late_type = "Flip"
        elif next_trick in SHUVIT_TRICKS: late_type = "Shuvit"
        
        if late_type:
            display_parts.append(f"{stance.title()} Late {next_trick.replace('_', ' ').title()}")
            combo_worklist.pop(0); combo_worklist.pop(0); combo_worklist.pop(0)

    # 2. Stance + Any Trick (if not a late trick)
    if len(combo_worklist) >= 2 and combo_worklist[0] in STANCES and combo_worklist[1] in CORE_TRICKS:
        stance, trick = combo_worklist[0], combo_worklist[1]
        display_parts.append(f"{stance.title()} {trick.replace('_', ' ').title()}")
        combo_worklist.pop(0); combo_worklist.pop(0)

    # 3. Late Flips and Late Shuvits
    i = 0
    while i < len(combo_worklist) - 1:
        if combo_worklist[i] == 'ollie' and (combo_worklist[i + 1] in FLIP_TRICKS or combo_worklist[i+1] in SHUVIT_TRICKS):
            late_trick = combo_worklist[i + 1]
            display_parts.append(f"Late {late_trick.replace('_', ' ').title()}")
            combo_worklist[i] = None; combo_worklist[i + 1] = None
            i += 2
        else:
            i += 1
    combo_worklist = [c for c in combo_worklist if c is not None]

    # 4. Handle remaining cards
    if combo_worklist:
        combo_counts = Counter(combo_worklist)
        for card in sorted(combo_counts.keys()):
            if card in SPECIAL_CARDS or card in STANCES: continue
            if card in TRICKS_DATABASE:
                display_parts.append(get_combo_display_name_single(card, combo_counts[card]))

    return ' + '.join(display_parts) if display_parts else "a basic move"

def create_themed_deck(skater: Skater):
    base_deck = ['bs_180', 'fs_180', 'pop_shuvit', 'wax', 'thrasher_magazine', 'thrasher_magazine', 'focus', 'pro_model_deck', 'sponsors', 'sponsors', 'bail', 'fakie', 'nollie', 'switch']
    specialty_packs = {
        "Flip Pro": ['kickflip']*3 + ['heelflip']*2 + ['treflip', 'varial_kickflip', 'hardflip', 'inward_heelflip'] + ['tall_ledge', '3_stair'] + ['focus', 'sponsors'],
        "Grind Specialist": ['fifty_fifty']*2 + ['boardslide']*2 + ['lipslide', 'crooked_grind', 'salad_grind', 'willy_grind'] + ['tall_ledge']*2 + ['flat_bar', 'down_rail', 'hubba'] + ['wax', 'wax', 'bail'],
        "Spot Finder": ['tall_ledge']*2 + ['flat_bar']*2 + ['round_rail', 'down_rail', 'hubba', '3_stair']*2 + ['5_stair', 'kicker_ramp'] + ['kickflip', 'boardslide'] + ['thrasher_magazine', 'bail'],
    }
    final_deck = base_deck + specialty_packs.get(skater.name, [])
    num_to_add = 38 - len(final_deck)
    if num_to_add > 0:
        deck_pool = [k for k in TRICKS_DATABASE.keys()] + list(STANCES.keys())
        final_deck.extend(random.sample(deck_pool, num_to_add))
    random.shuffle(final_deck)
    return final_deck

class Player:
    def __init__(self, name, is_ai=False):
        self.name, self.letters, self.skater, self.deck, self.discard_pile = name, "", None, [], []
        self.is_ai = is_ai
        self.hand = ['ollie']
        self.temporary_cards = []
    
    def draw_card(self, num_cards=1):
        drawn_cards = []
        for _ in range(num_cards):
            if not self.deck and self.discard_pile:
                logging.info(f"{self.name}'s deck is empty. Reshuffling {len(self.discard_pile)} cards.")
                print(f"\n{self.name}'s deck is empty! Reshuffling discard pile...")
                self.deck = self.discard_pile[:]; self.discard_pile = []
                random.shuffle(self.deck)
                time.sleep(1.5)
            if self.deck:
                card = self.deck.pop()
                self.hand.append(card)
                drawn_cards.append(card)
        logging.debug(f"{self.name} drew: {drawn_cards}")
        return drawn_cards

    def discard_cards(self, cards_to_discard):
        actual_discards = [c for c in cards_to_discard if c != 'ollie']
        for card in actual_discards:
            if card in self.hand:
                self.hand.remove(card)
                self.discard_pile.append(card)
                if card in self.temporary_cards:
                    self.temporary_cards.remove(card)
        if actual_discards: logging.debug(f"{self.name} discarded: {actual_discards}")
    
    def has_any_cards_for_trick(self, trick_combo):
        return any(card in self.hand for card in trick_combo)

    def has_all_cards_for_trick(self, trick_combo):
        return all(self.hand.count(card) >= Counter(trick_combo).get(card, 0) for card in set(trick_combo))

class SkateGame:
    def __init__(self, game_mode):
        self.players = [Player("You")]
        if game_mode == 'pve': self.players.append(Player("Rival AI", is_ai=True))
        else: self.players.append(Player("Player 2"))
        self.game_over, self.setter_index = False, 0
        self.trick_to_match, self.difficulty_to_beat = None, 0
        self.last_turn_summary = ""

    def run(self):
        self.setup_game()
        while not self.game_over:
            if self.trick_to_match: self.matcher_turn()
            else: self.setter_turn()
            for player in self.players:
                if len(player.letters) >= MAX_LETTERS:
                    self.game_over = True
                    winner = self.players[1 - self.players.index(player)]
                    logging.info(f"GAME OVER! {player.name} got S-K-8. Winner: {winner.name}")
                    clear_screen(); print(f"\nGAME OVER! {player.name} got S-K-8!\n{winner.name} wins the game!"); break

    def setup_game(self):
        clear_screen(); print("Welcome to SK8 - v1.0"); time.sleep(1)
        self.skater_selection()
        for player in self.players:
            player.deck = create_themed_deck(player.skater)
            logging.info(f"{player.name} (as {player.skater.name}) created a deck with {len(player.deck)} cards.")
        self.deal_cards()
        clear_screen(); print("Skaters are locked in!")
        for player in self.players: print(f"- {player.name} {'are' if player.name == 'You' else 'is'} the {player.skater.name}")
        input("\nPress Enter to start...");

    def skater_selection(self):
        available_skaters = list(SKATERS)
        for player in self.players:
            if player.is_ai:
                chosen_skater = random.choice(available_skaters)
                player.skater = chosen_skater
                available_skaters.remove(chosen_skater)
                logging.info(f"AI player {player.name} randomly selected {chosen_skater.name}")
                print(f"{player.name} has chosen the {player.skater.name}!"); time.sleep(1.5); continue
            clear_screen(); print(f"\n{player.name}, choose your skater:")
            for i, skater in enumerate(available_skaters): print(f"  {i+1}: {skater.name}\n     {skater.passive_desc}\n     {skater.activated_desc}\n     {skater.trade_desc}\n     {skater.negative_desc}")
            while True:
                try:
                    choice_str = input("> ")
                    if not choice_str: continue
                    choice = int(choice_str)
                    if 1 <= choice <= len(available_skaters):
                        chosen_skater = available_skaters.pop(choice - 1)
                        player.skater = chosen_skater
                        logging.info(f"Human player {player.name} chose {chosen_skater.name}")
                        break
                except (ValueError, IndexError): print("Invalid input.")

    def deal_cards(self):
        for _ in range(STARTING_HAND_SIZE - 1):
            for player in self.players: player.draw_card()
            
    def display_status(self):
        clear_screen()
        if self.last_turn_summary: print(f"Last Turn: {self.last_turn_summary}\n")
        for p in self.players: print(f"{p.name} ({p.skater.name}, {len(p.deck)} cards left): {p.letters or '(-)'}")
        print("-" * 30)
        
    def calculate_combo_difficulty(self, combo, player, ignore_negative_ability=False):
        total_difficulty, explanation = 0, []
        combo_worklist = list(combo)
    
        late_bonus = 0
        late_trick_type = ""
        # Check for stanced and regular late tricks
        if len(combo_worklist) >= 3 and combo_worklist[0] in STANCES and combo_worklist[1] == 'ollie' and (combo_worklist[2] in FLIP_TRICKS or combo_worklist[2] in SHUVIT_TRICKS):
            trick = combo_worklist[2]
            late_bonus = TRICKS_DATABASE.get(trick, 0)
            late_trick_type = "Flip" if trick in FLIP_TRICKS else "Shuvit"
        elif len(combo_worklist) >= 2 and combo_worklist[0] == 'ollie' and (combo_worklist[1] in FLIP_TRICKS or combo_worklist[1] in SHUVIT_TRICKS):
            trick = combo_worklist[1]
            late_bonus = TRICKS_DATABASE.get(trick, 0)
            late_trick_type = "Flip" if trick in FLIP_TRICKS else "Shuvit"

        if late_bonus > 0:
            total_difficulty += late_bonus
            explanation.append(f"  - Late {late_trick_type} Bonus (x2 {trick.replace('_',' ').title()}): +{late_bonus}")
        
        card_counts = Counter(combo_worklist)
        stance = next((c for c in combo_worklist if c in STANCES), None)
        
        if stance:
            total_difficulty += STANCES[stance]
            explanation.append(f"  - {stance.title()} Stance: +{STANCES[stance]}")
            
        if any(c in GRINDS_SLIDES for c in combo_worklist) and not any(c in GRIND_SURFACES for c in combo_worklist):
            total_difficulty += 2; explanation.append("  - Flatground Grind (Low Ledge): +2")
            
        for card, count in card_counts.items():
            if card not in TRICKS_DATABASE: continue
            base_difficulty, current_mods, mod_explanation = TRICKS_DATABASE[card], 0, []
            if (card in STAIRS or card in FLIP_TRICKS) and count > 1:
                bonus = sum(range(2, count + 1)); current_mods += bonus; mod_explanation.append(f"Duplicate: +{bonus}")
            passive = player.skater.passive_ability
            if passive['type'] == 'difficulty_modifier' and card in passive['category']:
                current_mods += passive['amount']; mod_explanation.append(f"Passive: {passive['amount']}")
            if not ignore_negative_ability:
                neg = player.skater.negative_ability
                if neg['type'] == 'difficulty_modifier' and card in neg['category']:
                    current_mods += neg['amount']; mod_explanation.append(f"Negative: +{neg['amount']}")
            total_difficulty += (base_difficulty * count) + current_mods
            explanation.append(f"  - {get_combo_display_name_single(card, count)}: {base_difficulty}{' x' + str(count) if count > 1 else ''}{' (' + ', '.join(mod_explanation) + ')' if mod_explanation else ''}")
            
        if 'wax' in combo: total_difficulty -= 2; explanation.append("  - Wax Card: -2")
        return max(1, total_difficulty), explanation

    def validate_combo(self, combo):
        if not any(c in TRICKS_DATABASE or c in STANCES for c in combo):
            return False, "You must select at least one trick card."
        
        if any(c in OBSTACLES for c in combo):
            if not any(c in CORE_TRICKS for c in combo):
                return False, "You must perform a trick (like an Ollie, Flip, etc.) to use an Obstacle."

        stance_cards = [c for c in combo if c in STANCES]
        if len(stance_cards) > 1: return False, "Cannot use more than one Stance."
        if stance_cards and combo.index(stance_cards[0]) != 0: return False, "A Stance card must be played first."
        if stance_cards and len(combo) == 1: return False, "A stance card must modify a trick."
        if stance_cards and len(combo) > 1 and combo[1] not in CORE_TRICKS:
            return False, "A Stance must be followed by a valid trick card."
            
        if len(set(c for c in combo if c in STAIRS)) > 1: return False, "Cannot combine different stair sets."
        if sum(1 for c in combo if c in GRIND_SURFACES) > 1: return False, "Cannot use more than one grind surface."
        if 'kicker_ramp' in combo and any(c in STAIRS for c in combo): return False, "Cannot combine a kicker with stairs."
        if len(set(c for c in combo if c in GRINDS_SLIDES)) > 1: return False, "Can't do more than one type of grind."
        if 'wax' in combo and not any(c in GRINDS_SLIDES for c in combo): return False, "'Wax' only works with grinds or slides."
        if len(set(c for c in combo if c in SHUVIT_TRICKS)) > 1: return False, "Cannot combine more than one type of Shuvit."
        if any(c in FLIP_TRICKS for c in combo) and any(c in SHUVIT_TRICKS for c in combo):
            # This allows late flips and late shuvits (which contain an ollie), but not a flip card and shuvit card together
            if 'ollie' not in combo:
                return False, "Cannot combine a Flip and a Shuvit card. Use Varial Flips instead."

        return True, "Valid combo!"

    def switch_setter(self): self.setter_index = (self.setter_index + 1) % len(self.players)

    def end_of_turn_cleanup(self, player):
        if player.temporary_cards:
            unused_temp = [card for card in player.temporary_cards if card in player.hand]
            if unused_temp:
                logging.info(f"{player.name} is discarding unused temporary cards: {unused_temp}")
                print(f"\nDiscarding unused temporary cards: {', '.join(unused_temp)}")
                player.discard_cards(unused_temp); time.sleep(1.5)
            player.temporary_cards = []

    def setter_turn(self):
        setter = self.players[self.setter_index]
        logging.info(f"--- SETTER TURN START --- Player: {setter.name}")
        cards_to_draw = STARTING_HAND_SIZE - len(setter.hand)
        if cards_to_draw > 0:
            logging.debug(f"{setter.name} needs to draw {cards_to_draw} card(s).")
            setter.draw_card(cards_to_draw)
        logging.debug(f"{setter.name}'s current hand: {setter.hand}")
        if setter.is_ai: self.ai_setter_turn(setter)
        else: self.human_setter_turn(setter)
        self.end_of_turn_cleanup(setter)
        logging.info(f"--- SETTER TURN END --- Player: {setter.name}")

    def human_setter_turn(self, setter):
        while True:
            self.display_status()
            print(f"\nYour turn to set ({setter.skater.name}). Your input order matters!")
            for i, card in enumerate(setter.hand):
                if card in SPECIAL_CARDS: print(f"  {i+1}: {card.replace('_', ' ').title()} - ({SPECIAL_CARDS[card]['description']})")
                elif card in STANCES: print(f"  {i+1}: {card.replace('_', ' ').title()} (Stance)")
                else: print(f"  {i+1}: {card.replace('_', ' ').title()} (D: {TRICKS_DATABASE.get(card, 'N/A')})")
            print("-" * 30)
            
            action_choice = input("Enter card numbers to set a trick, or (a)bility > ").lower()
            logging.debug(f"{setter.name} entered raw input: '{action_choice}'")
            
            try:
                if action_choice == 'a':
                    logging.info(f"{setter.name} chose to use an ability.")
                    self.ability_menu(setter); return
                indices = [int(i) - 1 for i in action_choice.split()]
                combo = [setter.hand[i] for i in indices]

                if 'thrasher_magazine' in combo:
                    if len(combo) > 1: print("\nThrasher Magazine must be played by itself."); time.sleep(2); continue
                    logging.info(f"{setter.name} played Thrasher Magazine.")
                    print("\nShuffling your hand and drawing 7 new cards...");
                    hand_to_shuffle = [c for c in setter.hand if c != 'ollie']; setter.discard_cards(hand_to_shuffle + ['thrasher_magazine'])
                    setter.deck.extend(hand_to_shuffle); random.shuffle(setter.deck); setter.draw_card(num_cards=7); continue
                
                if 'sponsors' in combo:
                    if len(combo) > 1: print("\nSponsors must be played by itself."); time.sleep(2); continue
                    logging.info(f"{setter.name} played Sponsors.")
                    print("\nDrawing 2 temporary cards from your sponsors..."); setter.discard_cards(['sponsors']); 
                    new_cards = setter.draw_card(num_cards=2); setter.temporary_cards.extend(new_cards); continue
                
                is_valid, message = self.validate_combo(combo)
                if not is_valid:
                    logging.warning(f"Invalid combo attempted by {setter.name}: {combo}. Reason: {message}")
                    print(f"\nINVALID COMBO: {message}"); time.sleep(2); continue
                
                logging.info(f"{setter.name} is attempting combo: {combo}")
                self.trick_to_match = combo
                self.difficulty_to_beat, explanation = self.calculate_combo_difficulty(combo, setter, 'pro_model_deck' in combo)
                logging.info(f"Calculated difficulty: {self.difficulty_to_beat}. Explanation: {' '.join(explanation)}")

                clear_screen(); print("--- ATTEMPTING TRICK ---")
                print(f"Trick: {get_combo_display_name(self.trick_to_match)}\n\nDifficulty Calculation:")
                for line in explanation: print(line)
                print(f"\nFinal Difficulty: {self.difficulty_to_beat}")
                input(f"\nYou must roll a {self.difficulty_to_beat} or higher. Press Enter to roll..."); roll = roll_dice()
                print(f"You rolled a {roll}!")
                
                opponent = self.players[(self.setter_index + 1) % len(self.players)]
                if roll >= self.difficulty_to_beat and 'bail' in opponent.hand:
                    if opponent.is_ai or 'y' in input(f"{opponent.name} has a Bail card! Force a re-roll? (y/n) > ").lower():
                        logging.info(f"{opponent.name} played Bail, forcing a re-roll.")
                        print(f"\n{opponent.name} plays Bail! You have to re-roll..."); opponent.discard_cards(['bail']); time.sleep(1)
                        roll = roll_dice(); print(f"Your re-roll is... {roll}!")
                
                if roll >= self.difficulty_to_beat:
                    print("You landed it!")
                    logging.info(f"Trick SET successfully by {setter.name}. Roll: {roll} >= Difficulty: {self.difficulty_to_beat}")
                    self.last_turn_summary = f"{setter.name} landed a {get_combo_display_name(self.trick_to_match)}."
                    trick_cards = [c for c in self.trick_to_match if c in TRICKS_DATABASE or c in STANCES or c in OBSTACLES]
                    specials = [c for c in self.trick_to_match if c in SPECIAL_CARDS]
                    discards = specials
                    if any(c != 'ollie' for c in trick_cards):
                        random_trick = random.choice([c for c in trick_cards if c != 'ollie'])
                        discards.append(random_trick)
                        print(f"Cost: discard 1 random trick: {random_trick.replace('_', ' ').title()}")
                    setter.discard_cards(discards)
                else:
                    print("Bailed! You lose the cards.")
                    logging.info(f"Trick SET FAILED by {setter.name}. Roll: {roll} < Difficulty: {self.difficulty_to_beat}")
                    self.last_turn_summary = f"{setter.name} bailed their set."
                    setter.discard_cards(self.trick_to_match); self.trick_to_match = None; self.switch_setter()
                time.sleep(3); break
            except (ValueError, IndexError): print("\nInvalid input."); time.sleep(2)

    def ai_setter_turn(self, ai_player):
        self.display_status(); print(f"\n--- {ai_player.name}'s Turn ---"); time.sleep(1.5)
        best_combo, best_difficulty = [], -1
        for i in range(1, min(len(ai_player.hand), 4)):
            for combo in combinations([c for c in ai_player.hand if c != 'ollie'], i):
                combo_list = list(combo)
                if self.validate_combo(combo_list)[0]:
                    difficulty, _ = self.calculate_combo_difficulty(combo_list, ai_player)
                    specialty_score = sum(1 for c in combo_list if c in ai_player.skater.passive_ability['category'])
                    score = difficulty + specialty_score * 2
                    if score > best_difficulty and difficulty < 14: best_difficulty = score; best_combo = combo_list
        if not best_combo:
            logging.info(f"AI {ai_player.name} could not find a suitable combo and passed the turn.")
            print(f"{ai_player.name} has no good combos, passing turn."); self.switch_setter(); time.sleep(2); return
        self.trick_to_match = best_combo
        self.difficulty_to_beat, _ = self.calculate_combo_difficulty(best_combo, ai_player)
        logging.info(f"AI {ai_player.name} is attempting combo: {best_combo} with difficulty {self.difficulty_to_beat}")
        print(f"{ai_player.name} is setting a {get_combo_display_name(self.trick_to_match)} (Difficulty: {self.difficulty_to_beat}).")
        time.sleep(3); print(f"\n{ai_player.name} is rolling..."); roll = roll_dice(); print(f"They rolled a {roll}!"); time.sleep(2)
        if roll >= self.difficulty_to_beat:
            print("They landed it! The trick is set.")
            logging.info(f"AI trick SET successfully. Roll: {roll} >= Difficulty: {self.difficulty_to_beat}")
            self.last_turn_summary = f"{ai_player.name} landed a {get_combo_display_name(self.trick_to_match)}."
            trick_cards = [c for c in self.trick_to_match if (c in TRICKS_DATABASE or c in STANCES) and c != 'ollie']
            specials = [c for c in self.trick_to_match if c in SPECIAL_CARDS]
            discards = specials
            if trick_cards: discards.append(random.choice(trick_cards))
            ai_player.discard_cards(discards)
        else:
            print("They bailed! The turn passes.")
            logging.info(f"AI trick SET FAILED. Roll: {roll} < Difficulty: {self.difficulty_to_beat}")
            self.last_turn_summary = f"{ai_player.name} bailed their set."
            ai_player.discard_cards(self.trick_to_match); self.trick_to_match = None; self.switch_setter()
        time.sleep(3)

    def matcher_turn(self):
        matcher = self.players[(self.setter_index + 1) % len(self.players)]
        logging.info(f"--- MATCHER TURN START --- Player: {matcher.name}")
        logging.info(f"Trick to match: {self.trick_to_match}")
        if matcher.is_ai: self.ai_matcher_turn(matcher)
        else: self.human_matcher_turn(matcher)
        self.end_of_turn_cleanup(matcher)
        logging.info(f"--- MATCHER TURN END --- Player: {matcher.name}")

    def human_matcher_turn(self, matcher):
        self.display_status(); print(f"\n--- Your Turn to Match ---")
        print(f"You need to match: {get_combo_display_name(self.trick_to_match)}"); time.sleep(1)
        ignore_neg = False
        if 'pro_model_deck' in matcher.hand and 'y' in input("Use 'Pro Model Deck'? (y/n) > ").lower():
            logging.info(f"{matcher.name} used Pro Model Deck."); ignore_neg = True
            matcher.discard_cards(['pro_model_deck'])
        base_difficulty, explanation = self.calculate_combo_difficulty(self.trick_to_match, matcher, ignore_neg)
        trick_only_combo = [c for c in self.trick_to_match if c in TRICKS_DATABASE or c in STANCES]
        print("\nDifficulty Calculation:"); [print(line) for line in explanation]
        if not matcher.has_all_cards_for_trick(trick_only_combo):
            difficulty = base_difficulty + 2; print("  - Defender Penalty (No cards): +2")
            logging.info(f"Applying defender penalty, final difficulty: {difficulty}")
        else:
            difficulty = base_difficulty; print("  - No Defender Penalty (You have all cards!)")
            logging.info(f"No defender penalty, final difficulty: {difficulty}")
        print(f"Your Final Target: {difficulty}")
        use_advantage = False
        if matcher.has_any_cards_for_trick(trick_only_combo):
            print("You have a required card! You can spend one to roll with ADVANTAGE.")
            if 'y' in input("Spend a card for advantage? (y/n) > ").lower():
                 use_advantage = True; logging.info(f"{matcher.name} is spending a card to roll with advantage.")
        input("Press Enter to roll..."); roll = roll_dice(with_advantage=use_advantage); print(f"You rolled a {roll}!")
        if roll < difficulty and 'focus' in matcher.hand and 'y' in input("Failed. Use 'Focus' to re-roll? (y/n) > ").lower():
            logging.info(f"{matcher.name} used Focus for a re-roll.")
            matcher.discard_cards(['focus']); roll = roll_dice(with_advantage=use_advantage); print(f"New roll: {roll}!")
        if roll < difficulty and len(matcher.letters) == MAX_LETTERS - 1:
            print("\nYou're on your last letter! You get one more chance to land this.")
            logging.info(f"{matcher.name} is on K and gets a last chance re-roll.")
            input("Press Enter for your last chance roll...")
            roll = roll_dice(with_advantage=use_advantage); print(f"Last chance roll... a {roll}!")
        time.sleep(2)
        if roll >= difficulty:
            print("Nice! You landed it.")
            logging.info(f"{matcher.name} MATCHED the trick. Roll: {roll} >= Difficulty: {difficulty}")
            self.last_turn_summary = f"{matcher.name} matched the trick."; self.switch_setter()
        else:
            print("Ah, you missed it! You get a letter.")
            logging.warning(f"{matcher.name} FAILED to match the trick. Roll: {roll} < Difficulty: {difficulty}. They get a letter.")
            matcher.letters += LETTERS[len(matcher.letters)]
            self.last_turn_summary = f"{matcher.name} bailed and got a letter."
        self.trick_to_match = None; time.sleep(3)
    
    def ai_matcher_turn(self, ai_player):
        self.display_status(); print(f"\n--- {ai_player.name}'s Turn to Match ---")
        print(f"They need to match: {get_combo_display_name(self.trick_to_match)}"); time.sleep(2)
        difficulty, _ = self.calculate_combo_difficulty(self.trick_to_match, ai_player)
        if not ai_player.has_all_cards_for_trick(self.trick_to_match): difficulty += 2
        logging.info(f"AI {ai_player.name}'s final target difficulty is {difficulty}")
        print(f"Final Target: {difficulty}"); time.sleep(2)
        use_advantage = ai_player.has_any_cards_for_trick(self.trick_to_match) and difficulty > 7
        if use_advantage:
            card_to_spend = next((c for c in ai_player.hand if c in self.trick_to_match), None)
            if card_to_spend:
                ai_player.discard_cards([card_to_spend])
                logging.info(f"AI {ai_player.name} spends a {card_to_spend} for advantage!")
                print(f"{ai_player.name} spends a {card_to_spend} for advantage!")
        roll = roll_dice(with_advantage=use_advantage); print(f"\n{ai_player.name} rolls a {roll}!")
        if roll < difficulty and 'focus' in ai_player.hand and difficulty > 8:
            ai_player.discard_cards(['focus']); logging.info(f"AI {ai_player.name} uses Focus to re-roll!")
            print(f"{ai_player.name} uses Focus to re-roll!")
            roll = roll_dice(with_advantage=use_advantage); print(f"New roll: {roll}!")
        if roll < difficulty and len(ai_player.letters) == MAX_LETTERS - 1:
            print(f"\n{ai_player.name} is on K and gets a last chance re-roll!")
            logging.info(f"AI {ai_player.name} is on K and gets a last chance re-roll.")
            time.sleep(2); roll = roll_dice(with_advantage=use_advantage); print(f"Last chance roll... a {roll}!")
        time.sleep(2)
        if roll >= difficulty:
            print("They landed it!"); logging.info(f"AI {ai_player.name} MATCHED the trick. Roll: {roll} >= Difficulty: {difficulty}")
            self.last_turn_summary = f"{ai_player.name} matched the trick."; self.switch_setter()
        else:
            print("They bailed! They get a letter."); logging.warning(f"AI {ai_player.name} FAILED to match. Roll: {roll} < Difficulty: {difficulty}. They get a letter.")
            ai_player.letters += LETTERS[len(ai_player.letters)]; self.last_turn_summary = f"{ai_player.name} bailed and got a letter."
        self.trick_to_match = None; time.sleep(3)
        
    def ability_menu(self, player):
        print(f"\n--- ABILITY MENU ---")
        print(f"1: {player.skater.activated_desc}"); print(f"2: {player.skater.trade_desc}"); print("3: Cancel")
        choice = input("> ")
        if choice == '1': self.activate_skater_ability(player)
        elif choice == '2': self.activate_trade_ability(player)
        else: return
        
    def activate_skater_ability(self, player):
        ability = player.skater.activated_ability
        if len([c for c in player.hand if c != 'ollie']) < ability['cost']: print(f"\nNeed at least {ability['cost']} discardable cards."); time.sleep(2); return
        search_category = ability['category']
        category_name = next((k for k, v in ALL_CATEGORIES.items() if v == search_category), "Unknown").replace('_', ' ').title()
        self.display_status(); print(f"\nChoose {ability['cost']} cards to discard to search for a {category_name} card.")
        discardable_hand = [c for c in player.hand if c != 'ollie']
        for i, card in enumerate(discardable_hand): print(f"  {i+1}: {card.replace('_', ' ').title()}")
        try:
            indices = sorted([int(i) - 1 for i in input("> ").split()], reverse=True)
            if len(indices) != ability['cost']: print(f"Must choose exactly {ability['cost']} cards."); time.sleep(2); return
            cards_to_discard = [discardable_hand[i] for i in indices]
            player.discard_cards(cards_to_discard)
            available_cards = [card for card in player.deck if card in search_category]
            if not available_cards: print(f"\nNo {category_name} cards left in your deck!"); self.switch_setter(); time.sleep(3); return
            print(f"\nFound these {category_name} cards. Choose one:"); [print(f"  {i+1}: {card.replace('_', ' ').title()}") for i, card in enumerate(available_cards)]
            while True:
                try:
                    choice = int(input("> "))
                    if 1 <= choice <= len(available_cards):
                        chosen_card = available_cards[choice-1]
                        player.deck.remove(chosen_card); player.hand.append(chosen_card); random.shuffle(player.deck)
                        logging.info(f"{player.name} used their main ability, discarding {cards_to_discard} to find {chosen_card}.")
                        print(f"\nYou took '{chosen_card.replace('_', ' ').title()}' and added it to your hand."); break
                except (ValueError, IndexError): print("Invalid input.")
            self.switch_setter(); time.sleep(3)
        except (ValueError, IndexError): print("\nInvalid input."); time.sleep(2)

    def activate_trade_ability(self, player):
        print("\n--- TRADE ABILITY ---")
        expertise_category = player.skater.activated_ability['category']
        expertise_name = next((k for k, v in ALL_CATEGORIES.items() if v == expertise_category), "Unknown").replace('_', ' ').title()
        cards_to_trade = [card for card in player.hand if card in expertise_category]
        if not cards_to_trade: print(f"You don't have any {expertise_name} cards to trade!"); time.sleep(2); return
        self.display_status(); print(f"Choose one of your {expertise_name} cards to discard:")
        for i, card in enumerate(cards_to_trade): print(f"  {i+1}: {card.replace('_', ' ').title()}")
        try:
            choice = int(input("> "))
            card_to_discard = cards_to_trade[choice - 1]
        except (ValueError, IndexError): print("Invalid selection."); time.sleep(2); return
        print("\nWhat type of card do you want to find?")
        other_categories = {k:v for k,v in ALL_CATEGORIES.items() if v != expertise_category}
        valid_trade_options = {}
        for i, (cat_name, cat_set) in enumerate(other_categories.items()):
            count = sum(1 for card in player.deck if card in cat_set)
            print(f"  {i+1}: {cat_name} ({count} available)")
            if count > 0: valid_trade_options[i+1] = (cat_name, cat_set)
        try:
            choice = int(input("> "))
            if choice not in valid_trade_options: print("Invalid selection or no cards available in that category."); time.sleep(2); return
            target_category_name, target_category = valid_trade_options[choice]
            available_cards = [card for card in player.deck if card in target_category]
            found_card = random.choice(available_cards)
            player.discard_cards([card_to_discard]); player.deck.remove(found_card); player.hand.append(found_card); random.shuffle(player.deck)
            logging.info(f"{player.name} used their trade ability, trading {card_to_discard} to find {found_card}.")
            print(f"You traded '{card_to_discard.replace('_',' ').title()}' and drew a '{found_card.replace('_',' ').title()}'!")
        except(ValueError, IndexError): print("Invalid selection."); time.sleep(2); return
        self.switch_setter(); time.sleep(3)

if __name__ == "__main__":
    if setup_logging():
        clear_screen()
        print("Welcome to SK8 - v0.7.1")
        game = SkateGame('pve')
        game.run()
