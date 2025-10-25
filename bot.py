import os
import asyncio
from dotenv import load_dotenv
import discord
from api_client import APIClient
from database import Database
from utils import is_valid_steam_id
import json
from collections import deque
import logging
from logging.handlers import TimedRotatingFileHandler
import gzip
import shutil
from typing import Optional, Tuple, List

# ---------------------------------------------------------------------
# .env laden
# ---------------------------------------------------------------------
load_dotenv()

# Discord / App-Konfiguration
TOKEN = os.getenv('DISCORD_BOT_TOKEN', '')
ALLOWED_CHANNEL_ID = os.getenv('ALLOWED_CHANNEL_ID', '')
DB_FILE = os.getenv('DB_FILE', 'bot.db')
LANGUAGE = os.getenv('LANGUAGE', 'en')
COMMAND_SWITCH = os.getenv('COMMAND_SWITCH', 'switch')
COMMAND_REG = os.getenv('COMMAND_REG', 'reg')

# RCON-Konfiguration
# Gemeinsamer Token für alle RCONs
API_TOKEN = os.getenv('API_TOKEN', '').strip()

# Variante A (empfohlen bei gleichem Token): Kommagetrennte Base-URLs oder JSON-Array von Strings
API_BASE_URLS = os.getenv('API_BASE_URLS', '').strip()

# Variante B (Legacy/Fallback): Einzel-Base-URL
API_BASE_URL = os.getenv('API_BASE_URL', '').strip()

# Variante C (Legacy/Optional): JSON-Array aus Objekten [{name, base_url, api_token}]
# – wird nur verwendet, wenn gesetzt; sonst ignoriert
RCONS_ENV = os.getenv('RCONS', '').strip()

# ---------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------
if not os.path.exists('logs'):
    os.makedirs('logs')

logger = logging.getLogger('discord_bot')
logger.setLevel(logging.DEBUG)

handler = TimedRotatingFileHandler(
    filename='logs/discord_bot.log',
    when='midnight',
    interval=1,
    backupCount=7,
    encoding='utf-8',
)
handler.suffix = "%Y%m%d"
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

def compress_old_logs():
    for filename in os.listdir('logs'):
        if filename.startswith('discord_bot.log.') and not filename.endswith('.gz'):
            filepath = os.path.join('logs', filename)
            gz_path = filepath + '.gz'
            try:
                with open(filepath, 'rb') as f_in, gzip.open(gz_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
                os.remove(filepath)
            except Exception as e:
                logger.warning(f"Konnte {filepath} nicht komprimieren: {e}")

compress_old_logs()

# ---------------------------------------------------------------------
# Translations
# ---------------------------------------------------------------------
with open('translations.json', 'r', encoding='utf-8') as file:
    all_langs = json.load(file)
    lang = all_langs.get(LANGUAGE, all_langs['en'])

# ---------------------------------------------------------------------
# Discord-Intents
# ---------------------------------------------------------------------
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

# ---------------------------------------------------------------------
# Globale Warteschlange (player_id = Steam64)
# ---------------------------------------------------------------------
switch_queue = deque()

# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
def _extract_players_map(players_response: dict) -> dict:
    if not isinstance(players_response, dict):
        return {}
    result = players_response.get('result', {})
    if not isinstance(result, dict):
        return {}
    players = result.get('players', {})
    return players if isinstance(players, dict) else {}

def _find_player_by_id_or_name(players_map: dict, player_id: str, player_name: Optional[str] = None) -> Tuple[Optional[str], Optional[dict]]:
    if not isinstance(players_map, dict):
        return None, None

    if player_id in players_map:
        return player_id, players_map[player_id]

    for pid, pdata in players_map.items():
        if not isinstance(pdata, dict):
            continue
        for k in ('steam_id_64', 'player_id', 'id'):
            if str(pdata.get(k, '')).strip() == str(player_id).strip():
                return pid, pdata

    if player_name:
        low = str(player_name).strip().lower()
        for pid, pdata in players_map.items():
            if isinstance(pdata, dict) and str(pdata.get('name', '')).strip().lower() == low:
                return pid, pdata

    return None, None

# ---------------------------------------------------------------------
# Bot-Klasse
# ---------------------------------------------------------------------
class MyBot(discord.Client):
    def __init__(self, intents):
        super().__init__(intents=intents)
        self.db = Database(DB_FILE)
        self.api_clients: List[APIClient] = self._load_rcons()
        logger.debug(f'Bot-Instanz initialisiert. RCON-Clients: {len(self.api_clients)}')

    def _load_rcons(self) -> List[APIClient]:
        clients: List[APIClient] = []

        # 1) RCONS (Objektliste) – nur falls gesetzt (Legacy/Optional)
        if RCONS_ENV:
            try:
                parsed = json.loads(RCONS_ENV)
                if isinstance(parsed, list):
                    for idx, item in enumerate(parsed):
                        if not isinstance(item, dict):
                            logger.warning(f"RCONS[{idx}] ist kein Objekt; wird übersprungen.")
                            continue
                        name = str(item.get('name', f'RCON{idx}'))
                        base_url = str(item.get('base_url', '')).rstrip('/')
                        token = str(item.get('api_token', API_TOKEN)).strip()
                        if not base_url or not token:
                            logger.warning(f"RCONS[{idx}] unvollständig (base_url/api_token fehlen); übersprungen.")
                            continue
                        c = APIClient(base_url, token)
                        setattr(c, '_rcon_name', name)
                        clients.append(c)
                else:
                    logger.error("RCONS ist gesetzt, aber kein JSON-Array.")
            except Exception as e:
                logger.error(f"Fehler beim Parsen von RCONS: {e}")

        # 2) API_BASE_URLS (empfohlen) – gleiche Tokens, unterschiedliche Base-URLs
        if not clients and API_BASE_URLS:
            urls: List[str] = []
            # JSON-Array?
            if API_BASE_URLS.startswith('['):
                try:
                    parsed = json.loads(API_BASE_URLS)
                    if isinstance(parsed, list):
                        urls = [str(u).strip().rstrip('/') for u in parsed if str(u).strip()]
                except Exception as e:
                    logger.error(f"Fehler beim Parsen von API_BASE_URLS (JSON): {e}")
            # Kommagetrennte Liste
            if not urls:
                urls = [u.strip().rstrip('/') for u in API_BASE_URLS.split(',') if u.strip()]

            for i, base_url in enumerate(urls):
                if not base_url:
                    continue
                if not API_TOKEN:
                    logger.error("API_TOKEN fehlt; kann Client nicht bauen.")
                    continue
                c = APIClient(base_url, API_TOKEN)
                setattr(c, '_rcon_name', f'RCON{i+1}')
                clients.append(c)

        # 3) Fallback: Single-URL
        if not clients and API_BASE_URL:
            if not API_TOKEN:
                logger.error("API_TOKEN fehlt; Single-RCON kann nicht erzeugt werden.")
            else:
                c = APIClient(API_BASE_URL.rstrip('/'), API_TOKEN)
                setattr(c, '_rcon_name', 'default')
                clients.append(c)

        if not clients:
            logger.error("Keine RCON-Konfiguration gefunden. Bitte .env prüfen.")
        return clients

    async def setup_hook(self):
        self.loop.create_task(self.process_switch_queue())

    async def on_ready(self):
        logger.info(lang['logged_in'].format(bot_name=self.user))
        logger.info(lang.get('api_initialized', 'API initialized.'))

    async def on_message(self, message: discord.Message):
        try:
            if message.author.bot or message.channel.id != int(ALLOWED_CHANNEL_ID):
                return
        except Exception:
            return

        logger.debug(f'Nachricht empfangen von {message.author}: {message.content}')
        await handle_command(self, message)

    # ---------------------- Async-Wrapper für APIClient ----------------------
    async def _get_detailed_players_async(self, client: APIClient) -> dict:
        return await asyncio.to_thread(client.get_detailed_players)

    async def _get_gamestate_async(self, client: APIClient) -> dict:
        return await asyncio.to_thread(client.get_gamestate)

    async def _switch_player_now_async(self, client: APIClient, player_id: str) -> dict:
        return await asyncio.to_thread(client.switch_player_now, player_id)

    async def _find_player_across_rcons(
        self, player_id: str, player_name: Optional[str] = None
    ) -> Tuple[Optional[APIClient], Optional[str], Optional[dict]]:
        """
        Sucht den Spieler über alle konfigurierten RCONs.
        Rückgabe: (client, found_id, pdata) oder (None, None, None)
        """
        for client in self.api_clients:
            try:
                players_resp = await self._get_detailed_players_async(client)
                players_map = _extract_players_map(players_resp)
                found_id, pdata = _find_player_by_id_or_name(players_map, player_id, player_name)
                if found_id:
                    rname = getattr(client, '_rcon_name', '?')
                    logger.debug(f"Spieler {player_name or player_id} gefunden auf RCON '{rname}'")
                    return client, found_id, pdata
            except Exception as e:
                rname = getattr(client, '_rcon_name', '?')
                logger.warning(f"Fehler bei get_detailed_players auf RCON '{rname}': {e}")
        return None, None, None

    # ---------------------- Queue-Verarbeitung ------------------------
    async def process_switch_queue(self):
        await self.wait_until_ready()
        try:
            channel = self.get_channel(int(ALLOWED_CHANNEL_ID))
        except Exception:
            channel = None

        while not self.is_closed():
            if switch_queue:
                item = switch_queue[0]
                player_id = item['player_id']
                player_name = item.get('player_name')
                target_team = item['target_team']

                logger.debug(f'Queue: {player_name or player_id} -> Zielteam {target_team}')

                try:
                    client, found_id, pdata = await self._find_player_across_rcons(player_id, player_name)
                    if not client or not found_id or not isinstance(pdata, dict):
                        if channel:
                            await channel.send(lang['player_left_game'].format(
                                player_name=player_name or player_id
                            ))
                        logger.info(f'{player_name or player_id}: nicht (mehr) im Spiel.')
                        switch_queue.popleft()
                        await asyncio.sleep(1)
                        continue

                    gamestate = await self._get_gamestate_async(client)
                    res = gamestate.get('result', {}) if isinstance(gamestate, dict) else {}
                    num_allied_players = int(res.get('num_allied_players', 0))
                    num_axis_players = int(res.get('num_axis_players', 0))
                    target_team_players = num_axis_players if target_team == 'axis' else num_allied_players

                    if target_team_players < 50:
                        response = await self._switch_player_now_async(client, player_id)
                        if response.get('result') is True and not response.get('failed'):
                            if channel:
                                await channel.send(lang['switch_request_success'].format(
                                    player_name=player_name or player_id
                                ))
                            logger.info(f'Switch OK: {player_name or player_id}')
                        else:
                            if channel:
                                await channel.send(lang['switch_request_failure'].format(
                                    player_name=player_name or player_id
                                ))
                            logger.warning(f'Switch FAIL: {player_name or player_id}')
                        switch_queue.popleft()
                    else:
                        logger.debug(f"Zielteam voll für {player_name or player_id}.")
                except Exception as e:
                    logger.error(f"Fehler in process_switch_queue: {e}")
                    switch_queue.popleft()
            await asyncio.sleep(10)

# ---------------------------------------------------------------------
# Command-Handler
# ---------------------------------------------------------------------
async def handle_command(client: MyBot, message: discord.Message):
    content = message.content.strip()

    if content.startswith(f'!{COMMAND_REG}'):
        parts = content.split()
        if len(parts) == 2 and is_valid_steam_id(parts[1]):
            steam_id = parts[1]
            logger.debug(f'Registrierungsanfrage von {message.author} mit Steam-ID {steam_id}')

            api_for_profile = client.api_clients[0] if client.api_clients else None
            if not api_for_profile:
                await message.channel.send("RCON ist nicht konfiguriert.")
                return

            player_info = await asyncio.to_thread(api_for_profile.get_player_profile, steam_id)
            if (isinstance(player_info, dict)
                and not player_info.get('failed')
                and 'result' in player_info
                and player_info['result'].get('names')):

                player_name = player_info['result']['names'][0].get('name', steam_id)
                if client.db.add_user_with_name(message.author.id, steam_id, player_name):
                    await message.channel.send(lang['register_success'].format(
                        player_name=player_name,
                        steam_id=steam_id,
                        user_mention=message.author.mention
                    ))
                    logger.info(f'Registriert: {message.author} als {player_name} ({steam_id}).')
                else:
                    await message.channel.send(lang['register_failure'].format(steam_id=steam_id))
                    logger.warning(f'Registrierung bereits vorhanden/aktualisiert: {message.author} ({steam_id}).')
            else:
                await message.channel.send(lang['fetch_failure'].format(steam_id=steam_id))
                logger.warning(f'Profil für {steam_id} nicht abrufbar.')
        else:
            await message.channel.send(lang['invalid_steam_id'])
            logger.warning(f'Ungültige Steam-ID von {message.author}: {message.content}')

    elif content.startswith(f'!{COMMAND_SWITCH}'):
        discord_id = str(message.author.id)
        steam_id, player_name = client.db.get_steam_id_and_name(discord_id)

        if steam_id is None:
            await message.channel.send(lang['not_registered'].format(COMMAND_REG=COMMAND_REG))
            logger.info(f'Nicht registriert: {message.author}.')
            return

        logger.debug(f'Switch-Anfrage: {message.author} für {player_name} ({steam_id})')

        rcon_client, found_id, pdata = await client._find_player_across_rcons(steam_id, player_name)
        if not rcon_client or not found_id or not isinstance(pdata, dict):
            await message.channel.send(lang['player_not_in_game'])
            logger.info(f'{player_name} ist nicht im Spiel.')
            return

        player_team = str(pdata.get('team', '')).lower()
        if not player_team:
            await message.channel.send(lang['player_not_in_game'])
            logger.info(f'{player_name}: kein Team in Daten.')
            return

        target_team = 'axis' if player_team == 'allies' else 'allies'

        gamestate = await client._get_gamestate_async(rcon_client)
        res = gamestate.get('result', {}) if isinstance(gamestate, dict) else {}
        num_allied_players = int(res.get('num_allied_players', 0))
        num_axis_players = int(res.get('num_axis_players', 0))
        target_team_players = num_axis_players if target_team == 'axis' else num_allied_players

        if target_team_players < 50:
            response = await client._switch_player_now_async(rcon_client, steam_id)
            if response.get('result') is True and not response.get('failed'):
                await message.channel.send(lang['switch_request_success'].format(player_name=player_name or steam_id))
                logger.info(f'Switch OK: {player_name or steam_id}')
            else:
                await message.channel.send(lang['switch_request_failure'].format(player_name=player_name or steam_id))
                logger.warning(f'Switch FAIL: {player_name or steam_id}')
        else:
            MAX_QUEUE_SIZE = 10
            if len(switch_queue) >= MAX_QUEUE_SIZE:
                await message.channel.send(lang['queue_full'])
                logger.info('Warteschlange voll.')
            else:
                switch_queue.append({
                    'player_id': steam_id,
                    'player_name': player_name,
                    'target_team': target_team,
                    'discord_id': discord_id,
                })
                await message.channel.send(lang['added_to_queue'].format(
                    player_name=player_name or steam_id,
                    target_team=target_team.capitalize()
                ))
                logger.info(f'In Queue: {player_name or steam_id} -> {target_team}')

    else:
        await message.channel.send(lang['unknown_command'].format(
            COMMAND_REG=COMMAND_REG,
            COMMAND_SWITCH=COMMAND_SWITCH
        ))
        logger.warning(f'Unbekannter Befehl: {message.author}: {message.content}')

# ---------------------------------------------------------------------
# Start
# ---------------------------------------------------------------------
bot = MyBot(intents=intents)
bot.run(TOKEN)
