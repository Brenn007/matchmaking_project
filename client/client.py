import tkinter as tk
from tkinter import messagebox
import socket
import threading

SERVER_IP = '127.0.0.1'  #a remplacer par l'IP du serveur
SERVER_PORT = 12345

class MatchmakingClient(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Client de Matchmaking")
        self.geometry("300x400")
        
        self.pseudo_label = tk.Label(self, text="Entrez votre pseudo :")
        self.pseudo_label.pack(pady=10)
        
        self.pseudo_entry = tk.Entry(self)
        self.pseudo_entry.pack(pady=5)
        
        self.connect_button = tk.Button(self, text="Se connecter", command=self.connect_to_server)
        self.connect_button.pack(pady=10)
        
        self.status_label = tk.Label(self, text="")
        self.status_label.pack(pady=10)
        
        self.socket = None
        self.board_buttons = []
        self.current_player = 'X'  #'X' ou 'O'
        self.match_id = None
        self.player_number = None

    def connect_to_server(self):
        pseudo = self.pseudo_entry.get()
        if not pseudo:
            messagebox.showwarning("Pseudo manquant", "Veuillez entrer un pseudo.")
            return
        
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.socket.connect((SERVER_IP, SERVER_PORT))
            self.socket.sendall(pseudo.encode())
            self.status_label.config(text="En attente d'un adversaire...")
            
            #ecoute des messages du serveur
            threading.Thread(target=self.listen_to_server, daemon=True).start()
        except Exception as e:
            messagebox.showerror("Erreur de connexion", f"Impossible de se connecter au serveur : {e}")
            self.socket = None

    def listen_to_server(self):
        try:
            while True:
                message = self.socket.recv(1024).decode()
                if message:
                    self.status_label.config(text=message)
                    if "Match trouvé" in message:
                        self.match_id, self.player_number = self.parse_match_info(message)
                        self.show_game_board()
                    elif "Coup joué" in message:
                        self.update_board(message)
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur de communication avec le serveur : {e}")
            self.socket = None

    def parse_match_info(self, message):
        parts = message.split(',')
        match_id = int(parts[0].split(':')[1].strip())
        player_number = int(parts[1].split(':')[1].strip())
        return match_id, player_number

    def show_game_board(self):
        self.status_label.config(text="Match en cours...")
        board_frame = tk.Frame(self)
        board_frame.pack(pady=10)
        
        for i in range(3):
            row = []
            for j in range(3):
                button = tk.Button(board_frame, text=" ", width=10, height=3,
                                   command=lambda i=i, j=j: self.make_move(i, j))
                button.grid(row=i, column=j)
                row.append(button)
            self.board_buttons.append(row)

    def make_move(self, i, j):
        if self.board_buttons[i][j]["text"] == " ":
            self.board_buttons[i][j]["text"] = self.current_player
            self.send_move(i, j)
            if self.check_victory():
                messagebox.showinfo("Victoire", f"Le joueur {self.current_player} a gagné !")
                self.reset_board()
            elif self.check_draw():
                messagebox.showinfo("Match nul", "Le match est nul !")
                self.reset_board()
            self.current_player = 'O' if self.current_player == 'X' else 'X'

    def send_move(self, i, j):
        move = f"{self.match_id},{self.player_number},{i}{j}"
        self.socket.sendall(move.encode())

    def update_board(self, message):
        parts = message.split(':')
        move = parts[1].strip()
        i, j = int(move[0]), int(move[1])
        self.board_buttons[i][j]["text"] = 'O' if self.current_player == 'X' else 'X'

    def check_victory(self):
        board = [[self.board_buttons[i][j]["text"] for j in range(3)] for i in range(3)]
        for i in range(3):
            if board[i][0] == board[i][1] == board[i][2] != " ":
                return True
            if board[0][i] == board[1][i] == board[2][i] != " ":
                return True
        if board[0][0] == board[1][1] == board[2][2] != " ":
            return True
        if board[0][2] == board[1][1] == board[2][0] != " ":
            return True
        return False

    def check_draw(self):
        return all(self.board_buttons[i][j]["text"] != " " for i in range(3) for j in range(3))

    def reset_board(self):
        for i in range(3):
            for j in range(3):
                self.board_buttons[i][j]["text"] = " "

if __name__ == "__main__":
    app = MatchmakingClient()
    app.mainloop()
