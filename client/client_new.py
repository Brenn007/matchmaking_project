#!/usr/bin/env python3
"""
Client amélioré pour le jeu de Tic-Tac-Toe
Utilise le nouveau protocole de communication et l'architecture modulaire
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

from shared.protocol import Protocol, MessageType, GameMessages, GameState
from client.game_logic import ClientGameLogic
from client.ui_tkinter import GameUI

class ModernMatchmakingClient:
    def __init__(self):
        self.protocol = Protocol()
        self.game_messages = GameMessages()
        self.socket = None
        self.pseudo = None
        self.match_id = None
        self.player_number = None
        self.game_state = None
        self.is_connected = False
        self.is_in_game = False
          # Configuration du serveur
        self.server_ip = '127.0.0.1'  # Localhost pour la compatibilité
        self.server_port = 12345
        
        # Interface utilisateur
        self.root = tk.Tk()
        self.ui = GameUI(self.root, self.on_move, self.on_connect, self.on_disconnect)
        
        # Logique de jeu côté client
        self.game_logic = ClientGameLogic()
        
        # Thread pour écouter le serveur
        self.listen_thread = None
        self.running = False

    def on_connect(self, pseudo):
        """Callback pour la connexion au serveur"""
        if self.is_connected:
            messagebox.showwarning("Déjà connecté", "Vous êtes déjà connecté au serveur.")
            return
            
        self.pseudo = pseudo
        self.connect_to_server()

    def on_disconnect(self):
        """Callback pour la déconnexion du serveur"""
        self.disconnect_from_server()

    def on_move(self, row, col):
        """Callback pour un coup joué par le joueur"""
        if not self.is_in_game:
            messagebox.showwarning("Pas en jeu", "Vous n'êtes pas dans une partie.")
            return
            
        if not self.game_logic.is_my_turn():
            messagebox.showwarning("Pas votre tour", "Attendez votre tour pour jouer !")
            return
            
        if not self.game_logic.is_valid_move(row, col):
            messagebox.showwarning("Coup invalide", "Cette case est déjà occupée !")
            return
        
        # Effectuer le coup localement
        if self.game_logic.make_move(row, col):
            # Mettre à jour l'interface
            symbol = self.game_logic.get_my_symbol()
            self.ui.update_cell(row, col, symbol, is_my_move=True)
            
            # Envoyer le coup au serveur
            self.send_move(row, col)
            
            # Vérifier la fin de partie
            self.check_game_end()

    def connect_to_server(self):
        """Connexion au serveur"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.server_ip, self.server_port))
            
            # Envoyer le message de connexion
            connect_msg = self.game_messages.player_connect(self.pseudo)
            self.send_message(connect_msg)
            
            # Démarrer l'écoute du serveur
            self.running = True
            self.listen_thread = threading.Thread(target=self.listen_to_server, daemon=True)
            self.listen_thread.start()
            
            self.is_connected = True
            self.ui.set_status("Connecté au serveur. En attente d'un adversaire...")
            self.ui.set_connected(True)
            
        except Exception as e:
            messagebox.showerror("Erreur de connexion", f"Impossible de se connecter au serveur : {e}")
            self.socket = None

    def disconnect_from_server(self):
        """Déconnexion du serveur"""
        if not self.is_connected:
            return
            
        try:
            if self.is_in_game and self.match_id:
                # Envoyer un message de déconnexion
                disconnect_msg = self.game_messages.player_disconnect(self.match_id, self.player_number)
                self.send_message(disconnect_msg)
            
            self.running = False
            if self.socket:
                self.socket.close()
                
        except Exception as e:
            print(f"Erreur lors de la déconnexion : {e}")
        finally:
            self.is_connected = False
            self.is_in_game = False
            self.socket = None
            self.match_id = None
            self.player_number = None
            self.game_state = None
            
            self.ui.set_connected(False)
            self.ui.set_status("Déconnecté du serveur")
            self.ui.reset_board()

    def send_message(self, message_data):
        """Envoie un message au serveur en utilisant le protocole"""
        try:
            if self.socket:
                encoded_message = self.protocol.encode_message(message_data)
                self.socket.sendall(encoded_message)
                print(f"[CLIENT] Message envoyé : {message_data}")
        except Exception as e:
            print(f"[CLIENT] Erreur envoi message : {e}")
            self.handle_connection_error()

    def send_move(self, row, col):
        """Envoie un coup au serveur"""
        if self.match_id and self.player_number:
            move_msg = self.game_messages.player_move(
                self.match_id, 
                self.player_number, 
                row, 
                col
            )
            self.send_message(move_msg)

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

                    # Traiter tous les messages complets dans le buffer
                    while b'\n' in buffer:
                        line, buffer = buffer.split(b'\n', 1)
                        if line.strip():
                            message = json.loads(line.decode())
                            # Traiter le message dans le thread principal
                            self.root.after(0, self.process_server_message, message)

                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"[CLIENT] Erreur réception : {e}")
                    break
                    
        except Exception as e:
            print(f"[CLIENT] Erreur écoute serveur : {e}")
        finally:
            if self.running:
                self.root.after(0, self.handle_connection_error)

    def process_server_message(self, message):
        """Traite les messages du serveur dans le thread principal"""
        try:
            msg_type = message.get('type')
            print(f"[CLIENT] Message reçu : {message}")
            
            if msg_type == MessageType.MATCH_FOUND.value:
                self.handle_match_found(message)
                
            elif msg_type == MessageType.MOVE_RESULT.value:
                self.handle_move_result(message)
                
            elif msg_type == MessageType.GAME_END.value:
                self.handle_game_end(message)
                
            elif msg_type == MessageType.OPPONENT_MOVE.value:
                self.handle_opponent_move(message)
                
            elif msg_type == MessageType.TURN_UPDATE.value:
                self.handle_turn_update(message)
                
            elif msg_type == MessageType.ERROR.value:
                self.handle_error_message(message)
                
            elif msg_type == MessageType.STATUS.value:
                self.handle_status_message(message)
                
            else:
                print(f"[CLIENT] Message non géré : {message}")
                
        except Exception as e:
            print(f"[CLIENT] Erreur traitement message : {e}")

    def handle_match_found(self, message):
        """Gère le message de match trouvé"""
        data = message.get('data', {})
        self.match_id = data.get('match_id')
        self.player_number = data.get('player_number')
        opponent = data.get('opponent', 'Adversaire')
        
        # Initialiser la logique de jeu
        self.game_logic.start_new_game(self.player_number)
        self.game_state = GameState()
        
        self.is_in_game = True
        
        # Mettre à jour l'interface
        self.ui.show_game_board()
        self.ui.set_player_info(self.player_number, self.game_logic.get_my_symbol())
        self.ui.set_status(f"Match trouvé ! Contre {opponent}")
        
        # Le joueur 1 commence
        if self.player_number == 1:
            self.game_logic.set_my_turn(True)
            self.ui.set_turn_info(True)
        else:
            self.game_logic.set_my_turn(False)
            self.ui.set_turn_info(False)

    def handle_move_result(self, message):
        """Gère le résultat d'un coup"""
        data = message.get('data', {})
        valid = data.get('valid', False)
        reason = data.get('reason', '')
        
        if not valid:
            messagebox.showwarning("Coup invalide", reason)
            # Annuler le coup local si invalide
            # (normalement ne devrait pas arriver avec la validation côté client)

    def handle_opponent_move(self, message):
        """Gère un coup de l'adversaire"""
        data = message.get('data', {})
        row = data.get('row')
        col = data.get('col')
        player = data.get('player')
        
        if row is not None and col is not None:
            # Appliquer le coup dans la logique
            self.game_logic.apply_opponent_move(row, col)
            
            # Mettre à jour l'interface
            opponent_symbol = 'X' if self.player_number == 2 else 'O'
            self.ui.update_cell(row, col, opponent_symbol, is_my_move=False)
            
            # C'est maintenant mon tour
            self.game_logic.set_my_turn(True)
            self.ui.set_turn_info(True)
            
            # Vérifier la fin de partie
            self.check_game_end()

    def handle_turn_update(self, message):
        """Gère la mise à jour des tours"""
        data = message.get('data', {})
        current_player = data.get('current_player')
        
        is_my_turn = (current_player == self.player_number)
        self.game_logic.set_my_turn(is_my_turn)
        self.ui.set_turn_info(is_my_turn)

    def handle_game_end(self, message):
        """Gère la fin de partie"""
        data = message.get('data', {})
        result = data.get('result')  # 'win', 'lose', 'draw'
        winner = data.get('winner')
        
        if result == 'win':
            messagebox.showinfo("Victoire", "Félicitations ! Vous avez gagné !")
        elif result == 'lose':
            messagebox.showinfo("Défaite", "Dommage ! Votre adversaire a gagné.")
        elif result == 'draw':
            messagebox.showinfo("Match nul", "La partie se termine par un match nul.")
        
        # Réinitialiser pour une nouvelle partie
        self.reset_for_new_game()

    def handle_error_message(self, message):
        """Gère les messages d'erreur"""
        data = message.get('data', {})
        error_msg = data.get('message', 'Erreur inconnue')
        messagebox.showerror("Erreur", error_msg)

    def handle_status_message(self, message):
        """Gère les messages de statut"""
        data = message.get('data', {})
        status = data.get('message', '')
        self.ui.set_status(status)

    def handle_connection_error(self):
        """Gère les erreurs de connexion"""
        messagebox.showerror("Erreur de connexion", "Connexion perdue avec le serveur.")
        self.disconnect_from_server()

    def check_game_end(self):
        """Vérifie si la partie est terminée"""
        board = self.game_logic.get_board()
        
        # Vérifier la victoire
        winner = self.game_logic.check_winner(board)
        if winner:
            if winner == self.game_logic.get_my_symbol():
                self.ui.set_status("Vous avez gagné !")
            else:
                self.ui.set_status("Vous avez perdu !")
            return True
        
        # Vérifier le match nul
        if self.game_logic.is_board_full(board):
            self.ui.set_status("Match nul !")
            return True
        
        return False

    def reset_for_new_game(self):
        """Réinitialise pour une nouvelle partie"""
        self.game_logic.reset()
        self.ui.reset_board()
        self.is_in_game = False
        
        # Remettre en attente d'un nouveau match
        self.ui.set_status("En attente d'un nouvel adversaire...")

    def run(self):
        """Lance l'application"""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()

    def on_closing(self):
        """Gère la fermeture de l'application"""
        if self.is_connected:
            self.disconnect_from_server()
        self.root.destroy()


if __name__ == "__main__":
    client = ModernMatchmakingClient()
    client.run()