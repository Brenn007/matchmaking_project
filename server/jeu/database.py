
import sqlite3
import datetime
from contextlib import contextmanager

class DatabaseManager:
    """Gestionnaire de base de données pour le serveur de matchmaking"""
    
    def __init__(self, db_path="matchmaking.db"):
        self.db_path = db_path
        self.init_database()
    
    @contextmanager
    def get_connection(self):
        """Context manager pour les connexions à la base de données"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Pour avoir des dictionnaires
        try:
            yield conn
        finally:
            conn.close()
    
    def init_database(self):
        """Initialise la base de données avec les tables nécessaires"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Table queue
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    player_name TEXT NOT NULL,
                    ip_address TEXT NOT NULL,
                    port INTEGER NOT NULL,
                    date_entry DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Table matches
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS matches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    player1_name TEXT NOT NULL,
                    player2_name TEXT NOT NULL,
                    winner TEXT,
                    board_state TEXT DEFAULT '         ',
                    status TEXT DEFAULT 'in_progress',
                    start_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                    end_date DATETIME
                )
            """)
            
            # Table turns
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS turns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    match_id INTEGER NOT NULL,
                    player_name TEXT NOT NULL,
                    turn_number INTEGER NOT NULL,
                    position_x INTEGER NOT NULL,
                    position_y INTEGER NOT NULL,
                    symbol TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (match_id) REFERENCES matches(id)
                )
            """)
            
            conn.commit()
    
    # CRUD pour la queue
    def add_player_to_queue(self, player_name, ip_address, port):
        """Ajoute un joueur à la file d'attente"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO queue (player_name, ip_address, port, date_entry)
                VALUES (?, ?, ?, ?)
            """, (player_name, ip_address, port, datetime.datetime.now()))
            conn.commit()
            return cursor.lastrowid
    
    def get_queue_players(self, limit=2):
        """Récupère les joueurs en attente (FIFO)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM queue 
                ORDER BY date_entry ASC 
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]
    
    def remove_player_from_queue(self, player_id):
        """Retire un joueur de la file d'attente"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM queue WHERE id = ?", (player_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def clear_queue(self):
        """Vide la file d'attente"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM queue")
            conn.commit()
    
    # CRUD pour les matches
    def create_match(self, player1_name, player2_name):
        """Crée un nouveau match"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO matches (player1_name, player2_name, start_date)
                VALUES (?, ?, ?)
            """, (player1_name, player2_name, datetime.datetime.now()))
            conn.commit()
            return cursor.lastrowid
    
    def get_match(self, match_id):
        """Récupère un match par son ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM matches WHERE id = ?", (match_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def update_match_board(self, match_id, board_state):
        """Met à jour l'état du plateau d'un match"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE matches 
                SET board_state = ? 
                WHERE id = ?
            """, (board_state, match_id))
            conn.commit()
            return cursor.rowcount > 0
    
    def end_match(self, match_id, winner=None):
        """Termine un match"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE matches 
                SET winner = ?, status = 'finished', end_date = ?
                WHERE id = ?
            """, (winner, datetime.datetime.now(), match_id))
            conn.commit()
            return cursor.rowcount > 0
    
    def get_active_matches(self):
        """Récupère tous les matches actifs"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM matches WHERE status = 'in_progress'")
            return [dict(row) for row in cursor.fetchall()]
    
    # CRUD pour les turns
    def add_turn(self, match_id, player_name, turn_number, position_x, position_y, symbol):
        """Ajoute un tour de jeu"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO turns (match_id, player_name, turn_number, position_x, position_y, symbol)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (match_id, player_name, turn_number, position_x, position_y, symbol))
            conn.commit()
            return cursor.lastrowid
    
    def get_match_turns(self, match_id):
        """Récupère tous les tours d'un match"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM turns 
                WHERE match_id = ? 
                ORDER BY turn_number ASC
            """, (match_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_last_turn_number(self, match_id):
        """Récupère le numéro du dernier tour d'un match"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT MAX(turn_number) as last_turn 
                FROM turns 
                WHERE match_id = ?
            """, (match_id,))
            result = cursor.fetchone()
            return result['last_turn'] if result['last_turn'] else 0
    
    # Méthodes utilitaires
    def get_player_stats(self, player_name):
        """Récupère les statistiques d'un joueur"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_games,
                    SUM(CASE WHEN winner = ? THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN winner IS NULL AND status = 'finished' THEN 1 ELSE 0 END) as draws
                FROM matches 
                WHERE (player1_name = ? OR player2_name = ?) 
                AND status = 'finished'
            """, (player_name, player_name, player_name))
            return dict(cursor.fetchone())
    
    def cleanup_old_queue_entries(self, hours=24):
        """Nettoie les anciennes entrées de la file d'attente"""
        cutoff_time = datetime.datetime.now() - datetime.timedelta(hours=hours)
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM queue 
                WHERE date_entry < ?
            """, (cutoff_time,))
            conn.commit()
            return cursor.rowcount