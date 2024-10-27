import os
import asyncio
from dotenv import load_dotenv
import discord
from api_client import APIClient
from database import Database
from utils import is_valid_steam_id
import json
from collections import deque

# Lade .env-Datei
load_dotenv()

# Konfiguration
TOKEN = os.getenv('DISCORD_BOT_TOKEN')
API_BASE_URL = os.getenv('API_BASE_URL')
API_TOKEN = os.getenv('API_TOKEN')
ALLOWED_CHANNEL_ID = os.getenv('ALLOWED_CHANNEL_ID')
DB_FILE = os.getenv('DB_FILE')
LANGUAGE = os.getenv('LANGUAGE', 'en')
COMMAND_SWITCH = os.getenv('COMMAND_SWITCH', 'switch')
COMMAND_REG = os.getenv('COMMAND_REG', 'reg')

# Lade die Sprachdatei
with open('translations.json', 'r', encoding='utf-8') as file:
    all_langs = json.load(file)
    lang = all_langs.get(LANGUAGE, all_langs['en'])

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

# Globale Warteschlange
switch_queue = deque()

class MyBot(discord.Client):
    def __init__(self, intents):
        super().__init__(intents=intents)
        self.db = Database(DB_FILE)
        self.api_client = APIClient(API_BASE_URL, API_TOKEN)
        # Hintergrundprozess wird jetzt in setup_hook gestartet

    async def setup_hook(self):
        self.loop.create_task(self.process_switch_queue())  # Hintergrundprozess starten

    async def on_ready(self):
        print(lang['logged_in'].format(bot_name=self.user))
        print(lang['api_initialized'])  # Neue Meldung hinzufügen, wenn die API-Initialisierung erfolgreich war

    async def on_message(self, message):
        # Ignoriere Nachrichten von Bots oder wenn der Bot selbst die Nachricht gesendet hat
        if message.author.bot or message.channel.id != int(ALLOWED_CHANNEL_ID):
            return

        # Rufe die handle_command Funktion auf
        await handle_command(self, message)

    async def process_switch_queue(self):
        await self.wait_until_ready()
        channel = self.get_channel(int(ALLOWED_CHANNEL_ID))
        while not self.is_closed():
            if switch_queue:
                player_info = switch_queue[0]  # Ersten Spieler in der Warteschlange auswählen

                try:
                    # Spielstatus abrufen
                    gamestate = self.api_client.get_gamestate()
                    num_allied_players = gamestate['result']['num_allied_players']
                    num_axis_players = gamestate['result']['num_axis_players']

                    # Spielerzahl auf der Zielseite ermitteln
                    target_team_players = num_axis_players if player_info['target_team'] == 'axis' else num_allied_players

                    if target_team_players < 50:
                        # Überprüfen, ob der Spieler noch im Spiel ist
                        players = self.api_client.get_detailed_players()
                        in_game = False
                        for pid, pdata in players['result']['players'].items():
                            if pdata['name'] == player_info['player_name']:
                                in_game = True
                                break

                        if not in_game:
                            # Spieler ist nicht mehr im Spiel
                            await channel.send(lang['player_left_game'].format(player_name=player_info['player_name']))
                            switch_queue.popleft()
                            continue

                        # Spieler wechseln
                        response = self.api_client.switch_player_now(player_info['player_name'])
                        if response.get('result') == True and not response.get('failed'):
                            await channel.send(lang['switch_request_success'].format(player_name=player_info['player_name']))
                            switch_queue.popleft()
                        else:
                            await channel.send(lang['switch_request_failure'].format(player_name=player_info['player_name']))
                            switch_queue.popleft()  # Optional: Spieler aus der Warteschlange entfernen
                    else:
                        # Zielseite ist noch voll
                        pass
                except Exception as e:
                    print(f"Fehler in process_switch_queue: {e}")
                    switch_queue.popleft()  # Optional: Fehlerbehandlung
            await asyncio.sleep(10)  # Alle 10 Sekunden überprüfen

async def handle_command(client, message):
    if message.content.startswith(f'!{COMMAND_REG}'):
        parts = message.content.split()
        if len(parts) == 2 and is_valid_steam_id(parts[1]):
            steam_id = parts[1]

            # API-Anfrage, um das Spielerprofil zu erhalten
            player_info = client.api_client.get_player_profile(steam_id)
            if not player_info.get('failed') and 'result' in player_info and player_info['result']['names']:
                player_name = player_info['result']['names'][0]['name']  # Erster Name in der Liste
                if client.db.add_user_with_name(message.author.id, steam_id, player_name):
                    await message.channel.send(lang['register_success'].format(
                        player_name=player_name,
                        steam_id=steam_id,
                        user_mention=message.author.mention
                    ))
                else:
                    await message.channel.send(lang['register_failure'].format(steam_id=steam_id))
            else:
                await message.channel.send(lang['fetch_failure'].format(steam_id=steam_id))
        else:
            await message.channel.send(lang['invalid_steam_id'])

    elif message.content.startswith(f'!{COMMAND_SWITCH}'):
        discord_id = str(message.author.id)
        steam_id, player_name = client.db.get_steam_id_and_name(discord_id)

        if steam_id is None or player_name is None:
            await message.channel.send(lang['not_registered'].format(COMMAND_REG=COMMAND_REG))
        else:
            # Detaillierte Spielerinformationen abrufen
            players = client.api_client.get_detailed_players()
            player_team = None
            for pid, pdata in players['result']['players'].items():
                if pdata['name'] == player_name:
                    player_team = pdata['team']
                    break

            if player_team is None:
                await message.channel.send(lang['player_not_in_game'])
                return

            # Zielteam bestimmen
            target_team = 'axis' if player_team.lower() == 'allies' else 'allies'

            # Spielstatus abrufen
            gamestate = client.api_client.get_gamestate()
            num_allied_players = gamestate['result']['num_allied_players']
            num_axis_players = gamestate['result']['num_axis_players']

            # Spielerzahl auf der Zielseite ermitteln
            target_team_players = num_axis_players if target_team == 'axis' else num_allied_players

            if target_team_players < 50:
                # Spieler kann sofort wechseln
                response = client.api_client.switch_player_now(player_name)
                if response.get('result') == True and not response.get('failed'):
                    await message.channel.send(lang['switch_request_success'].format(player_name=player_name))
                else:
                    await message.channel.send(lang['switch_request_failure'].format(player_name=player_name))
            else:
                # Optional: Warteschlange begrenzen
                MAX_QUEUE_SIZE = 10  # Maximale Warteschlangengröße
                if len(switch_queue) >= MAX_QUEUE_SIZE:
                    await message.channel.send(lang['queue_full'])
                else:
                    # Spieler zur Warteschlange hinzufügen
                    switch_queue.append({
                        'player_name': player_name,
                        'target_team': target_team,
                        'discord_id': discord_id
                    })
                    await message.channel.send(lang['added_to_queue'].format(
                        player_name=player_name,
                        target_team=target_team.capitalize()
                    ))
    else:
        # Unbekannter Befehl
        await message.channel.send(lang['unknown_command'].format(
            COMMAND_REG=COMMAND_REG,
            COMMAND_SWITCH=COMMAND_SWITCH
        ))

# Bot-Instanz erstellen und starten
bot = MyBot(intents=intents)
bot.run(TOKEN)
