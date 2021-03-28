from decouple import config
import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


SLACKBOT_ACCESS_TOKEN = config('SLACK_BOT_TOKEN')



class PylabnetSlackBot():
    """ Initializes Pylabnet Slack Bot"""

    def __init__(self):
        self.client = WebClient(token=SLACKBOT_ACCESS_TOKEN)
        self.subscribed_channels = []

    def subscribe_channel(self, channel):
        """ Add Slack channel to list of subscribed channels."""
        channel_list  = channel if isinstance(channel, list) else [channel]

        for channel in channel_list:
            self.subscribed_channels.append(channel)
    
    def post_to_channel(self, channel, message):
        """Post message to channel"""
        try:
            response = self.client.chat_postMessage(channel=channel, text=message)
            assert response["message"]["text"] == message
        except SlackApiError as e:
            # You will get a SlackApiError if "ok" is False
            assert e.response["ok"] is False
            assert e.response["error"]  # str like 'invalid_auth', 'channel_not_found'
            print(f"Got an error: {e.response['error']}")

    def broadcast_to_channels(self, message):
        """ Post message to all subscribed channels"""
        for channel in self.subscribed_channels:
            self.post_to_channel(channel, message)

    def upload_file(self, channel, filepath):
        """Upload file to channel"""
        try:
            response = self.client.files_upload(channels=channel, file=filepath)
            assert response["file"]  # the uploaded file
        except SlackApiError as e:
            # You will get a SlackApiError if "ok" is False
            assert e.response["ok"] is False
            assert e.response["error"]  # str like 'invalid_auth', 'channel_not_found'
            print(f"Got an error: {e.response['error']}")

    def upload_to_channels(self, filepath):
        """Upload file to all subscribed channels"""
        for channel in self.subscribed_channels:
            self.upload_file(channel, filepath)

def main():
    slackbot = PylabnetSlackBot()
    slackbot.subscribe_channel(['#pylabnet_slackbot'])
    slackbot.broadcast_to_channels('Lorem Ipsum')
    slackbot.upload_to_channels('devices.ico')

if __name__ == "__main__":
    main()