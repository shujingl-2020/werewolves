import json
import random


j = "{\"roleConfig\":{\"seer\":{\"num\":3,\"order\":1},\"werewolf\":{\"num\":2,\"order\":0}},\"gameMode\":\"Tubian\"}"
j= json.loads(j)
config=j['roleConfig']

for role in config:
    for a in range(config[role]['num']):
        print (role + " ")