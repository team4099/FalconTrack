import sys
from slack_sdk import WebClient
import json


class SlackWrapper:
    def __init__(self, api_key):
        self.client = WebClient(token=api_key)

    def send_message(self, first_name, last_name, block):
        try:
            print("first name")
            self.client.chat_postMessage(
                channel=self.client.users_lookupByEmail(
                    email=f"{first_name}@team4099.com"
                )["user"]["id"],
                blocks=block,
            )
            return None
        except:
            try:
                print("flast_name")
                self.client.chat_postMessage(
                    channel=self.client.users_lookupByEmail(
                        email=f"{first_name[0]}{last_name}@team4099.com"
                    )["user"]["id"],
                    blocks=block,
                )
                return None
            except:
                print("flast_name1")
                self.client.chat_postMessage(
                    channel=self.client.users_lookupByEmail(
                        email=f"{first_name[0]}{last_name}1@team4099.com"
                    )["user"]["id"],
                    blocks=block,
                )
                return None

    def send_verification_message(self, first_name, last_name, verification_number):
        verification_text_block = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        "*hey is this you?*\n\n"
                        " i recently discovered that a new person was trying to sign"
                        " into an account with permissions on another level."
                        " is this you? pls enter the 6 digit code below into FalconTrack."
                    ),
                },
            },
            {"type": "divider"},
        ]

        verification_number_block = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (f"*{verification_number}*"),
                },
            }
        ]

        self.send_message(first_name, last_name, verification_text_block)
        self.send_message(first_name, last_name, verification_number_block)

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
