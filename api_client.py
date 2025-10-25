import requests


class APIClient:
    def __init__(self, base_url: str, api_token: str):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_token}",
            "Connection": "keep-alive",
            "Content-Type": "application/json",
        })

    # ---- NEW signature: expects player_id (Steam64 / Xbox-ID), not name
    def switch_player_now(self, player_id: str):
        url = f"{self.base_url}/api/switch_player_now"
        data = {"player_id": str(player_id)}
        resp = self.session.post(url, json=data)
        resp.raise_for_status()
        return resp.json()

    def get_player_profile(self, player_id: str, num_sessions: int = 10):
        url = f"{self.base_url}/api/get_player_profile"
        params = {"player_id": str(player_id), "num_sessions": int(num_sessions)}
        resp = self.session.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

    def get_gamestate(self):
        url = f"{self.base_url}/api/get_gamestate"
        resp = self.session.get(url)
        resp.raise_for_status()
        return resp.json()

    def get_detailed_players(self):
        url = f"{self.base_url}/api/get_detailed_players"
        resp = self.session.get(url)
        resp.raise_for_status()
        return resp.json()

    # Optional: Mapping Name -> ID, falls du mal per Name auflösen willst
    def get_player_ids(self, as_dict: bool = True):
        url = f"{self.base_url}/api/get_player_ids"
        params = {"as_dict": str(as_dict).lower()}
        resp = self.session.get(url, params=params)
        resp.raise_for_status()
        return resp.json()
