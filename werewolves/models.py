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
    WOLF = "WOLF"
    SEER = "SEER"
    GUARD = "GUARD"
    ANNOUNCE = "ANNOUNCE"
    SPEECH = "SPEECH"
    VOTE = "VOTE"
    END_GAME = "END_GAME"
    END_VOTE = "END_VOTE"
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

# The Player model keeps track of the player's username and role.
class Player(models.Model):
    # Username must be shorter than 30 characters.
    user     = models.ForeignKey(User, on_delete=models.PROTECT, related_name="player", null=True)
    role     = models.CharField(max_length=30, choices=PlayerRole.choices(), default=PlayerRole.NONE)
    status   = models.CharField(max_length=30, choices=PlayerStatus.choices(), default=PlayerStatus.ALIVE)
    vote     = models.ForeignKey('self', on_delete=models.CASCADE, related_name='voted', null=True)
    # TODO: Tentative field, indicate whether a player is making a speech or not
    speech   = models.BooleanField(default=False)

    def __str__(self):
        return 'Player ' + self.role

class GameStatus(models.Model):
    # False means night, True means day.
    night           = models.BooleanField(default=False) 
    # Target player's id, null means the wolves haven't decided yet.
    wolves_target          = models.IntegerField(null=True)
    guard_target           = models.IntegerField(null=True)
    seer_target            = models.IntegerField(null=True)
    vote_target            = models.IntegerField(null=True)
    # Indicate which speaker is the first speaker and which is the current speaker
    first_speaker   = models.ForeignKey(Player, on_delete=models.PROTECT, related_name="is_first_speaker", null=True)
    current_speaker = models.ForeignKey(Player, on_delete=models.PROTECT, related_name="is_current_speaker", null=True)
    # Indicate the current game step
    step = models.CharField(max_length=30, choices=GameStep.choices(), default=GameStep.NONE)
    # Indicate if the game is over, False: wolves win, True: good people win, None: game is not over
    winning         = models.BooleanField(null=True, default=None)
    # null means the player who got assigned the character is out.
    wolves          = models.ForeignKey(Player, on_delete=models.PROTECT, related_name="is_wolf", null=True)
    seer            = models.ForeignKey(Player, on_delete=models.PROTECT, related_name="is_seer", null=True)
    guard           = models.ForeignKey(Player, on_delete=models.PROTECT, related_name="is_guard", null=True)
    villagers       = models.ForeignKey(Player, on_delete=models.PROTECT, related_name="is_villager", null=True)
    # Booleans indicating whose turn this is at night (tentative).
    #wolves_turn     = models.BooleanField(default=False)
    #seer_turn       = models.BooleanField(default=False)
    #guard_turn      = models.BooleanField(default=False)
