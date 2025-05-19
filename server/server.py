import socket
import threading
import sqlite3
import time
 
HOST = '0.0.0.0'
PORT = 12345
DB_FILE = 'matchmaking.db'
 
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
        return True, 0  # égalité
    return False, None

def handle_client(conn, addr):
    print(f"[+] Connexion de {addr}")
    try:
        pseudo = conn.recv(1024).decode()
        print(f"[+] Pseudo reçu : {pseudo}")
 
        # Ajouter à la file d'attente
        with sqlite3.connect(DB_FILE) as db:
            cursor = db.cursor()
            cursor.execute(
                "INSERT INTO queue (ip, port, pseudo) VALUES (?, ?, ?)",
                (addr[0], addr[1], pseudo)
            )
            db.commit()
 
        conn.sendall(b"En attente d'un adversaire...\n")
 
        # Boucle d'écoute des coups
        while True:
            try:
                data = conn.recv(1024).decode()
                if not data:
                    print(f"[!] Déconnexion de {addr}")
                    break
                print(f"[+] Données reçues : {data}")
                handle_move(data)
            except ConnectionResetError:
                print(f"[!] Client {addr} déconnecté brutalement")
                break
 
    except Exception as e:
        print(f"[!] Erreur avec {addr} : {e}")
    finally:
        conn.close()

def handle_move(data):
    try:
        match_id, player_number, move = data.strip().split(',')
        i, j = int(move[0]), int(move[1])
        player_number = int(player_number)
 
        with sqlite3.connect(DB_FILE) as db:
            cursor = db.cursor()
 
            # Récupérer le plateau actuel
            cursor.execute("SELECT board, player1_ip, player1_port, player2_ip, player2_port FROM matches WHERE id = ?", (match_id,))
            result = cursor.fetchone()
            if not result:
                return
 
            board, p1_ip, p1_port, p2_ip, p2_port = result
            board = list(board)
            index = i * 3 + j
 
            # Vérifier si la case est déjà prise
            if board[index] != ' ':
                print("[!] Coup invalide : case déjà occupée")
                return
 
            board[index] = 'X' if player_number == 1 else 'O'
            new_board = ''.join(board)
 
            # Vérifier fin de partie
            is_over, winner = check_game_end(new_board)
 
            # Mettre à jour le plateau et l'état du match
            cursor.execute("UPDATE matches SET board = ?, is_finished = ?, winner = ? WHERE id = ?",
                           (new_board, int(is_over), winner, match_id))
 
            # Enregistrer le tour
            cursor.execute("INSERT INTO turns (match_id, player, move) VALUES (?, ?, ?)", (match_id, player_number, move))
            db.commit()
 
        # Relayer le coup à l'autre joueur
        target_ip = p2_ip if player_number == 1 else p1_ip
        target_port = p2_port if player_number == 1 else p1_port
 
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((target_ip, target_port))
            s.sendall(f"Coup joué: {move}".encode())
 
    except Exception as e:
        print(f"[!] Erreur dans handle_move : {e}")
 
    except Exception as e:
        print(f"[!] Erreur dans handle_move : {e}")
 
def notify_player(player, match_id, player_number):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((player[1], player[2]))
            message = f"Match trouvé ! ID: {match_id}, Joueur: {player_number}"
            s.sendall(message.encode())
    except Exception as e:
        print(f"[!] Impossible de notifier {player[3]} : {e}")
 
def matchmaking():
    while True:
        with sqlite3.connect(DB_FILE) as db:
            cursor = db.cursor()
            cursor.execute("SELECT * FROM queue ORDER BY entry_time LIMIT 2")
            players = cursor.fetchall()
 
            if len(players) >= 2:
                player1 = players[0]
                player2 = players[1]
 
                # Créer un match avec un plateau vide
                cursor.execute(
                    "INSERT INTO matches (player1_ip, player1_port, player2_ip, player2_port, board, is_finished, winner) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (player1[1], player1[2], player2[1], player2[2], ' ' * 9, 0, None)
                )
                match_id = cursor.lastrowid
 
                # Supprimer les joueurs de la file
                cursor.execute("DELETE FROM queue WHERE id IN (?, ?)", (player1[0], player2[0]))
                db.commit()
 
                print(f"[+] Match créé entre {player1[3]} et {player2[3]} (ID: {match_id})")
 
                # Notifier les joueurs
                notify_player(player1, match_id, 1)
                notify_player(player2, match_id, 2)
 
        time.sleep(5)

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()
    print(f"[+] Serveur en écoute sur {HOST}:{PORT}")
 
    # Lancer le thread de matchmaking
    matchmaking_thread = threading.Thread(target=matchmaking, daemon=True)
    matchmaking_thread.start()
 
    while True:
        conn, addr = server.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.start()
 
if __name__ == "__main__":
    start_server()