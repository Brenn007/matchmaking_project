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
        
        # Configuration responsive
        self.state('zoomed')  # Windows
        # self.attributes('-zoomed', True)  # Linux alternative
        self.configure(bg='#1a1a2e')
        
        # Variables pour le responsive design
        self.screen_width = self.winfo_screenwidth()
        self.screen_height = self.winfo_screenheight()
        self.is_small_screen = self.screen_width < 1366 or self.screen_height < 768
        
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
        
        # Bind pour quitter en plein écran avec Escape et gérer le redimensionnement
        self.bind('<Escape>', self.toggle_fullscreen)
        self.bind('<F11>', self.toggle_fullscreen)
        self.bind('<Configure>', self.on_window_resize)

    def get_responsive_sizes(self):
        """Calcule les tailles en fonction de la résolution d'écran"""
        # Détection de la taille d'écran actuelle
        current_width = self.winfo_width() if self.winfo_width() > 1 else self.screen_width
        current_height = self.winfo_height() if self.winfo_height() > 1 else self.screen_height
        
        # Définir les tailles selon la résolution
        if current_width < 1366 or current_height < 768:
            # Petits écrans (laptops, tablettes)
            return {
                'title_font': ("Arial Black", 28, "bold"),
                'title_pady': (0, 15),
                'main_padx': 20,
                'main_pady': 20,
                'status_font': ("Arial", 12),
                'turn_font': ("Arial", 16, "bold"),
                'turn_font_big': ("Arial", 20, "bold"),
                'board_title_font': ("Arial", 14, "bold"),
                'button_width': 6,
                'button_height': 3,
                'button_font': ("Arial", 20, "bold"),
                'button_padx': 3,
                'button_pady': 3,
                'board_pady': 15,
                'pseudo_font': ("Arial", 12),
                'pseudo_label_font': ("Arial", 14, "bold"),
                'connect_font': ("Arial", 12, "bold"),
                'control_font': ("Arial", 12, "bold"),
                'control_padx': 20,
                'control_pady': 10
            }
        elif current_width < 1920 or current_height < 1080:
            # Écrans moyens (1366x768 à 1920x1080)
            return {
                'title_font': ("Arial Black", 36, "bold"),
                'title_pady': (0, 20),
                'main_padx': 30,
                'main_pady': 30,
                'status_font': ("Arial", 14),
                'turn_font': ("Arial", 20, "bold"),
                'turn_font_big': ("Arial", 24, "bold"),
                'board_title_font': ("Arial", 16, "bold"),
                'button_width': 7,
                'button_height': 3,
                'button_font': ("Arial", 24, "bold"),
                'button_padx': 4,
                'button_pady': 4,
                'board_pady': 20,
                'pseudo_font': ("Arial", 14),
                'pseudo_label_font': ("Arial", 16, "bold"),
                'connect_font': ("Arial", 13, "bold"),
                'control_font': ("Arial", 14, "bold"),
                'control_padx': 25,
                'control_pady': 12
            }
        else:
            # Grands écrans (1920x1080+)
            return {
                'title_font': ("Arial Black", 48, "bold"),
                'title_pady': (0, 30),
                'main_padx': 40,
                'main_pady': 40,
                'status_font': ("Arial", 16),
                'turn_font': ("Arial", 24, "bold"),
                'turn_font_big': ("Arial", 28, "bold"),
                'board_title_font': ("Arial", 20, "bold"),
                'button_width': 8,
                'button_height': 4,
                'button_font': ("Arial", 28, "bold"),
                'button_padx': 5,
                'button_pady': 5,
                'board_pady': 30,
                'pseudo_font': ("Arial", 16),
                'pseudo_label_font': ("Arial", 18, "bold"),
                'connect_font': ("Arial", 14, "bold"),
                'control_font': ("Arial", 16, "bold"),
                'control_padx': 30,
                'control_pady': 15
            }

    def on_window_resize(self, event=None):
        """Appelé lors du redimensionnement de la fenêtre"""
        if event and event.widget == self:
            # Mettre à jour les tailles si nécessaire
            self.update_ui_sizes()

    def update_ui_sizes(self):
        """Met à jour les tailles des éléments UI"""
        sizes = self.get_responsive_sizes()
        
        # Mettre à jour les fonts existantes
        try:
            self.title_label.config(font=sizes['title_font'])
            self.status_label.config(font=sizes['status_font'])
            self.turn_label.config(font=sizes['turn_font'])
            
            if hasattr(self, 'pseudo_label'):
                self.pseudo_label.config(font=sizes['pseudo_label_font'])
            if hasattr(self, 'pseudo_entry'):
                self.pseudo_entry.config(font=sizes['pseudo_font'])
            if hasattr(self, 'connect_button'):
                self.connect_button.config(font=sizes['connect_font'])
            
            # Mettre à jour les boutons du plateau s'ils existent
            if self.board_buttons:
                for row in self.board_buttons:
                    for button in row:
                        button.config(
                            font=sizes['button_font'],
                            width=sizes['button_width'],
                            height=sizes['button_height']
                        )
        except:
            pass  # Ignorer les erreurs si les éléments n'existent pas encore

    def setup_ui(self):
        """Configure l'interface utilisateur principale"""
        sizes = self.get_responsive_sizes()
        
        # Frame principal avec gradient simulé
        self.main_frame = tk.Frame(self, bg='#1a1a2e')
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=sizes['main_padx'], pady=sizes['main_pady'])
        
        # Titre principal
        self.title_label = tk.Label(
            self.main_frame,
            text="🎮 TICTACTOE ONLINE",
            font=sizes['title_font'],
            fg="#00d4aa",
            bg="#1a1a2e"
        )
        self.title_label.pack(pady=sizes['title_pady'])
        
        # Frame de connexion
        self.connection_frame = tk.Frame(self.main_frame, bg="#16213e", relief=tk.RAISED, bd=3)
        self.connection_frame.pack(pady=20)
        
        # Label pseudo avec style
        self.pseudo_label = tk.Label(
            self.connection_frame,
            text="✨ Entrez votre pseudo de joueur :",
            font=sizes['pseudo_label_font'],
            fg="#ffffff",
            bg="#16213e"
        )
        self.pseudo_label.pack(pady=(20, 10))
        
        # Entry pseudo avec style moderne
        self.pseudo_entry = tk.Entry(
            self.connection_frame,
            font=sizes['pseudo_font'],
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
            font=sizes['connect_font'],
            bg="#00d4aa",
            fg="#1a1a2e",
            relief=tk.FLAT,
            padx=sizes['control_padx'],
            pady=sizes['control_pady'],
            cursor="hand2"
        )
        self.connect_button.pack(pady=(10, 20))
        
        # Bind pour effet hover
        self.connect_button.bind("<Enter>", lambda e: self.connect_button.config(bg="#00ffcc"))
        self.connect_button.bind("<Leave>", lambda e: self.connect_button.config(bg="#00d4aa"))
        
        # Label de statut avec style
        self.status_label = tk.Label(
            self.main_frame,
            text="",
            font=sizes['status_font'],
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
            font=sizes['turn_font'],
            bg="#1a1a2e"
        )
        self.turn_label.pack(pady=15)
        
        # Frame pour les contrôles de fin de partie
        self.game_controls_frame = tk.Frame(self.game_container, bg="#1a1a2e")
        self.game_controls_frame.pack(pady=20)
        
        # Boutons avec design moderne
        self.replay_button = tk.Button(
            self.game_controls_frame,
            text="🔄 REJOUER",
            command=self.request_new_game,
            font=sizes['control_font'],
            bg="#4CAF50",
            fg="white",
            relief=tk.FLAT,
            padx=sizes['control_padx'],
            pady=sizes['control_pady'],
            cursor="hand2"
        )
        
        self.quit_button = tk.Button(
            self.game_controls_frame,
            text="❌ QUITTER",
            command=self.quit_game,
            font=sizes['control_font'],
            bg="#f44336",
            fg="white",
            relief=tk.FLAT,
            padx=sizes['control_padx'],
            pady=sizes['control_pady'],
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
            font=("Arial", 10 if sizes == self.get_responsive_sizes() and sizes['button_width'] < 7 else 12),
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
        
        # Forcer la mise à jour des tailles après changement de mode
        self.after(100, self.update_ui_sizes)

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
        print(f"[DEBUG] Message serveur reçu: {message}")
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
                
                print(f"[DEBUG] Nouveau match: ID={self.match_id}, Player={self.player_number}, Symbol={self.my_symbol}")
                
                self.after(0, lambda: self.status_label.config(
                    text=f"⚔️ Match trouvé! Vous jouez avec les {self.my_symbol} (Joueur {self.player_number})",
                    fg="#00ffcc"))
                self.after(0, self.create_game_board)
                
            elif data['type'] == 'game_state':
                # Vérifier que c'est bien pour notre match actuel
                if self.game_started:
                    print(f"[DEBUG] État de jeu: tour={data.get('current_turn')}, fini={data.get('is_finished')}")
                    self.after(0, lambda: self.update_game_state(data))
                
            elif data['type'] == 'new_game_accepted':
                self.after(0, lambda: self.status_label.config(text="🔍 " + data['message'], fg="#00d4aa"))
                
            elif data['type'] == 'opponent_disconnected':
                self.after(0, lambda: messagebox.showinfo("Déconnexion", data['message']))
                self.after(0, self.show_game_controls)
                
            elif data['type'] == 'error':
                # Afficher toutes les erreurs pour le debug
                print(f"[DEBUG] Erreur du serveur: {data['message']}")
                self.after(0, lambda: messagebox.showwarning("Erreur serveur", data['message']))
                
        except json.JSONDecodeError:
            # Message non-JSON (ancien format)
            self.after(0, lambda: self.status_label.config(text=message, fg="#00d4aa"))

    def create_game_board(self):
        """Crée le plateau de jeu avec un design moderne"""
        sizes = self.get_responsive_sizes()
        
        # Détruire l'ancien plateau s'il existe
        if self.board_frame:
            self.board_frame.destroy()
        
        # Cacher les boutons de contrôle
        self.hide_game_controls()
        
        # Afficher le conteneur de jeu
        self.game_container.pack(pady=sizes['board_pady'])
        
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
        self.board_frame.pack(pady=sizes['board_pady'])
        
        # Titre du plateau
        board_title = tk.Label(
            self.board_frame,
            text="🎯 PLATEAU DE JEU",
            font=sizes['board_title_font'],
            fg="#00d4aa",
            bg="#16213e"
        )
        board_title.pack(pady=(15, 10))
        
        # Frame spécifique pour la grille 3x3
        grid_frame = tk.Frame(self.board_frame, bg="#16213e")
        grid_frame.pack(pady=15)
        
        # Créer la grille 3x3 avec des boutons stylés
        for i in range(3):
            row = []
            for j in range(3):
                button = tk.Button(
                    grid_frame,
                    text=" ",
                    width=sizes['button_width'],
                    height=sizes['button_height'],
                    font=sizes['button_font'],
                    command=lambda r=i, c=j: self.make_move(r, c),
                    bg="#2d3561",
                    fg="#ffffff",
                    relief=tk.RAISED,
                    bd=3,
                    cursor="hand2",
                    activebackground="#3d4571"
                )
                button.grid(row=i, column=j, padx=sizes['button_padx'], pady=sizes['button_pady'], sticky="nsew")
                
                # Effet hover pour les cases
                button.bind("<Enter>", lambda e, b=button: self.on_button_hover(b, True))
                button.bind("<Leave>", lambda e, b=button: self.on_button_hover(b, False))
                
                row.append(button)
            self.board_buttons.append(row)
        
        # Configuration pour que la grille s'étende uniformément
        for i in range(3):
            grid_frame.grid_rowconfigure(i, weight=1)
            grid_frame.grid_columnconfigure(i, weight=1)
        
        # Espacement en bas du plateau
        bottom_spacer = tk.Label(self.board_frame, text="", bg="#16213e")
        bottom_spacer.pack(pady=15)
        
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
        
        sizes = self.get_responsive_sizes()
        
        print(f"[DEBUG] Mise à jour état: tour={state.get('current_turn')}, mon_numéro={self.player_number}")
        
        # Mettre à jour le plateau - CORRECTION: board est une string, pas un tableau 2D
        board = state['board']
        for i in range(3):
            for j in range(3):
                index = i * 3 + j  # Calculer l'index dans la string
                symbol = board[index] if index < len(board) else ' '
                button = self.board_buttons[i][j]
                button['text'] = symbol if symbol != ' ' else ' '
                
                # Colorer les cases selon le joueur avec des couleurs modernes
                if symbol == 'X':
                    button.config(bg="#e74c3c", fg="#ffffff", font=sizes['button_font'])  # Rouge moderne
                elif symbol == 'O':
                    button.config(bg="#3498db", fg="#ffffff", font=sizes['button_font'])  # Bleu moderne
                else:
                    button.config(bg="#2d3561", fg="#ffffff", font=sizes['button_font'])
        
        # Mettre à jour le statut du tour - CORRECTION: s'assurer que la comparaison fonctionne
        current_turn = state.get('current_turn')
        is_finished = state.get('is_finished', False)
        
        self.is_my_turn = (current_turn == self.player_number and not is_finished)
        
        print(f"[DEBUG] Tour actuel: {current_turn}, Mon numéro: {self.player_number}, C'est mon tour: {self.is_my_turn}, Fini: {is_finished}")
        
        if is_finished:
            # Partie terminée - Afficher le résultat avec style
            winner = state.get('winner')
            if winner == 0:
                self.turn_label.config(text="🤝 MATCH NUL!", fg="#ff9800", font=sizes['turn_font_big'])
            elif winner == self.player_number:
                self.turn_label.config(text="🏆 VICTOIRE!", fg="#4CAF50", font=sizes['turn_font_big'])
            else:
                self.turn_label.config(text="💀 DÉFAITE", fg="#f44336", font=sizes['turn_font_big'])
            
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
                    font=sizes['turn_font']
                )
                # Activer les boutons vides
                for row in self.board_buttons:
                    for button in row:
                        if button['text'] == ' ':
                            button.config(state=tk.NORMAL, cursor="hand2")
                        else:
                            button.config(state=tk.DISABLED, cursor="")
            else:
                self.turn_label.config(
                    text=f"⏳ TOUR ADVERSAIRE ({self.opponent_symbol})",
                    fg="#ff6b6b",
                    font=sizes['turn_font']
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
        print(f"[DEBUG] Tentative de coup: ({i},{j}), Mon tour: {self.is_my_turn}, Match ID: {self.match_id}")
        
        if not self.is_my_turn:
            messagebox.showwarning("Pas votre tour", "Attendez votre tour!")
            return
        
        if not self.match_id:
            messagebox.showerror("Erreur", "Aucun match en cours!")
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
            print(f"[DEBUG] Coup envoyé: {move_message}")
            # Désactiver temporairement tous les boutons
            for row in self.board_buttons:
                for button in row:
                    button.config(state=tk.DISABLED, cursor="")
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible d'envoyer le coup : {e}")
            print(f"[ERROR] Erreur envoi coup: {e}")

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
    
    