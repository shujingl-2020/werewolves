import json
from werewolves.models import Player
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        ### the default game room ###
        self.room_group_name = 'room_1'

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        # Check whether a user is logged in
        if self.scope["user"].is_anonymous:
            # Reject the connection
            await self.close()
        else:
            # Accept the connection
            await self.accept()

    async def disconnect(self, close_code):
        # Clear players before we disconnect
        await database_sync_to_async(self.clear_players)()
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

        self.close()

    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_type = text_data_json['type']
        if message_type == 'join-message':
            # When we receive a request, create a new player in the database
            await database_sync_to_async(self.create_player)()
            # Get the current number of players in the database
            num_players = await database_sync_to_async(self.get_num_players)()
            # TODO: Change later to <= 6
            if num_players > 0:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'players_message',
                        'message': num_players
                    }
                )
        elif message_type == 'chat-message':
            message = text_data_json['message']
            # Send message to room group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message,
                }
            )

    # Receive message from room group
    async def chat_message(self, event):
        message = event['message']
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message-type': 'chat_message',
            'username': self.scope["user"].username,
            'message': message
        }))
    
    # TODO: Let player name be the one who just logged in
    async def players_message(self, event):
        message = event['message']
        # Get an array of all players
        all_players = await database_sync_to_async(self.get_all_players)()
        last_player = await database_sync_to_async(self.get_last_joined_player)()
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message-type': 'players_message',
            'last_player': last_player,
            'players': all_players,
            'message': message
        }))
    
    def create_player(self):
        user = self.scope["user"]
        player = Player.objects.filter(user=user)
        if (len(player) == 0):
            new_player = Player(user=user)
            new_player.save()

    def get_num_players(self):
        return Player.objects.all().count()
    
    def get_all_players(self):
        players = Player.objects.all()
        ret = []
        for player in players:
            ret.append(player.user.username)
        return ret
    
    def get_last_joined_player(self):
        last_player = Player.objects.order_by('-id')[0]
        return last_player.user.username
        
    def clear_players(self):
        Player.objects.all().delete()