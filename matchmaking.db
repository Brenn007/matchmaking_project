-- Table des matchs
CREATE TABLE matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player1_ip TEXT NOT NULL,
    player1_port INTEGER NOT NULL,
    player2_ip TEXT NOT NULL,
    player2_port INTEGER NOT NULL,
    board TEXT NOT NULL,
    is_finished BOOLEAN NOT NULL,
    winner INTEGER
);

-- Table des tours
CREATE TABLE turns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id INTEGER NOT NULL,
    player INTEGER NOT NULL,
    move TEXT NOT NULL,
    FOREIGN KEY (match_id) REFERENCES matches (id)
);

-- Séquence SQLite (utilisée pour l'auto-incrémentation)
CREATE TABLE sqlite_sequence(name, seq);

-- File d'attente des joueurs
CREATE TABLE queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ip TEXT NOT NULL,
    port INTEGER NOT NULL,
    pseudo TEXT NOT NULL,
    entry_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
