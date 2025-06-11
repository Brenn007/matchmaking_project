from http.server import SimpleHTTPRequestHandler, HTTPServer
import socket
import threading
import time
import signal
import sys
import json

HOST = '10.31.32.143'
PORT = 12345
HTTP_PORT = 8080

queue = []
matches = {}
match_id_counter = 1
lock = threading.Lock()

def check_game_end(board):
    """Vérifie si le jeu est terminé et retourne (is_over, winner)"""
    # Vérifier les lignes
    for i in range(0, 9, 3):
        if board[i] == board[i+1] == board[i+2] != ' ':
            return True, 1 if board[i] == 'X' else 2
    
    # Vérifier les colonnes
    for i in range(3):
        if board[i] == board[i+3] == board[i+6] != ' ':
            return True, 1 if board[i] == 'X' else 2
    
    # Vérifier les diagonales
    if board[0] == board[4] == board[8] != ' ':
        return True, 1 if board[0] == 'X' else 2
    if board[2] == board[4] == board[6] != ' ':
        return True, 1 if board[2] == 'X' else 2
    
    # Vérifier si match nul
    if ' ' not in board:
        return True, 0
    
    return False, None

def send_game_state(match):
    """Envoie l'état du jeu à tous les joueurs du match"""
    state = {
        'type': 'game_state',
        'board': match['board'],
        'current_turn': match['current_turn'],
        'is_finished': match['is_finished'],
        'winner': match['winner']
    }
    
    message = json.dumps(state)
    try:
        match['player1_conn'].sendall(message.encode() + b'\n')
    except:
        print("[!] Impossible d'envoyer à player1")
    
    try:
        match['player2_conn'].sendall(message.encode() + b'\n')
    except:
        print("[!] Impossible d'envoyer à player2")

def handle_client(conn, addr):
    global queue
    print(f"[+] Connexion de {addr}")
    player_match_id = None
    player_number = None
    player_pseudo = None
    
    try:
        pseudo = conn.recv(1024).decode()
        print(f"[DEBUG] Message brut reçu : {pseudo}")

        if pseudo.startswith("GET") or pseudo.startswith("POST"):
            print(f"[!] Requête HTTP détectée sur le serveur socket")
            conn.close()
            return

        print(f"[+] Pseudo reçu : {pseudo}")
        player_pseudo = pseudo

        with lock:
            queue.append((addr[0], addr[1], pseudo, conn))
            print(f"[DEBUG] File d'attente actuelle : {len(queue)} joueur(s)")

        conn.sendall(b"En attente d'un adversaire...\n")

        # Attendre d'être assigné à un match
        while player_match_id is None:
            with lock:
                for match_id, match in matches.items():
                    if match['player1_conn'] == conn:
                        player_match_id = match_id
                        player_number = 1
                        break
                    elif match['player2_conn'] == conn:
                        player_match_id = match_id
                        player_number = 2
                        break
            time.sleep(0.1)

        print(f"[DEBUG] Joueur {pseudo} assigné au match {player_match_id} comme joueur {player_number}")

        # Boucle principale du jeu
        while True:
            try:
                data = conn.recv(1024).decode()
                if not data:
                    print(f"[!] Déconnexion de {addr}")
                    break
                
                print(f"[DEBUG] Données reçues de {pseudo}: {data}")
                
                # Traiter les différents types de messages
                if data.startswith("MOVE:"):
                    move_data = data[5:].strip()
                    handle_move(player_match_id, player_number, move_data)
                elif data.startswith("NEW_GAME"):
                    handle_new_game_request(conn, player_pseudo, addr)
                    # Réinitialiser les variables pour le nouveau match
                    player_match_id = None
                    player_number = None
                    
                    # Attendre d'être assigné à un nouveau match
                    while player_match_id is None:
                        with lock:
                            for match_id, match in matches.items():
                                if match['player1_conn'] == conn:
                                    player_match_id = match_id
                                    player_number = 1
                                    break
                                elif match['player2_conn'] == conn:
                                    player_match_id = match_id
                                    player_number = 2
                                    break
                        time.sleep(0.1)
                
            except Exception as e:
                print(f"[!] Erreur lors du traitement des données de {addr} : {e}")
                break
                
    except Exception as e:
        print(f"[!] Erreur avec {addr} : {e}")
    finally:
        # Nettoyer la connexion
        with lock:
            # Retirer de la queue si encore dedans
            queue[:] = [(ip, port, p, c) for ip, port, p, c in queue if c != conn]
            
            # Gérer la déconnexion en plein match
            if player_match_id and player_match_id in matches:
                match = matches[player_match_id]
                other_conn = match['player2_conn'] if player_number == 1 else match['player1_conn']
                try:
                    disconnect_message = json.dumps({
                        'type': 'opponent_disconnected',
                        'message': 'Votre adversaire s\'est déconnecté'
                    })
                    other_conn.sendall(disconnect_message.encode() + b'\n')
                except:
                    pass
                del matches[player_match_id]
        
        conn.close()

def handle_new_game_request(conn, pseudo, addr):
    """Gère une demande de nouvelle partie"""
    try:
        print(f"[+] {pseudo} demande une nouvelle partie")
        
        with lock:
            # Ajouter le joueur à la file d'attente pour une nouvelle partie
            queue.append((addr[0], addr[1], pseudo, conn))
            print(f"[DEBUG] {pseudo} ajouté à la file d'attente pour une nouvelle partie")
        
        # Confirmer que la demande a été reçue
        response = json.dumps({
            'type': 'new_game_accepted',
            'message': 'En attente d\'un adversaire...'
        })
        conn.sendall(response.encode() + b'\n')
        
    except Exception as e:
        print(f"[!] Erreur lors de la gestion de nouvelle partie pour {pseudo}: {e}")

def handle_move(match_id, player_number, move):
    """Gère un coup joué par un joueur"""
    try:
        i, j = int(move[0]), int(move[1])
        
        with lock:
            match = matches.get(match_id)
            if not match:
                print(f"[!] Match {match_id} introuvable")
                return
            
            # Vérifier si c'est le tour du joueur
            if match['current_turn'] != player_number:
                player_conn = match['player1_conn'] if player_number == 1 else match['player2_conn']
                error_message = json.dumps({
                    'type': 'error',
                    'message': 'Ce n\'est pas votre tour!'
                })
                player_conn.sendall(error_message.encode() + b'\n')
                return
            
            # Vérifier si la partie est finie
            if match['is_finished']:
                player_conn = match['player1_conn'] if player_number == 1 else match['player2_conn']
                error_message = json.dumps({
                    'type': 'error',
                    'message': 'La partie est terminée!'
                })
                player_conn.sendall(error_message.encode() + b'\n')
                return
            
            board = list(match['board'])
            index = i * 3 + j
            
            # Vérifier si la case est vide
            if board[index] != ' ':
                player_conn = match['player1_conn'] if player_number == 1 else match['player2_conn']
                error_message = json.dumps({
                    'type': 'error',
                    'message': 'Case déjà occupée!'
                })
                player_conn.sendall(error_message.encode() + b'\n')
                return
            
            # Jouer le coup
            board[index] = 'X' if player_number == 1 else 'O'
            match['board'] = ''.join(board)
            
            # Vérifier si la partie est terminée
            is_over, winner = check_game_end(match['board'])
            match['is_finished'] = is_over
            match['winner'] = winner
            
            # Changer de tour
            if not is_over:
                match['current_turn'] = 2 if player_number == 1 else 1
            
            # Envoyer l'état du jeu mis à jour aux deux joueurs
            send_game_state(match)
            
            print(f"[+] Coup joué: Match {match_id}, Joueur {player_number}, Position ({i},{j})")
            
            # Si la partie est terminée, programmer le nettoyage du match après un délai
            if is_over:
                threading.Timer(30.0, cleanup_finished_match, args=[match_id]).start()
            
    except Exception as e:
        print(f"[!] Erreur dans handle_move : {e}")

def cleanup_finished_match(match_id):
    """Nettoie un match terminé après un délai"""
    with lock:
        if match_id in matches:
            print(f"[+] Nettoyage du match terminé {match_id}")
            del matches[match_id]

def notify_players_match_found(match_id, match):
    """Notifie les deux joueurs qu'un match a été trouvé"""
    try:
        # Notifier le joueur 1
        message1 = json.dumps({
            'type': 'match_found',
            'match_id': match_id,
            'player_number': 1,
            'opponent': match['player2_pseudo']
        })
        match['player1_conn'].sendall(message1.encode() + b'\n')
        
        # Notifier le joueur 2
        message2 = json.dumps({
            'type': 'match_found',
            'match_id': match_id,
            'player_number': 2,
            'opponent': match['player1_pseudo']
        })
        match['player2_conn'].sendall(message2.encode() + b'\n')
        
        # Envoyer l'état initial du jeu
        time.sleep(0.5)  # Petit délai pour laisser le temps au client de se préparer
        send_game_state(match)
        
    except Exception as e:
        print(f"[!] Erreur lors de la notification des joueurs : {e}")

def matchmaking():
    """Thread de matchmaking qui associe les joueurs en attente"""
    global match_id_counter
    while True:
        with lock:
            # Nettoyer la file d'attente des connexions fermées
            queue[:] = [(ip, port, pseudo, conn) for ip, port, pseudo, conn in queue 
                       if conn.fileno() != -1]
            
            if len(queue) >= 2:
                p1 = queue.pop(0)
                p2 = queue.pop(0)
                
                match_id = match_id_counter
                match_id_counter += 1
                
                matches[match_id] = {
                    'player1_conn': p1[3],
                    'player2_conn': p2[3],
                    'player1_pseudo': p1[2],
                    'player2_pseudo': p2[2],
                    'board': ' ' * 9,
                    'current_turn': 1,  # Le joueur 1 (X) commence toujours
                    'is_finished': False,
                    'winner': None
                }
                
                print(f"[+] Match créé entre {p1[2]} et {p2[2]} (ID: {match_id})")
                notify_players_match_found(match_id, matches[match_id])
        
        time.sleep(1)

def start_server():
    """Démarre le serveur de jeu principal"""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen()
    print(f"[+] Serveur en écoute sur {HOST}:{PORT}")
    
    # Démarrer le thread de matchmaking
    threading.Thread(target=matchmaking, daemon=True).start()
    
    while True:
        conn, addr = server.accept()
        threading.Thread(target=handle_client, args=(conn, addr)).start()

class MyHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.send_header("refresh", "5")  # Auto-refresh toutes les 5 secondes
        self.end_headers()
        
        # Page d'état du serveur
        with lock:
            # Détails des matchs
            matches_html = ""
            for match_id, match in matches.items():
                status = "Terminé" if match['is_finished'] else "En cours"
                winner_text = ""
                if match['is_finished']:
                    if match['winner'] == 0:
                        winner_text = " (Match nul)"
                    elif match['winner'] == 1:
                        winner_text = f" (Gagnant: {match['player1_pseudo']})"
                    elif match['winner'] == 2:
                        winner_text = f" (Gagnant: {match['player2_pseudo']})"
                
                matches_html += f"""
                <li>Match {match_id}: {match['player1_pseudo']} vs {match['player2_pseudo']} - {status}{winner_text}</li>
                """
            
            # Joueurs en attente
            queue_html = ""
            for ip, port, pseudo, conn in queue:
                queue_html += f"<li>{pseudo} ({ip}:{port})</li>"
            
            html = f"""
            <html>
            <head>
                <title>Serveur TicTacToe - Monitoring</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    .stats {{ background-color: #f0f0f0; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
                    .section {{ margin-bottom: 20px; }}
                    ul {{ background-color: #f9f9f9; padding: 10px; border-radius: 3px; }}
                </style>
            </head>
            <body>
                <h1>🎮 Serveur de Matchmaking TicTacToe</h1>
                
                <div class="stats">
                    <h2>📊 Statistiques</h2>
                    <p><strong>Joueurs en attente:</strong> {len(queue)}</p>
                    <p><strong>Matchs en cours:</strong> {len([m for m in matches.values() if not m['is_finished']])}</p>
                    <p><strong>Matchs terminés:</strong> {len([m for m in matches.values() if m['is_finished']])}</p>
                    <p><strong>Total de matchs créés:</strong> {match_id_counter - 1}</p>
                </div>
                
                <div class="section">
                    <h2>⏳ Joueurs en attente</h2>
                    <ul>
                        {queue_html if queue_html else "<li>Aucun joueur en attente</li>"}
                    </ul>
                </div>
                
                <div class="section">
                    <h2>🎯 Matchs</h2>
                    <ul>
                        {matches_html if matches_html else "<li>Aucun match en cours</li>"}
                    </ul>
                </div>
                
                <p><em>Page actualisée automatiquement toutes les 5 secondes</em></p>
            </body>
            </html>
            """
        
        self.wfile.write(html.encode())

def signal_handler(sig, frame):
    print("\n[!] Arrêt du serveur...")
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    
    # Démarrer le serveur de jeu dans un thread
    threading.Thread(target=start_server, daemon=True).start()
    
    # Démarrer le serveur HTTP pour monitoring
    with HTTPServer((HOST, HTTP_PORT), MyHandler) as http_server:
        print(f"[+] Serveur HTTP en écoute sur {HOST}:{HTTP_PORT}")
        try:
            http_server.serve_forever()
        except KeyboardInterrupt:
            print("\n[!] Serveurs arrêtés.")