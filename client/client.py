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
        self.geometry("300x400")
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
        error_message = None
        try:
            while True:
                if not self.socket:
                    break
                    
                data = self.socket.recv(1024).decode()
                if not data:
                    break
                
                buffer += data
                
                # Traiter chaque ligne complète
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line.strip():
                        print(f"[DEBUG Client] Message reçu: {line.strip()}")  # Debug
                        self.process_server_message(line.strip())
                        
        except Exception as e:
            error_message = str(e)
            print(f"[DEBUG Client] Erreur de connexion: {error_message}")  # Debug
            if self.socket:  # Seulement afficher l'erreur si on était connecté
                self.after(0, lambda msg=error_message: messagebox.showerror("Erreur", f"Connexion perdue : {msg}"))
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
                    text=f"Match trouvé! Vous êtes le joueur {self.player_number} ({self.my_symbol})\n" +
                    f"{'Vous commencez!' if self.player_number == 1 else 'Votre adversaire (X) commence.'}",
                    fg="blue", wraplength=300))
                self.after(0, self.create_game_board)
                
            elif data['type'] == 'game_state':
                print(f"[DEBUG Client] État du jeu reçu: board='{data['board']}', turn={data['current_turn']}, finished={data['is_finished']}")
                # Afficher le plateau pour debug
                board = data['board']
                print("[DEBUG Client] Plateau actuel:")
                for i in range(3):
                    row = board[i*3:(i+1)*3]
                    print(f"  {row[0]} | {row[1]} | {row[2]}")
                    if i < 2:
                        print("  ---------")
                self.after(0, lambda: self.update_game_state(data))
                
        except json.JSONDecodeError:
            # Message non-JSON (ancien format)
            if "Votre adversaire s'est deconnecte" in message:
                self.after(0, lambda: messagebox.showinfo("Adversaire déconnecté", 
                    "Votre adversaire s'est déconnecté. Retour au menu principal."))
                # Fermer la socket pour éviter d'autres erreurs
                if self.socket:
                    try:
                        self.socket.close()
                    except:
                        pass
                    self.socket = None
                self.after(100, self.disconnect)
                self.after(200, lambda: self.connect_button.config(state=tk.NORMAL))
            else:
                self.after(0, lambda: self.status_label.config(text=message))

    def create_game_board(self):
        """Crée le plateau de jeu"""
        if self.board_frame:
            self.board_frame.destroy()
        
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
        if not self.game_started or not self.board_buttons:
            return
        
        # Mettre à jour le plateau
        board = state['board']
        for i in range(3):
            for j in range(3):
                symbol = board[i * 3 + j]
                current_text = self.board_buttons[i][j]['text']
                
                # Mettre à jour seulement si le contenu a changé
                if current_text != symbol:
                    self.board_buttons[i][j]['text'] = symbol if symbol != ' ' else ' '
                    
                    # Colorer les cases selon le joueur
                    if symbol == 'X':
                        self.board_buttons[i][j].config(bg="#ffcccc", fg="#cc0000")
                    elif symbol == 'O':
                        self.board_buttons[i][j].config(bg="#ccccff", fg="#0000cc")
        
        # Mettre à jour le statut du tour
        self.is_my_turn = (state['current_turn'] == self.player_number and not state['is_finished'])
        
        if state['is_finished']:
            # Partie terminée
            if state['winner'] == 0:
                self.turn_label.config(text="Match nul!", fg="orange")
                messagebox.showinfo("Fin de partie", "Match nul!")
            elif state['winner'] == self.player_number:
                self.turn_label.config(text="Vous avez gagné! 🎉", fg="green")
                messagebox.showinfo("Victoire", "Félicitations, vous avez gagné!")
            else:
                self.turn_label.config(text="Vous avez perdu...", fg="red")
                messagebox.showinfo("Défaite", "Vous avez perdu. Réessayez!")
            
            # Proposer une nouvelle partie
            self.after(1000, self.ask_new_game)
        else:
            # Partie en cours
            if self.is_my_turn:
                self.turn_label.config(text="C'est votre tour! Cliquez sur une case vide", fg="green")
                self.status_label.config(text=f"Vous jouez avec les {self.my_symbol}", fg="green")
                # Activer les boutons vides et les mettre en surbrillance
                for row in self.board_buttons:
                    for button in row:
                        if button['text'] == ' ':
                            button.config(state=tk.NORMAL, bg="#e6ffe6", cursor="hand2")
                        else:
                            button.config(state=tk.DISABLED, cursor="arrow")
            else:
                current_player_symbol = 'X' if state['current_turn'] == 1 else 'O'
                self.turn_label.config(text=f"Tour de l'adversaire ({current_player_symbol})... Patientez", fg="red")
                self.status_label.config(text=f"Vous jouez avec les {self.my_symbol}", fg="blue")
                # Désactiver tous les boutons
                for row in self.board_buttons:
                    for button in row:
                        button.config(state=tk.DISABLED, cursor="arrow")
                        # Remettre la couleur normale aux cases vides
                        if button['text'] == ' ':
                            button.config(bg="white")

    def make_move(self, i, j):
        """Envoie un coup au serveur"""
        if not self.is_my_turn:
            # Message plus informatif
            current_turn_symbol = 'X' if self.player_number == 2 else 'O'
            messagebox.showinfo("Pas votre tour", 
                f"C'est au tour de l'adversaire ({current_turn_symbol}) de jouer.\n\n" +
                f"Vous jouez avec les {self.my_symbol} et devez attendre votre tour.")
            return
        
        if self.board_buttons[i][j]['text'] != ' ':
            messagebox.showwarning("Case occupée", "Cette case est déjà occupée!")
            return
        
        # Envoyer le coup au serveur - Format attendu par le serveur original
        move_message = f"{self.match_id},{self.player_number},{i}{j}"
        try:
            print(f"[DEBUG Client] Envoi du coup: {move_message}")  # Debug
            self.socket.sendall(move_message.encode())
            # Désactiver temporairement tous les boutons
            for row in self.board_buttons:
                for button in row:
                    button.config(state=tk.DISABLED)
            # Feedback visuel immédiat
            self.board_buttons[i][j]['text'] = self.my_symbol
            if self.my_symbol == 'X':
                self.board_buttons[i][j].config(bg="#ffcccc", fg="#cc0000")
            else:
                self.board_buttons[i][j].config(bg="#ccccff", fg="#0000cc")
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible d'envoyer le coup : {e}")

    def ask_new_game(self):
        """Demande si le joueur veut faire une nouvelle partie"""
        response = messagebox.askyesno("Nouvelle partie", "Voulez-vous faire une nouvelle partie?")
        if response:
            # Se déconnecter et se reconnecter proprement
            self.disconnect()
            self.connect_button.config(state=tk.NORMAL)
            # Reconnecter automatiquement
            self.after(500, self.connect_to_server)
        else:
            self.quit()

    def reset_game(self):
        """Réinitialise le jeu pour une nouvelle partie"""
        if self.board_frame:
            self.board_frame.destroy()
        
        self.board_buttons = []
        self.match_id = None
        self.player_number = None
        self.my_symbol = None
        self.opponent_symbol = None
        self.is_my_turn = False
        self.game_started = False
        
        self.turn_label.config(text="")
        self.status_label.config(text="En attente d'un adversaire...")
        
        # Renvoyer le pseudo au serveur pour se réinscrire dans la queue
        if self.socket:
            try:
                pseudo = self.pseudo_entry.get().strip()
                if pseudo:
                    self.socket.sendall(pseudo.encode())
                    print(f"[DEBUG] Réinscription avec le pseudo: {pseudo}")
            except Exception as e:
                print(f"[!] Erreur lors de la réinscription: {e}")
                # Si erreur, se reconnecter complètement
                self.disconnect()
                self.connect_to_server()

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
            self.board_frame = None
        
        # Réinitialiser toutes les variables
        self.board_buttons = []
        self.match_id = None
        self.player_number = None
        self.my_symbol = None
        self.opponent_symbol = None
        self.is_my_turn = False
        self.game_started = False

    def on_closing(self):
        """Appelé quand la fenêtre est fermée"""
        self.disconnect()
        self.destroy()

if __name__ == "__main__":
    app = MatchmakingClient()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()