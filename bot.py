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
import random
import os
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
            self.log.warning("Send message data is not OK: {}, {}".format(data, rq.status))

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
                    
                    if allowed_users == None or message.from_username in allowed_users:
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

def addQuestion(chats, m):
    chats[m.chat_id] = m.text[4:].strip()
    print("Adding '{0}'".format(chats[m.chat_id]))
    m.respond("Answer is:")

def addAnswer(log, answers, chat_file, chats, m):
    question = chats[m.chat_id]
    
    if m.text != None:
        log.info("Adding text {0}".format(m.text))
        answers.append({ "q" : question, "txt" : m.text })
    else:
        log.info("Adding sticker {0}".format(m.sticker['file_id']))
        answers.append({ "q" : question, "sk" : m.sticker['file_id'] })        

    del chats[m.chat_id]

    m.respond("Noted")

    with open('chat', 'w') as f: # /root/.config/chat
        json.dump(answers, f)

def findAnswer(answers, msg):
    matches = [a for a in answers if a['q'] in msg.text]
    if matches:
        resp = random.choice(matches)
        if 'txt' in resp:
            msg.respond(resp['txt'])
        else:
            msg.respondSticker(resp['sk'])
    else:
        msg.respond("What?")

def exec(cmd):
    proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    output = "{}".format(proc.stdout.read())[:-1]
    return "```bash\n{}\n```".format(output).replace("\\n", "\n")

def transmissionHandler(dir):
    handlers = []

    def handleTorrentFile(m):
        torrent = "{}/{}".format(dir, m.document.file_name)
        m.document.download(torrent) # store file
        result = exec("transmission-remote -n 'transmission:transmission' -a '{}'".format(torrent))
        success = result.find("success") != -1
        m.respond("Added" if success else result)
        
    handlers.append(Handler(
        lambda m: m.document != None and m.document.file_name.endswith(".torrent"),
        lambda m: handleTorrentFile(m)
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
        
    answers = []
    adding_words_chats = {}

    chat_file = 'chat' # /root/.config/chat

    if os.path.isfile(chat_file):
        with open(chat_file, 'r') as f: 
            answers = json.load(f)

    log.info('Starting Telegram Bot')
    
    # File format: { "token": "bot:token", "allowed_users": [123] }
    with open('/root/.config/telegram_bot', 'r') as f:
        config = json.load(f)

    token = config['token']
    users = config['allowed_users']
    
    bot = TelegramBot(token, log)
    
    bot.addHandler(lambda m: m.text != None and m.text.startswith("/add"), lambda m: addQuestion(adding_words_chats, m))

    bot.addHandler(lambda m: m.text == "/ping",
                   lambda m: m.respond("pong"))

    bot.addHandlers(transmissionHandler("/root/Downloads/torrents"))

    bot.addHandler(lambda m: m.chat_id in adding_words_chats, lambda m: addAnswer(log, answers, chat_file, adding_words_chats, m))

    bot.addHandler(lambda m: m.text != None, lambda m: findAnswer(answers, m))

    # Call exec on any other text command
    # bot.addHandler(lambda m: m.document != None,
    #               lambda m: handleUpload(m))

    # Call exec on any other text command
    # bot.addHandler(lambda m: m.text != None, lambda m: m.respond(exec(m.text)))

    bot.poll(allowed_users = users)
