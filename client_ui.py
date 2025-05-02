import sys
import socket
import threading
from PyQt5.QtWidgets import (QApplication, QWidget, QPushButton, QGridLayout,
                             QLabel, QMessageBox, QVBoxLayout, QHBoxLayout, QInputDialog)
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QTimer

# Global client state
player_symbol = None
is_my_turn = False
board = [""] * 9
scoreboard = {"X": 0, "O": 0}

# We will set server_address later based on user input
server_address = None  
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Communicator for thread-safe UI updates
class Communicator(QObject):
    update_signal = pyqtSignal()
    message_signal = pyqtSignal(str, str)
    disconnect_signal = pyqtSignal()

comm = Communicator()

class TicTacToeWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.winner_cells = []
        self.flash_state = False
        self.win_flash_timer = QTimer()
        self.win_flash_timer.setInterval(300)
        self.win_flash_timer.timeout.connect(self.flash_winner)
        
        # Connect to server before initializing UI
        try:
            client_socket.connect(server_address)
        except Exception as e:
            QMessageBox.critical(self, "Connection Error", f"Unable to connect to server: {e}")
            sys.exit(1)
            
        self.init_ui()
        comm.update_signal.connect(self.update_gui)
        comm.message_signal.connect(self.show_message)
        comm.disconnect_signal.connect(self.handle_disconnect)
        self.start_network_thread()

    def init_ui(self):
        self.setWindowTitle("Tic Tac Toe Multiplayer")
        self.setFixedSize(600, 700)
        self.setStyleSheet("""
            QWidget {
                background-color: #f2f3fc;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QLabel#titleLabel {
                font-size: 28px;
                font-weight: bold;
                color: #4361ee;
                margin: 10px;
            }
            QLabel#statusLabel {
                font-size: 18px;
                color: #2b2d42;
                padding: 12px;
                background-color: #edf2fb;
                border-radius: 10px;
                border: 1px solid #d7dfe8;
            }
            QLabel#scoreLabel {
                font-size: 18px;
                color: #2b2d42;
                background-color: #ffffff;
                padding: 12px;
                border-radius: 10px;
                border: 1px solid #e0e0e0;
            }
            QPushButton.boardButton {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                font-size: 48px;
                font-weight: bold;
                min-width: 120px;
                min-height: 120px;
                border-radius: 5px;
                text-align: center;
                line-height: 120px;
            }
            QPushButton#restartButton {
                background-color: #a5a6ab;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                padding: 10px 20px;
                font-weight: bold;
                min-width: 150px;
            }
            QPushButton#restartButton:hover {
                background-color: #8d8f96;
            }
            QPushButton#restartButton:disabled {
                background-color: #c9ccd1;
            }
            QPushButton#exitButton {
                background-color: #ef476f;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                padding: 10px 20px;
                font-weight: bold;
                min-width: 150px;
            }
            QPushButton#exitButton:hover {
                background-color: #d64667;
            }
        """)
        
        main_layout = QVBoxLayout()
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        title_label = QLabel("✨ Tic Tac Toe Multiplayer ✨")
        title_label.setObjectName("titleLabel")
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        self.status_label = QLabel("🎮 Connected to server, waiting for opponent...")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.status_label)
        
        self.score_label = QLabel("Score: X: 0 • O: 0")
        self.score_label.setObjectName("scoreLabel")
        self.score_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.score_label)
        
        board_container = QWidget()
        self.grid_layout = QGridLayout(board_container)
        self.grid_layout.setSpacing(8)
        
        self.buttons = []
        for i in range(9):
            btn = QPushButton("")
            btn.setObjectName(f"cell{i}")
            btn.setProperty("class", "boardButton")
            btn.setStyleSheet("""
                QPushButton {
                    font-size: 48px;
                    font-weight: bold;
                    background-color: white;
                    border: 1px solid #e0e0e0;
                    border-radius: 5px;
                    text-align: center;
                }
            """)
            btn.clicked.connect(lambda checked, i=i: self.on_button_click(i))
            self.buttons.append(btn)
            self.grid_layout.addWidget(btn, i // 3, i % 3)
        
        for i in range(3):
            self.grid_layout.setRowStretch(i, 1)
            self.grid_layout.setColumnStretch(i, 1)
            
        board_container.setFixedHeight(380)
        main_layout.addWidget(board_container)
        
        control_layout = QHBoxLayout()
        control_layout.setSpacing(20)
        control_layout.setContentsMargins(10, 0, 10, 0)
        
        self.restart_button = QPushButton("🔄 New Game")
        self.restart_button.setObjectName("restartButton")
        self.restart_button.setEnabled(False)
        self.restart_button.clicked.connect(self.send_restart)
        
        self.exit_button = QPushButton("🚪 Exit")
        self.exit_button.setObjectName("exitButton")
        self.exit_button.clicked.connect(self.close)
        
        control_layout.addWidget(self.restart_button)
        control_layout.addWidget(self.exit_button)
        
        main_layout.addLayout(control_layout)
        
        self.setLayout(main_layout)

    def update_gui(self):
        for i in range(9):
            cell_content = board[i]
            self.buttons[i].setText(cell_content)
            base_style = """
                font-size: 48px;
                font-weight: bold;
                border: 1px solid #e0e0e0;
                border-radius: 5px;
                text-align: center;
            """
            if cell_content == "X":
                self.buttons[i].setStyleSheet(f"""
                    {base_style}
                    color: #ef476f;
                    background-color: #ffffff;
                """)
            elif cell_content == "O":
                self.buttons[i].setStyleSheet(f"""
                    {base_style}
                    color: #4361ee;
                    background-color: #ffffff;
                """)
            elif i in self.winner_cells:
                pass
            else:
                self.buttons[i].setStyleSheet(f"""
                    {base_style}
                    background-color: #ffffff;
                """)
        
        if is_my_turn:
            self.status_label.setText("🎮 Your turn!")
            self.status_label.setStyleSheet("background-color: #d7f9e3; color: #2d6a4f; font-size: 18px; padding: 12px; border-radius: 10px; border: 1px solid #c3e8d1;")
        else:
            self.status_label.setText("⏳ Waiting for opponent...")
            self.status_label.setStyleSheet("background-color: #fff3cd; color: #856404; font-size: 18px; padding: 12px; border-radius: 10px; border: 1px solid #ffeeba;")
        
        score_x = scoreboard.get('X', 0)
        score_o = scoreboard.get('O', 0)
        self.score_label.setText(f"Score: <span style='color:#ef476f'>X: {score_x}</span> • <span style='color:#4361ee'>O: {score_o}</span>")

    def on_button_click(self, index):
        global is_my_turn
        if not is_my_turn:
            QMessageBox.warning(self, "Not Your Turn", "Please wait for your turn! 🙂")
            return
        if board[index].strip() != "":
            QMessageBox.warning(self, "Space Taken", "This space is already taken! 😅")
            return
        try:
            client_socket.sendall((str(index) + "\n").encode())
        except Exception as e:
            print("Error sending move:", e)
            return
        is_my_turn = False
        self.update_gui()

    def send_restart(self):
        try:
            client_socket.sendall(("RESTART\n").encode())
        except Exception as e:
            print("Error sending restart:", e)
        self.restart_button.setEnabled(False)
        self.status_label.setText("🔄 Requesting new game...")
        self.status_label.setStyleSheet("background-color: #e9ecef; color: #495057; font-size: 18px; padding: 12px; border-radius: 10px; border: 1px solid #dee2e6;")

    def start_network_thread(self):
        thread = threading.Thread(target=self.handle_server_messages, daemon=True)
        thread.start()

    def handle_server_messages(self):
        global player_symbol, is_my_turn, board, scoreboard
        buffer = ""
        while True:
            try:
                data = client_socket.recv(1024).decode()
                if not data:
                    comm.disconnect_signal.emit()
                    break
                buffer += data
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split(" ", 1)
                    command = parts[0]
                    argument = parts[1] if len(parts) > 1 else ""
                    
                    if command == "SYMBOL":
                        player_symbol = argument
                        color = "#ef476f" if player_symbol == "X" else "#4361ee"
                        comm.message_signal.emit("Your Symbol", f"You are playing as <span style='color:{color}; font-size:32px; font-weight:bold;'>{player_symbol}</span>")
                    elif command == "BOARD":
                        new_board = argument.split(",")
                        if len(new_board) == 9:
                            board = new_board
                            comm.update_signal.emit()
                    elif command == "YOURTURN":
                        is_my_turn = True
                        comm.update_signal.emit()
                    elif command == "INVALID":
                        comm.message_signal.emit("Invalid Move", "That's not a valid move! Try again. 🤔")
                    elif command == "GAMEOVER":
                        is_my_turn = False
                        if argument.startswith("DRAW"):
                            self.status_label.setText("🤝 It's a draw!")
                            self.status_label.setStyleSheet("background-color: #e9ecef; color: #495057; font-size: 18px; padding: 12px; border-radius: 10px; border: 1px solid #dee2e6;")
                            comm.message_signal.emit("Game Over", "It's a draw! 🤝")
                        else:
                            parts_gameover = argument.split("SCORE")
                            main_part = parts_gameover[0].strip().split()
                            winner = main_part[0]
                            
                            win_cells = []
                            if len(main_part) > 1:
                                try:
                                    win_cells = list(map(int, main_part[1].split(",")))
                                except Exception:
                                    win_cells = []
                            
                            scoreboard_info = parts_gameover[1].strip() if len(parts_gameover) > 1 else ""
                            try:
                                sp = scoreboard_info.split(",")
                                scoreboard["X"] = int(sp[0].split(":")[1])
                                scoreboard["O"] = int(sp[1].split(":")[1])
                            except Exception:
                                pass
                            
                            if winner == player_symbol:
                                self.status_label.setText("🏆 You win!")
                                self.status_label.setStyleSheet("background-color: #d7f9e3; color: #2d6a4f; font-size: 18px; padding: 12px; border-radius: 10px; border: 1px solid #c3e8d1;")
                                win_message = "<span style='color:#2d6a4f'>You win! 🎉</span>"
                            else:
                                self.status_label.setText(f"😢 Player '{winner}' wins!")
                                self.status_label.setStyleSheet("background-color: #f8d7da; color: #721c24; font-size: 18px; padding: 12px; border-radius: 10px; border: 1px solid #f5c6cb;")
                                win_message = f"<span style='color:#721c24'>Player '{winner}' wins!</span>"
                            
                            score_x = scoreboard.get("X", 0)
                            score_o = scoreboard.get("O", 0)
                            formatted_score = f"<span style='color:#ef476f'>X: {score_x}</span> • <span style='color:#4361ee'>O: {score_o}</span>"
                            
                            comm.message_signal.emit("Game Over", f"{win_message}<br><br>Score: {formatted_score}")
                            
                            self.winner_cells = win_cells
                            self.flash_state = False
                            self.win_flash_timer.start()
                            
                        self.restart_button.setEnabled(True)
                        comm.update_signal.emit()
                    elif command == "RESTART_AVAILABLE":
                        self.restart_button.setEnabled(True)
                    elif command == "RESTART_REQUEST":
                        response = QMessageBox.question(
                            self,
                            "Restart Request",
                            "Your opponent requested a new game. Do you accept?",
                            QMessageBox.Yes | QMessageBox.No
                        )
                        if response == QMessageBox.Yes:
                            try:
                                client_socket.sendall("RESTART_YES\n".encode())
                            except Exception as e:
                                print("Error sending RESTART_YES:", e)
                        else:
                            try:
                                client_socket.sendall("RESTART_NO\n".encode())
                            except Exception as e:
                                print("Error sending RESTART_NO:", e)
                    elif command == "RESTARTED":
                        board = [""] * 9
                        is_my_turn = False
                        self.winner_cells = []
                        self.win_flash_timer.stop()
                        self.restart_button.setEnabled(False)
                        self.status_label.setText("🎮 Game restarted!")
                        self.status_label.setStyleSheet("background-color: #e9ecef; color: #495057; font-size: 18px; padding: 12px; border-radius: 10px; border: 1px solid #dee2e6;")
                        comm.update_signal.emit()
                    elif command == "DISCONNECT":
                        comm.message_signal.emit("Game Over", "Your opponent declined the restart. Disconnecting...")
                        client_socket.close()
                        return
            except Exception as e:
                print("Error receiving data:", e)
                comm.disconnect_signal.emit()
                break

    def flash_winner(self):
        self.flash_state = not self.flash_state
        winner_symbol = board[self.winner_cells[0]] if self.winner_cells else ""
        base_style = """
            font-size: 48px;
            font-weight: bold;
            border: 1px solid #e0e0e0;
            border-radius: 5px;
            text-align: center;
        """
        for i in self.winner_cells:
            if self.flash_state:
                if winner_symbol == "X":
                    self.buttons[i].setStyleSheet(f"""
                        {base_style}
                        background-color: #ffebef;
                        color: #ef476f;
                    """)
                else:
                    self.buttons[i].setStyleSheet(f"""
                        {base_style}
                        background-color: #ebf0ff;
                        color: #4361ee;
                    """)
            else:
                if winner_symbol == "X":
                    self.buttons[i].setStyleSheet(f"""
                        {base_style}
                        background-color: #ef476f;
                        color: white;
                    """)
                else:
                    self.buttons[i].setStyleSheet(f"""
                        {base_style}
                        background-color: #4361ee;
                        color: white;
                    """)

    def show_message(self, title, message):
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.setStyleSheet("""
            QMessageBox {
                background-color: #f8f9fa;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QLabel {
                color: #212529;
                font-size: 16px;
            }
            QPushButton {
                background-color: #4361ee;
                border: none;
                border-radius: 5px;
                padding: 8px 16px;
                color: white;
                font-weight: bold;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #3451e0;
            }
        """)
        msg_box.exec_()

    def handle_disconnect(self):
        disconnect_box = QMessageBox(self)
        disconnect_box.setWindowTitle("Connection Lost")
        disconnect_box.setText("😕 The connection to the server was lost.<br>The other player may have left the game.")
        disconnect_box.setStandardButtons(QMessageBox.Ok)
        disconnect_box.setStyleSheet("""
            QMessageBox {
                background-color: #f8f9fa;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QLabel {
                color: #212529;
                font-size: 16px;
            }
            QPushButton {
                background-color: #4361ee;
                border: none;
                border-radius: 5px;
                padding: 8px 16px;
                color: white;
                font-weight: bold;
                min-width: 80px;
            }
        """)
        disconnect_box.exec_()
        self.close()

    def closeEvent(self, event):
        try:
            client_socket.close()
        except:
            pass
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # Use a PyQt input dialog to ask for the server IP
    ip, ok = QInputDialog.getText(None, "Server IP", "Enter the server IP address:")
    if ok and ip:
        # Set the global server_address variable
        server_address = (ip, 12345)
    else:
        QMessageBox.critical(None, "Error", "No IP Address provided!")
        sys.exit(1)
    window = TicTacToeWindow()
    window.show()
    sys.exit(app.exec_())