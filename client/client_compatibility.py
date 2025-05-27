#!/usr/bin/env python3
"""
Client de compatibilité - Compatible avec l'ancien et le nouveau protocole
"""

import tkinter as tk
from tkinter import messagebox
import socket
import threading
import json
import sys
import os

# Ajouter le dossier parent au chemin pour importer shared
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from shared.protocol import Protocol, MessageType, GameMessages
    NEW_PROTOCOL_AVAILABLE = True
except ImportError:
    NEW_PROTOCOL_AVAILABLE = False
    print("Nouveau protocole non disponible, utilisation du mode compatibilité")

SERVER_IP = '127.0.0.1'  # Localhost pour la compatibilité
SERVER_PORT = 12345

class CompatibilityMatchmakingClient(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Client de Matchmaking (Compatible)")
        self.geometry("350x450")
        
        # Configuration du protocole
        if NEW_PROTOCOL_AVAILABLE:
            self.protocol = Protocol()
            self.game_messages = GameMessages()
            self.use_new_protocol = True
        else:
            self.use_new_protocol = False
        
        # Interface utilisateur
        self.setup_ui()
        
        # Variables de jeu
        self.socket = None
        self.board_buttons = []
        self.match_id = None
        self.player_number = None
        self.my_symbol = None
        self.current_turn = 1
        self.is_my_turn = False
        self.is_connected = False
        self.is_in_game = False
        
        # Threading
        self.running = False

    def setup_ui(self):
        """Configure l'interface utilisateur"""
        # Frame de connexion
        connection_frame = tk.Frame(self)
        connection_frame.pack(pady=10)
        
        self.pseudo_label = tk.Label(connection_frame, text="Entrez votre pseudo :")
        self.pseudo_label.pack(pady=5)
        
        self.pseudo_entry = tk.Entry(connection_frame)
        self.pseudo_entry.pack(pady=5)
        
        button_frame = tk.Frame(connection_frame)
        button_frame.pack(pady=5)
        
        self.connect_button = tk.Button(button_frame, text="Se connecter", command=self.connect_to_server)
        self.connect_button.pack(side=tk.LEFT, padx=5)
        
        self.disconnect_button = tk.Button(button_frame, text="Se déconnecter", command=self.disconnect_from_server, state=tk.DISABLED)
        self.disconnect_button.pack(side=tk.LEFT, padx=5)
        
        # Label de statut
        self.status_label = tk.Label(self, text="Entrez votre pseudo et connectez-vous", wraplength=300)
        self.status_label.pack(pady=10)
        
        # Indicateur de protocole
        protocol_text = "Nouveau protocole" if self.use_new_protocol else "Mode compatibilité"
        self.protocol_label = tk.Label(self, text=f"Mode: {protocol_text}", font=("Arial", 8), fg="gray")
        self.protocol_label.pack()

    def connect_to_server(self):
        """Connexion au serveur"""
        pseudo = self.pseudo_entry.get().strip()
        if not pseudo:
            messagebox.showwarning("Pseudo manquant", "Veuillez entrer un pseudo.")
            return
        
        if self.is_connected:
            messagebox.showwarning("Déjà connecté", "Vous êtes déjà connecté au serveur.")
            return
        
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((SERVER_IP, SERVER_PORT))
            
            # Envoyer le message de connexion selon le protocole
            if self.use_new_protocol:
                connect_msg = self.game_messages.player_connect(pseudo)
                self.send_message_new_protocol(connect_msg)
            else:
                # Ancien protocole - envoyer juste le pseudo
                self.socket.sendall(pseudo.encode())
            
            self.is_connected = True
            self.running = True
            
            # Démarrer l'écoute du serveur
            threading.Thread(target=self.listen_to_server, daemon=True).start()
            
            # Mettre à jour l'interface
            self.status_label.config(text="Connecté au serveur. En attente d'un adversaire...")
            self.connect_button.config(state=tk.DISABLED)
            self.disconnect_button.config(state=tk.NORMAL)
            self.pseudo_entry.config(state=tk.DISABLED)
            
        except Exception as e:
            messagebox.showerror("Erreur de connexion", f"Impossible de se connecter au serveur : {e}")
            self.socket = None

    def disconnect_from_server(self):
        """Déconnexion du serveur"""
        if not self.is_connected:
            return
        
        try:
            if self.is_in_game and self.match_id and self.use_new_protocol:
                # Envoyer un message de déconnexion avec le nouveau protocole
                disconnect_msg = self.game_messages.player_disconnect(self.match_id, self.player_number)
                self.send_message_new_protocol(disconnect_msg)
            
            self.running = False
            if self.socket:
                self.socket.close()
                
        except Exception as e:
            print(f"Erreur lors de la déconnexion : {e}")
        finally:
            self.cleanup_connection()

    def cleanup_connection(self):
        """Nettoie l'état de connexion"""
        self.is_connected = False
        self.is_in_game = False
        self.socket = None
        self.match_id = None
        self.player_number = None
        self.my_symbol = None
        
        # Mettre à jour l'interface
        self.status_label.config(text="Déconnecté du serveur")
        self.connect_button.config(state=tk.NORMAL)
        self.disconnect_button.config(state=tk.DISABLED)
        self.pseudo_entry.config(state=tk.NORMAL)
        
        # Masquer le plateau s'il est affiché
        if hasattr(self, 'board_frame'):
            self.board_frame.destroy()
            self.board_buttons = []

    def send_message_new_protocol(self, message_data):
        """Envoie un message avec le nouveau protocole"""
        try:
            if self.socket:
                encoded_message = self.protocol.encode_message(message_data)
                self.socket.sendall(encoded_message)
                print(f"[CLIENT] Message envoyé (nouveau protocole) : {message_data}")
        except Exception as e:
            print(f"[CLIENT] Erreur envoi message : {e}")
            self.handle_connection_error()

    def send_message_old_protocol(self, message):
        """Envoie un message avec l'ancien protocole"""
        try:
            if self.socket:
                self.socket.sendall(message.encode())
                print(f"[CLIENT] Message envoyé (ancien protocole) : {message}")
        except Exception as e:
            print(f"[CLIENT] Erreur envoi message : {e}")
            self.handle_connection_error()

    def listen_to_server(self):
        """Écoute les messages du serveur"""
        buffer = b""
        
        try:
            while self.running and self.socket:
                try:
                    data = self.socket.recv(1024)
                    if not data:
                        break
                    
                    buffer += data
                    
                    if self.use_new_protocol:
                        # Traiter avec le nouveau protocole
                        while True:
                            try:
                                message, remaining_buffer = self.protocol.decode_message(buffer)
                                buffer = remaining_buffer
                                self.after(0, self.process_server_message_new_protocol, message)
                            except json.JSONDecodeError:
                                break
                            except Exception as e:
                                print(f"[CLIENT] Erreur décodage : {e}")
                                break
                    else:
                        # Traiter avec l'ancien protocole
                        try:
                            message = buffer.decode()
                            buffer = b""
                            self.after(0, self.process_server_message_old_protocol, message)
                        except UnicodeDecodeError:
                            # Message incomplet, attendre plus de données
                            continue
                        
                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"[CLIENT] Erreur réception : {e}")
                    break
                    
        except Exception as e:
            print(f"[CLIENT] Erreur écoute serveur : {e}")
        finally:
            if self.running:
                self.after(0, self.handle_connection_error)

    def process_server_message_new_protocol(self, message):
        """Traite les messages du nouveau protocole"""
        try:
            msg_type = message.get('type')
            print(f"[CLIENT] Message reçu (nouveau) : {message}")
            
            if msg_type == MessageType.MATCH_FOUND.value:
                self.handle_match_found_new(message)
            elif msg_type == MessageType.OPPONENT_MOVE.value:
                self.handle_opponent_move_new(message)
            elif msg_type == MessageType.GAME_END.value:
                self.handle_game_end_new(message)
            elif msg_type == MessageType.ERROR.value:
                self.handle_error_new(message)
            elif msg_type == MessageType.STATUS.value:
                self.handle_status_new(message)
            else:
                print(f"[CLIENT] Message non géré : {message}")
                
        except Exception as e:
            print(f"[CLIENT] Erreur traitement message nouveau protocole : {e}")

    def process_server_message_old_protocol(self, message):
        """Traite les messages de l'ancien protocole"""
        print(f"[CLIENT] Message reçu (ancien) : {message}")
        self.status_label.config(text=message)
        
        if "Match trouvé" in message:
            self.match_id, self.player_number = self.parse_match_info_old(message)
            self.my_symbol = 'X' if self.player_number == 1 else 'O'
            self.is_my_turn = (self.player_number == 1)
            self.is_in_game = True
            self.show_game_board()
            self.update_turn_display()
            
        elif "Coup joué" in message:
            self.update_board_from_opponent_old(message)

    def handle_match_found_new(self, message):
        """Gère match trouvé (nouveau protocole)"""
        data = message.get('data', {})
        self.match_id = data.get('match_id')
        self.player_number = data.get('player_number')
        opponent = data.get('opponent', 'Adversaire')
        
        self.my_symbol = 'X' if self.player_number == 1 else 'O'
        self.is_my_turn = (self.player_number == 1)
        self.is_in_game = True
        
        self.show_game_board()
        self.status_label.config(text=f"Match trouvé ! Contre {opponent}")
        self.update_turn_display()

    def handle_opponent_move_new(self, message):
        """Gère coup adversaire (nouveau protocole)"""
        data = message.get('data', {})
        row = data.get('row')
        col = data.get('col')
        
        if row is not None and col is not None:
            opponent_symbol = 'O' if self.my_symbol == 'X' else 'X'
            self.board_buttons[row][col]["text"] = opponent_symbol
            self.board_buttons[row][col]["fg"] = "red"
            
            self.is_my_turn = True
            self.update_turn_display()
            
            if self.check_victory() or self.check_draw():
                self.handle_game_end_local()

    def handle_game_end_new(self, message):
        """Gère fin de partie (nouveau protocole)"""
        data = message.get('data', {})
        result = data.get('result')
        
        if result == 'win':
            messagebox.showinfo("Victoire", "Félicitations ! Vous avez gagné !")
        elif result == 'lose':
            messagebox.showinfo("Défaite", "Dommage ! Votre adversaire a gagné.")
        elif result == 'draw':
            messagebox.showinfo("Match nul", "La partie se termine par un match nul.")
        
        self.reset_for_new_game()

    def handle_error_new(self, message):
        """Gère erreurs (nouveau protocole)"""
        data = message.get('data', {})
        error_msg = data.get('message', 'Erreur inconnue')
        messagebox.showerror("Erreur", error_msg)

    def handle_status_new(self, message):
        """Gère statuts (nouveau protocole)"""
        data = message.get('data', {})
        status = data.get('message', '')
        self.status_label.config(text=status)

    def parse_match_info_old(self, message):
        """Parse info match (ancien protocole)"""
        parts = message.split(',')
        match_id = int(parts[0].split(':')[1].strip())
        player_number = int(parts[1].split(':')[1].strip())
        return match_id, player_number

    def update_board_from_opponent_old(self, message):
        """Met à jour plateau adversaire (ancien protocole)"""
        try:
            parts = message.split(':')
            move = parts[1].strip()
            i, j = int(move[0]), int(move[1])
            
            opponent_symbol = 'O' if self.my_symbol == 'X' else 'X'
            self.board_buttons[i][j]["text"] = opponent_symbol
            self.board_buttons[i][j]["fg"] = "red"
            
            if self.check_victory() or self.check_draw():
                self.handle_game_end_local()
            else:
                self.is_my_turn = True
                self.update_turn_display()
                
        except Exception as e:
            print(f"[CLIENT] Erreur mise à jour plateau : {e}")

    def show_game_board(self):
        """Affiche le plateau de jeu"""
        if hasattr(self, 'board_frame'):
            self.board_frame.destroy()
        
        self.board_frame = tk.Frame(self)
        self.board_frame.pack(pady=10)
        
        # Informations joueur
        self.player_info_label = tk.Label(self, text=f"Vous êtes le joueur {self.player_number} ({self.my_symbol})", 
                                        font=("Arial", 12, "bold"))
        self.player_info_label.pack(pady=5)
        
        # Indicateur de tour
        self.turn_label = tk.Label(self, text="", font=("Arial", 10))
        self.turn_label.pack(pady=5)
        
        # Plateau 3x3
        self.board_buttons = []
        for i in range(3):
            row = []
            for j in range(3):
                button = tk.Button(self.board_frame, text=" ", width=8, height=3, 
                                 font=("Arial", 16, "bold"),
                                 command=lambda i=i, j=j: self.make_move(i, j))
                button.grid(row=i, column=j, padx=2, pady=2)
                row.append(button)
            self.board_buttons.append(row)

    def update_turn_display(self):
        """Met à jour l'affichage du tour"""
        if hasattr(self, 'turn_label'):
            if self.is_my_turn:
                self.turn_label.config(text="C'est votre tour !", fg="green")
            else:
                self.turn_label.config(text="Tour de l'adversaire...", fg="red")

    def make_move(self, i, j):
        """Effectue un coup"""
        if not self.is_in_game:
            messagebox.showwarning("Pas en jeu", "Vous n'êtes pas dans une partie.")
            return
            
        if not self.is_my_turn:
            messagebox.showwarning("Pas votre tour", "Attendez votre tour pour jouer !")
            return
            
        if self.board_buttons[i][j]["text"] != " ":
            messagebox.showwarning("Case occupée", "Cette case est déjà occupée !")
            return
        
        # Placer le symbole
        self.board_buttons[i][j]["text"] = self.my_symbol
        self.board_buttons[i][j]["fg"] = "blue"
        
        # Envoyer le coup
        if self.use_new_protocol:
            move_msg = self.game_messages.player_move(self.match_id, self.player_number, i, j)
            self.send_message_new_protocol(move_msg)
        else:
            move = f"{self.match_id},{self.player_number},{i}{j}"
            self.send_message_old_protocol(move)
        
        # Vérifier fin de partie
        if self.check_victory() or self.check_draw():
            self.handle_game_end_local()
        else:
            self.is_my_turn = False
            self.update_turn_display()

    def check_victory(self):
        """Vérifie victoire"""
        board = [[self.board_buttons[i][j]["text"] for j in range(3)] for i in range(3)]
        
        # Lignes
        for i in range(3):
            if board[i][0] == board[i][1] == board[i][2] != " ":
                return True
        
        # Colonnes
        for j in range(3):
            if board[0][j] == board[1][j] == board[2][j] != " ":
                return True
        
        # Diagonales
        if board[0][0] == board[1][1] == board[2][2] != " ":
            return True
        if board[0][2] == board[1][1] == board[2][0] != " ":
            return True
        
        return False

    def check_draw(self):
        """Vérifie match nul"""
        return all(self.board_buttons[i][j]["text"] != " " for i in range(3) for j in range(3))

    def handle_game_end_local(self):
        """Gère fin de partie locale"""
        if self.check_victory():
            winner_symbol = None
            board = [[self.board_buttons[i][j]["text"] for j in range(3)] for i in range(3)]
            
            # Trouver le gagnant
            for i in range(3):
                if board[i][0] == board[i][1] == board[i][2] != " ":
                    winner_symbol = board[i][0]
                    break
            
            if not winner_symbol:
                for j in range(3):
                    if board[0][j] == board[1][j] == board[2][j] != " ":
                        winner_symbol = board[0][j]
                        break
            
            if not winner_symbol:
                if board[0][0] == board[1][1] == board[2][2] != " ":
                    winner_symbol = board[0][0]
                elif board[0][2] == board[1][1] == board[2][0] != " ":
                    winner_symbol = board[0][2]
            
            if winner_symbol == self.my_symbol:
                messagebox.showinfo("Victoire", "Vous avez gagné !")
            else:
                messagebox.showinfo("Défaite", "Votre adversaire a gagné !")
        else:
            messagebox.showinfo("Match nul", "Le match est nul !")
        
        self.reset_for_new_game()

    def reset_for_new_game(self):
        """Réinitialise pour nouvelle partie"""
        if hasattr(self, 'board_frame'):
            for i in range(3):
                for j in range(3):
                    self.board_buttons[i][j]["text"] = " "
                    self.board_buttons[i][j]["fg"] = "black"
        
        self.is_in_game = False
        self.is_my_turn = False
        self.status_label.config(text="En attente d'un nouvel adversaire...")

    def handle_connection_error(self):
        """Gère erreurs de connexion"""
        messagebox.showerror("Erreur de connexion", "Connexion perdue avec le serveur.")
        self.cleanup_connection()

    def on_closing(self):
        """Gère fermeture application"""
        if self.is_connected:
            self.disconnect_from_server()
        self.destroy()


if __name__ == "__main__":
    app = CompatibilityMatchmakingClient()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
