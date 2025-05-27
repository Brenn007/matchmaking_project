import sys
import os

# Ajouter le dossier parent au chemin
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(parent_dir)
sys.path.append(current_dir)

from database import DatabaseManager
from shared.protocol import GameState, GameMessages, MessageType

class GameManager:
    """Gestionnaire de la logique de jeu côté serveur"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.active_games = {}  # match_id -> GameState
        self.game_states = {}  # alias for active_games for compatibility
        self.player_connections = {}  # player_name -> connection
        self.match_players = {}  # match_id -> {player1_name, player2_name, player1_conn, player2_conn}
    
    def add_player_to_queue(self, player_name, connection, ip_address, port):
        """Ajoute un joueur à la file d'attente"""
        # Ajouter en base de données
        queue_id = self.db_manager.add_player_to_queue(player_name, ip_address, port)
        
        # Stocker la connexion
        self.player_connections[player_name] = connection
        
        # Vérifier si on peut créer un match
        queue_players = self.db_manager.get_queue_players(2)
        
        if len(queue_players) >= 2:
            # Créer un match avec les 2 premiers joueurs
            player1 = queue_players[0]
            player2 = queue_players[1]
            
            match_id = self.create_match(player1['player_name'], player2['player_name'])
              # Retirer les joueurs de la file d'attente
            self.db_manager.remove_player_from_queue(player1['id'])
            self.db_manager.remove_player_from_queue(player2['id'])
            
            return match_id
        else:
            # Envoyer le statut de la file d'attente
            position = len(queue_players)
            message = GameMessages.queue_status(position, position)
            connection.sendall(message)
            return None
    
    def create_match(self, player1_name, player2_name):
        """Crée un nouveau match"""
        # Créer en base de données
        match_id = self.db_manager.create_match(player1_name, player2_name)
        
        # Créer l'état du jeu
        game_state = GameState(match_id)
        self.active_games[match_id] = game_state
        self.game_states[match_id] = game_state  # alias for compatibility
        
        # Stocker les informations des joueurs
        player1_conn = self.player_connections[player1_name]
        player2_conn = self.player_connections[player2_name]
        
        self.match_players[match_id] = {
            'player1_name': player1_name,
            'player2_name': player2_name,
            'player1_conn': player1_conn,
            'player2_conn': player2_conn
        }
        
        # Notifier les joueurs
        self.notify_match_start(match_id)
        
        return match_id
    
    def notify_match_start(self, match_id):
        """Notifie les joueurs qu'un match commence"""
        match_info = self.match_players[match_id]
        
        # Notifier le joueur 1
        message1 = GameMessages.match_found(
            match_id, 1, match_info['player2_name']
        )
        match_info['player1_conn'].sendall(message1)
        
        # Notifier le joueur 2
        message2 = GameMessages.match_found(
            match_id, 2, match_info['player1_name']
        )
        match_info['player2_conn'].sendall(message2)
        
        # Envoyer l'état initial du jeu
        self.send_game_state(match_id)
    
    def handle_move(self, player_name, match_id, position_x, position_y):
        """Gère un coup joué par un joueur"""
        if match_id not in self.active_games:
            return False, "Match introuvable"
        
        game_state = self.active_games[match_id]
        match_info = self.match_players[match_id]
        
        # Déterminer le numéro du joueur
        if player_name == match_info['player1_name']:
            player_number = 1
        elif player_name == match_info['player2_name']:
            player_number = 2
        else:
            return False, "Joueur non autorisé pour ce match"
        
        # Essayer de jouer le coup
        success, message = game_state.make_move(player_number, position_x, position_y)
        
        if success:
            # Sauvegarder le coup en base de données
            turn_number = self.db_manager.get_last_turn_number(match_id) + 1
            symbol = 'X' if player_number == 1 else 'O'
            
            self.db_manager.add_turn(
                match_id, player_name, turn_number, 
                position_x, position_y, symbol
            )
            
            # Mettre à jour l'état du plateau en base
            self.db_manager.update_match_board(match_id, game_state.get_board_string())
            
            # Envoyer l'état du jeu à tous les joueurs
            self.send_game_state(match_id)
            
            # Vérifier si le jeu est terminé
            if game_state.game_over:
                self.end_match(match_id)
        
        return success, message
    
    def validate_move(self, match_id, player_number, position_x, position_y):
        """Valide un coup sans l'exécuter"""
        if match_id not in self.active_games:
            return False, "Match introuvable"
        
        game_state = self.active_games[match_id]
        
        # Vérifier si c'est le bon tour
        if player_number != game_state.current_turn:
            return False, "Ce n'est pas votre tour"
          # Vérifier la position
        index = position_x * 3 + position_y
        if index < 0 or index >= 9:
            return False, "Position invalide"
        
        if game_state.board_state[index] != ' ':
            return False, "Case déjà occupée"
        
        return True, "Coup valide"
    
    def get_game_state(self, match_id):
        """Retourne l'état du jeu pour un match donné"""
        if match_id in self.active_games:
            return self.active_games[match_id]
        return None
    
    def get_match_history(self, match_id):
        """Retourne l'historique d'un match"""
        return self.db_manager.get_match_turns(match_id)
    
    def send_game_state(self, match_id):
        """Envoie l'état du jeu à tous les joueurs du match"""
        if match_id not in self.active_games:
            return
        
        game_state = self.active_games[match_id]
        match_info = self.match_players[match_id]
        
        # Message pour le joueur 1
        is_player1_turn = (game_state.current_turn == 1)
        message1 = GameMessages.game_state(
            match_id, game_state.get_board_string(), 
            game_state.current_turn, is_player1_turn
        )
        
        # Message pour le joueur 2
        is_player2_turn = (game_state.current_turn == 2)
        message2 = GameMessages.game_state(
            match_id, game_state.get_board_string(), 
            game_state.current_turn, is_player2_turn
        )
        
        try:
            # Add a delimiter (\n) to all outgoing messages
            match_info['player1_conn'].sendall(message1 + b'\n')
            match_info['player2_conn'].sendall(message2 + b'\n')
        except Exception as e:
            print(f"[ERROR] Erreur lors de l'envoi de l'état du jeu : {e}")
    
    def end_match(self, match_id):
        """Termine un match"""
        if match_id not in self.active_games:
            return
        
        game_state = self.active_games[match_id]
        match_info = self.match_players[match_id]
        
        # Déterminer le gagnant
        winner_name = None
        reason = "Match nul"
        
        if game_state.winner == 1:
            winner_name = match_info['player1_name']
            reason = f"{winner_name} a gagné"
        elif game_state.winner == 2:
            winner_name = match_info['player2_name']
            reason = f"{winner_name} a gagné"
        
        # Sauvegarder en base de données
        self.db_manager.end_match(match_id, winner_name)
        
        # Notifier les joueurs
        end_message = GameMessages.game_end(
            match_id, winner_name, reason, game_state.get_board_string()
        )
        
        try:
            match_info['player1_conn'].sendall(end_message)
            match_info['player2_conn'].sendall(end_message)
        except Exception as e:
            print(f"[ERROR] Erreur lors de l'envoi de fin de match : {e}")
        
        # Nettoyer les structures en mémoire
        del self.active_games[match_id]
        del self.match_players[match_id]
        
        # Retirer les connexions des joueurs
        if match_info['player1_name'] in self.player_connections:
            del self.player_connections[match_info['player1_name']]
        if match_info['player2_name'] in self.player_connections:
            del self.player_connections[match_info['player2_name']]
    
    def disconnect_player(self, player_name):
        """Gère la déconnexion d'un joueur"""
        # Trouver le match du joueur
        for match_id, match_info in self.match_players.items():
            if (player_name == match_info['player1_name'] or 
                player_name == match_info['player2_name']):
                
                # Notifier l'autre joueur
                other_player = (match_info['player2_name'] 
                              if player_name == match_info['player1_name'] 
                              else match_info['player1_name'])
                
                other_conn = (match_info['player2_conn'] 
                            if player_name == match_info['player1_name'] 
                            else match_info['player1_conn'])
                
                # Terminer le match avec victoire par forfait
                self.db_manager.end_match(match_id, other_player)
                
                disconnect_message = GameMessages.game_end(
                    match_id, other_player, 
                    f"Victoire par forfait - {player_name} s'est déconnecté",
                    self.active_games[match_id].get_board_string()
                )
                
                try:
                    other_conn.sendall(disconnect_message)
                except:
                    pass
                
                # Nettoyer
                if match_id in self.active_games:
                    del self.active_games[match_id]
                if match_id in self.match_players:
                    del self.match_players[match_id]
                break
        
        # Retirer de la file d'attente si présent
        queue_players = self.db_manager.get_queue_players(100)  # Récupérer tous
        for player in queue_players:
            if player['player_name'] == player_name:
                self.db_manager.remove_player_from_queue(player['id'])
                break
        
        # Retirer la connexion
        if player_name in self.player_connections:
            del self.player_connections[player_name]
    
    def get_match_info(self, match_id):
        """Récupère les informations d'un match"""
        return self.db_manager.get_match(match_id)
    
    def get_active_matches_count(self):
        """Retourne le nombre de matches actifs"""
        return len(self.active_games)