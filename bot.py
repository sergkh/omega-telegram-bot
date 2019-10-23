#!/usr/local/bin/python3
import http.client
import urllib.parse
import json
import encodings.idna
import subprocess
import time
import sys
import logging
import logging.handlers
from time import sleep

class Handler:
    def __init__(self, matcher, handler):
        self.matcher = matcher
        self.handler = handler

class Document:
    def __init__(self, bot, caption, document):
        self.bot = bot
        self.caption = caption
        self.file_id = document['file_id']
        self.file_name = document.get('file_name')

    def download(self, path):
        file = self.bot.getFile(self.file_id)
        if file['ok']:
            url = "https://api.telegram.org/file/bot{0}/{1}".format(self.bot.token, file['result']['file_path'])
            subprocess.Popen("wget -O '{0}' '{1}'".format(path, url), shell=True).wait(timeout=90)
            return True
        else:
            return False    

class Message:
    def __init__(self, bot, msgDict):        
        self.bot = bot
        self.original = msgDict
        self.from_username = msgDict['from']['username']
        self.date = msgDict['date']
        self.chat_id = msgDict['chat']['id']
        self.text = msgDict.get('text')
        self.sticker = msgDict.get('sticker')
        self.document = Document(bot, msgDict.get('caption'), msgDict.get('document')) if msgDict.get('document') else None

    def respond(self, response, mode="Markdown"):
        self.bot.sendMessage(self.chat_id, response, None, mode)

    def respondSticker(self, sticker_id):
        self.bot.sendSticker(self.chat_id, sticker_id, None)

class TelegramBot:

    def __init__(self, token, log):
        self.token = token
        self.log = log
        self.handlers = []

    # {"ok":true, "result":[{
    #   "update_id":602971325,
    #   "message": {
    #      "message_id": 3,
    #      "from": {"id": 111111111, "is_bot": false, "first_name": "_", "last_name": "_", "username": "_", "language_code": "en-UA"},
    #      "chat": {"id": 111111111, "first_name": "_", "last_name": "_", "username": "_", "type": "private"},
    #      "date": 1520930989,
    #      "text": "hello"
    # }}
    # ]}
    def getUpdates(self, offset, timeout=90):
        conn = http.client.HTTPSConnection("api.telegram.org", 443, timeout=timeout+10)
        conn.request(
            "GET", "/bot{0}/getUpdates?offset={1}&timeout={2}".format(self.token, offset, timeout))
        rq = conn.getresponse()
        response = rq.read().decode('utf-8')
        conn.close()
        data = json.loads(response)
        if not data['ok']:
            self.log.warn("Send message data is not OK: {}, {}".format(data, rq.status))

        return data

    # https://core.telegram.org/bots/api#available-methods
    def sendMessage(self, chat_id, text, reply_to=None, mode="Markdown"):
        conn = http.client.HTTPSConnection("api.telegram.org", 443, timeout=30)
        headers = { "Content-type": "application/json" }
        data = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': mode
        }

        if reply_to:
            data['reply_to_message_id'] = reply_to

        conn.request("POST", "/bot{0}/sendMessage".format(self.token), json.dumps(data), headers)

        rq = conn.getresponse()

        response = rq.read()
        conn.close()

        data = json.loads(response)

        if not data['ok']:
          self.log.warn("Send message data is not OK: {}".format(data))

        return data

    # Pass a file_id as String to send a file that exists on the Telegram servers (recommended), 
    # pass an HTTP URL as a String for Telegram to get a .webp file from the Internet.
    def sendSticker(self, chat_id, sticker_id, reply_to=None):
        conn = http.client.HTTPSConnection("api.telegram.org", 443, timeout=30)
        headers = { "Content-type": "application/json" }
        data = {
            'chat_id': chat_id,
            'sticker': sticker_id         
        }

        if reply_to:
            data['reply_to_message_id'] = reply_to

        conn.request("POST", "/bot{0}/sendSticker".format(self.token), json.dumps(data), headers)

        rq = conn.getresponse()

        response = rq.read()
        conn.close()

        data = json.loads(response)

        if not data['ok']:
          self.log.warn("Send message data is not OK: {}".format(data))

        return data

    def getFile(self, file_id):
        conn = http.client.HTTPSConnection("api.telegram.org", 443, timeout=30)
        conn.request("GET", "/bot{0}/getFile?file_id={1}".format(self.token, file_id))
        rq = conn.getresponse()
        return json.loads(rq.read())

    def addHandlers(self, handlers):
        self.handlers += handlers

    def addHandler(self, matcher, handler):
        self.handlers.append(Handler(matcher, handler))

    def recentDate(self, date):
        return (time.time() - date) < 120 # 120 seconds

    def processMessage(self, msg):
        for h in self.handlers:
            if h.matcher(msg):
                self.log.debug("Found handler for {}".format(msg.text))
                h.handler(msg)
                return True

        self.log.info("No handler for message: {}".format(msg.text))

        return False

    def poll(self, offset=0, sleepTime=5, timeout=680, allowed_users=[]):
        while True:
            try:
                updates = self.getUpdates(offset, timeout)            

                for update in updates['result']:
                    offset = update['update_id'] + 1
                    
                    self.log.debug("Update: {}".format(update))

                    message = Message(self, update['message'])
                    
                    if message.from_username in allowed_users:
                        if self.recentDate(message.date):
                            self.processMessage(message)
                        else:
                            self.log.debug("Old message: {}".format((time.time() - message.date)))
                    else:
                        self.log.debug("User: {} is not allowed, with message: {}".format(message.from_username, message.text))
                        self.sendMessage(self.token, message.chat_id, "Who are you?")        
                sleep(sleepTime)
            except:
                self.log.warn("Error: {}".format(sys.exc_info()[0]))
                pass

def exec(cmd):
    proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    output = "{}".format(proc.stdout.read())[:-1]
    return "```bash\n{}\n```".format(output).replace("\\n", "\n")

def display(msg):
    text = msg.text[len("/display "):]
    exec("oled-exp -i write \"{}\"".format(text))
    msg.respond("Message written!")

def clearDisplay(msg):
    exec("oled-exp power off")
    msg.respond("Display turned off!")

def transmissionHandler(dir):
    handlers = []

    def handleTorrentFile(m):
        torrent = "{}/{}".format(dir, m.document.file_name)
        m.document.download(torrent) # store file
        exec("/etc/init.d/transmission start")
        m.respond(exec("transmission-remote -n 'transmission:transmission' -a '{}'".format(torrent)))
        
    handlers.append(Handler(
        lambda m: m.document != None and m.document.file_name.endswith(".torrent"),
        lambda m: handleTorrentFile(m)
    ))
    
    handlers.append(Handler(
        lambda m: m.text == "/torrent stop", 
        lambda m: m.respond(exec("transmission-remote -n 'transmission:transmission' -S && /etc/init.d/transmission stop"))
    ))

    handlers.append(Handler(
        lambda m: m.text == "/torrent start", 
        lambda m: m.respond(exec("/etc/init.d/transmission start && transmission-remote -n 'transmission:transmission' -s"))
    ))

    handlers.append(Handler(
        lambda m: m.text == "/torrent list", 
        lambda m: m.respond(exec("transmission-remote -n 'transmission:transmission' -l"))
    ))

    handlers.append(Handler(
        lambda m: m.text == "/torrent remove", 
        lambda m: m.respond(exec("transmission-remote --torrent 1 --remove"))
    ))

    return handlers

def handleUpload(msg):
    doc = msg.document
    dst = doc.caption if doc.caption else '~/{0}'.format(doc.file_name)
    res = doc.download(dst)
    if res:
        msg.respond("File uploaded to `{0}`".format(dst))
    else:
        msg.respond("Failed to upload file!")

if __name__ == "__main__":
    log = logging.getLogger(__name__)
    log.setLevel(logging.DEBUG)
    fh = logging.FileHandler('/root/bot.log')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    log.addHandler(fh)
    
    #handler = logging.handlers.SysLogHandler(address = '/dev/log')
    #handler.setFormatter(logging.Formatter('%(module)s.%(funcName)s: %(message)s'))
    #log.addHandler(handler)

    log.info('Starting Telegram Bot')
    # File format: { "token": "bot:token", "allowed_users": [123] }
    with open('/root/.config/telegram_bot', 'r') as f:
        config = json.load(f)

    token = config['token']
    users = config['allowed_users']
    
    bot = TelegramBot(token, log)    
    
    bot.addHandler(lambda m: m.text == "/help",
                   lambda m: m.respond("Supported commands: help, display, torrent"))

    bot.addHandler(lambda m: m.text == "/ping",
                   lambda m: m.respond("pong"))

    # Turn display off
    bot.addHandler(lambda m: m.text == "/display off",
                   lambda m: clearDisplay(m))

    # Display text 
    bot.addHandler(lambda m: m.text and m.text.startswith("/display"),
                   lambda m: display(m))

    bot.addHandlers(transmissionHandler("/root/Downloads/torrents"))

    # Call exec on any other text command
    bot.addHandler(lambda m: m.document != None, 
                   lambda m: handleUpload(m))

    # Call exec on any other text command
    bot.addHandler(lambda m: m.text != None, lambda m: m.respond(exec(m.text)))

    bot.poll(allowed_users = users)
