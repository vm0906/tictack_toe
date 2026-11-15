"""Adapters for playing a Tic-Tac-Toe AI turn."""

from __future__ import annotations

from typing import Optional, Tuple, TYPE_CHECKING

from gamelogic import Difficulty

if TYPE_CHECKING:
    from gamelogic import TicTacToeGame

Move = Tuple[int, int]


class TicTacToeAgent:
    """Choose and play a move using the selected game AI difficulty."""

    def __init__(self, difficulty: Difficulty = Difficulty.INTERMEDIATE) -> None:
        self.difficulty = difficulty

    def choose_move(self, game: TicTacToeGame) -> Optional[Move]:
        """Return the game's chosen move without changing its state."""
        return game.get_ai_move(self.difficulty)

    def play_turn(self, game: TicTacToeGame) -> Optional[Move]:
        """Choose and apply a move, returning None when the game is over."""
        move = self.choose_move(game)
        if move is None:
            return None
        if not game.make_move(*move):
            raise RuntimeError(f"AI selected an illegal move: {move}")
        return move