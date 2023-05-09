from telethon.sync import TelegramClient
from telethon.sessions import StringSession

api_id = int(input("Enter API KEY: "))
api_hash = input("Enter API HASH: ")
# Generating a new one
with TelegramClient('./bill_cipher_telethon_one.session', api_id, api_hash) as client:
    print(client.session.save())
