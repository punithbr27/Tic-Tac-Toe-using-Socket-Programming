import socket

# Global game state
board = [""] * 9         # Each cell is "" if empty, otherwise "X" or "O"
current_turn = 0         # 0 for player1, 1 for player2
scoreboard = {"X": 0, "O": 0}

def check_winner():
    win_conditions = [
        (0, 1, 2), (3, 4, 5), (6, 7, 8),  # rows
        (0, 3, 6), (1, 4, 7), (2, 5, 8),  # columns
        (0, 4, 8), (2, 4, 6)              # diagonals
    ]
    for condition in win_conditions:
        a, b, c = condition
        if board[a] and board[a] == board[b] == board[c]:
            return board[a], condition
    return None, None

def board_to_string():
    return ",".join(board)

def broadcast(message, players):
    """Send message (with newline) to all players."""
    for p in players:
        try:
            p.sendall((message + "\n").encode())
        except Exception as e:
            print("Broadcast error:", e)

def reset_game():
    global board, current_turn
    board = [""] * 9
    current_turn = 0

def wait_for_restart(players):
    """
    Wait for both players to respond after a game over.
    Each player should send either "RESTART" (or "RESTART_YES") or "RESTART_NO".
    Returns True if both players agree to restart, otherwise False.
    """
    # Inform players to send restart response
    broadcast("RESTART_PROMPT: Send 'RESTART' to continue or 'RESTART_NO' to quit.", players)
    
    responses = {}
    while len(responses) < 2:
        for p in players:
            if p in responses:
                continue
            try:
                data = p.recv(1024).decode().strip().upper()
                if data in ("RESTART", "RESTART_YES"):
                    responses[p] = True
                elif data in ("RESTART_NO", "NO"):
                    responses[p] = False
            except Exception as e:
                print("Error during restart wait:", e)
                responses[p] = False
    print("Restart responses:", responses)
    # Return True if both players agreed
    return all(responses.values())

def handle_game(player1, player2):
    players = [player1, player2]
    symbols = {player1: "X", player2: "O"}
    
    # Send symbol assignments
    try:
        player1.sendall("SYMBOL X\n".encode())
        player2.sendall("SYMBOL O\n".encode())
    except Exception as e:
        print("Error sending symbols:", e)
        return

    global current_turn, board, scoreboard

    while True:
        # Broadcast current board state
        broadcast("BOARD " + board_to_string(), players)
        
        # Check for win or draw
        winner, win_cells = check_winner()
        if winner:
            scoreboard[winner] += 1
            print(f"Player {winner} won!")
            broadcast(f"GAMEOVER {winner} {','.join(map(str, win_cells))} SCORE X:{scoreboard['X']},O:{scoreboard['O']}", players)
        elif "" not in board:
            print("Game ended in a draw.")
            broadcast(f"GAMEOVER DRAW SCORE X:{scoreboard['X']},O:{scoreboard['O']}", players)
        
        # If game over, wait for restart responses
        if winner or "" not in board:
            restart = wait_for_restart(players)
            if restart:
                reset_game()
                broadcast("RESTARTED", players)
                continue
            else:
                broadcast("DISCONNECT", players)
                break

        # Prompt current player for a move
        current_player = players[current_turn]
        try:
            current_player.sendall("YOURTURN\n".encode())
        except Exception as e:
            print("Error: current player disconnected.", e)
            break

        # Receive move from current player
        try:
            move_data = current_player.recv(1024).decode().strip()
            if not move_data:
                print("Player disconnected.")
                break
            move = int(move_data)
        except Exception as e:
            print("Error receiving move:", e)
            continue

        # Validate move
        if 0 <= move < 9 and board[move] == "":
            board[move] = symbols[current_player]
            print(f"Player {symbols[current_player]} played move at cell {move}")
            current_turn = 1 - current_turn
        else:
            try:
                current_player.sendall("INVALID\n".encode())
            except Exception as e:
                print("Error sending invalid message:", e)
            continue

    # Close sockets when game ends
    for p in players:
        try:
            p.close()
        except:
            pass

def main():
    host = "0.0.0.0"
    port = 12345
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(2)
    print(f"Server listening on {host}:{port}")

    print("Waiting for Player 1...")
    player1, addr1 = server_socket.accept()
    print("Player 1 connected from", addr1)

    print("Waiting for Player 2...")
    player2, addr2 = server_socket.accept()
    print("Player 2 connected from", addr2)

    handle_game(player1, player2)
    server_socket.close()
    print("Game over, server closing.")

if __name__ == "__main__":
    main()
