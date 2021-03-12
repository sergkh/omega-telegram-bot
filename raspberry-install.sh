#!/bin/bash

# Installs and configures the telegram bot on a Raspberry PI
# Requires python3 to be run

INSTALL_DIR='/usr/local/telegram'
SYSTEMD_SERVICE='/etc/systemd/system/bot.service'

is_user_root () { [ "${EUID:-$(id -u)}" -eq 0 ]; }

if ! is_user_root; then
    echo 'Run script as sudo.' >&2
    exit 1
fi

# Telegram Bot installation 
mkdir "$INSTALL_DIR"
cd "$INSTALL_DIR" 
wget https://raw.githubusercontent.com/sergkh/omega-telegram-bot/master/bot.py

## Replace some config locations in the script itself

# Change the log file location to /var/log/telegram_bot.log
sed 's/\/root\/bot.log/\/var\/log\/telegram_bot.log/g' "$INSTALL_DIR"/bot.py > "$INSTALL_DIR"/temp.py

# Change the config file location to /etc/telegram_bot.conf
sed 's/\/root\/.config\/telegram_bot/\/etc\/telegram_bot.conf/g' "$INSTALL_DIR"/temp.py > "$INSTALL_DIR"/temp2.py

read -p "Run the bot under the username [pi]: " username
username=${username:-pi}

# Change the config file location to /etc/telegram_bot.conf
sed "s/\/root\/Downloads\/torrents/\/home\/$username\/Downloads\/torrents/g" "$INSTALL_DIR"/temp2.py > "$INSTALL_DIR"/bot.py

rm "$INSTALL_DIR"/temp.py
rm "$INSTALL_DIR"/temp2.py

# Create a system.d service
# sudo tee -a "$SYSTEMD_SERVICE" > /dev/null <<EOT
# Description=Telegram Bot
# Wants=network-online.target
# After=syslog.target network-online.target

# [Service]
# Type=simple
# User=$username
# ExecStart=/usr/bin/python3 $INSTALL_DIR/bot.py
# Restart=always

# [Install]
# WantedBy=multi-user.target
# EOT

# Update bot configuration
echo "Enter telegram bot token. To get a new one use the link: https://t.me/BotFather";
read bot_token;

echo "Specify a telegram user name allowed to talk to a bot (as bot becomes public):";
read allowed_user;

echo "{ \"token\": \"$bot_token\", \"allowed_users\": [\"$allowed_user\"] }" > /etc/telegram_bot.conf

touch /var/log/telegram_bot.log && sudo chown "$username":"$username" /var/log/telegram_bot.log