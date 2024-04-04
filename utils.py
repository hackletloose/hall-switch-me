def is_valid_steam_id(steam_id):
    return steam_id.isdigit() and steam_id.startswith('7656') and len(steam_id) == 17