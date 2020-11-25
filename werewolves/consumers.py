import json
import random
from werewolves.models import Player, PlayerRole, GameStatus, Message
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async


class ChatConsumer(AsyncWebsocketConsumer):
    # TODO: Know when
    async def connect(self):
        self.general_group = "general_group"    # all players are in this group
        self.wolves_group = "wolves_group"      # all wolves are in this group
        self.seer_group = "seer_group"          # seer is in this group
        self.guard_group = "guard_group"        # guard is in this group

        # num_players = await database_sync_to_async(self.check_num_players)()
        # if num_players < 6:
        await self.channel_layer.group_add(
            self.general_group,
            self.channel_name
        )

        # Put all players in the general group
        await self.channel_layer.group_add(
            self.general_group,
            self.channel_name
        )
        # TODO: should be put after assigned players role, here for testing
        await self.channel_layer.group_add(
            self.seer_group,
            self.channel_name
        )
        # TODO: should be put after assigned players role, here for testing
        await self.channel_layer.group_add(
            self.wolves_group,
            self.channel_name
        )
        # TODO: should be put after assigned players role, here for testing
        await self.channel_layer.group_add(
            self.guard_group,
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
        # Leave room group
        await self.channel_layer.group_discard(
            # self.room_group_name,
            self.general_group,
            self.channel_name
        )

        # await database_sync_to_async(self.clear_players)()

        self.close()

    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_type = text_data_json['type']
        #print("in receive")
        if message_type == 'join-message':
            await self.receiveJoinMessage()
        elif message_type == 'start-game-message':
            await self.receiveStartGameMessage()
        elif message_type == 'system-message':
            await self.receiveSystemMessage(text_data_json)
        elif message_type == 'chat-message':
            await self.receiveChatMessage(text_data_json)
        elif message_type == 'select-message':
            await  self.receiveSelectMessage(text_data_json)
        elif message_type == 'confirm-message':
            await  self.receiveConfirmMessage(text_data_json)
        elif message_type == 'exit-game-message':
            await  self.receiveExitGameMessage()

    """moduralized received messaages"""
    # join message
    async def receiveJoinMessage(self):
        print()
        # When we receive a request, create a new player in the database
        await database_sync_to_async(self.create_player)()

        # TODO: should be put after assigned players role, here for testing
        await database_sync_to_async(self.init_game_status)()

        # Get the current number of players in the database
        num_players = await database_sync_to_async(self.get_num_players)()
        # TODO: Change later to <= 6
        if num_players > 0:
            await self.channel_layer.group_send(
                # self.room_group_name,
                self.general_group,
                {
                    'type': 'players_message',
                    'message': num_players
                }
            )

    # start game message
    async def receiveStartGameMessage(self):
         await database_sync_to_async(self.assign_roles)()
         await self.channel_layer.group_send(
             # self.room_group_name,
             self.general_group,
             {
                 'type': 'start_game_message',
                 'message': 'start_game'
             }
         )

    #system message
    async def receiveSystemMessage(self, data):
        update = data['update']
        if update == 'update':
            target_id = data['target_id']
            await database_sync_to_async(self.update_status)(target_id=target_id)
        elif update == 'next_step':
            await database_sync_to_async(self.next_step)()
        # Send system message to different groups
        await self.channel_layer.group_send(
            self.general_group,
            {
                'type': 'system_message',
                'group': 'general',
            }
        )
        await self.channel_layer.group_send(
            self.seer_group,
            {
                'type': 'system_message',
                'group': 'seer',
            }
        )
        await self.channel_layer.group_send(
            self.wolves_group,
            {
                'type': 'system_message',
                'group': 'wolves',
            }
        )
        await self.channel_layer.group_send(
            self.guard_group,
            {
                'type': 'system_message',
                'group': 'guard',
            }
        )

    #chat message
    async def receiveChatMessage(self, data):
        message = data['message']
        await database_sync_to_async(self.create_message)(message)
        id, username, role = await database_sync_to_async(self.get_last_message)()
        # check what is the game status and the message sender role to decide which group to send
        status = await database_sync_to_async(self.get_game_status)()
        # if werewolves are killing people, the messages that they send should be seen among themselves
        if status.step == role:
            await self.channel_layer.group_send(
                # self.room_group_name,
                self.wolves_group,
                {
                    'type': 'chat_message',
                    'message': message,
                    'id': id,
                    'username': username,
                }
            )
        # Send message to room group
        # Send all messages in the data base to the room group
        else:
            await self.channel_layer.group_send(
                # self.room_group_name,
                self.general_group,
                {
                    'type': 'chat_message',
                    'message': message,
                    'id': id,
                    'username': username,
                }
            )

    #select target message
    async def receiveSelectMessage(self, data):
        target_id = data['id']
        await self.channel_layer.group_send(
            # self.room_group_name,
            self.general_group,
            {
                'type': 'select_message',
                'target_id': target_id,
            }
        )

    # confirm target message
    async def receiveConfirmMessage(self, data):
        target_id = data['target']
        await database_sync_to_async(self.update_status)(target_id=target_id)
        await database_sync_to_async(self.next_step)()
        # TODO send different system message to tell different players who is selected
        await self.channel_layer.group_send(
            # self.room_group_name,
            self.general_group,
            {
                'type': 'confirm_message',
                'target_id': target_id,
            }
        )

    # exit game message
    async def receiveExitGameMessage(self):
            await database_sync_to_async(self.delete_current_player)()
            await self.channel_layer.group_send(
                self.general_group,
                {
                    'type': 'exit_game_message',
                    'message': 'exit_game'
                }
            )

    '''join waiting room feature'''
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

    async def start_game_message(self, event):
        await self.send(text_data=json.dumps({
            'message-type': 'start_game_message',
        }))


    '''chat message feature'''
    # Receive message from room group
    async def chat_message(self, event):
        type = event['type']
        message = event['message']
        username = event['username']
        id = event['id']
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message-type': type,
            'username': username,
            'message': message,
            'id': id
        }))

    # TODO: Let player name be the one who just logged in

    def create_message(self, message):
        message_sender = self.scope["user"]
        message_text = message
        new_message = Message(message_sender= message_sender,  message_text= message_text)
        new_message.save()

    def get_last_message(self):
        messageObject = Message.objects.last()
        id = messageObject.id
        sender = messageObject.message_sender
        username = sender.username
        print("sender: " + username)
        player = Player.objects.get(user=sender)
        role = player.role
        print("role: " + role)
        return (id, username, role)

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


    '''start game feature'''

    # TODO: Change broadcast audience to the first six players
    async def start_game_message(self, event):
        await self.send(text_data=json.dumps({
            'message-type': 'start_game_message'
        }))

    def create_player(self):
        user = self.scope["user"]
        player = Player.objects.filter(user=user)
        if len(player) == 0:
            new_player = Player(user=user)
            new_player.save()

    def assign_roles(self):
        print("in assign roles")
        arr = [0, 1, 2, 3, 4, 5]
        random.shuffle(arr)
        all_players = Player.objects.all()
        print(f'all_players {all_players}')
        # TODO: Change later to len(arr)
        for i in range(len(all_players)):
            if arr[i] == 0 or arr[i] == 1:
                all_players[i].role = "VILLAGER"
            elif arr[i] == 2 or arr[i] == 3:
                all_players[i].role = "WOLF"
            elif arr[i] == 4:
                all_players[i].role = "SEER"
            elif arr[i] == 5:
                all_players[i].role = "GUARD"
            all_players[i].save()

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

    def delete_current_player(self):
        current_user   = self.scope["user"]
        current_player = Player.objects.filter(user=current_user)[0]
        current_player.delete()

    def clear_players(self):
        Player.objects.all().delete()

    # Used to initialize game_status
    def init_game_status(self):
        game = GameStatus()
        game.night = False
        game.wolves_target = None
        game.guard_target = None
        game.seer_target = None
        game.vote_target = None
        game.first_speaker = None
        game.current_speaker = None
        game.step = "NOT ASSIGNED"
        game.winning = None
        game.speech_over = None
        game.vote_over = None
        game.wolves = None
        # TODO: should be set from Player.objects, only for testing
        game.guard = None
        game.seer = None
        game.villagers = None
        #game.wolves = Player.objects.filter(role = "WOLF")
        #game.guard = Player.objects.filter(role = "GUARD")
        #game.seer = Player.objects.filter(role = "SEER")
        #game.villagers = Player.objects.filter(role = "VILLAGER")

        game.save()


    '''update game status feature'''
    # update target field in GameStatus
    def update_status(self, target_id):
        print(target_id)
        game = GameStatus.objects.last()
        new_status = GameStatus()
        new_status = game
        if (game.step == "WOLF"):
            if (game.wolves != None):
                new_status.wolves_target = target_id
            else:
                new_status.wolves_target = None
        elif (game.step == "GUARD"):
            if (game.guard != None):
                new_status.guard_target = target_id
            else:
                new_status.guard_target = None
        elif (game.step == "SEER"):
            if (game.seer != None):
                new_status.seer_target = target_id
            else:
                new_status.seer_target = None
        elif (game.step == "ANNOUNCE"):
            if (game.wolves_target != None):
                if (game.guard_target != game.wolves_target):
                    player = Player.objects.select_for_update(
                        id=game.wolves_target)
                    player.status = "OUT"
                    player.save()
                else:
                    new_status.wolves_target = None
        elif (game.step == "SPEECH"):
            if (game.speech_over == None):
                if (game.first_speaker == None):
                    new_status.first_speaker = self.next_speaker(game.wolves_target)
                    new_status.current_speaker = new_status.first_speaker
            elif (~game.speech_over):
                new_status.current_speaker = self.next_speaker(
                    game.current_speaker)
            #if (game.first_speaker == None):
            #    new_status.first_speaker = self.next_speaker(game.wolves_target)
            #if (game.current_speaker == None):
            #   new_status.current_speaker = new_status.first_speaker
            #else:
            #    new_status.current_speaker = self.next_speaker(game.current_speaker)
        elif (game.step == "VOTE"):
            if (game.vote_target != None):
                player = Player.objects.select_for_update(id=game.vote_target)
                player.status = "OUT"
                player.save()
        # else:
            # TODO: update default status

        new_status.save()


    #   Update next step
    def next_step(self):
        game = GameStatus.objects.last()
        new_status = GameStatus()
        new_status = game
        if (game.step == "WOLF"):
            new_status.step = "GUARD"
            new_status.night = False
        elif (game.step == "GUARD"):
            new_status.step = "SEER"
            new_status.night = False
        elif (game.step == "SEER"):
            new_status.step = "ANNOUNCE"
            new_status.night = True
        elif (game.step == "ANNOUNCE"):
            new_status.winning = self.is_end_game()
            if (new_status.winning == None):
                new_status.step = "SPEECH"
                new_status.night = True
            else:
                new_status.step = "END_GAME"
        elif (game.step == "SPEECH"):
            new_status.speech_over = self.is_end_speech()
            if (new_status.speech_over):
                new_status.step = "END_SPEECH"
                new_status.night = True
        elif (game.step == "END_SPEECH"):
            new_status.step = "VOTE"
            new_status.night = True
        elif (game.step == "VOTE"):
            new_status.vote_over = self.is_end_vote()
            if (new_status.vote_over):
                new_status.step = "END_VOTE"
                new_status.night = True
        elif (game.step == "END_VOTE"):
            new_status.step = "WOLF"
            new_status.night = False
        elif (game.step == "NOT ASSIGNED"):
            new_status.step = "WOLF"
            new_status.night = False

        new_status.save()


    ''' system message feature'''
    #   send system_message based on groups and steps
    #   groups include:
    #       general group,
    #       wolves group,
    #       guard group,
    #       seer group,
    #
    async def system_message(self, event):
        game = await database_sync_to_async(self.get_game_status)()
        message = ""
        group = event["group"]
        if (group == "general"):
            if (game.step == "WOLF"):
                message = "Wolf is choosing a player to kill."
            elif (game.step == "GUARD"):
                message = "Guard is choosing a player to protect."
            elif (game.step == "SEER"):
                message = "Seer is checking a player's identity."
            elif (game.step == "ANNOUNCE"):
                if (game.winning == None):
                    if (game.wolves_target == None):
                        message = "Last night, nobody gets killed."
                    else:
                        target = Player.objects.get(id=game.wolves_target)
                        message = "Last night, " + target.user + " gets killed."
                else:
                    general_message = "Game Over."
            elif (game.step == "SPEECH"):
                message = "Now each player needs to make a speech."
            elif (game.step == "VOTE"):
                message = "Now each player needs to make a vote."
            elif (game.step == "END_VOTE"):
                if (game.vote_target != None):
                    target = Player.objects.get(id=game.vote_target)
                    message = target.user + " is voted out."
                    if (target.role == "WOLF"):
                        message += " This player is a wolf."
                    else:
                        message += " This player is not a wolf."
                else:
                    message = "Nobody gets voted out."
            elif (game.step == "END_GAME"):
                message = "Game Over."
        elif (group == "wolves"):
            if (game.wolves_target != None):
                wolves_target = await sync_to_async(Player.objects.get, thread_sensitive=True)(id=game.wolves_target)
                message = "You chose to kill " + wolves_target.user.username
        elif (group == "guard"):
            if (game.guard_target != None):
                guard_target = await sync_to_async(Player.objects.get, thread_sensitive=True)(id=game.guard_target)
                message = "You chose to protect " + guard_target.user.username
        elif (group == "seer"):
            if (game.seer_target != None):
                seer_target = await sync_to_async(Player.objects.get, thread_sensitive=True)(id=game.seer_target)
                if (seer_target.role == "WOLF"):
                    message = "This player is bad."
                else:
                    message = "This player is good."

        await self.send(text_data=json.dumps({
            'message-type': 'system_message',
            'message': message,
        }))

    #  get the next alive speaker.
    # TODO: the first player killed at night should also be counted. debug needed
    # param(in): id: the current speaker, need to find the next one
    # return(out): a plaer model, next availbe speaker
    #
    def next_speaker(self, id):
        alive_players = Player.objects.filter(status="ALIVE")
        # if no dead player from the night, select the oldest alive player joined the room
        if (id == None):
            return alive_players.first()
        else:
            for player in alive_players:
                if (player.id > id):
                    return player

    #
    #   Used to check the end game condition.
    #   TODO: debug needed
    #   return(out):
    #       None: the game is not endpoints
    #       True: good people win
    #       False: wolves win
    #
    def is_end_game(self):
        #TODO: only for testing
        return None
        game = GameStatus.objects.last()
        wolf_alive = 0
        good_alive = 0
        for player in Player.objects.filter(status="ALIVE"):
            if (player.role == "WOLF"):
                wolf_alive += 1
            else:
                good_alive += 1
        if (wolf_alive == 0):
            return True
        elif (good_alive == 0):
            return False
        else:
            return None

    #
    #   Used to check the end game condition.
    #   TODO: debug needed
    #   return(out):
    #       None: speech is not started
    #       True: speech is over
    #       False: speech is started but not over
    #
    def is_end_speech(self):
        #TODO: only for testing
        return True
        game = GameStatus.objects.last()
        if (~game.speech_over):
            if (game.current_speaker == game.first_speaker):
                return True
        elif (game.speech_over == None):
            if (game.current_speaker != None):
                return False
        else:
            return None

    #
    #   Used to check the voting condition.
    #   TODO: debug needed
    #   return(out):
    #       None: voting is not started
    #       True: voting is over
    #       False: voting is started but not over
    #
    def is_end_vote(self):
        #TODO: only for testing
        return True
        #TODO: need to implement vote checking function

    #Used to get the most recent game status
    def get_game_status(self):
        return GameStatus.objects.last()

    # Used to get the current player's role
    def get_current_player_role(self):
        role = Player.objects.get(user=self.scope['user']).role
        return role


    async def select_message(self, event):
        status = await database_sync_to_async(self.get_game_status)()
        status = status.step
        role = await database_sync_to_async(self.get_current_player_role)()
        target_id = event['target_id']
        await self.send(text_data=json.dumps({
            'message-type': 'select_message',
            'role': role,
            'status':status,
            'target_id': target_id,
        }))

    async def confirm_message(self, event):
        id = event['target_id']
        await self.send(text_data=json.dumps({
            'message-type': 'confirm_message',
            'target_id': id
        }))

    '''exit game feature'''

    async def exit_game_message(self, event):
        print('exiting game')
        await self.send(text_data=json.dumps({
            'message-type': 'exit_game_message'
        }))

