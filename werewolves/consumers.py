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
            count = await database_sync_to_async(self.game_objects_count)()
            if (count >= 6):
                await self.channel_layer.group_send(
                    self.general_group,
                    {
                        'type': 'system_message',
                        'group': 'general',
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
            print("update: ", update)
            if update == 'update':
                target_id = text_data_json['target_id']
                await database_sync_to_async(self.update_status)(target_id=target_id, times_up=False)
                #if (target_id != None):
                    #await database_sync_to_async(self.update_status)(target_id=target_id, times_up=False)
                    #await database_sync_to_async(self.next_step)(times_up=False)
            elif update == 'next_step':
                await database_sync_to_async(self.next_step)(times_up=False)
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
            # if i == 0 or i == 1:
            #     all_players[i].role = "VILLAGER"
            # elif i == 2 or i == 3:
            #     all_players[i].role = "WOLF"
            # elif i == 4:
            #     all_players[i].role = "SEER"
            # elif i == 5:
            #     all_players[i].role = "GUARD"
            # all_players[i].id_in_game = i + 1
            # all_players[i].save()
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

    def game_objects_count(self):
        return GameStatus.objects.count()

    # Used to initialize game_status
    def init_game_status(self):
        print("in init_game_status")
        if (GameStatus.objects.count() > 6):
            game = GameStatus.objects.select_for_update().last()
        else:
            game = GameStatus()
        #game = GameStatus()
        game.wolves_select = None
        game.wolves_target = None
        game.wolves_target_name = None
        game.guard_select = None
        game.guard_previous_id = None
        game.guard_target = None
        game.guard_target_name = None
        game.seer_select = None
        game.seer_target = None
        game.seer_target_name = None
        game.seer_target_role = None
        game.vote_select = None
        game.vote_target = None
        game.vote_target_name = None
        game.first_speaker_id = None
        game.speaker_id = None
        game.current_speaker = None
        game.current_speaker_name = None
        game.current_speaker_role = None
        game.step               = "END_DAY"
        game.winning            = None
        game.wolves             = self.get_player_id_string("WOLF")
        game.seer               = self.get_player_id_string("SEER")
        game.guard              = self.get_player_id_string("GUARD")
        game.villagers          = self.get_player_id_string("VILLAGER")
        game.save()

        self.clean_action()


    '''update game status feature'''
    # update target field in GameStatus
    def update_status(self, target_id, times_up):
        print("in update_status")
        print("     target_id:", target_id)
        game = GameStatus.objects.select_for_update().last()
        new_status = GameStatus()
        new_status = game
        user = self.scope["user"]
        if (game.step == "WOLF"):
            if (times_up):
                if (game.wolves_select == None):
                    new_status.wolves_select = 0
            else:
                #wolf_player = Player.objects.select_for_update().get(user=user)
                try:
                    wolf_player = Player.objects.select_for_update().get(user=user)
                    #wolf_player = Player.objects.select_for_update().get(user=user)
                    if (wolf_player.role == "WOLF" and wolf_player.status == "ALIVE"):
                        #print("         target_id:", target_id)
                        if (target_id == None):
                            wolf_player.kill = 0
                        else:
                            wolf_player.kill = target_id
                    wolf_player.save()
                except:
                    print("Error in wolf step!")
                    pass

                new_status.wolves_select = self.valid_kill_target()
                print("     new_status.wolves: ", new_status.wolves_select)
            
            if (new_status.wolves_select != None):
                if (new_status.wolves_select > 0):
                    new_status.wolves_target = Player.objects.get(
                        id_in_game=new_status.wolves_select)
                    new_status.wolves_target_name = Player.objects.get(
                        id_in_game=new_status.wolves_select).user.username
        elif (game.step == "GUARD"):
            if (times_up):
                if (game.guard_select == None):
                    new_status.guard_select = 0
                #new_status.step = "SEER"
            else:
                guard_id = self.valid_target(target_id)
                if (guard_id != game.guard_previous_id):
                    new_status.guard_select = guard_id
                else:
                    new_status.guard_select = None

            if (new_status.guard_select != None):
                if (new_status.guard_select > 0):
                    new_status.guard_target = Player.objects.get(
                        id_in_game=new_status.guard_select)
                    new_status.guard_target_name = Player.objects.get(
                        id_in_game=new_status.guard_select).user.username
        elif (game.step == "SEER"):
            if (times_up):
                if (game.seer_select == None):
                    new_status.seer_select = 0
                #new_status.step = "END_NIGHT"
            else:
                new_status.seer_select = self.valid_target(target_id)
                print("     new_status.seer: ", new_status.seer_select)
            
            if (new_status.seer_select != None):
                if (new_status.seer_select > 0):
                    new_status.seer_target = Player.objects.get(
                        id_in_game=new_status.seer_select)
                    new_status.seer_target_name = Player.objects.get(
                        id_in_game=new_status.seer_select).user.username
                    new_status.seer_target_role = Player.objects.get(
                        id_in_game=new_status.seer_select).role
        #elif (game.step == "ANNOUNCE"):
        #    if (game.wolves_target > 0):
        #        if (game.guard_target > 0 and game.guard_target == game.wolf_target):
        #            new_status.wolves_target = 0
        #        else:
        #            player = Player.objects.select_for_update(
        #                id_in_game=game.wolves_target.id_in_game)
        #            player.status = "OUT"
        #            player.save()
        
        #elif (game.step == "SPEECH"):
        #    if (game.first_speaker_id == None):
        #        new_status.first_speaker_id = self.next_speaker(game.wolves_select)
        #        new_status.speaker_id = new_status.first_speaker_id
        #    else:
                #if (self.end_speech()):
                #    new_status.next_step = "END_SPEECH"
                #else:
        #        new_status.speaker_id = self.next_speaker(
        #                game.speaker_id)
                
        #        if (new_status.speaker_id != None):
        #            if (new_status.speaker_id > 0):
        #                new_status.current_speaker = Player.objects.get(
        #                    id_in_game=new_status.speaker_id)
        #                new_status.current_speaker_name = Player.objects.get(
        #                    id_in_game=new_status.speaker_id).user.username
        #                new_status.current_speaker_role = Player.objects.get(
        #                    id_in_game=new_status.speaker_id).role
        elif (game.step == "VOTE"):
            if (times_up):
                if (game.vote_target == None):
                    new_status.vote_select = 0
                #new_status.step = "END_VOTE"
            else:
                try:
                    player = Player.objects.select_for_update().get(user=user)
                    #vote_player = Player.objects.select_for_update().get(user=user)
                    if (target_id == None):
                        player.vote = 0
                    else:
                        player.vote = target_id
                    player.save()
                except:
                    print("Error in vote step!")
                    pass

                new_status.vote_select = self.vote_player()
            
            if (new_status.speaker_id != None):
                if (new_status.vote_select > 0):
                    new_status.vote_target = Player.objects.get(
                        id_in_game=new_status.vote_select)
                    new_status.vote_target = Player.objects.get(
                        id_in_game=new_status.vote_select).user.username
        elif (game.step == "END_DAY"):
            self.clean_action()
        #elif (game.step == "END_VOTE"):
        #    if (game.vote_target != None):
        #        player = Player.objects.select_for_update(id_in_game=game.vote_target)
        #        player.status = "OUT"
        #        player.save()
        # else:
            # TODO: update default status
        game = new_status
        game.save()
        #new_status.save()

    # check the select target_id
    # if select None, return 0
    # if select is not valid, return None
    # if select is valid, return traget_id
    def valid_target(self, target_id):
        #print("in valid_target")
        if (target_id == None):
            return 0
        elif (target_id == 0):
            return 0
        elif (target_id > 0):
            target_player = Player.objects.get(id_in_game=target_id)
            #print(" target_player:", target_player)
            if (target_player.status != "ALIVE"):
                return None
            else:
                return target_id

    # if all wolves player select different target, return None
    # else return the valid target id
    def valid_kill_target(self):
        #print("in valid_kill_target")
        try:
        #if (1):
            wolves = Player.objects.filter(role="WOLF")
            i = 0
            kill_target = None
            for wolf in wolves:
                #print(wolf)
                if (wolf.status == "ALIVE"):
                    #print("     i:", i, " wolf.kill:", wolf.kill)
                    if (i == 0):
                        kill_target = self.valid_target(wolf.kill)
                    else:
                        if (wolf.kill != None):
                            if (kill_target != wolf.kill):
                                #print("kill_target:", kill_target)
                                return None
                    i += 1
                    #print("     i:",i," kill_target:",kill_target)
            
            if (kill_target != None):
                if (kill_target > 0):
                    return kill_target
            return None
        except:
            print("Error in valid_kill_target!")
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
            print("Error in voted_player!")
            return None

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
                #end of seer
                #update night killing
                if (game.wolves_select != None):
                    if (game.wolves_select > 0):
                        if (game.guard_select != None):
                            if (game.guard_select > 0 and game.guard_select == game.wolves_select):
                                new_status.wolves_select = 0
                                new_status.wolves_target = None
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

                #new_status.winning = self.is_end_game()
                #if (new_status.winning == None):
                #    new_status.step = "ANNOUNCE"
                #else:
                #    new_status.step = "END_GAME"

            #new_status.winning = self.is_end_game()

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
                if (game.first_speaker_id == None):
                    new_status.first_speaker_id = self.next_speaker(game.wolves_select)
                    new_status.speaker_id = new_status.first_speaker_id
                else:
                #if (self.end_speech()):
                #    new_status.next_step = "END_SPEECH"
                #else:
                    new_status.speaker_id = self.next_speaker(game.speaker_id)
                print("     speaker_id:", new_status.speaker_id)
                
                if (new_status.speaker_id != None):
                    if (new_status.speaker_id > 0):
                        new_status.current_speaker = Player.objects.get(
                            id_in_game=new_status.speaker_id)
                        new_status.current_speaker_name = Player.objects.get(
                            id_in_game=new_status.speaker_id).user.username
                        new_status.current_speaker_role = Player.objects.get(
                            id_in_game=new_status.speaker_id).role
                        player = Player.objects.select_for_update().get(id=new_status.speaker_id)
                        player.speech = True
                        player.save()
                        
        elif (game.step == "VOTE"):
            if (game.vote_select == None):
                new_status.step = "VOTE"
            else:
                #if (game.vote_select != None):
                new_status.next_step = "END_VOTE"
                if (game.vote_select > 0):
                    player = Player.objects.select_for_update().get(id_in_game=game.vote_select)
                    player.status = "OUT"
                    player.save()


                #new_status.winning = self.is_end_game()
                #if (new_status.winning == None):
                #    new_status.step = "END_VOTE"
                #else:
                #    new_status.step = "END_GAME"

        elif (game.step == "END_VOTE"):
            #if (game.vote_target > 0):
            #    player = Player.objects.select_for_update(id_in_game=game.vote_target)
            #    player.status = "OUT"
            #    player.save()

            new_status.winning = self.is_end_game()
            if (new_status.winning == None):
                new_status.step = "END_DAY"
            else:
                new_status.step = "END_GAME"
        elif (game.step == "END_DAY"):
            new_status.step = "WOLF"

        game = new_status
        #new_status.save()
        game.save()


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
        print("in system message")
        #print("     user:", user)
        print("     group:", group, " step: ", step, " user: ", user)
        current_player = await database_sync_to_async(self.get_current_player)()
        #current_player = await sync_to_async(Player.objects.get, thread_sensitive=True)(user=user)
        #current_player = Player.objects.filter(id_in_game = 1)
        #print("     current_player", current_player.id)
        current_player_id = current_player.id_in_game
        current_player_role = current_player.role
        current_player_name = await database_sync_to_async(self.get_player_username)(id=current_player_id)
        #current_player_name = current_player.user.username
        speaker_id = None
        current_speaker_role = None
        current_speaker_name = None
        all_players_vote = None
        target_id = None
        target_name = None
        seer_id = None
        guard_id = None
        wolf_id = None
        villager_id = None
        message = None

        if (group == "general"):
            if (step == "ANNOUNCE"):
                out_player_id = game.wolves_select
            elif (step == "SPEECH"):

                speaker_id = game.speaker_id
                #current_speaker = await sync_to_async(Player.objects.get, thread_sensitive=True)(id_in_game=game.current_speaker)
                if (speaker_id != None):
                    if (speaker_id > 0):
                        current_speaker_role = game.current_speaker_role
                        current_speaker_name = game.current_speaker_name
                        #current_speaker_role = game.current_speaker.role
                        #current_speaker_name = game.current_speaker.name
            elif (step == "END_VOTE"):
                out_player_id = game.vote_select
                all_players_vote = self.get_player_id("VOTE")
            elif (step == "END_GAME"):
                seer_id = game.seer
                guard_id = game.guard
                wolf_id = game.wolves
                villager_id = game.villagers
                message = game.winning
            elif (step == "WOLF"):
                target_id = current_player.kill
                out_player_id = game.wolves_select
                print("     target_id: ", target_id, "  out_player_id: ", out_player_id)
            #target_id = game.wolves_select
                if (game.wolves_select != None):
                    if (game.wolves_select > 0):
                        target_name = game.wolves_target_name
            elif (step == "GUARD"):
                target_id = game.guard_select
            elif (step == "SEER"):
                target_id = game.seer_select
        elif (group == "seer" and step == "SEER"):
            target_id = game.seer_target
            print("     target_id: ", target_id)
            if (game.seer_select != None):
                if (game.seer_select > 0):
                #seer_target_player = await sync_to_async(Player.objects.get, thread_sensitive=True)(id_in_game=game.seer_target)
                    #role = game.seer_target.role
                    role = game.seer_target_role
                    print("     seer target role:", role)
                #role = Player.objects.filter(id_in_game=game.seer_target).role
                    if (role == "WOLF"):
                        message = "Bad"
                    else:
                        message = "Good"
        
        elif (group == "wolves" and step == "WOLF"):
            #print(" here")
            target_id = current_player.kill
            out_player_id = game.wolves_select
            print("     target_id: ", target_id, "  out_player_id: ", out_player_id)
            #target_id = game.wolves_select
            if (game.wolves_select != None):
                if (game.wolves_select > 0):
                    target_name = game.wolves_target_name
                    #target_name = await database_sync_to_async(self.get_player_username)(id=game.wolves_select)
        elif (group == "guard" and step == "GUARD"):
            target_id = game.guard_select
            print("     target_id: ", target_id)
            if (game.guard_select != None):
                if (game.guard_select > 0):
                    target_name = game.guard_target_name
                    #target_name = await database_sync_to_async(self.get_player_username)(id=game.guard_select)

        await self.send(text_data=json.dumps({
            'message-type': "system_message",
            'group': group,
            'step': step,
            'out_player_id': out_player_id, # step wolf: id of final decision
            'current_player_id': current_player_id,
            'current_player_role': current_player_role,
            'speaker_id': speaker_id,
            'current_speaker_role': current_speaker_role,
            'current_speaker_name': current_speaker_name,
            'target_id': target_id, #in step vote, it is the voted player
            'target_name': target_name, # out player username
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
        god_alive = 0
        villager_alive = 0
        for player in Player.objects.filter(status="ALIVE"):
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
        #TODO: only for testing
        #return True
        print("in is_end_speech")
        players = Player.objects.filter(status="ALIVE")
        for player in players:
            print("     id:", player.id_in_game, " speech:", player.speech)
            if (player.speech == False):
                return False
        
        return True
        #if (~game.speech_over):
        #    if (game.current_speaker == game.first_speaker):
        #        return True
        #elif (game.speech_over == None):
        #    if (game.current_speaker != None):
        #        return False
        #else:
        #    return None
    
    def clean_action(self):
        print("in clean_action")
        players = Player.objects.all()
        for player in players:
            player.vote = None
            player.kill = None
            player.speech = False
            player.save()
        
        game = GameStatus.objects.select_for_update().last()
        game.wolves_select = None
        game.wolves_target = None
        game.wolves_target_name = None
        game.guard_select = None
        game.guard_previous_id = None
        game.guard_target = None
        game.guard_target_name = None
        game.seer_select = None
        game.seer_target = None
        game.seer_target_name = None
        game.seer_target_role = None
        game.vote_select = None
        game.vote_target = None
        game.vote_target_name = None
        game.first_speaker_id = None
        game.speaker_id = None
        game.current_speaker = None
        game.current_speaker_name = None
        game.current_speaker_role = None
        game.save()


    def get_player_id_string(self,role):
        id_string = ""
        empty = ""
        if (role == "VOTE"):
            try:
                players = Player.objects.order_by(F('id_in_game').asc())
                for player in players:
                    if (player.vote == None):
                        id_string += str(-1)
                    else:
                        id_string += str(player.vote_target)
            except:
                print("Error in vote, get_player_id_string!")
                return empty
        else:
            try:
                players = Player.objects.filter(role = role)
                for player in players:
                    id_string += str(player.id_in_game)
            except:
                print("Error in none vote, get_player_id_string!")
                return ""
        return id_string
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

    def get_current_player(self):
        try:
            return Player.objects.get(user=self.scope['user'])
        except:
            print("Error in get_current_player!")
            return None

    def get_player_username(self,id):
        try:
            player = Player.objects.get(id_in_game=id)
            return player.user.username
        except:
            print("Error in get_player_username!")
            return None

    # Used to get the current player's role
    def get_current_player_role(self):
        #print("in get_current_player_role")
        try:
            role = Player.objects.get(user=self.scope['user']).role
        except:
            print("Error in get_player_role!")
            role = None
        return role


    '''exit game feature'''

    async def exit_game_message(self, event):
        print('exiting game')
        await self.send(text_data=json.dumps({
            'message-type': 'exit_game_message'
        }))
