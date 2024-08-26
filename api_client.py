import requests

class APIClient:
    def __init__(self, base_url, api_token):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_token}",
            "Connection": "keep-alive",
            "Content-Type": "application/json"
        })

    def login(self, username, password):
        url = f'{self.base_url}/api/login'
        data = {'username': username, 'password': password}
        response = self.session.post(url, json=data)
        if response.status_code != 200:
            print(f"Fehler beim Login: {response.status_code}, Antwort: {response.text}")
            return False
        return True

    def switch_player_now(self, player_name):
        url = f'{self.base_url}/api/switch_player_now'
        data = {"player_name": player_name}
        response = self.session.post(url, json=data)
        response.raise_for_status()
        return response.json()

    def get_player_profile(self, steam_id_64):
        url = f'{self.base_url}/api/get_player_profile?player_id={steam_id_64}'
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()
