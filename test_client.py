#!/usr/bin/env python3
"""
Client de test simple pour valider le serveur en mode réel
"""

import socket
import threading
import time
import sys
import os

# Ajouter le chemin vers les modules partagés
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from shared.protocol import Protocol, MessageType, GameMessages
    USE_NEW_PROTOCOL = True
    print("✓ Nouveau protocole chargé")
except ImportError:
    USE_NEW_PROTOCOL = False
    print("⚠️ Utilisation du mode compatibilité")

def test_client(player_name, server_ip="10.31.32.143", server_port=12345):
    """Test d'un client simple"""
    print(f"🔌 Test du client {player_name}")
    
    try:
        # Connexion au serveur
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((server_ip, server_port))
        print(f"✓ {player_name} connecté au serveur")
        
        if USE_NEW_PROTOCOL:
            # Utiliser le nouveau protocole
            protocol = Protocol()
            game_messages = GameMessages()
            
            # Envoyer un message de connexion (mode compatibilité - juste le pseudo)
            sock.sendall(player_name.encode())
        else:
            # Ancien protocole - envoyer juste le pseudo
            sock.sendall(player_name.encode())
        
        # Écouter les réponses du serveur
        buffer = b""
        timeout_count = 0
        max_timeout = 30  # 30 secondes max
        
        while timeout_count < max_timeout:
            try:
                sock.settimeout(1.0)  # Timeout de 1 seconde
                data = sock.recv(1024)
                
                if not data:
                    break
                    
                buffer += data
                message = buffer.decode()
                buffer = b""  # Reset buffer après décodage
                
                print(f"📨 {player_name} reçu: {message.strip()}")
                
                # Si on reçoit un match trouvé, simuler quelques coups
                if "Match trouvé" in message or "match_found" in message.lower():
                    print(f"🎮 {player_name} commence à jouer")
                    
                    # Simuler quelques coups (format ancien protocole)
                    moves = ["1,1,00", "1,1,11", "1,1,22"]  # match_id,player_num,position
                    for i, move in enumerate(moves):
                        time.sleep(2)  # Attendre 2 secondes entre les coups
                        try:
                            sock.sendall(move.encode())
                            print(f"🎯 {player_name} joue: {move}")
                        except:
                            break
                        
                        if i >= 2:  # Limiter à 3 coups par joueur
                            break
                
                timeout_count = 0  # Reset timeout sur réception de données
                
            except socket.timeout:
                timeout_count += 1
                continue
            except Exception as e:
                print(f"❌ Erreur pour {player_name}: {e}")
                break
        
        if timeout_count >= max_timeout:
            print(f"⏰ Timeout pour {player_name}")
            
    except Exception as e:
        print(f"❌ Erreur de connexion pour {player_name}: {e}")
    finally:
        try:
            sock.close()
            print(f"🔐 {player_name} déconnecté")
        except:
            pass

def test_multiple_clients():
    """Test avec plusieurs clients simultanés"""
    print("🧪 Test avec plusieurs clients")
    
    # Créer des threads pour simuler plusieurs clients
    threads = []
    
    for i in range(2):
        player_name = f"TestPlayer{i+1}"
        thread = threading.Thread(target=test_client, args=(player_name,))
        threads.append(thread)
    
    # Lancer les clients avec un petit délai
    for i, thread in enumerate(threads):
        if i > 0:
            time.sleep(1)  # Délai entre les connexions
        thread.start()
        print(f"🚀 Client {i+1} lancé")
    
    # Attendre que tous les threads se terminent
    for thread in threads:
        thread.join()
    
    print("✅ Test terminé")

def main():
    """Fonction principale"""
    print("🧪 Test du serveur de matchmaking")
    print("=" * 40)
    
    # Vérifier si le serveur écoute
    try:
        test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        test_sock.settimeout(2)
        result = test_sock.connect_ex(('127.0.0.1', 12345))
        test_sock.close()
        
        if result == 0:
            print("✓ Serveur détecté sur 127.0.0.1:12345")
        else:
            print("❌ Serveur non détecté. Assurez-vous qu'il est démarré.")
            return
    except Exception as e:
        print(f"❌ Erreur de vérification du serveur: {e}")
        return
    
    # Test avec plusieurs clients
    test_multiple_clients()

if __name__ == "__main__":
    main()
