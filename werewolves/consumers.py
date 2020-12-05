import json
import random
from werewolves.models import Player, PlayerRole, GameStatus, Message
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.general_group = "general_group"  # all players are in this group
        self.wolves_group = "wolves_group"  # all wolves are in this group
        user = self.scope["user"]

        await self.channel_layer.group_add(
            self.general_group,
            self.channel_name
        )

        #add wolf player into a special group
        role = await database_sync_to_async(self.get_current_player_role)()
        if (role == "WOLF"):
            await self.channel_layer.group_add(
                self.wolves_group,
                self.channel_name
            )

        #initalize game status
        #print the first system message when all players are in the game room
        if (role != "NONE" and role != None):
            # initialize game status
            await database_sync_to_async(self.init_game_status)()
            #first system message
            count = await database_sync_to_async(self.game_objects_count)()           
            if (count >= 6):
                await self.channel_layer.group_send(
                    self.general_group,
                    {
                        'type': 'system_message',
                        'group': 'general',
                        'sender_id': 0,
                    }
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

        self.close()

    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_type = text_data_json['type']

        # join message
        if message_type == 'join-message':
            await database_sync_to_async(self.create_player)()
            # Get the current number of players in the database
            num_players = await database_sync_to_async(self.get_num_players)()
            # TODO: Change later to <= 6
            if num_players > 0:
                await self.channel_layer.group_send(
                    self.general_group,
                    {
                        'type': 'players_message',
                        'message': num_players
                    }
                )

        # start game message
        elif message_type == 'start-game-message':
            # assign roles and id in game for players
            await database_sync_to_async(self.assign_roles_and_ids)()
            await self.channel_layer.group_send(
                self.general_group,
                {
                    'type': 'start_game_message',
                    'message': 'start_game'
                }
            )

        # system message
        elif message_type == 'system-message':
            update = text_data_json['update']
            sender_id = text_data_json['sender_id']
            #handle selected player id 
            if update == 'update':
                target_id = text_data_json['target_id']
                await database_sync_to_async(self.update_status)(target_id=target_id, times_up=False)
            #update step
            elif update == 'next_step':
                await database_sync_to_async(self.next_step)(times_up=False)

            #send system messages to general groups
            await self.channel_layer.group_send(
                self.general_group,
                {
                    'type': 'system_message',
                    'group': 'general',
                    'sender_id': sender_id,
                }
            )
            #If a round of game is ended, clean all players selected infomation.
            game = await database_sync_to_async(self.get_game_status)()
            if (game.step == "END_DAY"):
                await database_sync_to_async(self.clean_action)()

        # chat message
        elif message_type == 'chat-message':
            message = text_data_json['message']
            await database_sync_to_async(self.create_message)(message)
            id, username, role = await database_sync_to_async(self.get_last_message)()
            # check what is the game status and the message sender role to decide which group to send
            status = await database_sync_to_async(self.get_game_status)()
            # if werewolves are killing people, the messages that they send should be seen among themselves
            if status.step == 'WOLF' and role == 'WOLF':
                await self.channel_layer.group_send(
                    self.wolves_group,
                    {
                        'type': 'chat_message',
                        'message': message,
                        'id': id,
                        'username': username,
                    }
                )
            # Send message to room group
            else:
                await self.channel_layer.group_send(
                    self.general_group,
                    {
                        'type': 'chat_message',
                        'message': message,
                        'id': id,
                        'username': username,
                    }
                )

        # exit game message
        elif message_type == 'exit-game-message':
            # Delete current player
            await database_sync_to_async(self.delete_current_player)()
            await self.channel_layer.group_send(
                self.general_group,
                {
                    'type': 'exit_game_message',
                    'message': 'exit_game'
                }
            )
        elif message_type == "end-game-message":
            await database_sync_to_async(self.clear_database)()

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

    # TODO: Change broadcast audience to the first six players
    async def start_game_message(self, event):
        # players = await database_sync_to_async(self.get_all_players)()
        # print(f'in start game message: current players{players}')
        await self.send(text_data=json.dumps({
            'message-type': 'start_game_message',
        }))

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

    #handle a player exit game in the waiting room
    async def exit_game_message(self, event):
        # Get number of players in the database
        count = await database_sync_to_async(self.get_num_players)()
        # If there are more than 1 player in the database, assign new host
        if count > 0:
            # Obtain the new host, which is the second player in the database
            all_players = await database_sync_to_async(self.get_all_players)()
            last_player = await database_sync_to_async(self.get_last_joined_player)()
            new_host = await database_sync_to_async(self.get_first_player_username)()
            # Send message only to the new host
            if self.scope['user'].username == new_host:
                await self.send(text_data=json.dumps({
                    'message-type': 'change_host_message',
                    'last_player': last_player,
                    'players': all_players,
                    'message': count
                }))
            else:
                await self.send(text_data=json.dumps({
                    'message-type': 'players_message',
                    'last_player': last_player,
                    'players': all_players,
                    'message': count
                }))

    #   send system_message based on game status
    async def system_message(self, event):
        game = await database_sync_to_async(self.get_game_status)()
        step = game.step
        all_players_vote = game.vote
        trigger_id = game.trigger_id

        group = event['group']
        sender_id = event['sender_id']

        current_player = await database_sync_to_async(self.get_current_player)()
        current_player_id = current_player.id_in_game
        current_player_role = current_player.role
        current_player_status = current_player.status

        speaker_id = None
        current_speaker_role = None
        out_player_id = None
        target_id = None
        seer_id = None
        guard_id = None
        wolf_id = None
        villager_id = None
        message = None

        if (step == "ANNOUNCE"):
            # ID of killed player at night; 0: means no one gets killed,
            out_player_id = game.wolves_select
        elif (step == "SPEECH"):
            speaker_id = game.speaker_id
            if (speaker_id != None):
                if (speaker_id > 0):
                    current_speaker_role = game.current_speaker_role
        elif (step == "VOTE"):
            # out_player_id: ID of voted out player
            # None: voting is not finished
            # 0: no one gets voted out
            target_id = current_player.vote
            out_player_id = game.vote_select
        elif (step == "END_VOTE"):
            # out_player_id: ID of voted out player
            # 0: no one gets voted out
            out_player_id = game.vote_select
        elif (step == "END_GAME"):
            # IDs for all players with different roles
            seer_id = game.seer
            guard_id = game.guard
            wolf_id = game.wolves
            villager_id = game.villagers
            message = game.winning
        elif (step == "WOLF"):
            # "True"/"False": representing if any wolf has made selection
            message = game.is_kill
            target_id = current_player.kill
            # out_player_id: ID of killing player
            # None: decision has not made yet
            # 0: choose to kill no one
            out_player_id = game.wolves_select
        elif (step == "GUARD"):
            # target_id: ID of protecting player
            # None: decision has not made yet
            # 0: choose to protect no one
            target_id = game.guard_select
        elif (step == "SEER"):
            # target_id: ID of player chose to see
            # None: decision has not made yet
            # 0: choose to see no one
            target_id = game.seer_select
            if (game.seer_select != None):
                if (game.seer_select > 0):
                    role = game.seer_target_role
                    if (role == "WOLF"):
                        message = "Bad"
                    else:
                        message = "Good"

        await self.send(text_data=json.dumps({
            'message-type': "system_message", #message type
            'group': group,             #current group
            'step': step,               #current step
            'out_player_id': out_player_id,                 #ID of out player in this step
            'current_player_id': current_player_id,         #ID of current player
            'current_player_role': current_player_role,     #role of current player
            'current_player_status': current_player_status, #status of current player
            'speaker_id': speaker_id,   #ID of current speaker
            'current_speaker_role': current_speaker_role,   #role of current speaker
            'target_id': target_id,     #ID of selected target for current player
            'trigger_id': trigger_id,   #ID of player for the next request
            'sender_id': sender_id,     #ID of request player
            'seer_id': seer_id,         #string of seer's ID
            'guard_id': guard_id,       #string of guard's ID
            'wolf_id': wolf_id,         #string of all wolves' IDs
            'villager_id': villager_id, #string of all villagers' IDs
            'all_players_vote': all_players_vote,  #a string contains voting result for all players
            'message': message,  # in step seer, good/bad person; in step wolf, if a wolf select a target
        }))


    # create a chat message
    def create_message(self, message):
        message_sender = self.scope["user"]
        message_text = message
        new_message = Message(message_sender=message_sender, message_text=message_text)
        new_message.save()

    # get the last piece of chat message
    def get_last_message(self):
        messageObject = Message.objects.last()
        id = messageObject.id
        sender = messageObject.message_sender
        username = sender.username
        player = Player.objects.get(user=sender)
        role = player.role
        return (id, username, role)

    #create a new player
    def create_player(self):
        user = self.scope["user"]
        player = Player.objects.filter(user=user)
        if len(player) == 0:
            new_player = Player(user=user)
            new_player.save()

    #assign roles and id_in_game for every player
    def assign_roles_and_ids(self):
        arr = [0, 1, 2, 3, 4, 5]
        random.shuffle(arr)
        all_players = Player.objects.all()
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
            all_players[i].id_in_game = i + 1
            all_players[i].save()

    # get number of player
    def get_num_players(self):
        return Player.objects.all().count()
    
    # get the name of the first player
    def get_first_player_username(self):
        return Player.objects.all()[0].user.username

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
        current_user = self.scope["user"]
        current_player = Player.objects.get(user=current_user)
        if current_player:
            current_player.delete()

    def clear_players(self):
        Player.objects.all().delete()

    def game_objects_count(self):
        return GameStatus.objects.count()

    # Used to initialize game_status
    def init_game_status(self):
        if (GameStatus.objects.count() > 6):
            game = GameStatus.objects.select_for_update().last()
        else:
            game = GameStatus()
        game.wolves_select = None
        game.guard_select = None
        game.guard_previous_id = None
        game.seer_select = None
        game.seer_target_role = None
        game.vote_select = None
        game.first_speaker_id = None
        game.speaker_id = None
        game.current_speaker_role = None
        game.step = "END_DAY"
        game.winning = None
        game.vote = "XXXXXX"
        game.is_kill = "False"
        game.trigger_id = self.get_trigger_id()
        game.wolves = self.get_player_id_string("WOLF")
        game.seer = self.get_player_id_string("SEER")
        game.guard = self.get_player_id_string("GUARD")
        game.villagers = self.get_player_id_string("VILLAGER")
        game.save()

        self.clean_action()

    '''update game status feature'''

    # update target field in GameStatus
    def update_status(self, target_id, times_up):
        game = GameStatus.objects.select_for_update().last()
        new_status = GameStatus()
        new_status = game
        user = self.scope["user"]

        if (game.step == "WOLF"):
            if (times_up):
                if (game.wolves_select == None):
                    new_status.wolves_select = 0
            else:
                try:
                    wolf_player = Player.objects.select_for_update().get(user=user)
                    if (wolf_player.role == "WOLF" and wolf_player.status == "ALIVE"):
                        if (target_id == None):
                            wolf_player.kill = 0
                        else:
                            wolf_player.kill = target_id
                    wolf_player.save()
                except:
                    print("Error in wolf step!")
                    pass

                new_status.wolves_select, new_status.is_kill = self.valid_kill_target()
        elif (game.step == "GUARD"):
            if (times_up):
                if (game.guard_select == None):
                    new_status.guard_select = 0
            else:
                # get the valid guarding target
                guard_id = self.valid_target(target_id)
                # check if protecting the same player in two consecutive round
                # if yes, id = None, the decision is not valid
                if (guard_id != game.guard_previous_id):
                    new_status.guard_select = guard_id
                else:
                    new_status.guard_select = None
        elif (game.step == "SEER"):
            if (times_up):
                if (game.seer_select == None):
                    new_status.seer_select = 0
            else:
                new_status.seer_select = self.valid_target(target_id)

            if (new_status.seer_select != None):
                if (new_status.seer_select > 0):
                    new_status.seer_target_role = Player.objects.get(
                        id_in_game=new_status.seer_select).role
        elif (game.step == "VOTE"):
            if (times_up):
                # if players didn't vote, treated as pass voting 
                if (game.vote_select == None):
                    players = Player.objects.select_for_update().filter(status="ALIVE")
                    for player in players:
                        if (player.vote == None):
                            player.vote = 0
            else:
                try:
                    player = Player.objects.select_for_update().get(user=user)
                    # pass voting
                    if (target_id == None):
                        player.vote = 0
                    else:
                        player.vote = target_id
                    player.save()
                except:
                    print("Error in vote step!")
                    pass

            # update final voted out player and voting condition
            new_status.vote_select, new_status.vote = self.voted_player()

        game = new_status
        # assign next playe to trigger next step
        game.trigger_id = self.get_trigger_id()
        game.save()


    # check the select target_id
    # if select None, return 0
    # if select is not valid, return None
    # if select is valid, return traget_id
    def valid_target(self, target_id):
        if (target_id == None):
            return 0
        elif (target_id == 0):
            return 0
        elif (target_id > 0):
            target_player = Player.objects.get(id_in_game=target_id)
            if (target_player.status != "ALIVE"):
                return None
            else:
                return target_id

    # update final kill target and is_kill string
    # if all wolves player select different target, return None
    # else return the valid target id
    def valid_kill_target(self):
        kill_string = "False"
        try:
            wolves = Player.objects.filter(role="WOLF")
            i = 0
            kill_target = None
            for wolf in wolves:
                if (wolf.status == "ALIVE"):
                    if (wolf.kill != None):
                        kill_string = "True"
                    if (i == 0):
                        kill_target = self.valid_target(wolf.kill)
                    else:
                        if (wolf.kill != None):
                            if (kill_target != wolf.kill):
                                return None, kill_string
                        else:
                            return None, kill_string
                    i += 1

            if (kill_target != None):
                return kill_target, kill_string
            return None, kill_string
        except:
            print("Error in valid_kill_target!")
            return None, kill_string

    # get the final voted out player and voting status
    # 
    def voted_player(self):
        game = GameStatus.objects.last()
        vote_string = game.vote
        vote_list = list(vote_string)
        vote_finished = True
        if (game.vote_select != None):
            return game.vote_select, game.vote

        try:
            vote_count = [0, 0, 0, 0, 0, 0]
            most_vote = 0
            most_vote_id = 0
            alive_players = Player.objects.filter(status="ALIVE")
            for player in alive_players:
                if (player.vote != None):
                    if (player.vote > 0):
                        vote_count[player.vote - 1] += 1
                    vote_list[player.id_in_game - 1] = str(player.vote)
                    vote_string = "".join(vote_list)
                elif (player.vote == None):
                    vote_finished = False

            # vote is not finished
            if (vote_finished == False):
                return None, vote_string
            # get max vote
            for i in range(0, len(vote_count)):
                #print("     i:", i, " vote:", vote_count[i])
                if (vote_count[i] > most_vote):
                    most_vote = vote_count[i]
                    most_vote_id = i
            # check if there are same votes
            for i in range(0, len(vote_count)):
                # if same vote, no one is voted out
                if (vote_count[i] == most_vote and i != most_vote_id):
                    return 0, vote_string
            # return the voted out player
            return most_vote_id + 1, vote_string
        except:
            print("Error in voted_player!")
            return None, vote_string

    #   Update next step
    def next_step(self, times_up):
        game = GameStatus.objects.select_for_update().last()
        new_status = GameStatus()
        new_status = game
        if (game.step == "WOLF"):
            if (game.wolves_select == None):
                new_status.step = "WOLF"
            else:
                new_status.step = "GUARD"
        elif (game.step == "GUARD"):
            if (game.guard_select == None):
                new_status.step = "GUARD"
            else:
                new_status.step = "SEER"
                new_status.guard_previous_id = game.guard_select
        elif (game.step == "SEER"):
            if (game.seer_select == None):
                new_status.step = "SEER"
            else:
                if (game.wolves_select != None):
                    if (game.wolves_select > 0):
                        if (game.guard_select != None):
                            if (game.guard_select > 0 and game.guard_select == game.wolves_select):
                                new_status.wolves_select = 0
                            else:
                                player = Player.objects.select_for_update().get(
                                    id_in_game=game.wolves_select)
                                player.status = "OUT"
                                player.save()
                        else:
                            player = Player.objects.select_for_update().get(
                                id_in_game=game.wolves_select)
                            player.status = "OUT"
                            player.save()

                new_status.step = "ANNOUNCE"

        elif (game.step == "ANNOUNCE"):

            new_status.winning = self.is_end_game()
            if (new_status.winning == None):
                new_status.step = "SPEECH"
            else:
                new_status.step = "END_GAME"
        elif (game.step == "SPEECH"):
            if (self.is_end_speech()):
                new_status.step = "VOTE"
            else:
                new_status.step = "SPEECH"
                if (game.first_speaker_id == None):
                    new_status.first_speaker_id = self.next_speaker(game.wolves_select)
                    new_status.speaker_id = new_status.first_speaker_id
                else:

                    new_status.speaker_id = self.next_speaker(game.speaker_id)

                if (new_status.speaker_id != None):
                    if (new_status.speaker_id > 0):
                        new_status.current_speaker_role = Player.objects.get(
                            id_in_game=new_status.speaker_id).role
                        player = Player.objects.select_for_update().get(id_in_game=new_status.speaker_id)
                        player.speech = True
                        player.save()


        elif (game.step == "VOTE"):
            if (game.vote_select == None):
                new_status.step = "VOTE"
            else:

                new_status.step = "END_VOTE"
                if (game.vote_select > 0):
                    player = Player.objects.select_for_update().get(id_in_game=game.vote_select)
                    player.status = "OUT"
                    player.save()



        elif (game.step == "END_VOTE"):


            new_status.winning = self.is_end_game()
            if (new_status.winning == None):
                new_status.step = "END_DAY"
            else:
                new_status.step = "END_GAME"
        elif (game.step == "END_DAY"):
            new_status.step = "WOLF"

        game = new_status
        game.trigger_id = self.get_trigger_id()
        game.save()

    ''' system message feature'''



    def get_trigger_id(self):
        players = Player.objects.all()
        for player in players:
            if (player.status == "ALIVE"):
                return player.id_in_game

        return None

    #  get the next alive speaker.
    # TODO: the first player killed at night should also be counted. debug needed
    # param(in): id: the current speaker, need to find the next one
    # return(out): a player model, next availbe speaker
    #
    def next_speaker(self, id):
        # print("in next_speaker")
        # print("     id:", id)
        alive_players = Player.objects.filter(status="ALIVE")
        # if no dead player from the night, select the oldest alive player joined the room
        if (id == None):
            return alive_players.first().id_in_game
        elif (id == 0):
            return alive_players.first().id_in_game
        else:
            speaker_id = (id+1) % 6
            if (speaker_id == 0):
                speaker_id = 6
            # print("     speaker id:", speaker_id)
            while (speaker_id != id):
                # print("     speaker id:", speaker_id)
                if (Player.objects.get(id_in_game=speaker_id).status == "ALIVE"):
                    return speaker_id
                else:
                    speaker_id = (speaker_id+1) % 6
                    if (speaker_id == 0):
                        speaker_id = 6
            return None

    def select_kill_id(self):
        # print("in select_kill_id")
        players = Player.objects.filter(role="WOLF")
        for player in players:
            if (player.status == "ALIVE"):
                # print("     player:", player.user, " kill:",player.kill)
                if player.kill != None:
                    return player.kill
        return None

    #
    #   Used to check the end game condition.
    #   TODO: debug needed
    #   return(out):
    #       None: the game is not endpoints
    #       True: good people win
    #       False: wolves win
    #
    def is_end_game(self):
        # TODO: only for testing
        #print("in is_end_game")
        game = GameStatus.objects.last()
        wolf_alive = 0
        god_alive = 0
        villager_alive = 0
        for player in Player.objects.filter(status="ALIVE"):
            #print("     id:", player.id_in_game, "role:", player.role)
            if (player.role == "WOLF"):
                wolf_alive += 1
            elif (player.role == "VILLAGER"):
                villager_alive += 1
            elif (player.role == "GUARD" or player.role == "SEER"):
                god_alive += 1
        if (wolf_alive == 0):
            return True
        elif (god_alive == 0):
            return False
        elif (villager_alive == 0):
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
        players = Player.objects.filter(status="ALIVE")
        for player in players:
            if (player.speech == False):
                return False

        return True

    def clear_database(self):
        #game = GameStatus.objects.last()
        if (GameStatus.objects.count() > 0):
        #if (game.step == "END_GAME"):
            print("clear_database, user:", self.scope['user'])
            GameStatus.objects.all().delete()
            Player.objects.all().delete()

    def clean_action(self):
        game = GameStatus.objects.select_for_update().last()
        #if (game.step == "END_DAY") :
        print("in clean_action")
        players = Player.objects.all()
        for player in players:
            player.vote = None
            player.kill = None
            player.speech = False
            player.save()
        game.wolves_select = None
        game.guard_select = None
        game.seer_select = None
        game.seer_target_role = None
        game.vote_select = None
        game.first_speaker_id = None
        game.speaker_id = None
        game.current_speaker_role = None
        game.vote = "XXXXXX"
        game.is_kill = "False"
        game.trigger_id = self.get_trigger_id()
        game.save()
        print("end in clean_action")

    def get_player_id_string(self, role):
        id_string = ""
        try:
            players = Player.objects.filter(role=role)
            for player in players:
                id_string += str(player.id_in_game)
        except:
            print("Error in none vote, get_player_id_string!")
            return ""
        return id_string

    # Used to get the most recent game status
    def get_game_status(self):
        return GameStatus.objects.last()

    def get_current_player(self):
        try:
            return Player.objects.get(user=self.scope['user'])
        except:
            #print("Error in get_current_player!")
            return None

    def get_player_username(self, id):
        try:
            player = Player.objects.get(id_in_game=id)
            return player.user.username
        except:
            print("Error in get_player_username!")
            return None

    # Used to get the current player's role
    def get_current_player_role(self):
        # print("in get_current_player_role")
        try:
            role = Player.objects.get(user=self.scope['user']).role
        except:
            print("Error in get_player_role!")
            role = None
        return role

    '''exit game feature'''


            
