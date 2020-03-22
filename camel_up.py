#!/usr/bin/env python3
import random, copy, argparse
from functools import reduce
from pprint import pprint

# ====================================================================================================

class board_state:
  def new_board(total_camels):
    return board_state( board={0:[i for i in range(0,total_camels)]}, total_camels=total_camels, camel_index=([0]*total_camels) )

  def __init__(this, board, total_camels, camel_index):
    this.board = board
    this.total_camels = total_camels
    this.camel_index = camel_index

  def copy(this):
    return board_state(board=copy.deepcopy(this.board), total_camels=this.total_camels, camel_index=copy.deepcopy(this.camel_index))

  def move(this, camel, spaces):
    new_board = this.copy()

    current_spot = this.camel_index[camel]
    new_spot = current_spot + spaces

    # initialize new spot with empty camel stack if necessary
    if new_spot not in this.board:
      new_board.board[new_spot] = []

    # "Space" "zero" has special rules, in that all camels start there, but are
    # not stackd
    if current_spot == 0:
      # simply move it to new location on board
      new_board.board[new_spot].append(camel)
      new_board.board[current_spot].remove(camel)

      # update camel's index
      new_board.camel_index[camel] = new_spot

    # regular stacked movement
    else:
      # get current position of this cmel in the stack
      current_stack_position = this.board[current_spot].index( camel )
      # move this camel and everything above it to the new location
      new_board.board[new_spot] += list( this.board[current_spot][current_stack_position:] )
      # remove the stack from current location
      new_board.board[current_spot] = list( this.board[current_spot][:current_stack_position] )

      # update all camels' indexes
      for moved_camel in this.board[current_spot][current_stack_position:]:
        new_board.camel_index[moved_camel] = new_spot

    # if current location is empty, remove it from board represntation.
    if len(new_board.board[current_spot]) == 0:
      del( new_board.board[current_spot] )

    return new_board

  def race_order(this):
    order = []
    for spot in reversed(sorted(set(this.camel_index))):
      for camel in reversed( this.board[spot] ):
        order.append( camel )
    return order

  def __str__(this):
    # print( f"board_state\n\tboard: {this.board}\n\tcamel_index: {this.camel_index}" )
    return "\n".join( ( f"{spot}: {this.board[spot]}" for spot in sorted( set(this.camel_index) ) ) )

  def __hash__(this):
    digit_list = [this.total_camels] + this.camel_index
    for spot in sorted(this.board.keys()):
      digit_list += [spot] + this.board[spot]
    hash = 0
    place = 1
    for digit in digit_list:
      hash += digit * place
      place *= 10
    return hash

  def __eq__(this, that):
    return     this.total_camels == that.total_camels \
           and this.camel_index == that.camel_index \
           and this.board == that.board

# ====================================================================================================

class game_state:
  def new_game(total_camels):
    return game_state( board_state.new_board(total_camels), total_camels, set(range(total_camels)) )

  def __init__(this, board, total_camels, playable_camels):
    this.board = board
    this.total_camels = total_camels
    this.playable_camels = playable_camels

  def copy(this):
    return game_state(board=copy.deepcopy(this.board), total_camels=this.total_camels, playable_camels=copy.deepcopy(this.playable_camels))

  def is_valid_move(this, camel, spaces):
    return camel in this.playable_camels and spaces > 0

  def move(this, camel, spaces, auto_restart_round=True):
    new_game = this.copy()

    if this.is_valid_move(camel, spaces):
      new_game.board = this.board.move( camel, spaces )
      new_game.playable_camels.remove( camel )

    if auto_restart_round:
      new_game = new_game.renew_dice_pool()

    return new_game

  def renew_dice_pool(this, force=False):
    new_game = this.copy()
    if force or len(new_game.playable_camels) == 0:
      new_game.playable_camels = set(range(this.total_camels))
    return new_game

  def __str__(this):
    return f"playable: ({','.join(map(str,this.playable_camels))})\nboard:\n{str(this.board)}"

  def __hash__(this):
    board_hash = hash(this.board) << this.total_camels
    place = 1
    for k in range(this.total_camels):
      board_hash |= place if k in this.playable_camels else 0
      place <<= 1
    return board_hash

  def __eq__(this, that):
    return     this.total_camels == that.total_camels \
           and this.board == that.board \
           and this.playable_camels == that.playable_camels

# ====================================================================================================

class game_runner:
  def new_game( total_camels, min_die, max_die, total_spaces ):
    return game_runner( total_camels=total_camels, min_die=min_die, max_die=max_die, total_spaces=total_spaces, game=game_state.new_game(total_camels) )

  def __init__(this, total_camels, min_die, max_die, total_spaces, game ):
    this.total_camels =  total_camels
    this.min_die =  min_die
    this.max_die =  max_die
    this.total_spaces = total_spaces
    this.game_state = game

  def copy(this):
    return game_runner( total_camels=this.total_camels, min_die=this.min_die, max_die=this.max_die, total_spaces=this.total_spaces, game=this.game_state.copy() )

  def is_valid_move(this, camel, spaces):
    return this.game_state.is_valid_move(camel, spaces) and this.min_die <= spaces and spaces <= this.max_die

  def move(this, camel, spaces, auto_restart_round=True):
    return_game = this.copy()
    if this.is_valid_move( camel, spaces ):
      return_game.game_state = this.game_state.move( camel, spaces, auto_restart_round )
    return return_game

  def random_move(this, auto_restart_round=True):
    if this.game_completed() or this.round_over():
      return (None, None, this.copy())
    camel = random.choice( list(this.game_state.playable_camels) )
    spaces = random.randint( this.min_die, this.max_die )
    new_game = this.move( camel, spaces, auto_restart_round )
    return (camel, spaces, new_game)

  def start_round(this, force=False):
    new_game = this.copy()
    new_game.game_state = this.game_state.renew_dice_pool(force)
    return new_game

  def round_over(this):
    return len(this.game_state.playable_camels) == 0

  def game_completed(this):
    return     (len(this.game_state.playable_camels) == 0 or len(this.game_state.playable_camels) == this.total_camels) \
           and max(this.game_state.board.camel_index) > this.total_spaces

  def winner(this):
    winning_camel = None
    if this.game_completed():
      winning_camel = this.game_state.board.race_order()[0]
    return winning_camel

  def __hash__(this):
    return hash(this.game_state)

  def __eq__(this, that):
    return     this.total_camels ==  that.total_camels \
           and this.min_die ==  that.min_die \
           and this.max_die ==  that.max_die \
           and this.total_spaces == that.total_spaces \
           and this.game_state == that.game_state \

  def __str__(this):
    return str(this.game_state)

# ====================================================================================================

class outcome_analyser:
  def __init__(this, game_runner):
    this.game_runner = game_runner
    this.collect_all_single_moves_result = None
    this.collect_all_single_move_outcomes_result = None
    this.collect_all_round_outcomes_result = None
    this.collect_all_round_outcome_probabilities_result = None
    this.collect_all_round_ordering_probabilities_result = None
    this.collect_all_round_positional_ordering_probabilities_result = None

  def copy(this):
    analyser = outcome_analyser( this.game_runner.copy() )
    analyser.collect_all_single_moves_result = this.collect_all_single_moves_result
    analyser.collect_all_single_move_outcomes_result = this.collect_all_single_move_outcomes_result
    analyser.collect_all_round_outcomes_result = this.collect_all_round_outcomes_result
    analyser.collect_all_round_outcome_probabilities_result = this.collect_all_round_outcome_probabilities_result
    analyser.collect_all_round_ordering_probabilities_result = this.collect_all_round_ordering_probabilities_result
    analyser.collect_all_round_positional_ordering_probabilities_result = this.collect_all_round_positional_ordering_probabilities_result
    return analyser


  def game_completed(this):
    return this.game_runner.game_completed()

  def collect_all_single_moves(this):
    if this.collect_all_single_moves_result == None:
      moves = []
      for camel in this.game_runner.game_state.playable_camels:
        for die_face in range(this.game_runner.min_die, this.game_runner.max_die+1):
          moves.append( (camel, die_face) )
      this.collect_all_single_moves_result = set(moves)
    return this.collect_all_single_moves_result

  def collect_all_single_move_outcomes(this):
    if this.collect_all_single_move_outcomes_result == None:
      # game_runner => [(camel, spaces), ...]
      outcomes = {}
      for (camel, spaces) in this.collect_all_single_moves():
        outcome = this.game_runner.move( camel, spaces, auto_restart_round=False )
        if outcome not in outcomes:
          outcomes[outcome] = []
        outcomes[outcome].append( (camel, spaces) )
      this.collect_all_single_move_outcomes_result = outcomes
    return this.collect_all_single_move_outcomes_result

  def collect_all_round_outcomes(this):
    if this.collect_all_round_outcomes_result == None:
      # [ (game_runner, moves) ]
      work_list = [ (this.game_runner, []) ]
      # game_runner => [[(camel, spaces), ...], ...]
      outcomes = {}
      while len(work_list) > 0:
        (game, moves) = work_list.pop()
        for (camel, spaces) in outcome_analyser(game).collect_all_single_moves():
          outcome = game.move( camel, spaces, auto_restart_round=False )
          new_moves = moves + [(camel, spaces)]
          # game's round is done, put in resultins
          if outcome.round_over():
            if outcome not in outcomes:
              outcomes[outcome] = []
            # add new move list to existing move set
            outcomes[outcome].append( new_moves )
          else:
            # push this work onto the work list
            work_list.append( (outcome, new_moves) )
      this.collect_all_round_outcomes_result = outcomes
    return this.collect_all_round_outcomes_result

  def collect_all_round_outcome_probabilities(this):
    if this.collect_all_round_outcome_probabilities_result == None:
      outcomes = this.collect_all_round_outcomes()
      total_move_strings = sum( [ len(move_list) for (game, move_list) in outcomes.items() ] )
      unit_probability = 1.0/total_move_strings if total_move_strings > 0 else 0
      board_probabilities = { game :  {
                                        "probability" : unit_probability * len(move_list),
                                        "moves" : move_list
                                      }
                              for (game, move_list) in outcomes.items()
                           }
    this.collect_all_round_outcome_probabilities_result = board_probabilities
    return this.collect_all_round_outcome_probabilities_result

  def collect_all_round_ordering_probabilities(this):
    if this.collect_all_round_ordering_probabilities_result == None:
      board_probabilities = this.collect_all_round_outcome_probabilities()
      # order => { games : [ { game : [[moves],], probability : % }], probability : % }
      ordering_outcomes = {}
      for (game, properties) in board_probabilities.items():
        order = tuple(game.game_state.board.race_order())
        game_data = { "game" : game, **properties}
        if order not in ordering_outcomes:
          ordering_outcomes[order] = { "games" : [], "probability" : 0 }
        ordering_outcomes[order]["games"].append( game_data )
        ordering_outcomes[order]["probability"] += properties["probability"]

      this.collect_all_round_ordering_probabilities_result = ordering_outcomes
    return this.collect_all_round_ordering_probabilities_result

  def collect_all_round_positional_ordering_probabilities(this):
    if this.collect_all_round_positional_ordering_probabilities_result == None:
      outcomes = this.collect_all_round_ordering_probabilities()
      positional_probability = [ [0.0]*this.game_runner.total_camels for _ in range(this.game_runner.total_camels)]
      for (order, properties) in outcomes.items():
        probability = properties["probability"]
        for (camel, position) in zip(order, range(len(order))):
          positional_probability[camel][position] += probability
      this.collect_all_round_positional_ordering_probabilities_result = positional_probability
    return this.collect_all_round_positional_ordering_probabilities_result

# ====================================================================================================

class game_and_analysis:
  def __init__(this, total_camels=5, min_die=1, max_die=3, total_spaces=16, sep_length=70 ):
    this.total_camels = total_camels
    this.min_die = min_die
    this.max_die = max_die
    this.total_spaces = total_spaces
    this.game = game_runner.new_game( total_camels=this.total_camels, min_die=this.min_die, max_die=this.max_die, total_spaces=this.total_spaces )
    this.round_counter = 1
    this.move_counter = 1

    this.sep_length = sep_length
    this.round_sep = "#" * sep_length
    this.move_sep = "=" * sep_length
    this.section_sep = "-" * sep_length

  def run(this):
    while not this.game.game_completed():
      this.step()
    print( f"Ending Game\n{this.game.game_state.board}\nThe winner is camel {this.game.winner()}" )

  def print_state(this):
     print( f"Round {this.round_counter} move {this.move_counter}\nRace order: {this.game.game_state.board.race_order()}\n{this.game}\n{this.section_sep}\nProbabilities:")

  def do_analysis(this):
    analyser = outcome_analyser( this.game )
    analyser.collect_all_round_positional_ordering_probabilities()
    return analyser

  def print_analysis(this, analysis):
    # note that this is memoized, so it has already been done.
    positional_probability = analysis.collect_all_round_positional_ordering_probabilities()
    print("position:", end="")
    for camel in range(this.total_camels):
      print(f"\t{camel+1}", end="")
    for camel in range(this.total_camels):
      print( f"\ncamel {camel}:", end="" )
      for position in range(this.total_camels):
        print( f"\t{positional_probability[camel][position]:.2%}", end="")
    print("")

  def do_and_print_analysis(this):
    this.print_analysis( this.do_analysis() )

  def take_move(this):
    return (-1, -1)

  def print_move(this, camel, steps):
    print( f"Moved camel {camel}, {steps} step{'s' if steps > 1 else ''}\nRace order: {this.game.game_state.board.race_order()}" )

  def do_and_print_move(this):
    (camel, steps) = this.take_move();
    this.print_move( camel, steps)

  def round_check(this):
    new_round = this.game.round_over()
    if new_round:
      print( f"Round {this.round_counter} over.")
      this.game = this.game.start_round()
      this.round_counter += 1
      this.move_counter = 1
    return new_round

  def step(this):
    this.print_state()
    print( f"{this.section_sep}" )
    this.do_and_print_analysis()
    print( f"{this.section_sep}" )
    this.do_and_print_move()
    print( f"{this.section_sep}" )
    new_round = this.round_check()
    if new_round:
      print(this.round_sep)
    else:
      print(this.move_sep)

class random_game_and_analysis(game_and_analysis):
  def take_move(this):
    this.move_counter += 1
    (camel, steps, this.game) = this.game.random_move(auto_restart_round=False)
    return (camel, steps)

class interactive_game_and_analysis(game_and_analysis):
  def __init__(this, *args, **kwargs):
    super().__init__( *args, **kwargs )
    # [(round, move, camel, steps), ...]
    this.move_history = []

  def take_move(this):
    escape_counter = 0
    first_run = True
    max_escapes = 2
    while first_run or (1 <= escape_counter and escape_counter <= max_escapes):
      first_run = False
      try:
        valid_camel = False;
        valid_move = False

        while not valid_camel:
          camel = int(input("> Input Camel: "))
          if not (0 <= camel and camel < this.total_camels):
            print(f"Invalid camel id.")
          elif camel not in this.game.game_state.playable_camels:
            print(f"Camel {camel} has already played this round.")
          else:
            valid_camel = True

          if not valid_camel:
            print(f"Please enter a one of the available camel IDs: {sorted(this.game.game_state.playable_camels)}.")

        while not valid_move:
          moves = int(input("> Input Moves: "))
          if not( this.min_die <= moves and moves <= this.max_die ):
            print(f"Invalid number of moves.")
          else:
            valid_move = True
          if not valid_move:
            print(f"Please enter a number in the range [{this.min_die}, {this.max_die}].")

        this.game = this.game.move(camel, moves, auto_restart_round=False)
        this.move_history.append( (this.round_counter, this.move_counter, camel, moves) )
        this.move_counter += 1
      except KeyboardInterrupt as expt:
        escape_counter += 1
        if escape_counter == 1:
          if len(this.move_history) == 0:
            print("\nNo previous move history.")
          else:
            print( f"\n{this.section_sep}\nMove history:" + "".join( [ f"\n\tRound {round} move {move}: moved camel {camel}, {steps} step{'s' if steps > 1 else ''}" for round, move, camel, steps in this.move_history ] ) + f"\n{this.section_sep}" )
        elif escape_counter == 2:
          print( f"\n{this.section_sep}\nFlat move history [(camel, steps), ...]:\n" + str([ (camel, steps) for round, move, camel, steps in this.move_history ]) + f"\n{this.section_sep}" )
        else:
          raise expt

    return (camel, moves)


def main():
  parser = argparse.ArgumentParser(description='Camel Up Simulator')
  parser.add_argument('--camels',            type=int,  default=5,                          help='Number of camels in the race (default: 3)')
  parser.add_argument('--minimum_die_value', type=int,  default=1,                          help='Minimum die value (default: 1)')
  parser.add_argument('--maximum_die_value', type=int,  default=3,                          help='Maximum die value (default: 3)')
  parser.add_argument('--total_spaces',      type=int,  default=16,                         help='Total spaces on board (default: 16)')
  parser.add_argument('--interactive',                  default=False, action="store_true", help='Run simulation in interactive mode (plays random game by default)')

  args = parser.parse_args( )

  if args.interactive:
    game = interactive_game_and_analysis(total_camels=args.camels, min_die=args.minimum_die_value, max_die=args.maximum_die_value, total_spaces=args.total_spaces)
  else:
    game = random_game_and_analysis(total_camels=args.camels, min_die=args.minimum_die_value, max_die=args.maximum_die_value, total_spaces=args.total_spaces)

  game.run()

if __name__ == "__main__":
  main()
