# SK8 (v0.6)

Yo! This is SK8, a turn-based card and dice game. Here's the quick-and-dirty on getting it running.

## How to Play

### 1. Requirements

* You'll need Python installed. If you don't have it, get it from [python.org](https://www.python.org/downloads/).
* When you run the installer, make sure you check the box for **"Add Python to PATH"**.

### 2. Run the Game

1.  Download the `sk8` folder from GitHub and unzip it.
2.  Open a terminal or command prompt inside that `sk8` folder.
3.  Run the command: `python sk8.py`

That's it. The game will start. A `sk8-log.txt` file will be created in the folder for any debugging.

## The Rules

The goal: be the last one skating. Set tricks, and make your friend match them. If they fail, they get a letter. Spell **S-K-8** and you lose.

### The Flow

* **Pick a Skater:** Each skater has a unique deck, a passive bonus, two activated abilities, and a penalty.
* **Your Hand:** You start with 8 cards (7 drawn + your permanent **Ollie** card, which can never be discarded).
* **Drawing Cards:** At the start of your turn to *set a trick*, you'll automatically draw cards until you have 8 in your hand.
* **Deck Reshuffle:** If your draw deck runs out of cards, your discard pile is automatically shuffled to become your new deck.
* **Taking a Turn:** On your turn, you can either **(s)et a trick** or **(a)ctivate an ability**.
* **Setting a Trick:** Combine cards, the game calculates the difficulty. You must roll 2d8 and beat the score. If you land it, you only discard one random trick card from the combo (plus specials). If you bail, you lose all the cards from the combo.
* **Matching a Trick:** Try to land the trick the Setter just set.
    * **Defender Penalty:** Difficulty is **+2** if you don't have all the cards for the trick.
    * **Advantage Roll:** If you have at least one card for the trick, you can spend it to roll with *advantage* (roll 3 dice, drop lowest).
    * **Bailing:** Get a letter. On your last letter ('K'), you get one free re-roll to save yourself.

### The Nitty-Gritty

* **Combos:** Mix flips, grinds, stances, and obstacles. The game shows the math.
* **Duplicate Tricks:** Two `Kickflip` cards = `Double Kickflip`. This works for stacking flips and stairs.
* **Stances:** Cards like `Nollie`, `Switch`, and `Fakie` modify a flip trick or an Ollie, adding difficulty.
* **Flatground Grinds:** You can do a grind without a rail or ledge card. The game assumes you found a random curb and adds a small score.
* **Special Cards:** Cards like `Wax`, `Focus`, `Pro Model Deck`, `Sponsors`, and `Bail` can completely change the game.

That's the gist of it. Now go play!
