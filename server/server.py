from http.server import SimpleHTTPRequestHandler, HTTPServer
import socket
import threading
import time
import signal
import sys

HOST = '10.31.32.143'
PORT = 12345
HTTP_PORT = 8080

queue = []
matches = {}
match_id_counter = 1
lock = threading.Lock()

def check_game_end(board):
    lines = [
        board[0:3], board[3:6], board[6:9],  # lignes
        board[0::3], board[1::3], board[2::3],  # colonnes
        board[0::4], board[2:7:2]  # diagonales
    ]
    if 'XXX' in lines:
        return True, 1
    elif 'OOO' in lines:
        return True, 2
    elif ' ' not in board:
        return True, 0
    return False, None

def handle_client(conn, addr):
    global queue
    print(f"[+] Connexion de {addr}")
    try:
        pseudo = conn.recv(1024).decode()
        print(f"[DEBUG] Message brut reçu : {pseudo}")  # Log détaillé du message reçu

        # Vérifier si la requête ressemble à une requête HTTP
        if pseudo.startswith("GET") or pseudo.startswith("POST"):
            print(f"[!] Requête HTTP détectée sur le serveur socket : {pseudo[:50]}...")
            conn.close()
            return

        print(f"[+] Pseudo reçu : {pseudo}")

        with lock:
            queue.append((addr[0], addr[1], pseudo, conn))
            print(f"[DEBUG] File d'attente actuelle : {queue}")  # Log de l'état de la file d'attente

        conn.sendall(b"En attente d'un adversaire...\n")

        while True:
            try:
                data = conn.recv(1024).decode()
                print(f"[DEBUG] Données reçues : {data}")  # Log détaillé des données reçues
                if not data:
                    print(f"[!] Déconnexion de {addr}")
                    break
                handle_move(data)
            except Exception as e:
                print(f"[!] Erreur lors du traitement des données de {addr} : {e}")
                break
    except Exception as e:
        print(f"[!] Erreur avec {addr} : {e}")
    finally:
        print(f"[DEBUG] Connexion fermée pour {addr}")  # Log de la fermeture de connexion
        conn.close()

def handle_move(data):
    try:
        match_id, player_number, move = data.strip().split(',')
        i, j = int(move[0]), int(move[1])
        player_number = int(player_number)

        with lock:
            match = matches.get(int(match_id))
            if not match:
                return

            board = list(match['board'])
            index = i * 3 + j

            if board[index] != ' ':
                print("[!] Coup invalide : case déjà occupée")
                return

            board[index] = 'X' if player_number == 1 else 'O'
            match['board'] = ''.join(board)

            is_over, winner = check_game_end(match['board'])
            match['is_finished'] = is_over
            match['winner'] = winner

            target_conn = match['player2_conn'] if player_number == 1 else match['player1_conn']
            target_conn.sendall(f"Coup joué: {move}".encode())

    except Exception as e:
        print(f"[!] Erreur dans handle_move : {e}")

def notify_player(conn, match_id, player_number):
    try:
        message = f"Match trouvé ! ID: {match_id}, Joueur: {player_number}"
        conn.sendall(message.encode())
    except Exception as e:
        print(f"[!] Impossible de notifier un joueur : {e}")

def matchmaking():
    global match_id_counter
    while True:
        with lock:
            # Nettoyer la file d'attente des connexions fermées
            queue[:] = [player for player in queue if player[3].fileno() != -1]

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
                notify_player(p1[3], match_id, 1)
                notify_player(p2[3], match_id, 2)

        time.sleep(2)

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()
    print(f"[+] Serveur en écoute sur {HOST}:{PORT}")

    threading.Thread(target=matchmaking, daemon=True).start()

    while True:
        conn, addr = server.accept()
        threading.Thread(target=handle_client, args=(conn, addr)).start()

class MyHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"<html><body><h1>Serveur HTTP actif</h1></body></html>")

def signal_handler(sig, frame):
    print("\n[!] Arrêt du serveur...")
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)  # Capture Ctrl+C
    threading.Thread(target=start_server, daemon=True).start()
    with HTTPServer((HOST, HTTP_PORT), MyHandler) as http_server:
        print(f"Serveur HTTP en écoute sur {HOST}:{HTTP_PORT}")
        try:
            http_server.serve_forever()
        except KeyboardInterrupt:
            print("\n[!] Serveur HTTP arrêté.")
