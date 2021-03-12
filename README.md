# omega-telegram-bot
Small and simple Telegram Bot for Omega2 written in Python 3. 

## Features

* Files upload and download
* Can be used without a SD card
* Accepts messages only from allowed users list
* Allows to execute bash commands
* Displays messages on Omega's display
* Torrents management (using transmission client)
* Easy to add user commands

## Installation on Raspberry Pi
1. Register a bot using [@BotFather](http://t.me/botfather).
2. Run a script

```bash
curl -o- -L https://raw.githubusercontent.com/sergkh/omega-telegram-bot/master/raspberry-install.py | sudo bash
```

## Installation on Omega2

1. Register a bot using [@BotFather](http://t.me/botfather).
2. Install Python3 and necessary modules:
```bash
# opkg update
# opkg install python3 python3-base python3-codecs python3-logging python3-openssl
```
3. Copy [bot.py](https://raw.githubusercontent.com/sergkh/omega-telegram-bot/master/bot.py) into Omega's root folder: 

```bash 
# cd ~ && wget https://raw.githubusercontent.com/sergkh/omega-telegram-bot/master/bot.py
```
4. Create a configuration file: `/root/.config/telegram_bot`:

```bash
# mkdir /root/.config/ && vi /root/.config/telegram_bot
```

with the following contents:

```json
{ "token": "bot_token", "allowed_users": ["your_username"] }
```

5. Copy [init.d script](init.d/bot) into your init.d folder:

```bash
# cd /etc/init.d/ && wget https://raw.githubusercontent.com/sergkh/omega-telegram-bot/master/init.d/bot
```

6. Enable a service autostart and run it:

```bash
# chmod +x /etc/init.d/bot
# /etc/init.d/bot enable 
# /etc/init.d/bot start
```
