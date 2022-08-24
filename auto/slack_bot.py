import sys
from slack_sdk import WebClient
import json


class SlackWrapper:
    def __init__(self, api_key):
        self.client = WebClient(token=api_key)

    def send_verification_message(self, first_name, last_name, verification_number):
        verification_message_block = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        "*hey is this you?*\n\n"
                        "my name is FalconTrack, and i am the fastest bot alive."
                        " i recently discovered that a new person was trying to sign"
                        " into an account with permissions on another level."
                        " is this you? pls enter the 6 digit code below into FalconTrack."
                    ),
                },
            },
            {"type": "divider"},
        ]

        verification_number_messsage = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (f"*{verification_number}*"),
                },
            }
        ]

        try:
            print("first name")
            self.client.chat_postMessage(
                channel=f"@{first_name}", blocks=verification_message_block
            )
            self.client.chat_postMessage(
                channel=f"@{first_name}", blocks=verification_number_messsage
            )
            return None
        except:
            try:
                print("firstinit_lastname")
                print(f"@{first_name[0]}{last_name}")
                self.client.chat_postMessage(
                    channel=f"@{first_name[0]}{last_name}",
                    blocks=verification_message_block,
                )
                self.client.chat_postMessage(
                    channel=f"@{first_name[0]}{last_name}",
                    blocks=verification_number_messsage,
                )
                return None
            except:
                print("firstinit_lastname_1")
                self.client.chat_postMessage(
                    channel=f"@{first_name[0]}{last_name}1",
                    blocks=verification_message_block,
                )
                self.client.chat_postMessage(
                    channel=f"@{first_name[0]}{last_name}1",
                    blocks=verification_number_messsage,
                )
