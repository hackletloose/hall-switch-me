import os
from dotenv import load_dotenv
import discord
from api_client import APIClient
from database import Database
from utils import is_valid_steam_id
import json

# Lade .env-Datei
load_dotenv()

# Konfiguration
TOKEN = os.getenv('DISCORD_BOT_TOKEN')
API_BASE_URL = os.getenv('API_BASE_URL')
USERNAME = os.getenv('USERNAME')
PASSWORD = os.getenv('PASSWORD')
API_TOKEN = os.getenv('API_TOKEN')
ALLOWED_CHANNEL_ID = os.getenv('ALLOWED_CHANNEL_ID')
DB_FILE = os.getenv('DB_FILE')
LANGUAGE = os.getenv('LANGUAGE', 'en')
COMMAND_SWITCH = os.getenv('COMMAND_SWITCH')
COMMAND_REG = os.getenv('COMMAND_REG')

# Lade die Sprachdatei
with open('translations.json', 'r') as file:
    all_langs = json.load(file)
    lang = all_langs.get(LANGUAGE, all_langs['en'])

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True


class MyBot(discord.Client):
    def __init__(self, intents):
        super().__init__(command_prefix='!', intents=intents)
        self.db = Database(DB_FILE)
        self.api_client = APIClient(API_BASE_URL, API_TOKEN)

    async def on_ready(self):
        print(lang['logged_in'].format(bot_name=self.user))
        if self.api_client.login(USERNAME, PASSWORD):
            print(lang['api_login_success'])
        else:
            print(lang['api_login_failure'])

    async def on_message(self, message):
        # Ignoriere Nachrichten von Bots oder wenn der Bot selbst die Nachricht gesendet hat
        if message.author.bot or message.channel.id != int(ALLOWED_CHANNEL_ID):
            return

        # Rufe die handle_command Funktion auf
        await handle_command(self, message)

async def handle_command(client, message):
    if message.content.startswith(f'!{COMMAND_REG}'):
        parts = message.content.split()
        if len(parts) == 2 and is_valid_steam_id(parts[1]):
            steam_id = parts[1]

            # API-Anfrage, um den Spielername zu erhalten
            player_info = client.api_client.get_player_by_steam_id(steam_id)
            if not player_info.get('failed') and 'result' in player_info and player_info['result']['names']:
                player_name = player_info['result']['names'][0]['name']  # Erster Name in der Liste
                if client.db.add_user_with_name(message.author.id, steam_id, player_name):
                    await message.channel.send(lang['register_success'].format(player_name=player_name, steam_id=steam_id, user_mention=message.author.mention))
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
            await message.channel.send(lang['not_registered'])
        else:
            response = client.api_client.do_switch_player_now(player_name, steam_id, 'Nachricht')
            if response.get('result') == 'SUCCESS' and not response.get('failed'):
                await message.channel.send(lang['switch_request_success'].format(player_name=player_name))
            else:
                await message.channel.send(lang['switch_request_failure'].format(player_name=player_name))




# Bot-Instanz erstellen und starten
bot = MyBot(intents=intents)
bot.run(TOKEN)
