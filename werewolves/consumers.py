import json
import random
from werewolves.models import Player, PlayerRole, GameStatus, Message
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.general_group = "general_group"    # all players are in this group
        self.wolves_group = "wolves_group"      # all wolves are in this group
        self.seer_group = "seer_group"          # seer is in this group
        self.guard_group = "guard_group"        # guard is in this group

        print("in connect")
        user = self.scope["user"]
        print("     user:", user)
        role = await database_sync_to_async(self.get_current_player_role)()
        print("     role:", role)
        # num_players = await database_sync_to_async(self.check_num_players)()
        # if num_players < 6:
        # Put all players in the general group
        await self.channel_layer.group_add(
            self.general_group,
            self.channel_name
        )

        if (role == "WOLF") :
            await self.channel_layer.group_add(
                self.wolves_group,
                self.channel_name
            )
        elif (role == "GUARD") :
            await self.channel_layer.group_add(
                self.guard_group,
                self.channel_name
            )
        elif (role == "SEER") :
            await self.channel_layer.group_add(
                self.seer_group,
                self.channel_name
            )

        #TODO this will call init_game_status 6 times, could be updated
        if (role != None):
            await database_sync_to_async(self.init_game_status)()

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
            # TODO: should be put after assigned players role, here for testing
            #await database_sync_to_async(self.init_game_status)()
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
        elif message_type == 'start-game-message':
            # assign roles and id in game for players
            await database_sync_to_async(self.assign_roles_and_ids)()
            await self.channel_layer.group_send(
                # self.room_group_name,
                self.general_group,
                {
                    'type': 'start_game_message',
                    'message': 'start_game'
                }
            )

        # system message
        elif message_type == 'system-message':
            update = text_data_json['update']
            if update == 'update':
                target_id = text_data_json['target_id']
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

        # select message
        elif message_type == 'select-message':
            target_id = text_data_json['id']
            await self.channel_layer.group_send(
                # self.room_group_name,
                self.general_group,
                {
                    'type': 'select_message',
                    'target_id': target_id,
                }
            )
        # exit game message
        elif message_type == 'exit-game-message':
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


    '''start game feature'''

    # TODO: Change broadcast audience to the first six players
    async def start_game_message(self, event):
        # players = await database_sync_to_async(self.get_all_players)()
        # print(f'in start game message: current players{players}')
        await self.send(text_data=json.dumps({
            'message-type': 'start_game_message',
        }))

    def create_player(self):
        user = self.scope["user"]
        player = Player.objects.filter(user=user)
        if len(player) == 0:
            new_player = Player(user=user)
            new_player.save()

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
        print(f'all_players in assign roles in consumer {all_players}')


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
        current_player = Player.objects.get(user=current_user)
        if current_player:
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
        game.step = "END_DAY"
        game.winning = None
        game.save()


    '''update game status feature'''
    # update target field in GameStatus
    def update_status(self, target_id, times_up):
        print("in update_status")
        print("target_id:", target_id)
        game = GameStatus.objects.last()
        new_status = GameStatus()
        new_status = game
        user = self.scope["user"]
        if (game.step == "WOLF"):
            if (times_up):
                if (game.wolves_target == None):
                    new_status.wolves_target = 0
                #new_status.step = "END_KILL"
            else:
                try:
                    wolf_player = Player.objects.select_for_update().filter(user=user)
                    if (wolf_player.role == "WOLF" and wolf_player.status == "ALIVE"):
                        if (target_id == None):
                            wolf_player.kill = 0
                        else:
                            wolf_player.kill = target_id
                    wolf_player.save()
                except:
                    pass

                new_status.wolves_target = self.valid_kill_target()
            #update kill status in player model
        elif (game.step == "GUARD"):
            if (times_up):
                if (game.guard_target == None):
                    new_status.guard_target = 0
                #new_status.step = "SEER"
            else:
                new_status.guard_target = self.valid_target(target_id)
        elif (game.step == "SEER"):
            if (times_up):
                if (game.seer_target == None):
                    new_status.seer_target = 0
                #new_status.step = "END_NIGHT"
            else:
                new_status.seer_target = self.valid_target(target_id)
        #elif (game.step == "ANNOUNCE"):
        #    if (game.wolves_target > 0):
        #        if (game.guard_target > 0 and game.guard_target == game.wolf_target):
        #            new_status.wolves_target = 0
        #        else:
        #            player = Player.objects.select_for_update(
        #                id_in_game=game.wolves_target.id_in_game)
        #            player.status = "OUT"
        #            player.save()
        elif (game.step == "SPEECH"):
            if (game.first_speaker == None):
                new_status.first_speaker = self.next_speaker(game.wolves_target)
                new_status.current_speaker = new_status.first_speaker
            else:

                if (self.end_speech()):
                    new_status.next_step = "END_SPEECH"
                else:
                    new_status.current_speaker = self.next_speaker(
                        game.current_speaker)
        elif (game.step == "VOTE"):
            if (times_up):
                if (game.vote_target == None):
                    new_status.vote_target = 0
                #new_status.step = "END_VOTE"
            else:
                try:
                    vote_player = Player.objects.select_for_update().filter(user=user)
                    if (target_id == None):
                        vote_player.vote = 0
                    else:
                        vote_player.vote = target_id
                    vote_player.save()
                except:
                    pass

                new_status.vote_target = self.vote_player()
        #elif (game.step == "END_VOTE"):
        #    if (game.vote_target != None):
        #        player = Player.objects.select_for_update(id_in_game=game.vote_target)
        #        player.status = "OUT"
        #        player.save()
        # else:
            # TODO: update default status

        new_status.save()

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
            target_player = Player.objects.filter(id_in_game=target_id)
            if (target_player.status != "ALIVE"):
                return None
            else:
                return target_id

    # if all wolves player select different target, return None
    # else return the valid target id
    def valid_kill_target(self):
        try:
            wolves = Player.objects.filter(role="WOLF")
            i = 0
            kill_target = None
            for wolf in wolves:
                if (wolf.status == "ALIVE"):
                    if (i == 0):
                        kill_target = self.valid_target_id(wolf.kill).id_in_game
                    else:
                        if (kill_target != wolf.kill):
                            return None, "WOLF"
                    i += 1

            if (kill_target > 0):
                return kill_target
            else:
                return None
        except:
            return None

    def voted_player(self):
        if (self.is_vote_end() == False):
            return None
        try:
            vote_count = [0, 0, 0, 0, 0, 0]
            most_vote = 0
            most_vote_id = 0
            alive_players = Player.objects.filter(status="ALIVE")
            for player in alive_players:
                if (player.vote != None and player.vote > 0):
                    vote_count[player.id_in_game - 1] += 1
                elif (player.vote == None):
                    return None
            # get max vote
            for i in range(0, len(vote_count)):
                if (vote_count[i] > most_vote):
                    most_vote = vote_count[i]
                    most_vote_id = i
            # check if there are same votes
            for i in range(0, len(vote_count)):
                if (vote_count[i] == most_vote and i != most_vote_id):
                    return 0

            return most_vote_id + 1
        except:
            return None

    #   Update next step
    def next_step(self, times_up):
        game = GameStatus.objects.last()
        new_status = GameStatus()
        new_status = game
        if (game.step == "WOLF"):
            if (game.wolf_target == None):
                new_status.step = "WOLF"
            else:
                new_status.step = "GUARD"
        elif (game.step == "GUARD"):
            if (game.guard_target == None):
                new_status.step = "GUARD"
            else:
                new_status.step = "SEER"
        elif (game.step == "SEER"):
            if (game.seer_target == None):
                new_status.step = "SEER"
            else:
                #end of seer
                #update night killing
                if (game.wolves_target > 0):
                    if (game.guard_target > 0 and game.guard_target == game.wolf_target):
                        new_status.wolves_target = 0
                else:
                    player = Player.objects.select_for_update(
                        id_in_game=game.wolves_target.id_in_game)
                    player.status = "OUT"
                    player.save()

                new_status.winning = self.is_end_game()
                if (new_status.winning == None):
                    new_status.step = "ANNOUNCE"
                else:
                    new_status.step = "END_GAME"

            new_status.winning = self.is_end_game()

        elif (game.step == "ANNOUNCE"):
            #update night killing
            #if (game.wolves_target > 0):
            #    if (game.guard_target > 0 and game.guard_target == game.wolf_target):
            #        new_status.wolves_target = 0
            #    else:
            #        player = Player.objects.select_for_update(
            #            id_in_game=game.wolves_target.id_in_game)
            #        player.status = "OUT"
            #        player.save()

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
        elif (game.step == "VOTE"):
            new_status.night = True
            if (game.vote_target == None):
                new_status.step = "VOTE"
            else:
                if (game.vote_target > 0):
                    player = Player.objects.select_for_update(id_in_game=game.vote_target)
                    player.status = "OUT"
                    player.save()

                new_status.winning = self.is_end_game()
                if (new_status.winning == None):
                    new_status.step = "END_VOTEF"
                else:
                    new_status.step = "END_GAME"

        elif (game.step == "END_VOTE"):
            #if (game.vote_target > 0):
            #    player = Player.objects.select_for_update(id_in_game=game.vote_target)
            #    player.status = "OUT"
            #    player.save()

            new_status.winning = self.is_end_game()
            if (new_status.winning == None):
                new_status.step = "WOLF"
            else:
                new_status.step = "END_GAME"

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
        step = game.step
        out_player_id = None
        user = self.scope['user']
        current_player = Player.objects.filter(user=user)
        current_player_id = current_player.id_in_game
        current_player_role = current_player.role
        current_speaker_id = None
        current_speaker_role = None
        target_id = None
        seer_id = None
        guard_id = None
        wolf_id = None
        villager_id = None
        message = None

        if (group == "general"):
            if (step == "ANNOUNCE"):
                out_player_id = game.wolf_target
            elif (step == "SPEECH"):
                current_speaker_id = game.current_speaker
                current_speaker_role = Player.objects.filter(id_in_game = game.current_speaker).role
            elif (step == "END_VOTE"):
                out_player_id = game.vote_target
                target_id = self.get_player_id("VOTE")
            elif (step == "END_GAME"):
                seer_id = self.get_player_id("SEER")
                guard_id = self.get_player_id("GUARD")
                wolf_id = self.get_player_id("WOLF")
                villager_id = self.get_player_id("VILLAGER")
                message = game.winning
        elif (group == "SEER" and step == "SEER"):
            target_id = game.seer_target
            if (game.seer_target > 0):
                role = Player.objects.filter(id_in_game=game.seer_target).role
                if (role == "WOLF"):
                    message = "Bad"
                else:
                    message = "Good"
        elif (group == "WOLF" and step == "WOLF"):
            target_id = game.wolf_target
        elif (group == "GUARD" and step == "GUARD"):
            target_id = game.guard_target

        '''
        if (group == "general"):
            if (game.step == "END_DAY"):
                message = "It is night time."
            elif (game.step == "WOLF"):
                message = "Wolf is choosing a player to kill."
            elif (game.step == "GUARD"):
                message = "Guard is choosing a player to protect."
            elif (game.step == "SEER"):
                message = "Seer is seeing a player's identity."
            elif (game.step == "END_NIGHT"):
                message = "It is day time."
            elif (game.step == "ANNOUNCE"):
                #if (game.winning == None):
                if (game.wolves_target == None):
                    message = "Last night, nobody gets killed."
                else:
                    target = Player.objects.get(id_in_game=game.wolves_target)
                    message = "Last night, " + target.user + " gets killed."
                #else:
                    #general_message = "Game Over."
            elif (game.step == "SPEECH"):
                if (game.first_speaker == None):
                    message = "Now each player needs to make a speech."
                else:
                    message = "Player " + game.current_speaker + "'s turn to speak."
            elif (game.step == "VOTE"):
                message = "Now each player needs to make a vote, or not."
            elif (game.step == "END_VOTE"):
                alive_players = Player.objects.filter(status="ALIVE")
                for player in alive_players:
                    message += "Player " + player.id_in_game + " voted Player " + player.vote + "\n"
                if (game.vote_target > 0):
                    out_id = game.vote_target
                    target = Player.objects.get(id_in_game=game.vote_target)
                    message += target.user + " is voted out.\n"
                else:
                    message += "Nobody gets voted out.\n"
            elif (game.step == "END_GAME"):
                message = "Game Over.\n"
                if (game.winning):
                    message += "Good people won."
                else:
                    message += "Wolves won."
        elif (group == "wolves"):
            if (game.step == "WOLF"):
                if (game.wolves_target == None):
                    message = "All wolves should pick the same player to kill. Wolves can decide to kill no one."
                #elif (game.step == "END_KILL"):
                else:
                    if (game.wolves_target > 0):
                        out_id = game.wolves_target
                        wolves_target =  await database_sync_to_async(self.get_target_player)(out_id)
                        #wolves_target = await sync_to_async(Player.objects.filter, thread_sensitive=True)(id=game.wolves_target)
                        message = "You chose to kill " + wolves_target.user.username
                    else:
                        message = "You chose to kill no one"
        elif (group == "guard"):
            if (game.step == "GUARD"):
                if (game.guard_target != None):
                    if (game.guard_target > 0):
                        guard_target = Player.objects.filter(id_in_game=game.guard_target)
                        #guard_target = await sync_to_async(Player.objects.get, thread_sensitive=True)(id=game.guard_target)
                        message = "You chose to protect " + guard_target.user.username
                    else:
                        message = "You chose to protect no one"
                else:
                    message = "You can choose to protect one player, or protect no one."
        elif (group == "seer"):
            if (game.step == "SEER"):
                if (game.seer_target != None):
                    if (game.seer_target > 0):
                        seer_target = Player.objects.filter(id_in_game=game.seer_target)
                        #seer_target = await sync_to_async(Player.objects.get, thread_sensitive=True)(id=game.seer_target)
                        if (seer_target.role == "WOLF"):
                            message = "This player is bad."
                        else:
                            message = "This player is good."
                    else:
                        message = "You chose to see no one."
                else:
                    message = "You can choose to see a player's role, or see no one."
        '''
        print("in system message")
        print("     user:", self.scope["user"])
        print("     group:", group)

        await self.send(text_data=json.dumps({
            'group': group,
            'step': step,
            'out_player_id': out_player_id,
            'current_player_id': current_player_id,
            'current_player_role': current_player_role,
            'current_speaker_id': current_speaker_id,
            'current_speaker_role': current_speaker_role,
            'target_id': target_id, #in step vote, it is the voted player
            'seer_id': seer_id,
            'guard_id': guard_id,
            'wolf_id': wolf_id,
            'villager_id': villager_id,
            'message': message, # in step seer, good/bad person
        }))


    #  get the next alive speaker.
    # TODO: the first player killed at night should also be counted. debug needed
    # param(in): id: the current speaker, need to find the next one
    # return(out): a player model, next availbe speaker
    #
    def next_speaker(self, id):
        alive_players = Player.objects.filter(status="ALIVE")
        # if no dead player from the night, select the oldest alive player joined the room
        if (id == None):
            return alive_players.first()
        else:
            for player in alive_players:
                if (player.id_in_game > id):
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
        #return True
        game = GameStatus.objects.last()
        if (game.step != "END_SPEECH"):
            if (game.current_speaker == game.first_speaker):
                return True
        else:
            return False
        #if (~game.speech_over):
        #    if (game.current_speaker == game.first_speaker):
        #        return True
        #elif (game.speech_over == None):
        #    if (game.current_speaker != None):
        #        return False
        #else:
        #    return None

    def get_player_id(self,role):
        id_array = []
        if (role == "VOTE"):
            players = Player.objects.order_by(F('id_in_game').asc())
            for player in players:
                if (player.vote == None):
                    id_array.append(-1)
                else:
                    id_array.append(player.vote_target)
        else:
        #elif (role == "WOLF"):
            players = Player.objects.filter(role = role)
            for player in players:
                id_array.append(player.id_in_game)

        return id_array
    '''
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
        alive_players = Player.objects.filter(status = "ALIVE")
        for player in alive_players:
            if (player.vote == None):
                return False
        return True
        #TODO: need to implement vote checking function


    def is_end_multi_select(self, step):
        if (step == "VOTE"):
            players = Player.objects.filter(status = "ALIVE")
        elif (step == "WOLF"):
            players = Player.objects.filter(role = "WOLF")

        for player in players:
            if (player.vote == None):
                return False
        return True
    '''
    #Used to get the most recent game status
    def get_game_status(self):
        return GameStatus.objects.last()

    # Used to get the current player's role
    def get_current_player_role(self):
        #print("in get_current_player_role")
        try:
            role = Player.objects.get(user=self.scope['user']).role
        except:
            role = None
        return role

    def get_current_player_id(self):
        player = Player.objects.get(user=self.scope['user'])
        id = player.id_in_game
        return id

    # Used to get all the players that are out of game after a step
    def get_players_out(self):
        res = []
        # get only the players killed last night
        players = Player.objects.filter(status="OUT")
        for player in players:
            res.append(str(player.id_in_game))
        return res

    # get the status of the player that is selected
    def get_selected_player_status(self, id):
        player = Player.objects.get(id_in_game=id)
        return player.status

    # Used to get the player that is speaking
    def get_current_speaker_role_and_id(self):
        game = self.get_game_status()
        speaker = game.current_speaker
        id = speaker.id_in_game
        role = speaker.role
        return role, id

    async def select_message(self, event):
        target_id = event['target_id']
        status = await database_sync_to_async(self.get_game_status)()
        step = status.step
        role = await database_sync_to_async(self.get_current_player_role)()
        selected_player_status = await database_sync_to_async(self.get_selected_player_status)(target_id)
        await self.send(text_data=json.dumps({
            'message-type': 'select_message',
            'role': role,
            'step':step,
            'target_id': target_id,
            'selected_player_status': selected_player_status
        }))

    '''exit game feature'''

    async def exit_game_message(self, event):
        print('exiting game')
        await self.send(text_data=json.dumps({
            'message-type': 'exit_game_message'
        }))
