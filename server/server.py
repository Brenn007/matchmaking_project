
import socket
import threading
import time
import signal
import sys
import os
from http.server import HTTPServer, SimpleHTTPRequestHandler
import json

# Ajouter le chemin vers les modules partagés
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'jeu'))

from jeu.database import DatabaseManager
from jeu.game_logic import GameManager
from shared.protocol import Protocol, MessageType, GameMessages

HOST = '10.31.32.143'  # Localhost pour la compatibilité
PORT = 12345
HTTP_PORT = 8080

# Gestionnaires globaux
db_manager = None
game_manager = None
lock = threading.Lock()
matches = {}  # Dictionnaire pour stocker les matches actifs

def initialize_server():
    """Initialise le serveur avec la base de données"""
    global db_manager, game_manager
    
    # Initialiser la base de données
    db_manager = DatabaseManager("../matchmaking.db")
    
    # Nettoyer les anciennes entrées de la file d'attente
    db_manager.clear_queue()
    
    # Initialiser le gestionnaire de jeu
    game_manager = GameManager(db_manager)
    
    print("[+] Serveur initialisé avec la base de données")

def handle_client(conn, addr):
    """Gère un client connecté"""
    print(f"[+] Connexion de {addr}")
    player_name = None
    
    try:
        # Réception du pseudo
        raw_message = conn.recv(1024)
        message_type, data = Protocol.decode_message(raw_message)
        
        if message_type == MessageType.JOIN_QUEUE.value:
            player_name = data.get('player_name')
            print(f"[+] Joueur connecté : {player_name}")
            
            with lock:
                # Ajouter le joueur à la file d'attente
                match_id = game_manager.add_player_to_queue(
                    player_name, conn, addr[0], addr[1]
                )
                
                if match_id:
                    print(f"[+] Match créé : {match_id}")
                else:
                    print(f"[+] {player_name} ajouté à la file d'attente")
        
        else:
            # Ancienne compatibilité pour les clients qui envoient juste le pseudo
            player_name = raw_message.decode().strip()
            print(f"[+] Joueur connecté (ancien format) : {player_name}")
            
            with lock:
                match_id = game_manager.add_player_to_queue(
                    player_name, conn, addr[0], addr[1]
                )
                
                if match_id:
                    print(f"[+] Match créé : {match_id}")
                else:
                    print(f"[+] {player_name} ajouté à la file d'attente")
        
        # Écouter les messages du client
        while True:
            try:
                raw_data = conn.recv(1024)
                if not raw_data:
                    print(f"[!] Déconnexion de {player_name or addr}")
                    break
                
                # Essayer de décoder comme nouveau protocole
                message_type, data = Protocol.decode_message(raw_data)
                
                if message_type == MessageType.MAKE_MOVE.value:
                    handle_new_move(player_name, data)
                else:
                    # Ancien format de coup : "match_id,player_number,move"
                    handle_legacy_move(raw_data.decode(), conn, player_name)
                    
            except Exception as e:
                print(f"[!] Erreur lors du traitement des données de {player_name or addr} : {e}")
                break
                
    except Exception as e:
        print(f"[!] Erreur avec {player_name or addr} : {e}")
    finally:
        # Nettoyer à la déconnexion
        if player_name:
            with lock:
                game_manager.disconnect_player(player_name)
        
        print(f"[DEBUG] Connexion fermée pour {player_name or addr}")
        conn.close()

def handle_new_move(player_name, data):
    """Gère un coup selon le nouveau protocole"""
    match_id = data.get('match_id')
    position_x = data.get('position_x')
    position_y = data.get('position_y')
    
    with lock:
        success, message = game_manager.handle_move(
            player_name, match_id, position_x, position_y
        )
        
        if success:
            print(f"[+] Coup valide de {player_name} : ({position_x},{position_y})")
        else:
            print(f"[!] Coup invalide de {player_name} : {message}")

def handle_legacy_move(data, sender_conn, player_name):
    """Gère un coup selon l'ancien format pour compatibilité"""
    try:
        parts = data.strip().split(',')
        if len(parts) != 3:
            print(f"[!] Format de coup invalide : {data}")
            return
            
        match_id, player_number, move = parts
        match_id = int(match_id)
        
        if len(move) != 2:
            print(f"[!] Format de position invalide : {move}")
            return
            
        position_x, position_y = int(move[0]), int(move[1])
        
        with lock:
            success, message = game_manager.handle_move(
                player_name, match_id, position_x, position_y
            )
            
            if success:
                print(f"[+] Coup valide de {player_name} : ({position_x},{position_y})")
            else:
                print(f"[!] Coup invalide de {player_name} : {message}")
                
    except Exception as e:
        print(f"[!] Erreur dans handle_legacy_move : {e}")

def start_server():
    """Démarre le serveur de jeu"""
    # Initialiser le serveur
    initialize_server()
    
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server.bind((HOST, PORT))
        server.listen(5)
        print(f"[+] Serveur de jeu en écoute sur {HOST}:{PORT}")
        print(f"[+] Base de données initialisée")
        print(f"[+] En attente de connexions...")
        
        while True:
            conn, addr = server.accept()
            # Créer un thread pour chaque client
            client_thread = threading.Thread(
                target=handle_client, 
                args=(conn, addr), 
                daemon=True
            )
            client_thread.start()
            
    except KeyboardInterrupt:
        print("\n[!] Arrêt du serveur...")
    except Exception as e:
        print(f"[!] Erreur du serveur : {e}")
    finally:
        server.close()
        print("[+] Serveur fermé")

def signal_handler(sig, frame):
    """Gestionnaire de signal pour arrêt propre"""
    print('\n[!] Signal d\'arrêt reçu')
    sys.exit(0)

if __name__ == "__main__":
    # Gestionnaire de signal pour arrêt propre
    signal.signal(signal.SIGINT, signal_handler)
    
    print("[+] Démarrage du serveur de matchmaking...")
    start_server()

def check_game_end(board):
    """Vérifie si le jeu est terminé"""
    # Convertir le board en liste pour faciliter les vérifications
    lines = [
        [board[0], board[1], board[2]],  # ligne 1
        [board[3], board[4], board[5]],  # ligne 2
        [board[6], board[7], board[8]],  # ligne 3
        [board[0], board[3], board[6]],  # colonne 1
        [board[1], board[4], board[7]],  # colonne 2
        [board[2], board[5], board[8]],  # colonne 3
        [board[0], board[4], board[8]],  # diagonale 1
        [board[2], board[4], board[6]]   # diagonale 2
    ]
    
    # Vérifier les victoires
    for line in lines:
        if line[0] == line[1] == line[2] != ' ':
            if line[0] == 'X':
                return True, 1  # Joueur 1 gagne
            elif line[0] == 'O':
                return True, 2  # Joueur 2 gagne
    
    # Vérifier le match nul
    if ' ' not in board:
        return True, 0  # Match nul
    
    return False, None  # Jeu en cours

def handle_client(conn, addr):
    global queue
    print(f"[+] Connexion de {addr}")
    try:
        pseudo = conn.recv(1024).decode()
        print(f"[DEBUG] Message brut reçu : {pseudo}")

        # Vérifier si la requête ressemble à une requête HTTP
        if pseudo.startswith("GET") or pseudo.startswith("POST"):
            print(f"[!] Requête HTTP détectée sur le serveur socket : {pseudo[:50]}...")
            conn.close()
            return

        print(f"[+] Pseudo reçu : {pseudo}")

        with lock:
            queue.append((addr[0], addr[1], pseudo, conn))
            print(f"[DEBUG] File d'attente actuelle : {len(queue)} joueurs")

        conn.sendall(b"En attente d'un adversaire...\n")

        while True:
            try:
                data = conn.recv(1024).decode()
                if not data:
                    print(f"[!] Déconnexion de {addr}")
                    break
                print(f"[DEBUG] Données reçues de {addr} : {data}")
                handle_move(data, conn)
            except Exception as e:
                print(f"[!] Erreur lors du traitement des données de {addr} : {e}")
                break
    except Exception as e:
        print(f"[!] Erreur avec {addr} : {e}")
    finally:
        print(f"[DEBUG] Connexion fermée pour {addr}")
        # Retirer le joueur de la queue s'il y est encore
        with lock:
            queue[:] = [player for player in queue if player[3] != conn]
        conn.close()

def handle_move(data, sender_conn):
    """Traite un coup reçu d'un joueur"""
    try:
        parts = data.strip().split(',')
        if len(parts) != 3:
            print(f"[!] Format de coup invalide : {data}")
            return
            
        match_id, player_number, move = parts
        match_id = int(match_id)
        player_number = int(player_number)
        
        if len(move) != 2:
            print(f"[!] Format de position invalide : {move}")
            return
            
        i, j = int(move[0]), int(move[1])
        
        print(f"[DEBUG] Coup reçu - Match: {match_id}, Joueur: {player_number}, Position: {i},{j}")

        with lock:
            match = matches.get(match_id)
            if not match:
                print(f"[!] Match {match_id} introuvable")
                return

            board = list(match['board'])
            index = i * 3 + j

            if index < 0 or index >= 9:
                print(f"[!] Position invalide : {index}")
                return
                
            if board[index] != ' ':
                print(f"[!] Coup invalide : case {index} déjà occupée")
                return

            # Placer le symbole du joueur
            symbol = 'X' if player_number == 1 else 'O'
            board[index] = symbol
            match['board'] = ''.join(board)
            
            print(f"[DEBUG] Plateau mis à jour : {match['board']}")

            # Vérifier la fin du jeu
            is_over, winner = check_game_end(match['board'])
            match['is_finished'] = is_over
            match['winner'] = winner
            
            if is_over:
                if winner == 0:
                    print(f"[+] Match {match_id} terminé - Match nul")
                else:
                    print(f"[+] Match {match_id} terminé - Joueur {winner} gagne")
            
            # Envoyer le coup à l'autre joueur
            target_conn = match['player2_conn'] if player_number == 1 else match['player1_conn']
            try:
                message = f"Coup joué: {move}"
                target_conn.sendall(message.encode())
                print(f"[DEBUG] Coup transmis à l'adversaire : {message}")
            except Exception as e:
                print(f"[!] Erreur lors de l'envoi du coup à l'adversaire : {e}")

    except Exception as e:
        print(f"[!] Erreur dans handle_move : {e}")

def notify_player(conn, match_id, player_number):
    """Notifie un joueur qu'un match a été trouvé"""
    try:
        message = f"Match trouvé ! ID: {match_id}, Joueur: {player_number}"
        conn.sendall(message.encode())
        print(f"[DEBUG] Notification envoyée - Match: {match_id}, Joueur: {player_number}")
    except Exception as e:
        print(f"[!] Impossible de notifier le joueur {player_number} : {e}")

def matchmaking():
    """Thread de matchmaking"""
    global match_id_counter
    while True:
        with lock:
            # Nettoyer la file d'attente des connexions fermées
            valid_queue = []
            for player in queue:
                try:
                    # Tester si la connexion est encore valide
                    player[3].fileno()
                    valid_queue.append(player)
                except:
                    print(f"[DEBUG] Connexion fermée retirée de la queue : {player[2]}")
            
            queue[:] = valid_queue

            if len(queue) >= 2:
                p1 = queue.pop(0)
                p2 = queue.pop(0)

                match_id = match_id_counter
                match_id_counter += 1

                matches[match_id] = {
                    'player1_conn': p1[3],
                    'player2_conn': p2[3],
                    'board': ' ' * 9,
                    'is_finished': False,
                    'winner': None
                }

                print(f"[+] Match créé entre {p1[2]} et {p2[2]} (ID: {match_id})")
                
                # Notifier les joueurs
                notify_player(p1[3], match_id, 1)
                notify_player(p2[3], match_id, 2)

        time.sleep(1)  # Réduire l'intervalle pour un matchmaking plus réactif

def start_server():
    """Démarre le serveur de jeu"""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Permettre de réutiliser l'adresse
    server.bind((HOST, PORT))
    server.listen(5)
    print(f"[+] Serveur de jeu en écoute sur {HOST}:{PORT}")

    # Démarrer le thread de matchmaking
    threading.Thread(target=matchmaking, daemon=True).start()

    while True:
        try:
            conn, addr = server.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
        except Exception as e:
            print(f"[!] Erreur lors de l'acceptation d'une connexion : {e}")

class MyHandler(SimpleHTTPRequestHandler):
    """Handler pour le serveur HTTP de monitoring"""
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        
        # Afficher des statistiques
        with lock:
            queue_size = len(queue)
            active_matches = len([m for m in matches.values() if not m['is_finished']])
        
        html = f"""
        <html>
        <head><title>Serveur Morpion - Monitoring</title></head>
        <body>
            <h1>Serveur de Morpion</h1>
            <p>Joueurs en attente : {queue_size}</p>
            <p>Matchs actifs : {active_matches}</p>
            <p>Total des matchs créés : {match_id_counter - 1}</p>
        </body>
        </html>
        """
        self.wfile.write(html.encode())

def signal_handler(sig, frame):
    """Gestionnaire de signal pour arrêter proprement le serveur"""
    print("\n[!] Arrêt du serveur...")
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    
    # Démarrer le serveur de jeu
    threading.Thread(target=start_server, daemon=True).start()
    
    # Démarrer le serveur HTTP de monitoring
    with HTTPServer((HOST, HTTP_PORT), MyHandler) as http_server:
        print(f"[+] Serveur HTTP de monitoring en écoute sur {HOST}:{HTTP_PORT}")
        try:
            http_server.serve_forever()
        except KeyboardInterrupt:
            print("\n[!] Serveur HTTP arrêté.")