import threading
import configparser
bot_stop_event = threading.Event()

config = configparser.ConfigParser()
config.read('resources/config.cfg')

botIsRunning = False
streamEnding = False

class TwitchState:
    def __init__(self):
        self.twitch = None
        self.chat = None

state = TwitchState()

text = bool(config['user_settings']['admin_mode'])
if text:
    adminMode = True
else:
    adminMode = False

customMessage = config['user_settings']['custom_message']