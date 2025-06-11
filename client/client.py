import tkinter as tk
from tkinter import messagebox
import socket
import threading
import json

SERVER_IP = '10.31.32.143'
SERVER_PORT = 12345

class MatchmakingClient(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Client de Matchmaking TicTacToe")
        self.geometry("320x480")
        self.resizable(False, False)
        
        # Interface de connexion
        self.pseudo_label = tk.Label(self, text="Entrez votre pseudo :", font=("Arial", 12))
        self.pseudo_label.pack(pady=5)
        
        self.pseudo_entry = tk.Entry(self, font=("Arial", 11), width=20)
        self.pseudo_entry.pack(pady=5)
        
        self.connect_button = tk.Button(self, text="Se connecter", command=self.connect_to_server,
                                      bg="#4CAF50", fg="white", font=("Arial", 11), padx=20, pady=5)
        self.connect_button.pack(pady=5)
        
        self.status_label = tk.Label(self, text="", font=("Arial", 10), fg="blue", wraplength=300)
        self.status_label.pack(pady=5)
        
        # Variables de jeu
        self.socket = None
        self.board_frame = None
        self.board_buttons = []
        self.match_id = None
        self.player_number = None
        self.my_symbol = None
        self.opponent_symbol = None
        self.is_my_turn = False
        self.game_started = False
        
        # Label pour afficher le tour actuel
        self.turn_label = tk.Label(self, text="", font=("Arial", 12, "bold"))
        self.turn_label.pack(pady=3)
        
        # Frame pour les contrôles de fin de partie
        self.game_controls_frame = tk.Frame(self)
        self.game_controls_frame.pack(pady=10)
        
        # Bouton rejouer (caché initialement)
        self.replay_button = tk.Button(self.game_controls_frame, text="🔄 Rejouer", 
                                     command=self.request_new_game,
                                     bg="#2196F3", fg="white", font=("Arial", 11, "bold"), 
                                     padx=20, pady=8)
        # Le bouton n'est pas packed initialement
        
        # Bouton quitter (caché initialement)
        self.quit_button = tk.Button(self.game_controls_frame, text="❌ Quitter", 
                                   command=self.quit_game,
                                   bg="#f44336", fg="white", font=("Arial", 11, "bold"), 
                                   padx=20, pady=8)
        # Le bouton n'est pas packed initialement

    def connect_to_server(self):
        pseudo = self.pseudo_entry.get().strip()
        if not pseudo:
            messagebox.showwarning("Pseudo manquant", "Veuillez entrer un pseudo.")
            return
        
        # Désactiver le bouton de connexion
        self.connect_button.config(state=tk.DISABLED)
        
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
            self.connect_button.config(state=tk.NORMAL)

    def listen_to_server(self):
        """Thread qui écoute les messages du serveur"""
        buffer = ""
        try:
            while True:
                data = self.socket.recv(1024).decode()
                if not data:
                    break
                
                buffer += data
                
                # Traiter chaque ligne complète
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line.strip():
                        self.process_server_message(line.strip())
                        
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Erreur", f"Connexion perdue : {e}"))
            self.socket = None
        finally:
            self.after(0, self.disconnect)

    def process_server_message(self, message):
        """Traite les messages reçus du serveur"""
        try:
            # Essayer de parser comme JSON
            data = json.loads(message)
            
            if data['type'] == 'match_found':
                self.match_id = data['match_id']
                self.player_number = data['player_number']
                self.my_symbol = 'X' if self.player_number == 1 else 'O'
                self.opponent_symbol = 'O' if self.player_number == 1 else 'X'
                
                self.after(0, lambda: self.status_label.config(
                    text=f"Match trouvé! Vous êtes le joueur {self.player_number} ({self.my_symbol})"))
                self.after(0, self.create_game_board)
                
            elif data['type'] == 'game_state':
                self.after(0, lambda: self.update_game_state(data))
                
        except json.JSONDecodeError:
            # Message non-JSON (ancien format)
            self.after(0, lambda: self.status_label.config(text=message))

    def create_game_board(self):
        """Crée le plateau de jeu"""
        if self.board_frame:
            self.board_frame.destroy()
        
        # Cacher les boutons de contrôle
        self.hide_game_controls()
        
        self.board_frame = tk.Frame(self, bg="#f0f0f0", relief=tk.RAISED, bd=2)
        self.board_frame.pack(pady=10)
        
        self.board_buttons = []
        for i in range(3):
            row = []
            for j in range(3):
                button = tk.Button(self.board_frame, text=" ", width=3, height=1,
                                 font=("Arial", 20, "bold"),
                                 command=lambda r=i, c=j: self.make_move(r, c),
                                 bg="white", relief=tk.RAISED, bd=2)
                button.grid(row=i, column=j, padx=1, pady=1)
                row.append(button)
            self.board_buttons.append(row)
        
        self.game_started = True

    def update_game_state(self, state):
        """Met à jour l'interface selon l'état du jeu reçu du serveur"""
        if not self.game_started:
            return
        
        # Mettre à jour le plateau
        board = state['board']
        for i in range(3):
            for j in range(3):
                symbol = board[i * 3 + j]
                self.board_buttons[i][j]['text'] = symbol if symbol != ' ' else ' '
                
                # Colorer les cases selon le joueur
                if symbol == 'X':
                    self.board_buttons[i][j].config(bg="#ffcccc", fg="#cc0000")  # Rouge clair avec texte rouge foncé
                elif symbol == 'O':
                    self.board_buttons[i][j].config(bg="#ccccff", fg="#0000cc")  # Bleu clair avec texte bleu foncé
                else:
                    self.board_buttons[i][j].config(bg="white", fg="black")
        
        # Mettre à jour le statut du tour
        self.is_my_turn = (state['current_turn'] == self.player_number and not state['is_finished'])
        
        if state['is_finished']:
            # Partie terminée - Afficher le résultat et les boutons
            if state['winner'] == 0:
                self.turn_label.config(text="🤝 Match nul!", fg="orange", font=("Arial", 14, "bold"))
            elif state['winner'] == self.player_number:
                self.turn_label.config(text="🎉 Vous avez gagné!", fg="green", font=("Arial", 14, "bold"))
            else:
                self.turn_label.config(text="😔 Vous avez perdu", fg="red", font=("Arial", 14, "bold"))
            
            # Désactiver tous les boutons du plateau
            for row in self.board_buttons:
                for button in row:
                    button.config(state=tk.DISABLED)
            
            # Afficher les boutons de contrôle
            self.show_game_controls()
            
        else:
            # Partie en cours
            if self.is_my_turn:
                self.turn_label.config(text="C'est votre tour!", fg="green", font=("Arial", 12, "bold"))
                # Activer les boutons
                for row in self.board_buttons:
                    for button in row:
                        if button['text'] == ' ':
                            button.config(state=tk.NORMAL)
            else:
                self.turn_label.config(text="Tour de l'adversaire...", fg="red", font=("Arial", 12, "bold"))
                # Désactiver tous les boutons
                for row in self.board_buttons:
                    for button in row:
                        button.config(state=tk.DISABLED)

    def show_game_controls(self):
        """Affiche les boutons Rejouer et Quitter"""
        self.replay_button.pack(side=tk.LEFT, padx=10)
        self.quit_button.pack(side=tk.LEFT, padx=10)

    def hide_game_controls(self):
        """Cache les boutons Rejouer et Quitter"""
        self.replay_button.pack_forget()
        self.quit_button.pack_forget()

    def make_move(self, i, j):
        """Envoie un coup au serveur"""
        if not self.is_my_turn:
            messagebox.showwarning("Pas votre tour", "Attendez votre tour!")
            return
        
        if self.board_buttons[i][j]['text'] != ' ':
            messagebox.showwarning("Case occupée", "Cette case est déjà occupée!")
            return
        
        # Envoyer le coup au serveur
        move_message = f"MOVE:{i}{j}"
        try:
            self.socket.sendall(move_message.encode())
            # Désactiver temporairement tous les boutons
            for row in self.board_buttons:
                for button in row:
                    button.config(state=tk.DISABLED)
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible d'envoyer le coup : {e}")

    def request_new_game(self):
        """Demande une nouvelle partie au serveur"""
        self.reset_game_ui()
        self.status_label.config(text="En attente d'un adversaire...")
        
        # Ici, vous pourriez envoyer un message au serveur pour demander une nouvelle partie
        # Pour l'instant, on réinitialise juste l'interface
        # Le serveur devrait gérer la réinscription dans la queue automatiquement
        
        # Note: Si le serveur supporte un message de nouvelle partie, l'envoyer ici :
        # try:
        #     self.socket.sendall(b"NEW_GAME")
        # except Exception as e:
        #     messagebox.showerror("Erreur", f"Impossible de demander une nouvelle partie : {e}")

    def reset_game_ui(self):
        """Réinitialise l'interface utilisateur pour une nouvelle partie"""
        if self.board_frame:
            self.board_frame.destroy()
        
        # Cacher les boutons de contrôle
        self.hide_game_controls()
        
        self.board_buttons = []
        self.match_id = None
        self.player_number = None
        self.my_symbol = None
        self.opponent_symbol = None
        self.is_my_turn = False
        self.game_started = False
        
        self.turn_label.config(text="", font=("Arial", 12, "bold"))

    def quit_game(self):
        """Quitte l'application"""
        self.on_closing()

    def disconnect(self):
        """Déconnecte le client proprement"""
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        
        self.connect_button.config(state=tk.NORMAL)
        self.status_label.config(text="Déconnecté du serveur")
        self.turn_label.config(text="")
        
        if self.board_frame:
            self.board_frame.destroy()
        
        # Cacher les boutons de contrôle
        self.hide_game_controls()

    def on_closing(self):
        """Appelé quand la fenêtre est fermée"""
        self.disconnect()
        self.destroy()

if __name__ == "__main__":
    app = MatchmakingClient()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()