import ssl
import certifi
from slack_sdk import WebClient


class SlackWrapper:
    def __init__(self, api_key):
        # Bypass SSL certificate not being verified
        self.client = WebClient(token=api_key, ssl=ssl.create_default_context(cafile=certifi.where()))
        self.members = {}
        for member in self.client.users_list()["members"]:
            try:
                self.members[member["real_name"].lower()] = member["id"]
            except:
                pass

    def send_message(self, first_name, last_name, block):
        try:
            self.client.chat_postMessage(
                channel=f"@{self.members[first_name+' '+last_name]}", blocks=block
            )
            return None
        except:
            print(f"@{first_name[0]}{last_name}")
            self.client.chat_postMessage(
                channel=f"@{self.members[first_name[0]+last_name]}",
                blocks=block,
            )
            return None

    def send_verification_message(self, first_name, last_name, verification_number):
        verification_block = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*FalconTrack Code*: {verification_number}"
                    ),
                },
            }
        ]

        self.send_message(first_name, last_name, verification_block)

    def send_generic_message(self, first_name, last_name, message):
        generic_text_block = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (message),
                },
            },
            {"type": "divider"},
        ]

        self.send_message(first_name, last_name, generic_text_block)
