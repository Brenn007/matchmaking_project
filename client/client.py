import tkinter as tk
from tkinter import messagebox
import socket
import threading
import json
import sys
import os

# Ajouter le dossier parent au chemin pour importer shared
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
        """Écoute les messages du serveur"""
        buffer = b""
        
        try:
            while self.socket:
                try:
                    data = self.socket.recv(1024)
                    if not data:
                        break
                        
                    buffer += data
                    
                    # Traiter tous les messages complets dans le buffer
                    while b'\n' in buffer:
                        line, buffer = buffer.split(b'\n', 1)
                        if line.strip():
                            # Décoder le message JSON
                            try:
                                message = json.loads(line.decode())
                                # Traiter le message dans le thread principal
                                self.after(0, self.process_server_message, message)
                            except json.JSONDecodeError as e:
                                print(f"[CLIENT] Erreur décodage JSON : {e}, message: {line}")
                                
                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"[CLIENT] Erreur réception : {e}")
                    break
                    
        except Exception as e:
            print(f"[CLIENT] Erreur écoute serveur : {e}")
        finally:
            self.after(0, self.handle_connection_error)

    def process_server_message(self, message):
        """Traite les messages du serveur dans le thread principal"""
        try:
            print(f"[CLIENT] Message reçu : {message}")
            
            msg_type = message.get('type')
            data = message.get('data', {})
            
            if msg_type == "match_found":
                self.handle_match_found(data)
                
            elif msg_type == "game_state":
                self.handle_game_state(data)
                
            elif msg_type == "move_result":
                self.handle_move_result(data)
                
            elif msg_type == "game_end":
                self.handle_game_end(data)
                
            elif msg_type == "queue_status":
                self.handle_queue_status(data)
                
            else:
                print(f"[CLIENT] Type de message non reconnu : {msg_type}")
                
        except Exception as e:
            print(f"[CLIENT] Erreur traitement message : {e}")

    def handle_match_found(self, data):
        """Gère la notification de match trouvé"""
        match_id = data.get('match_id')
        player_number = data.get('player_number')
        opponent = data.get('opponent_name', 'Adversaire')
        
        self.match_id = match_id
        self.player_number = player_number
        
        # Déterminer mon symbole
        if player_number == 1:
            self.my_symbol = 'X'
        else:
            self.my_symbol = 'O'
        
        # C'est toujours au joueur 1 (X) de commencer
        self.is_my_turn = (player_number == 1)
        
        self.status_label.config(text=f"Match trouvé contre {opponent} ! Vous êtes {self.my_symbol}")
        
        # Créer le plateau de jeu
        self.create_game_board()

    def handle_game_state(self, data):
        """Gère la mise à jour de l'état du jeu"""
        board_state = data.get('board_state', '         ')  # 9 espaces par défaut
        current_turn = data.get('current_turn', 1)
        is_your_turn = data.get('is_your_turn', False)
        
        self.current_turn = current_turn
        self.is_my_turn = is_your_turn
        
        # Mettre à jour le plateau
        self.update_board(board_state)
        
        # Mettre à jour le statut
        if is_your_turn:
            self.status_label.config(text="C'est votre tour de jouer !")
        else:
            self.status_label.config(text="En attente du coup de l'adversaire...")

    def handle_move_result(self, data):
        """Gère le résultat d'un coup joué"""
        valid = data.get('valid', False)
        reason = data.get('reason', '')
        
        if not valid:
            messagebox.showwarning("Coup invalide", reason)
            # Le serveur va renvoyer l'état du jeu correct

    def handle_game_end(self, data):
        """Gère la fin de la partie"""
        winner = data.get('winner')
        reason = data.get('reason', 'Partie terminée')
        board = data.get('final_board', '         ')
        
        # Mettre à jour le plateau une dernière fois
        self.update_board(board)
        
        # Déterminer le message de fin
        if winner is None:
            message = "Match nul !"
        elif (self.player_number == 1 and winner == "player1") or \
             (self.player_number == 2 and winner == "player2"):
            message = "Vous avez gagné !"
        else:
            message = "Vous avez perdu !"
        
        messagebox.showinfo("Fin de partie", f"{message}\n{reason}")
        
        # Remettre à zéro
        self.reset_game()

    def handle_queue_status(self, data):
        """Gère les mises à jour de la file d'attente"""
        position = data.get('position', 1)
        total = data.get('total_players', 1)
        
        self.status_label.config(text=f"Position dans la file: {position}/{total}")

    def handle_connection_error(self):
        """Gère la perte de connexion"""
        messagebox.showerror("Erreur de connexion", "Connexion perdue avec le serveur")
        self.reset_game()
        
        if self.socket:
            self.socket.close()
            self.socket = None

    def create_game_board(self):
        """Crée le plateau de jeu"""
        # Supprimer l'interface de connexion
        for widget in self.winfo_children():
            widget.destroy()
        
        # Créer le titre
        title_label = tk.Label(self, text="Tic-Tac-Toe", font=("Arial", 16))
        title_label.grid(row=0, column=0, columnspan=3, pady=10)
        
        # Créer le plateau
        self.board_frame = tk.Frame(self)
        self.board_frame.grid(row=1, column=0, columnspan=3)
        
        self.board_buttons = []
        for i in range(3):
            for j in range(3):
                btn = tk.Button(
                    self.board_frame, 
                    text=" ", 
                    font=("Arial", 20), 
                    width=3, height=1,
                    command=lambda r=i, c=j: self.make_move(r, c)
                )
                btn.grid(row=i, column=j)
                self.board_buttons.append(btn)
        
        # Statut
        self.status_label = tk.Label(
            self, 
            text="C'est votre tour !" if self.is_my_turn else "En attente de l'adversaire...",
            font=("Arial", 12)
        )
        self.status_label.grid(row=2, column=0, columnspan=3, pady=10)
        
        # Informations
        player_info = tk.Label(
            self,
            text=f"Vous êtes le joueur {self.player_number} ({self.my_symbol})",
            font=("Arial", 10)
        )
        player_info.grid(row=3, column=0, columnspan=3, pady=5)

    def update_board(self, board_state):
        """Met à jour le plateau avec l'état reçu"""
        if not self.board_buttons:
            return  # Plateau pas encore créé
            
        for i, char in enumerate(board_state):
            if i < len(self.board_buttons):
                if char == " ":
                    self.board_buttons[i].config(text=" ")
                else:
                    self.board_buttons[i].config(text=char)

    def make_move(self, row, col):
        """Joue un coup"""
        if not self.is_my_turn:
            messagebox.showwarning("Pas votre tour", "Attendez votre tour pour jouer !")
            return
            
        # Calculer l'index dans le tableau 1D
        index = row * 3 + col
        
        # Vérifier si la case est libre
        if self.board_buttons[index]['text'] != " ":
            messagebox.showwarning("Coup invalide", "Cette case est déjà occupée !")
            return
            
        # Envoyer le coup au serveur
        try:
            message = json.dumps({
                "type": "player_move",
                "data": {
                    "match_id": self.match_id,
                    "player_number": self.player_number,
                    "position_x": row,
                    "position_y": col
                }
            }).encode() + b'\n'
            
            self.socket.sendall(message)
            
            # Mettre à jour localement (le serveur confirmera)
            self.board_buttons[index].config(text=self.my_symbol)
            self.is_my_turn = False
            self.status_label.config(text="En attente de la confirmation du serveur...")
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible d'envoyer le coup : {e}")

    def reset_game(self):
        """Réinitialise l'interface pour une nouvelle partie"""
        self.match_id = None
        self.player_number = None
        self.my_symbol = None
        self.is_my_turn = False
        
        # Recréer l'interface de connexion
        for widget in self.winfo_children():
            widget.destroy()
            
        self.pseudo_label = tk.Label(self, text="Entrez votre pseudo :")
        self.pseudo_label.pack(pady=10)
        
        self.pseudo_entry = tk.Entry(self)
        self.pseudo_entry.pack(pady=5)
        
        self.connect_button = tk.Button(self, text="Se connecter", command=self.connect_to_server)
        self.connect_button.pack(pady=10)
        
        self.status_label = tk.Label(self, text="")
        self.status_label.pack(pady=10)

if __name__ == "__main__":
    client = MatchmakingClient()
    client.mainloop()
