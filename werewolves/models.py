from django.db import models
from enum import Enum

# A Player can have four different roles, plus one unassigned:
class PlayerRole(Enum):
    VILLAGER = "VILLAGER"
    WOLF     = "WOLF"
    WITCH    = "WITCH"
    GUARD    = "GUARD"
    NONE     = "NOT ASSIGNED"

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
    username = models.CharField(max_length=30)
    role     = models.CharField(max_length=30, choices=PlayerRole.choices())
    status   = models.CharField(max_length=30, choices=PlayerStatus.choices())
    skill1   = models.CharField(max_length=30, null=True)
    skill2   = models.CharField(max_length=30, null=True)
    vote     = models.ForeignKey('self', on_delete=models.CASCADE)
    # TODO: Tentative field, indicate whether a player is making a speech or not
    speech   = models.BooleanField(default=False)

    def __str__(self):
        return 'Player(' + self.username + ')' + self.role

class GameStatus(models.Model):
    # False means night, True means day.
    night           = models.BooleanField(default=False) 
    # Target player's id, null means the wolves haven't decided yet.
    target          = models.IntegerField(null=True)
    # Indicates whether it is time for a character to use skill.
    # null means the player who got assigned the character is out.
    wolves          = models.ForeignKey(Player, on_delete=models.PROTECT, related_name="is_wolf", null=True)
    witch           = models.ForeignKey(Player, on_delete=models.PROTECT, related_name="is_witch", null=True)
    guard           = models.ForeignKey(Player, on_delete=models.PROTECT, related_name="is_guard", null=True)
    villagers       = models.ForeignKey(Player, on_delete=models.PROTECT, related_name="is_villager", null=True)
    # Booleans indicating whose turn this is at night (tentative).
    wolves_turn     = models.BooleanField(default=False)
    witch_turn      = models.BooleanField(default=False)
    guard_turn      = models.BooleanField(default=False)

