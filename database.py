import sqlite3


class Database:
    def __init__(self, db_file: str):
        # check_same_thread=False, falls du irgendwann Threads nutzt
        self.connection = sqlite3.connect(db_file, check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        self.connection.execute('''CREATE TABLE IF NOT EXISTS users
                                   (discord_id TEXT PRIMARY KEY,
                                    steam_id   TEXT,
                                    player_name TEXT)''')
        self.connection.commit()

    def add_user_with_name(self, discord_id: str, steam_id: str, player_name: str) -> bool:
        cursor = self.connection.cursor()
        cursor.execute('SELECT 1 FROM users WHERE discord_id = ?', (discord_id,))
        if cursor.fetchone() is None:
            with self.connection:
                self.connection.execute(
                    'INSERT INTO users (discord_id, steam_id, player_name) VALUES (?, ?, ?)',
                    (discord_id, steam_id, player_name)
                )
            return True
        else:
            # optional: Namen aktualisieren, falls er sich geändert hat
            with self.connection:
                self.connection.execute(
                    'UPDATE users SET steam_id = ?, player_name = ? WHERE discord_id = ?',
                    (steam_id, player_name, discord_id)
                )
            return False  # existierte bereits

    def get_steam_id_and_name(self, discord_id: str):
        cursor = self.connection.cursor()
        cursor.execute('SELECT steam_id, player_name FROM users WHERE discord_id = ?', (discord_id,))
        result = cursor.fetchone()
        return (result[0], result[1]) if result else (None, None)
