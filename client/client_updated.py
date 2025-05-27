import tkinter as tk
from tkinter import messagebox
import socket
import threading
import json

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
            buffer = ""
            while True:
                data = self.socket.recv(1024).decode()
                if not data:
                    break
                
                buffer += data
                print(f"[CLIENT] Données reçues : {data}")  # Debug
                
                # Traiter tous les messages JSON complets dans le buffer
                while buffer:
                    try:
                        # Trouver la fin du premier objet JSON
                        json_end = buffer.find("}")
                        if json_end == -1:
                            break  # Pas de JSON complet
                        
                        # Extraire le message JSON
                        json_text = buffer[:json_end+1]
                        
                        # Tenter de parser le JSON pour vérifier qu'il est complet
                        message = json.loads(json_text)
                        
                        # Si on arrive ici, c'est un JSON valide
                        print(f"[CLIENT] Message traité : {json_text}")
                        
                        # Traiter le message dans le thread principal
                        self.after(0, self.process_server_message, json_text)
                        
                        # Retirer ce message du buffer
                        buffer = buffer[json_end+1:]
                    except json.JSONDecodeError:
                        # JSON incomplet, attendre plus de données
                        break
                    except Exception as e:
                        print(f"[CLIENT] Erreur de traitement JSON: {e}")
                        break
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Erreur", f"Erreur de communication avec le serveur : {e}"))
            self.socket = None

    def process_server_message(self, message):
        """Traite les messages du serveur dans le thread principal"""
        try:
            msg = json.loads(message)
            msg_type = msg.get("type")
            data = msg.get("data", {})
            
            # Mettre à jour le label de statut
            status_text = f"Message reçu : {msg_type}"
            self.status_label.config(text=status_text)
            
            if msg_type == "match_found":
                # Match trouvé, récupérer les infos
                self.match_id = data.get("match_id")
                self.player_number = data.get("player_number")
                opponent_name = data.get("opponent_name")
                
                # Définir le symbole du joueur
                self.my_symbol = data.get("symbol")
                
                # Le joueur 1 (X) commence
                self.is_my_turn = (self.player_number == 1)
                
                # Afficher le plateau
                self.show_game_board()
                self.update_turn_display()
                
            elif msg_type == "game_state":
                # État du jeu
                board_state = data.get("board_state", "")
                self.current_turn = data.get("current_turn")
                self.is_my_turn = data.get("is_your_turn", False)
                
                # Mettre à jour l'affichage du plateau si nécessaire
                self.update_board_display(board_state)
                self.update_turn_display()
                
            elif msg_type == "move_result":
                # Résultat d'un coup
                success = data.get("success", False)
                message = data.get("message", "")
                
                if not success:
                    messagebox.showwarning("Coup invalide", message)
                    
            elif msg_type == "game_end":
                # Fin de partie
                winner = data.get("winner")
                reason = data.get("reason", "")
                final_board = data.get("final_board", "")
                
                # Mettre à jour le plateau final
                if final_board:
                    self.update_board_display(final_board)
                
                # Afficher le résultat
                messagebox.showinfo("Fin du match", reason)
                
                # Réinitialiser le plateau après confirmation
                self.reset_board()
                
            elif msg_type == "queue_status":
                # Statut de la file d'attente
                position = data.get("position", 0)
                total = data.get("total_players", 0)
                message = data.get("message", "")
                
                self.status_label.config(text=f"En file d'attente : {position}/{total}")
                
        except json.JSONDecodeError:
            print(f"[CLIENT] Impossible de décoder le message JSON: {message}")
        except Exception as e:
            print(f"[CLIENT] Erreur lors du traitement du message: {e}")

    def update_board_display(self, board_state):
        """Met à jour l'affichage du plateau avec l'état donné"""
        if len(board_state) != 9 or not hasattr(self, 'board_buttons'):
            return
            
        for i in range(3):
            for j in range(3):
                index = i * 3 + j
                cell = board_state[index]
                
                if cell == 'X':
                    self.board_buttons[i][j]["text"] = 'X'
                    self.board_buttons[i][j]["fg"] = "blue" if self.my_symbol == 'X' else "red"
                elif cell == 'O':
                    self.board_buttons[i][j]["text"] = 'O'
                    self.board_buttons[i][j]["fg"] = "blue" if self.my_symbol == 'O' else "red"
                else:
                    self.board_buttons[i][j]["text"] = " "

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
            
            # Créer le plateau de jeu
            self.board_buttons = []
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
        
        # On ne vérifie plus la victoire localement car le serveur nous enverra l'état du jeu mis à jour
        
        # Changer de tour en attendant la confirmation du serveur
        self.is_my_turn = False
        self.update_turn_display()

    def send_move(self, i, j):
        """Envoie le coup au serveur"""
        try:
            # Format JSON pour la compatibilité avec le protocole
            move_data = json.dumps({
                "type": "make_move",
                "data": {
                    "match_id": self.match_id,
                    "player_number": self.player_number,
                    "position_x": i,
                    "position_y": j
                }
            }).encode('utf-8')
            
            self.socket.sendall(move_data)
            print(f"[CLIENT] Coup envoyé : {i},{j}")
        except Exception as e:
            print(f"[CLIENT] Erreur lors de l'envoi du coup : {e}")

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
