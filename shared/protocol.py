import json
from enum import Enum

class MessageType(Enum):
    """Types de messages dans le protocole"""
    # Messages du client vers le serveur
    JOIN_QUEUE = "join_queue"
    MAKE_MOVE = "make_move"
    DISCONNECT = "disconnect"
    
    # Messages du serveur vers le client
    QUEUE_STATUS = "queue_status"
    MATCH_FOUND = "match_found"
    GAME_STATE = "game_state"
    MOVE_RESULT = "move_result"
    GAME_END = "game_end"
    ERROR = "error"

class Protocol:
    """Classe pour encoder/décoder les messages du protocole"""
    
    @staticmethod
    def encode_message(message_type, data=None):
        """Encode un message selon le protocole"""
        message = {
            "type": message_type.value if isinstance(message_type, MessageType) else message_type,
            "data": data or {}
        }
        return json.dumps(message).encode('utf-8')
    
    @staticmethod
    def decode_message(raw_message):
        """Décode un message selon le protocole"""
        try:
            message = json.loads(raw_message.decode('utf-8'))
            return message.get("type"), message.get("data", {})
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None, None

class GameMessages:
    """Constructeurs de messages spécifiques au jeu"""
    
    @staticmethod
    def player_connect(player_name):
        """Message de connexion d'un joueur"""
        return Protocol.encode_message(MessageType.JOIN_QUEUE, {
            "player_name": player_name
        })
    
    @staticmethod
    def join_queue(player_name):
        """Message pour rejoindre la file d'attente"""
        return Protocol.encode_message(MessageType.JOIN_QUEUE, {
            "player_name": player_name
        })
    
    @staticmethod
    def queue_status(position, total_players):
        """Message de statut de la file d'attente"""
        return Protocol.encode_message(MessageType.QUEUE_STATUS, {
            "position": position,
            "total_players": total_players,
            "message": f"Position dans la file: {position}/{total_players}"
        })
    
    @staticmethod
    def match_found(match_id, player_number, opponent_name):
        """Message d'annonce de match trouvé"""
        return Protocol.encode_message(MessageType.MATCH_FOUND, {
            "match_id": match_id,
            "player_number": player_number,
            "opponent_name": opponent_name,
            "symbol": "X" if player_number == 1 else "O"
        })
    
    @staticmethod
    def make_move(match_id, player_number, position_x, position_y):
        """Message pour effectuer un coup"""
        return Protocol.encode_message(MessageType.MAKE_MOVE, {
            "match_id": match_id,
            "player_number": player_number,
            "position_x": position_x,
            "position_y": position_y
        })
    
    @staticmethod
    def game_state(match_id, board_state, current_turn, is_your_turn):
        """Message d'état du jeu"""
        return Protocol.encode_message(MessageType.GAME_STATE, {
            "match_id": match_id,
            "board_state": board_state,
            "current_turn": current_turn,
            "is_your_turn": is_your_turn
        })
    
    @staticmethod
    def move_result(success, message, board_state=None):
        """Message de résultat d'un coup"""
        data = {
            "success": success,
            "message": message
        }
        if board_state:
            data["board_state"] = board_state
        return Protocol.encode_message(MessageType.MOVE_RESULT, data)
    
    @staticmethod
    def game_end(match_id, winner, reason, final_board):
        """Message de fin de partie"""
        return Protocol.encode_message(MessageType.GAME_END, {
            "match_id": match_id,
            "winner": winner,
            "reason": reason,
            "final_board": final_board
        })
    
    @staticmethod
    def error(error_code, message):
        """Message d'erreur"""
        return Protocol.encode_message(MessageType.ERROR, {
            "error_code": error_code,
            "message": message
        })

class GameState:
    """Représentation de l'état d'un jeu"""
    
    def __init__(self, match_id, board_state=" " * 9, current_turn=1):
        self.match_id = match_id
        self.board_state = list(board_state)
        self.current_turn = current_turn  # 1 pour joueur 1 (X), 2 pour joueur 2 (O)
        self.game_over = False
        self.winner = None
    
    def make_move(self, player_number, position_x, position_y):
        """Effectue un coup et retourne le résultat"""
        # Vérifier si c'est le bon tour
        if player_number != self.current_turn:
            return False, "Ce n'est pas votre tour"
        
        # Vérifier la position
        index = position_x * 3 + position_y
        if index < 0 or index >= 9:
            return False, "Position invalide"
        
        if self.board_state[index] != ' ':
            return False, "Case déjà occupée"
        
        # Effectuer le coup
        symbol = 'X' if player_number == 1 else 'O'
        self.board_state[index] = symbol
        
        # Vérifier la victoire
        if self.check_victory():
            self.game_over = True
            self.winner = player_number
            return True, f"Joueur {player_number} gagne!"
        
        # Vérifier le match nul
        if self.check_draw():
            self.game_over = True
            self.winner = None
            return True, "Match nul!"
        
        # Changer de tour
        self.current_turn = 2 if self.current_turn == 1 else 1
        return True, "Coup valide"
    
    def check_victory(self):
        """Vérifie s'il y a une victoire"""
        lines = [
            [0, 1, 2], [3, 4, 5], [6, 7, 8],  # lignes
            [0, 3, 6], [1, 4, 7], [2, 5, 8],  # colonnes
            [0, 4, 8], [2, 4, 6]              # diagonales
        ]
        
        for line in lines:
            if (self.board_state[line[0]] == self.board_state[line[1]] == 
                self.board_state[line[2]] != ' '):
                return True
        return False
    
    def check_winner(self):
        """Vérifie et retourne le gagnant (alias pour check_victory)"""
        if self.check_victory():
            return self.winner
        return None
    
    def check_draw(self):
        """Vérifie s'il y a match nul"""
        return ' ' not in self.board_state
    
    def set_board_cell(self, x, y, symbol):
        """Définit une cellule du plateau"""
        index = x * 3 + y
        if 0 <= index < 9:
            self.board_state[index] = symbol
            return True
        return False
    
    def get_board_string(self):
        """Retourne l'état du plateau sous forme de chaîne"""
        return ''.join(self.board_state)
    
    def get_board(self):
        """Retourne l'état du plateau sous forme de liste 2D"""
        board = []
        for i in range(3):
            row = []
            for j in range(3):
                row.append(self.board_state[i * 3 + j])
            board.append(row)
        return board
    
    def to_dict(self):
        """Convertit l'état en dictionnaire"""
        return {
            "match_id": self.match_id,
            "board_state": self.get_board_string(),
            "current_turn": self.current_turn,
            "game_over": self.game_over,
            "winner": self.winner
        }