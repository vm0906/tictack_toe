"""
game_logic.py
=============
Backend logic for an advanced Tic-Tac-Toe game.

Features
--------
* Board sizes: 4x4, 5x5, 6x6, 8x8
* Configurable consecutive win target (e.g. 4-in-a-row on large boards)
* AI opponent with three difficulty levels
    - BEGINNER:     random valid moves
    - INTERMEDIATE: takes immediate wins, blocks immediate losses, otherwise
                    prefers central squares
    - TOUGH:        iterative-deepening alpha-beta (negamax) search with
                    candidate-move pruning, move ordering and a vectorised
                    window-based heuristic (fast enough for 8x8)
* One-time-per-game hint that returns the best strategic move

Dependencies: numpy (standard library otherwise).

Quick usage
-----------
    game = TicTacToeGame(size=6, win_length=4)
    game.make_move(2, 3)                       # human (X)
    row, col = game.play_ai_turn(Difficulty.TOUGH)   # AI (O)
    hint = game.get_hint()                     # (row, col) or None
"""

from __future__ import annotations

import random
import time
from enum import Enum
from typing import List, Optional, Tuple

import numpy as np

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #
EMPTY, X, O = 0, 1, 2
SYMBOLS = {EMPTY: "", X: "X", O: "O"}

SUPPORTED_SIZES = (4, 5, 6, 8)

# "Standard" win targets per board size (customisable via `win_length`).
DEFAULT_WIN_LENGTH = {4: 4, 5: 4, 6: 4, 8: 5}

# Horizontal, vertical, diagonal, anti-diagonal.
DIRECTIONS = ((0, 1), (1, 0), (1, 1), (1, -1))

Move = Tuple[int, int]


class Difficulty(Enum):
    BEGINNER = "Beginner"
    INTERMEDIATE = "Intermediate"
    TOUGH = "Tough"


def opponent(player: int) -> int:
    """Return the other player."""
    return O if player == X else X


# --------------------------------------------------------------------------- #
# Board helpers
# --------------------------------------------------------------------------- #
def winning_line(board: np.ndarray, row: int, col: int,
                 player: int, win_length: int) -> Optional[List[Move]]:
    """
    If `player` has `win_length` or more in a row through (row, col),
    return the list of cells forming that run; otherwise return None.
    """
    n = board.shape[0]
    for dr, dc in DIRECTIONS:
        line = [(row, col)]
        r, c = row + dr, col + dc
        while 0 <= r < n and 0 <= c < n and board[r, c] == player:
            line.append((r, c))
            r, c = r + dr, c + dc
        r, c = row - dr, col - dc
        while 0 <= r < n and 0 <= c < n and board[r, c] == player:
            line.insert(0, (r, c))
            r, c = r - dr, c - dc
        if len(line) >= win_length:
            return line
    return None


def valid_moves(board: np.ndarray) -> List[Move]:
    """All empty cells as (row, col) tuples."""
    rows, cols = np.nonzero(board == EMPTY)
    return [(int(r), int(c)) for r, c in zip(rows, cols)]


def candidate_moves(board: np.ndarray) -> List[Move]:
    """
    Empty cells adjacent (8-neighbourhood) to at least one occupied cell.
    Any move that creates or blocks a line is always among these, so this
    safely shrinks the search space. Opens at the centre on an empty board.
    """
    n = board.shape[0]
    occupied = board != EMPTY
    if not occupied.any():
        mid = n // 2
        return [(mid, mid)]
    padded = np.pad(occupied, 1)
    near = np.zeros_like(occupied)
    for dr in range(3):
        for dc in range(3):
            near |= padded[dr:dr + n, dc:dc + n]
    cells = near & ~occupied
    rows, cols = np.nonzero(cells)
    moves = [(int(r), int(c)) for r, c in zip(rows, cols)]
    return moves or valid_moves(board)


def find_immediate_win(board: np.ndarray, player: int,
                       win_length: int) -> Optional[Move]:
    """Return a move that wins immediately for `player`, if any."""
    for r, c in valid_moves(board):
        board[r, c] = player
        won = winning_line(board, r, c, player, win_length) is not None
        board[r, c] = EMPTY
        if won:
            return (r, c)
    return None


# --------------------------------------------------------------------------- #
# AI: Beginner & Intermediate
# --------------------------------------------------------------------------- #
def beginner_move(board: np.ndarray) -> Optional[Move]:
    """Random valid move."""
    moves = valid_moves(board)
    return random.choice(moves) if moves else None


def intermediate_move(board: np.ndarray, player: int,
                      win_length: int) -> Optional[Move]:
    """Win if possible -> block if necessary -> prefer central squares."""
    moves = valid_moves(board)
    if not moves:
        return None
    work = board.copy()
    win = find_immediate_win(work, player, win_length)
    if win:
        return win
    block = find_immediate_win(work, opponent(player), win_length)
    if block:
        return block
    centre = (board.shape[0] - 1) / 2
    # Distance to centre plus a little jitter so games vary.
    return min(moves, key=lambda m: abs(m[0] - centre) + abs(m[1] - centre)
               + random.random() * 1.5)


# --------------------------------------------------------------------------- #
# AI: Tough (alpha-beta negamax + heuristic)
# --------------------------------------------------------------------------- #
class _Timeout(Exception):
    pass


class SearchEngine:
    """
    Iterative-deepening negamax with alpha-beta pruning.

    Speed-ups for large boards:
      * only neighbours of existing stones are searched,
      * forced wins / forced blocks short-circuit the move list,
      * moves are ordered by a heuristic and trimmed to a beam,
      * the heuristic scores every k-length window at once with numpy,
      * search is bounded by a wall-clock budget.
    """

    WIN_SCORE = 1_000_000.0
    INF = float("inf")

    def __init__(self, size: int, win_length: int,
                 root_beam: int = 12, beam: int = 8):
        self.n = size
        self.k = win_length
        self.root_beam = root_beam
        self.beam = beam
        self.windows = self._build_windows(size, win_length)
        # weights[c] = value of a window containing c uncontested stones.
        self.weights = np.array(
            [0.0] + [10.0 ** (c - 1) for c in range(1, win_length + 1)])
        self._deadline = 0.0

    # -- setup ------------------------------------------------------------- #
    @staticmethod
    def _build_windows(n: int, k: int) -> np.ndarray:
        """Flat-index array of shape (num_windows, k) for every possible line."""
        windows = []
        for r in range(n):
            for c in range(n):
                for dr, dc in DIRECTIONS:
                    er, ec = r + dr * (k - 1), c + dc * (k - 1)
                    if 0 <= er < n and 0 <= ec < n:
                        windows.append(
                            [(r + dr * i) * n + (c + dc * i) for i in range(k)])
        return np.array(windows, dtype=np.intp)

    # -- heuristic --------------------------------------------------------- #
    def evaluate(self, board: np.ndarray, me: int) -> float:
        """Static score from `me`'s perspective (higher = better for me)."""
        vals = board.ravel()[self.windows]
        mine = (vals == me).sum(axis=1)
        theirs = (vals == opponent(me)).sum(axis=1)
        my_score = self.weights[mine[theirs == 0]].sum()
        their_score = self.weights[theirs[mine == 0]].sum()
        # Slightly overweight opponent threats (defence matters on big boards).
        return float(my_score - 1.2 * their_score)

    # -- move generation --------------------------------------------------- #
    def _ordered_moves(self, board: np.ndarray, player: int,
                       beam: int) -> List[Move]:
        opp = opponent(player)
        scored: List[Tuple[float, Move]] = []
        blocks: List[Move] = []
        for r, c in candidate_moves(board):
            board[r, c] = player
            if winning_line(board, r, c, player, self.k):
                board[r, c] = EMPTY
                return [(r, c)]                       # immediate win
            scored.append((self.evaluate(board, player), (r, c)))
            board[r, c] = opp
            if winning_line(board, r, c, opp, self.k):
                blocks.append((r, c))                 # must block here
            board[r, c] = EMPTY
        if blocks:
            return blocks[:1]
        scored.sort(key=lambda t: t[0], reverse=True)
        return [m for _, m in scored[:beam]]

    # -- search ------------------------------------------------------------ #
    def _tick(self) -> None:
        if time.monotonic() > self._deadline:
            raise _Timeout

    def _negamax(self, board: np.ndarray, player: int, depth: int,
                 empties: int, alpha: float, beta: float) -> float:
        self._tick()
        moves = self._ordered_moves(board, player, self.beam)
        if not moves:
            return 0.0
        opp = opponent(player)
        best = -self.INF
        for r, c in moves:
            board[r, c] = player
            if winning_line(board, r, c, player, self.k):
                score = self.WIN_SCORE + depth        # sooner wins score higher
            elif empties == 1:
                score = 0.0                           # board full -> draw
            elif depth == 1:
                score = self.evaluate(board, player)
            else:
                score = -self._negamax(board, opp, depth - 1, empties - 1,
                                       -beta, -alpha)
            board[r, c] = EMPTY
            if score > best:
                best = score
            if best > alpha:
                alpha = best
            if alpha >= beta:
                break
        return best

    def _search_root(self, board: np.ndarray, player: int, depth: int,
                     empties: int, moves: List[Move]) -> Tuple[Move, float]:
        opp = opponent(player)
        alpha, beta = -self.INF, self.INF
        best_score, best_move = -self.INF, moves[0]
        for r, c in moves:
            self._tick()
            board[r, c] = player
            if winning_line(board, r, c, player, self.k):
                score = self.WIN_SCORE + depth
            elif empties == 1:
                score = 0.0
            elif depth == 1:
                score = self.evaluate(board, player)
            else:
                score = -self._negamax(board, opp, depth - 1, empties - 1,
                                       -beta, -alpha)
            board[r, c] = EMPTY
            if score > best_score:
                best_score, best_move = score, (r, c)
            alpha = max(alpha, best_score)
        return best_move, best_score

    def best_move(self, board: np.ndarray, player: int,
                  time_limit: float = 1.0, max_depth: int = 6) -> Optional[Move]:
        """Best move for `player` found within `time_limit` seconds."""
        empties = int((board == EMPTY).sum())
        if empties == 0:
            return None
        self._deadline = time.monotonic() + time_limit
        root = board.copy()
        moves = self._ordered_moves(root, player, self.root_beam)
        if not moves:
            return None
        best = moves[0]
        for depth in range(1, min(max_depth, empties) + 1):
            try:
                move, score = self._search_root(
                    board.copy(), player, depth, empties, moves)
            except _Timeout:
                break
            best = move
            if score >= self.WIN_SCORE:               # forced win found
                break
            moves = [move] + [m for m in moves if m != move]  # reuse ordering
        return best


# --------------------------------------------------------------------------- #
# Game state
# --------------------------------------------------------------------------- #
class TicTacToeGame:
    """
    Game state, rules and AI access.

    Attributes
    ----------
    board          : np.ndarray (size x size) of EMPTY / X / O
    current_player : X or O
    winner         : X, O or None
    winning_line   : list of (row, col) cells of the winning run, or None
    is_draw        : True when the board is full with no winner
    hint_used      : True once the one-time hint has been consumed
    """

    TOUGH_TIME_LIMIT = 1.0
    HINT_TIME_LIMIT = 2.0

    def __init__(self, size: int = 4, win_length: Optional[int] = None,
                 starting_player: int = X):
        if size not in SUPPORTED_SIZES:
            raise ValueError(f"size must be one of {SUPPORTED_SIZES}")
        if win_length is None:
            win_length = DEFAULT_WIN_LENGTH[size]
        if not 3 <= win_length <= size:
            raise ValueError(f"win_length must be between 3 and {size}")
        if starting_player not in (X, O):
            raise ValueError("starting_player must be X or O")

        self.size = size
        self.win_length = win_length
        self.starting_player = starting_player
        self._engine = SearchEngine(size, win_length)
        self.reset()

    # -- lifecycle --------------------------------------------------------- #
    def reset(self) -> None:
        """Start a fresh game with the same settings."""
        self.board = np.zeros((self.size, self.size), dtype=np.int8)
        self.current_player = self.starting_player
        self.winner: Optional[int] = None
        self.winning_line: Optional[List[Move]] = None
        self.is_draw = False
        self.hint_used = False
        self.move_history: List[Tuple[int, int, int]] = []  # (player, r, c)

    # -- state queries ----------------------------------------------------- #
    @property
    def is_over(self) -> bool:
        return self.winner is not None or self.is_draw

    @property
    def hint_available(self) -> bool:
        return not self.hint_used and not self.is_over

    def get_valid_moves(self) -> List[Move]:
        return valid_moves(self.board)

    def is_valid_move(self, row: int, col: int) -> bool:
        return (not self.is_over
                and 0 <= row < self.size and 0 <= col < self.size
                and self.board[row, col] == EMPTY)

    def board_symbols(self) -> List[List[str]]:
        """Board as a list of lists of '', 'X', 'O' (handy for UIs)."""
        return [[SYMBOLS[int(v)] for v in row] for row in self.board]

    # -- playing ----------------------------------------------------------- #
    def make_move(self, row: int, col: int) -> bool:
        """Place the current player's mark. Returns False if the move is illegal."""
        if not self.is_valid_move(row, col):
            return False
        player = self.current_player
        self.board[row, col] = player
        self.move_history.append((player, row, col))

        line = winning_line(self.board, row, col, player, self.win_length)
        if line:
            self.winner, self.winning_line = player, line
        elif not (self.board == EMPTY).any():
            self.is_draw = True
        else:
            self.current_player = opponent(player)
        return True

    # -- AI ---------------------------------------------------------------- #
    def get_ai_move(self, difficulty: Difficulty = Difficulty.INTERMEDIATE
                    ) -> Optional[Move]:
        """Choose (without playing) a move for the current player."""
        if self.is_over:
            return None
        if difficulty == Difficulty.BEGINNER:
            return beginner_move(self.board)
        if difficulty == Difficulty.INTERMEDIATE:
            return intermediate_move(self.board, self.current_player,
                                     self.win_length)
        if difficulty == Difficulty.TOUGH:
            return self._engine.best_move(
                self.board, self.current_player,
                time_limit=self.TOUGH_TIME_LIMIT)
        raise ValueError(f"Unknown difficulty: {difficulty}")

    def play_ai_turn(self, difficulty: Difficulty = Difficulty.INTERMEDIATE
                     ) -> Optional[Move]:
        """Choose and play an AI move for the current player; returns it."""
        move = self.get_ai_move(difficulty)
        if move is not None:
            self.make_move(*move)
        return move

    # -- hint -------------------------------------------------------------- #
    def get_hint(self) -> Optional[Move]:
        """
        One-time-per-game hint: the strongest move for the current player.
        Returns (row, col), or None if the hint was already used or the
        game is over. Does NOT play the move.
        """
        if not self.hint_available:
            return None
        move = self._engine.best_move(
            self.board, self.current_player,
            time_limit=self.HINT_TIME_LIMIT, max_depth=8)
        if move is not None:
            self.hint_used = True
        return move


# --------------------------------------------------------------------------- #
# Self-test: AI vs AI
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    for size in SUPPORTED_SIZES:
        g = TicTacToeGame(size=size)
        t0 = time.time()
        while not g.is_over:
            level = Difficulty.TOUGH if g.current_player == X else Difficulty.INTERMEDIATE
            g.play_ai_turn(level)
        result = "draw" if g.is_draw else f"{SYMBOLS[g.winner]} wins"
        print(f"{size}x{size} (win={g.win_length}): {result} "
              f"in {len(g.move_history)} moves, {time.time() - t0:.1f}s")