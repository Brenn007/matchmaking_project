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
        self.title("🎮 TicTacToe Matchmaking")
        
        # Configuration plein écran
        self.state('zoomed')  # Windows
        # self.attributes('-zoomed', True)  # Linux alternative
        self.configure(bg='#1a1a2e')
        
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
        
        self.setup_ui()
        
        # Bind pour quitter en plein écran avec Escape
        self.bind('<Escape>', self.toggle_fullscreen)
        self.bind('<F11>', self.toggle_fullscreen)

    def setup_ui(self):
        """Configure l'interface utilisateur principale"""
        # Frame principal avec gradient simulé
        self.main_frame = tk.Frame(self, bg='#1a1a2e')
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=40, pady=40)
        
        # Titre principal
        self.title_label = tk.Label(
            self.main_frame,
            text="🎮 TICTACTOE ONLINE",
            font=("Arial Black", 48, "bold"),
            fg="#00d4aa",
            bg="#1a1a2e"
        )
        self.title_label.pack(pady=(0, 30))
        
        # Frame de connexion
        self.connection_frame = tk.Frame(self.main_frame, bg="#16213e", relief=tk.RAISED, bd=3)
        self.connection_frame.pack(pady=20)
        
        # Label pseudo avec style
        self.pseudo_label = tk.Label(
            self.connection_frame,
            text="✨ Entrez votre pseudo de joueur :",
            font=("Arial", 18, "bold"),
            fg="#ffffff",
            bg="#16213e"
        )
        self.pseudo_label.pack(pady=(30, 10))
        
        # Entry pseudo avec style moderne
        self.pseudo_entry = tk.Entry(
            self.connection_frame,
            font=("Arial", 16),
            width=25,
            bg="#2d3561",
            fg="#ffffff",
            insertbackground="#00d4aa",
            relief=tk.FLAT,
            bd=5
        )
        self.pseudo_entry.pack(pady=10, ipady=8)
        self.pseudo_entry.bind('<Return>', lambda e: self.connect_to_server())
        
        # Bouton de connexion avec effet hover
        self.connect_button = tk.Button(
            self.connection_frame,
            text="🚀 SE CONNECTER",
            command=self.connect_to_server,
            font=("Arial", 14, "bold"),
            bg="#00d4aa",
            fg="#1a1a2e",
            relief=tk.FLAT,
            padx=30,
            pady=12,
            cursor="hand2"
        )
        self.connect_button.pack(pady=(10, 30))
        
        # Bind pour effet hover
        self.connect_button.bind("<Enter>", lambda e: self.connect_button.config(bg="#00ffcc"))
        self.connect_button.bind("<Leave>", lambda e: self.connect_button.config(bg="#00d4aa"))
        
        # Label de statut avec style
        self.status_label = tk.Label(
            self.main_frame,
            text="",
            font=("Arial", 16),
            fg="#00d4aa",
            bg="#1a1a2e",
            wraplength=800
        )
        self.status_label.pack(pady=20)
        
        # Frame pour le jeu (initialement caché)
        self.game_container = tk.Frame(self.main_frame, bg="#1a1a2e")
        
        # Label pour afficher le tour actuel avec style
        self.turn_label = tk.Label(
            self.game_container,
            text="",
            font=("Arial", 24, "bold"),
            bg="#1a1a2e"
        )
        self.turn_label.pack(pady=20)
        
        # Frame pour les contrôles de fin de partie
        self.game_controls_frame = tk.Frame(self.game_container, bg="#1a1a2e")
        self.game_controls_frame.pack(pady=30)
        
        # Boutons avec design moderne
        self.replay_button = tk.Button(
            self.game_controls_frame,
            text="🔄 REJOUER",
            command=self.request_new_game,
            font=("Arial", 16, "bold"),
            bg="#4CAF50",
            fg="white",
            relief=tk.FLAT,
            padx=30,
            pady=15,
            cursor="hand2"
        )
        
        self.quit_button = tk.Button(
            self.game_controls_frame,
            text="❌ QUITTER",
            command=self.quit_game,
            font=("Arial", 16, "bold"),
            bg="#f44336",
            fg="white",
            relief=tk.FLAT,
            padx=30,
            pady=15,
            cursor="hand2"
        )
        
        # Effet hover pour les boutons de contrôle
        self.replay_button.bind("<Enter>", lambda e: self.replay_button.config(bg="#66BB6A"))
        self.replay_button.bind("<Leave>", lambda e: self.replay_button.config(bg="#4CAF50"))
        self.quit_button.bind("<Enter>", lambda e: self.quit_button.config(bg="#EF5350"))
        self.quit_button.bind("<Leave>", lambda e: self.quit_button.config(bg="#f44336"))
        
        # Instructions en bas
        self.instructions_label = tk.Label(
            self.main_frame,
            text="💡 Appuyez sur [Echap] ou [F11] pour basculer le mode plein écran",
            font=("Arial", 12),
            fg="#666999",
            bg="#1a1a2e"
        )
        self.instructions_label.pack(side=tk.BOTTOM, pady=10)

    def toggle_fullscreen(self, event=None):
        """Bascule entre plein écran et fenêtré"""
        current_state = self.attributes('-fullscreen') if hasattr(self, '_fullscreen_state') else False
        if not hasattr(self, '_fullscreen_state'):
            self._fullscreen_state = False
        
        self._fullscreen_state = not self._fullscreen_state
        self.attributes('-fullscreen', self._fullscreen_state)
        
        if not self._fullscreen_state:
            self.state('zoomed')  # Maximiser si pas en plein écran

    def connect_to_server(self):
        pseudo = self.pseudo_entry.get().strip()
        if not pseudo:
            messagebox.showwarning("Pseudo manquant", "Veuillez entrer un pseudo.")
            return
        
        # Animation de connexion
        self.connect_button.config(state=tk.DISABLED, text="🔄 CONNEXION...", bg="#666666")
        
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.socket.connect((SERVER_IP, SERVER_PORT))
            self.socket.sendall(pseudo.encode())
            self.status_label.config(text="🔍 Recherche d'un adversaire en cours...", fg="#00d4aa")
            
            # Cacher le formulaire de connexion
            self.connection_frame.pack_forget()
            
            # Écoute des messages du serveur
            threading.Thread(target=self.listen_to_server, daemon=True).start()
        except Exception as e:
            messagebox.showerror("Erreur de connexion", f"Impossible de se connecter au serveur : {e}")
            self.socket = None
            self.connect_button.config(state=tk.NORMAL, text="🚀 SE CONNECTER", bg="#00d4aa")

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
                # Nouveau match trouvé - réinitialiser complètement
                self.match_id = data['match_id']
                self.player_number = data['player_number']
                self.my_symbol = 'X' if self.player_number == 1 else 'O'
                self.opponent_symbol = 'O' if self.player_number == 1 else 'X'
                self.is_my_turn = False
                self.game_started = False
                
                print(f"[DEBUG] Nouveau match: ID={self.match_id}, Player={self.player_number}")
                
                self.after(0, lambda: self.status_label.config(
                    text=f"⚔️ Match trouvé! Vous jouez avec les {self.my_symbol} (Joueur {self.player_number})",
                    fg="#00ffcc"))
                self.after(0, self.create_game_board)
                
            elif data['type'] == 'game_state':
                # Vérifier que c'est bien pour notre match actuel
                if self.game_started:
                    self.after(0, lambda: self.update_game_state(data))
                
            elif data['type'] == 'new_game_accepted':
                self.after(0, lambda: self.status_label.config(text="🔍 " + data['message'], fg="#00d4aa"))
                
            elif data['type'] == 'opponent_disconnected':
                self.after(0, lambda: messagebox.showinfo("Déconnexion", data['message']))
                self.after(0, self.show_game_controls)
                
            elif data['type'] == 'error':
                # Ignorer les erreurs "partie terminée" car elles peuvent venir de l'ancien match
                if "terminée" not in data['message']:
                    self.after(0, lambda: messagebox.showwarning("Erreur", data['message']))
                
        except json.JSONDecodeError:
            # Message non-JSON (ancien format)
            self.after(0, lambda: self.status_label.config(text=message, fg="#00d4aa"))

    def create_game_board(self):
        """Crée le plateau de jeu avec un design moderne"""
        # Détruire l'ancien plateau s'il existe
        if self.board_frame:
            self.board_frame.destroy()
        
        # Cacher les boutons de contrôle
        self.hide_game_controls()
        
        # Afficher le conteneur de jeu
        self.game_container.pack(pady=20)
        
        # Réinitialiser les variables de jeu
        self.board_buttons = []
        self.is_my_turn = False
        
        # Frame principale du plateau avec effet de profondeur
        self.board_frame = tk.Frame(
            self.game_container,
            bg="#16213e",
            relief=tk.RAISED,
            bd=8
        )
        self.board_frame.pack(pady=30)
        
        # Titre du plateau
        board_title = tk.Label(
            self.board_frame,
            text="🎯 PLATEAU DE JEU",
            font=("Arial", 20, "bold"),
            fg="#00d4aa",
            bg="#16213e"
        )
        board_title.grid(row=0, column=0, columnspan=3, pady=20)
        
        # Créer la grille 3x3 avec des boutons stylés
        for i in range(3):
            row = []
            for j in range(3):
                button = tk.Button(
                    self.board_frame,
                    text=" ",
                    width=6,
                    height=3,
                    font=("Arial", 32, "bold"),
                    command=lambda r=i, c=j: self.make_move(r, c),
                    bg="#2d3561",
                    fg="#ffffff",
                    relief=tk.RAISED,
                    bd=3,
                    cursor="hand2",
                    activebackground="#3d4571"
                )
                button.grid(row=i+1, column=j, padx=8, pady=8)
                
                # Effet hover pour les cases
                button.bind("<Enter>", lambda e, b=button: self.on_button_hover(b, True))
                button.bind("<Leave>", lambda e, b=button: self.on_button_hover(b, False))
                
                row.append(button)
            self.board_buttons.append(row)
        
        # Espacement en bas du plateau
        tk.Label(self.board_frame, text="", bg="#16213e").grid(row=4, column=0, pady=10)
        
        self.game_started = True
        print(f"[DEBUG] Plateau de jeu créé pour le match {self.match_id}")

    def on_button_hover(self, button, entering):
        """Effet hover pour les boutons du plateau"""
        if button['text'] == ' ' and self.is_my_turn:
            if entering:
                button.config(bg="#4d5591", relief=tk.RAISED)
            else:
                button.config(bg="#2d3561", relief=tk.RAISED)

    def update_game_state(self, state):
        """Met à jour l'interface selon l'état du jeu reçu du serveur"""
        if not self.game_started:
            return
        
        # Mettre à jour le plateau
        board = state['board']
        for i in range(3):
            for j in range(3):
                symbol = board[i * 3 + j]
                button = self.board_buttons[i][j]
                button['text'] = symbol if symbol != ' ' else ' '
                
                # Colorer les cases selon le joueur avec des couleurs modernes
                if symbol == 'X':
                    button.config(bg="#e74c3c", fg="#ffffff", font=("Arial", 32, "bold"))  # Rouge moderne
                elif symbol == 'O':
                    button.config(bg="#3498db", fg="#ffffff", font=("Arial", 32, "bold"))  # Bleu moderne
                else:
                    button.config(bg="#2d3561", fg="#ffffff", font=("Arial", 32, "bold"))
        
        # Mettre à jour le statut du tour
        self.is_my_turn = (state['current_turn'] == self.player_number and not state['is_finished'])
        
        if state['is_finished']:
            # Partie terminée - Afficher le résultat avec style
            if state['winner'] == 0:
                self.turn_label.config(text="🤝 MATCH NUL!", fg="#ff9800", font=("Arial", 28, "bold"))
            elif state['winner'] == self.player_number:
                self.turn_label.config(text="🏆 VICTOIRE!", fg="#4CAF50", font=("Arial", 28, "bold"))
            else:
                self.turn_label.config(text="💀 DÉFAITE", fg="#f44336", font=("Arial", 28, "bold"))
            
            # Désactiver tous les boutons du plateau
            for row in self.board_buttons:
                for button in row:
                    button.config(state=tk.DISABLED, cursor="")
            
            # Afficher les boutons de contrôle
            self.show_game_controls()
            
        else:
            # Partie en cours
            if self.is_my_turn:
                self.turn_label.config(
                    text=f"🎯 VOTRE TOUR ({self.my_symbol})",
                    fg="#00ffcc",
                    font=("Arial", 24, "bold")
                )
                # Activer les boutons vides
                for row in self.board_buttons:
                    for button in row:
                        if button['text'] == ' ':
                            button.config(state=tk.NORMAL, cursor="hand2")
            else:
                self.turn_label.config(
                    text=f"⏳ TOUR ADVERSAIRE ({self.opponent_symbol})",
                    fg="#ff6b6b",
                    font=("Arial", 24, "bold")
                )
                # Désactiver tous les boutons
                for row in self.board_buttons:
                    for button in row:
                        button.config(state=tk.DISABLED, cursor="")

    def show_game_controls(self):
        """Affiche les boutons Rejouer et Quitter"""
        self.replay_button.pack(side=tk.LEFT, padx=15)
        self.quit_button.pack(side=tk.LEFT, padx=15)

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
        
        # Effet visuel temporaire
        self.board_buttons[i][j].config(bg="#00d4aa")
        
        # Envoyer le coup au serveur
        move_message = f"MOVE:{i}{j}"
        try:
            self.socket.sendall(move_message.encode())
            # Désactiver temporairement tous les boutons
            for row in self.board_buttons:
                for button in row:
                    button.config(state=tk.DISABLED, cursor="")
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible d'envoyer le coup : {e}")

    def request_new_game(self):
        """Demande une nouvelle partie au serveur"""
        try:
            # Envoyer la demande de nouvelle partie au serveur
            self.socket.sendall(b"NEW_GAME")
            print("[DEBUG] Demande de nouvelle partie envoyée au serveur")
            
            # Réinitialiser l'interface
            self.reset_game_ui()
            self.status_label.config(text="🔍 Recherche d'un nouvel adversaire...", fg="#00d4aa")
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de demander une nouvelle partie : {e}")
            print(f"[ERROR] Erreur lors de la demande de nouvelle partie: {e}")

    def reset_game_ui(self):
        """Réinitialise l'interface utilisateur pour une nouvelle partie"""
        if self.board_frame:
            self.board_frame.destroy()
        
        # Cacher le conteneur de jeu
        self.game_container.pack_forget()
        
        # Cacher les boutons de contrôle
        self.hide_game_controls()
        
        self.board_buttons = []
        self.match_id = None
        self.player_number = None
        self.my_symbol = None
        self.opponent_symbol = None
        self.is_my_turn = False
        self.game_started = False
        
        self.turn_label.config(text="", font=("Arial", 24, "bold"))

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
        
        # Réafficher le formulaire de connexion
        self.connection_frame.pack(pady=20)
        self.connect_button.config(state=tk.NORMAL, text="🚀 SE CONNECTER", bg="#00d4aa")
        self.status_label.config(text="❌ Déconnecté du serveur", fg="#ff6b6b")
        self.turn_label.config(text="")
        
        if self.board_frame:
            self.board_frame.destroy()
        
        # Cacher le conteneur de jeu
        self.game_container.pack_forget()
        
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