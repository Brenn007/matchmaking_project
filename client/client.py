import tkinter as tk
from tkinter import messagebox
import socket
import threading

SERVER_IP = '127.0.0.1'  # Localhost pour la compatibilité
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
        self.match_id = None
        self.player_number = None
        self.my_symbol = None  # 'X' ou 'O' selon le numéro du joueur
        self.current_turn = 1   # Toujours 1 pour commencer (joueur X)
        self.is_my_turn = False

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
            
            # Écoute des messages du serveur
            threading.Thread(target=self.listen_to_server, daemon=True).start()
        except Exception as e:
            messagebox.showerror("Erreur de connexion", f"Impossible de se connecter au serveur : {e}")
            self.socket = None

    def listen_to_server(self):
        try:
            while True:
                message = self.socket.recv(1024).decode()
                if message:
                    print(f"[CLIENT] Message reçu : {message}")  # Debug
                    
                    # Utiliser after() pour mettre à jour l'interface depuis le thread principal
                    self.after(0, self.process_server_message, message)
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Erreur", f"Erreur de communication avec le serveur : {e}"))
            self.socket = None

    def process_server_message(self, message):
        """Traite les messages du serveur dans le thread principal"""
        self.status_label.config(text=message)
        
        if "Match trouvé" in message:
            self.match_id, self.player_number = self.parse_match_info(message)
            # Définir le symbole du joueur
            self.my_symbol = 'X' if self.player_number == 1 else 'O'
            # Le joueur 1 (X) commence
            self.is_my_turn = (self.player_number == 1)
            self.show_game_board()
            self.update_turn_display()
            
        elif "Coup joué" in message:
            self.update_board_from_opponent(message)

    def parse_match_info(self, message):
        parts = message.split(',')
        match_id = int(parts[0].split(':')[1].strip())
        player_number = int(parts[1].split(':')[1].strip())
        return match_id, player_number

    def show_game_board(self):
        self.status_label.config(text="Match en cours...")
        
        # Créer le frame pour le plateau si il n'existe pas
        if not hasattr(self, 'board_frame'):
            self.board_frame = tk.Frame(self)
            self.board_frame.pack(pady=10)
            
            # Label pour afficher les informations du joueur
            self.player_info_label = tk.Label(self, text="", font=("Arial", 12, "bold"))
            self.player_info_label.pack(pady=5)
            
            # Label pour indiquer le tour
            self.turn_label = tk.Label(self, text="", font=("Arial", 10))
            self.turn_label.pack(pady=5)
            
            for i in range(3):
                row = []
                for j in range(3):
                    button = tk.Button(self.board_frame, text=" ", width=10, height=3, font=("Arial", 16, "bold"),
                                     command=lambda i=i, j=j: self.make_move(i, j))
                    button.grid(row=i, column=j, padx=2, pady=2)
                    row.append(button)
                self.board_buttons.append(row)
        
        # Afficher les informations du joueur
        self.player_info_label.config(text=f"Vous êtes le joueur {self.player_number} ({self.my_symbol})")

    def update_turn_display(self):
        """Met à jour l'affichage du tour"""
        if self.is_my_turn:
            self.turn_label.config(text="C'est votre tour !", fg="green")
        else:
            self.turn_label.config(text="Tour de l'adversaire...", fg="red")

    def make_move(self, i, j):
        """Effectue un coup si c'est le tour du joueur"""
        if not self.is_my_turn:
            messagebox.showwarning("Pas votre tour", "Attendez votre tour pour jouer !")
            return
            
        if self.board_buttons[i][j]["text"] != " ":
            messagebox.showwarning("Case occupée", "Cette case est déjà occupée !")
            return
        
        # Placer le symbole du joueur
        self.board_buttons[i][j]["text"] = self.my_symbol
        self.board_buttons[i][j]["fg"] = "blue"  # Couleur pour mes coups
        
        # Envoyer le coup au serveur
        self.send_move(i, j)
        
        # Vérifier la victoire ou match nul
        if self.check_victory():
            messagebox.showinfo("Victoire", f"Vous avez gagné !")
            self.reset_board()
            return
        elif self.check_draw():
            messagebox.showinfo("Match nul", "Le match est nul !")
            self.reset_board()
            return
        
        # Changer de tour
        self.is_my_turn = False
        self.update_turn_display()

    def send_move(self, i, j):
        """Envoie le coup au serveur"""
        move = f"{self.match_id},{self.player_number},{i}{j}"
        self.socket.sendall(move.encode())
        print(f"[CLIENT] Coup envoyé : {move}")  # Debug

    def update_board_from_opponent(self, message):
        """Met à jour le plateau avec le coup de l'adversaire"""
        try:
            parts = message.split(':')
            move = parts[1].strip()
            i, j = int(move[0]), int(move[1])
            
            # Le symbole de l'adversaire
            opponent_symbol = 'O' if self.my_symbol == 'X' else 'X'
            
            # Placer le coup de l'adversaire
            self.board_buttons[i][j]["text"] = opponent_symbol
            self.board_buttons[i][j]["fg"] = "red"  # Couleur pour les coups adverses
            
            print(f"[CLIENT] Coup adversaire reçu : {i},{j} -> {opponent_symbol}")  # Debug
            
            # Vérifier la victoire ou match nul
            if self.check_victory():
                messagebox.showinfo("Défaite", "Votre adversaire a gagné !")
                self.reset_board()
                return
            elif self.check_draw():
                messagebox.showinfo("Match nul", "Le match est nul !")
                self.reset_board()
                return
            
            # C'est maintenant mon tour
            self.is_my_turn = True
            self.update_turn_display()
            
        except Exception as e:
            print(f"[CLIENT] Erreur lors de la mise à jour du plateau : {e}")

    def check_victory(self):
        """Vérifie s'il y a une victoire"""
        board = [[self.board_buttons[i][j]["text"] for j in range(3)] for i in range(3)]
        
        # Vérifier les lignes
        for i in range(3):
            if board[i][0] == board[i][1] == board[i][2] != " ":
                return True
        
        # Vérifier les colonnes
        for j in range(3):
            if board[0][j] == board[1][j] == board[2][j] != " ":
                return True
        
        # Vérifier les diagonales
        if board[0][0] == board[1][1] == board[2][2] != " ":
            return True
        if board[0][2] == board[1][1] == board[2][0] != " ":
            return True
        
        return False

    def check_draw(self):
        """Vérifie s'il y a match nul"""
        return all(self.board_buttons[i][j]["text"] != " " for i in range(3) for j in range(3))

    def reset_board(self):
        """Remet le plateau à zéro"""
        for i in range(3):
            for j in range(3):
                self.board_buttons[i][j]["text"] = " "
                self.board_buttons[i][j]["fg"] = "black"
        
        # Réinitialiser le tour (le joueur 1 commence toujours)
        self.is_my_turn = (self.player_number == 1)
        self.update_turn_display()

if __name__ == "__main__":
    app = MatchmakingClient()
    app.mainloop()