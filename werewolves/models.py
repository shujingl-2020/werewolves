from django.db import models
from django.contrib.auth.models import User
from enum import Enum

# A Player can have four different roles, plus one unassigned:
class PlayerRole(Enum):
    VILLAGER = "VILLAGER"
    WOLF     = "WOLF"
    SEER     = "SEER"
    GUARD    = "GUARD"
    NONE     = "NOT ASSIGNED"

    @classmethod
    def choices(cls):
        return tuple((i.name, i.value) for i in cls)

# A game procedure has multiple steps, plus one unassigned:
class GameStep(Enum):
    WOLF = "WOLF" # wolf select target
    #END_KILL = "END_KILL" # wolf finished kill
    GUARD = "GUARD" # guard select target
    SEER = "SEER" # seer select target
    #END_NIGHT = "END_NIGHT"  # update killing at night status
    ANNOUNCE = "ANNOUNCE" # announce game status and last night killed status
    SPEECH = "SPEECH" # every player make a speech
    #END_SPEECH = "END_SPEECH" # end speech
    VOTE = "VOTE" # start voting
    END_VOTE = "END_VOTE" #annouce voting status
    END_DAY = "END_DAY" # clean all data at this step
    END_GAME = "END_GAME"  # Game Over
    NONE = "NOT ASSIGNED"

    @classmethod
    def choices(cls):
        return tuple((i.name, i.value) for i in cls)

# A Player can have three statuses.
class PlayerStatus(Enum):
    ALIVE = "ALIVE"
    OUT   = "OUT" # attacked by the wolves or voted out by other players

    @classmethod
    def choices(cls):
        return tuple((i.name, i.value) for i in cls)

class Game(models.Model):
    step = models.CharField(default="NONE")
    # a string that stores each role's num, eg. "wolves: 2, villagers: 3"
    rolesNum = models.CharField(default="NONE")
    isEnd = models.BooleanField(default=True)
    # a string that stores all players' usernames, eg "a b c"
    playersList = models.CharField(default="NONE")# json string, username1:role
    onlinePlayerNum = models.IntegerField(null=True)
    neededPlayerNum = models.IntegerField(null=True)
    gameStatus = models.CharField(default="NONE")
    gameMode = models.CharField(default="NONE")
    roleOrder = models.CharField(default="NONE")

# The Player model keeps track of the player's username and role.
class Player(models.Model):
   username     = models.CharField(max_length=30, primary_key=True)
   gameID = models.IntegerField(default=-1)
   idInGame = models.IntegerField(null=True)
   role = models.CharField(default="NONE")
   #online, offline, waiting, inGame
   status = models.CharField(default="NONE")
   actionStatus = models.CharField(default="NONE")
   joinedWaitingRoomTimestamp = models.IntegerField(null=True)
   alive = models.BooleanField(default=True)
   # should be a stringify dictionary to store different roles’ actions
   context = models.CharField(default="NONE")

   def __str__(self):
        return 'Player' + str(self.username) +  ": " + self.role


class Message(models.Model):
    message_text = models.CharField(max_length=200)
    message_sender = models.ForeignKey(User, on_delete=models.PROTECT, related_name="message_creator")

    def __str__(self):
        return 'Message(id=' + str(self.id) + ')'

class GameStatus(models.Model):
    wolves_select = models.IntegerField(null=True)
    guard_select = models.IntegerField(null=True)
    guard_previous_id       = models.IntegerField(null=True)
    seer_select = models.IntegerField(null=True)
    seer_target_role        = models.CharField(max_length=30, null=True, default="NONE")
    vote_select             = models.IntegerField(null=True)
    first_speaker_id        = models.IntegerField(null=True)
    speaker_id = models.IntegerField(null=True)
    current_speaker_role    = models.CharField(max_length=30, null=True, default="NONE")
    step            = models.CharField(max_length=30, choices=GameStep.choices(), default=GameStep.NONE)
    # Indicate if the game is over, False: wolves win, True: good people win, None: game is not over
    winning         = models.BooleanField(null=True, default=None)
    wolves          = models.CharField(max_length=6, null=True, blank=True)
    seer            = models.CharField(max_length=6, null=True, blank=True)
    guard           = models.CharField(max_length=6, null=True, blank=True)
    villagers       = models.CharField(max_length=6, null=True, blank=True)
    vote            = models.CharField(max_length=6, null=True, blank=True)
    is_kill         = models.CharField(max_length=6, null=True, blank=True)

    trigger_id      = models.IntegerField(null=True)

