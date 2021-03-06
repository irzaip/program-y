"""
Copyright (c) 2016-2018 Keith Sterling http://www.keithsterling.com

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
documentation files (the "Software"), to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the
Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
from programy.utils.logging.ylogger import YLogger

from flask import Flask, request
from pymessenger.bot import Bot

from programy.clients.restful.flask.client import FlaskRestBotClient
from programy.clients.restful.flask.facebook.config import FacebookConfiguration


class FacebookBot(object):

    def __init__(self, access_token):
        self._bot = Bot(access_token)

    def send_text_message(self, recipient_id, response):
        self._bot.send_text_message(recipient_id, response)


class FacebookBotClient(FlaskRestBotClient):
    
    def __init__(self, argument_parser=None):
        FlaskRestBotClient.__init__(self, 'facebook', argument_parser)

        YLogger.debug(self, "Facebook Client is running....")

        self._facebook_bot = self.create_facebook_bot()

        print("Facebook Client loaded")

    def get_description(self):
        return 'ProgramY AIML2.0 Facebook Client'

    def get_license_keys(self):
        self._access_token = self.license_keys.get_key("FACEBOOK_ACCESS_TOKEN")
        self._verify_token = self.license_keys.get_key("FACEBOOK_VERIFY_TOKEN")

    def get_client_configuration(self):
        return FacebookConfiguration()

    def create_facebook_bot(self):
        return FacebookBot(self._access_token)

    def get_hub_challenge(self, request):
        return request.args.get("hub.challenge")

    def get_hub_verify_token(self, request):
        return request.args.get("hub.verify_token")

    def verify_fb_token(self, token_sent, request):
        # take token sent by facebook and verify it matches the verify token you sent
        # if they match, allow the request, else return an error
        if token_sent is None:
            YLogger.error(self, "Verify Token is None!")

        if token_sent == self._verify_token:
            return self.get_hub_challenge(request)

        YLogger.error(self, "Facebook verify token failed received [%s]", token_sent)
        return 'Invalid verification token'

    def return_hub_challenge(self, request):
        """Before allowing people to message your bot, Facebook has implemented a verify token
        that confirms all requests that your bot receives came from Facebook."""
        token_sent = self.get_hub_verify_token(request)
        return self.verify_fb_token(token_sent, request)

    def send_message(self, recipient_id, response):
        # sends user the text message provided via input response parameter
        self._facebook_bot.send_text_message(recipient_id, response)
        return "success"

    def receive_message(self, request):
        if request.method == 'GET':
            return self.return_hub_challenge(request)
        else:
            data = request.get_json()
            self.process_facebook_request(data)
        return "Message Processed"

    def get_recipitent_id(self, message):
        if 'sender' in message:
            if 'id' in message['sender']:
                return message['sender']['id']
        return None

    def get_message_text(self, message):
        if 'message' in message:
            return message['message'].get('text')
        return None

    def has_attachements(self, message):
        if 'message' in message:
            if message['message'].get('attachments') is not None:
                return True
        return False

    def process_facebook_request(self, request):
        if 'entry' in request:
            for event in request['entry']:
                if 'messaging' in event:
                    messaging = event['messaging']
                    self.process_facebook_message(messaging)

    def process_facebook_message(self, messaging):
        for message in messaging:
            if message.get('message'):
                self.handle_message(message)

    def handle_message(self, message):

        if self.configuration.client_configuration.debug is True:
            self.dump_request(message)

        # Facebook Messenger ID for user so we know where to send response back to
        recipient_id = self.get_recipitent_id(message)
        if recipient_id:

            message_text = self.get_message_text(message)
            # We have been send a text message, we can respond
            if message_text is not None:
                response_text = self.ask_question(recipient_id, message_text)

            # else if user sends us a GIF, photo,video, or any other non-text item
            elif self.has_attachements(message):
                response_text = "Sorry, I cannot handle attachements right now!"

            # otherwise its a general error
            else:
                response_text = "Sorry, I do not understand you!"

            self.send_message(recipient_id, response_text)

if __name__ == "__main__":

    FACEBOOK_CLIENT = None

    print("Initiating Facebook Client...")
    APP = Flask(__name__)

    @APP.route("/api/facebook/v1.0/ask", methods=['GET', 'POST'])
    def receive_message():
        try:
            return FACEBOOK_CLIENT.receive_message(request)
        except Exception as e:
            YLogger.exception(None, e)

    FACEBOOK_CLIENT = FacebookBotClient()
    FACEBOOK_CLIENT.run(APP)

