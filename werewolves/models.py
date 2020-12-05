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

# The Player model keeps track of the player's username and role.
class Player(models.Model):
    # Username must be shorter than 30 characters.
    user     = models.ForeignKey(User, on_delete=models.PROTECT, related_name="player", null=True)
    role     = models.CharField(max_length=30, choices=PlayerRole.choices(), default="NONE")
    status   = models.CharField(max_length=30, choices=PlayerStatus.choices(), default="ALIVE")
    #vote     = models.ForeignKey('self', on_delete=models.CASCADE, related_name='voted', null=True)
    vote     = models.IntegerField(null=True)
    kill     = models.IntegerField(null=True)
    # TODO: Tentative field, indicate whether a player is making a speech or not
    speech   = models.BooleanField(default=False)
    id_in_game = models.PositiveSmallIntegerField(default=0)

    def __str__(self):
        return 'Player' + str(self.id_in_game) +  ": " + self.role


class Message(models.Model):
    message_text = models.CharField(max_length=200)
    message_sender = models.ForeignKey(User, on_delete=models.PROTECT, related_name="message_creator")

    def __str__(self):
        return 'Message(id=' + str(self.id) + ')'

class GameStatus(models.Model):
    # False means night, True means day.
    #night           = models.BooleanField(default=False)
    # Target player's id, null means the wolves haven't decided yet.
    wolves_select = models.IntegerField(null=True)
    #wolves_target           = models.ForeignKey(
    #    Player, on_delete=models.PROTECT, related_name="is_wolf_target", null=True)
    #wolves_target_name      =  models.CharField(max_length=30, null=True, default="NONE")
    guard_select = models.IntegerField(null=True)
    #guard_target            = models.ForeignKey(
    #    Player, on_delete=models.PROTECT, related_name="is_guard_target", null=True)
    #guard_target_name = models.CharField(max_length=30, null=True, default="NONE")
    guard_previous_id       = models.IntegerField(null=True)
    seer_select = models.IntegerField(null=True)
    #seer_target             = models.ForeignKey(
    #    Player, on_delete=models.PROTECT, related_name="is_seer_target", null=True)
    #seer_target_name        = models.CharField(max_length=30, null=True, default="NONE")
    seer_target_role        = models.CharField(max_length=30, null=True, default="NONE")
    vote_select             = models.IntegerField(null=True)
    #vote_target             = models.ForeignKey(
    #    Player, on_delete=models.PROTECT, related_name="is_vote_target", null=True)
    #vote_target_name        = models.CharField(max_length=30, null=True, default="NONE")
    first_speaker_id        = models.IntegerField(null=True)
    speaker_id = models.IntegerField(null=True)
    #current_speaker         = models.ForeignKey(
    #    Player, on_delete=models.PROTECT, related_name="is_current_speaker", null=True)
    #current_speaker_name    = models.CharField(max_length=30, null=True, default="NONE")
    current_speaker_role    = models.CharField(max_length=30, null=True, default="NONE")
    #wolves_target = models.ForeignKey(
    #    Player, on_delete=models.PROTECT, related_name="is_wolf_target", null=True)
    #guard_target = models.ForeignKey(
    #    Player, on_delete=models.PROTECT, related_name="is_guard_target", null=True)
    #seer_target = models.ForeignKey(
    #    Player, on_delete=models.PROTECT, related_name="is_seer_target", null=True)
    #vote_target = models.ForeignKey(
    #    Player, on_delete=models.PROTECT, related_name="is_vote_target", null=True)
    # Indicate which speaker is the first speaker and which is the current speaker
    #first_speaker   = models.ForeignKey(Player, on_delete=models.PROTECT, related_name="is_first_speaker", null=True)
    #current_speaker = models.ForeignKey(Player, on_delete=models.PROTECT, related_name="is_current_speaker", null=True)
    # Indicate the current game step
    step            = models.CharField(max_length=30, choices=GameStep.choices(), default=GameStep.NONE)
    # Indicate if the game is over, False: wolves win, True: good people win, None: game is not over
    winning         = models.BooleanField(null=True, default=None)
    # Indicate if the speech is over, False: speech started but not end True: speech end, None: speech not started
    #speech_over = models.BooleanField(null=True, default=None)
    # Indicate if the game is over, False: vote started but not end, True: vote end, None: vote not started
    #vote_over = models.BooleanField(null=True, default=None)
    # null means the player who got assigned the character is out.
    wolves          = models.CharField(max_length=6, null=True, blank=True)
    seer            = models.CharField(max_length=6, null=True, blank=True)
    guard           = models.CharField(max_length=6, null=True, blank=True)
    villagers       = models.CharField(max_length=6, null=True, blank=True)
    vote            = models.CharField(max_length=6, null=True, blank=True)
    is_kill         = models.CharField(max_length=6, null=True, blank=True)

    trigger_id      = models.IntegerField(null=True)
    # Booleans indicating whose turn this is at night (tentative).
    #wolves_turn     = models.BooleanField(default=False)
    #seer_turn       = models.BooleanField(default=False)
    #guard_turn      = models.BooleanField(default=False)
