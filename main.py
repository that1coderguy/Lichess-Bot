import os
import requests
import sseclient
import json
import chess
import chess.engine
import time

# ----------------------------
# Load Lichess token from Railway
# ----------------------------
TOKEN = os.environ["RomeFish"]  # Must match your environment variable name

HEADERS = {
    "Authorization": f"Bearer {TOKEN}"
}

# ----------------------------
# Points-based evaluation function
# ----------------------------
PIECE_VALUES = {
    chess.PAWN: 1,
    chess.KNIGHT: 3,
    chess.BISHOP: 3,
    chess.ROOK: 5,
    chess.QUEEN: 9,
    chess.KING: 0
}

CENTER_SQUARES = [chess.D4, chess.E4, chess.D5, chess.E5]

def evaluate_move(board, move):
    score = 0
    piece = board.piece_at(move.from_square)
    target = board.piece_at(move.to_square)

    # Pawn advancement points
    if piece.piece_type == chess.PAWN:
        start_row = 1 if piece.color == chess.WHITE else 6
        row_distance = abs(chess.square_rank(move.to_square) - start_row)
        score += 0.25 * row_distance

    # Captures
    if target:
        score += PIECE_VALUES[target.piece_type]

    # Center control bonus
    if move.to_square in CENTER_SQUARES:
        score += 0.2

    return score

def pick_best_move(board):
    legal_moves = list(board.legal_moves)
    if not legal_moves:
        return None

    best_move = None
    best_score = -float('inf')

    for move in legal_moves:
        score = evaluate_move(board, move)
        if score > best_score:
            best_score = score
            best_move = move

    return best_move

# ----------------------------
# Connect to Lichess event stream
# ----------------------------
def connect_events():
    url = "https://lichess.org/api/stream/event"
    response = requests.get(url, headers=HEADERS, stream=True)
    client = sseclient.SSEClient(response)
    print("Connected to Lichess event stream.")
    return client

# ----------------------------
# Accept challenges
# ----------------------------
def accept_challenge(challenge_id):
    url = f"https://lichess.org/api/challenge/{challenge_id}/accept"
    r = requests.post(url, headers=HEADERS)
    if r.status_code == 200:
        print(f"Challenge {challenge_id} accepted!")
    else:
        print(f"Failed to accept challenge {challenge_id}: {r.status_code}")

# ----------------------------
# Play a game
# ----------------------------
def play_game(game_id, color):
    stream_url = f"https://lichess.org/api/bot/game/stream/{game_id}"
    response = requests.get(stream_url, headers=HEADERS, stream=True)
    client = sseclient.SSEClient(response)
    board = chess.Board()
    print(f"Started game {game_id} as {'white' if color=='white' else 'black'}.")

    for event in client.events():
        if not event.data:
            continue

        data = json.loads(event.data)

        # Game state update
        if data.get("type") == "gameFull":
            # Set up initial moves if black
            moves = data["state"]["moves"].split()
            for move in moves:
                board.push_uci(move)

        elif data.get("type") == "gameState":
            moves = data.get("moves", "").split()
            board = chess.Board()
            for move in moves:
                board.push_uci(move)

            # Check if it's our turn
            if (board.turn == chess.WHITE and color == "white") or (board.turn == chess.BLACK and color == "black"):
                move = pick_best_move(board)
                if move:
                    uci = move.uci()
                    make_move_url = f"https://lichess.org/api/bot/game/{game_id}/move/{uci}"
                    r = requests.post(make_move_url, headers=HEADERS)
                    if r.status_code == 200:
                        print(f"Played move: {uci}")
                    else:
                        print(f"Failed to play move {uci}: {r.status_code}")

# ----------------------------
# Main loop
# ----------------------------
def main():
    client = connect_events()
    for event in client.events():
        if not event.data:
            continue

        data = json.loads(event.data)

        # Detect challenge
        if data.get("type") == "challenge":
            challenge_id = data["challenge"]["id"]
            print(f"New challenge: {challenge_id}")
            accept_challenge(challenge_id)

        # Detect game start
        elif data.get("type") == "gameStart":
            game_id = data["game"]["id"]
            color = data["game"]["color"]
            print(f"Game started: {game_id}, playing {color}")
            play_game(game_id, color)

if __name__ == "__main__":
    main()
