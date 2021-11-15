from django.db import models


class Game(models.Model):
    step = models.CharField(max_length=200, default="NONE")
    isEnd = models.BooleanField(max_length=200, default=True)
    # a string that stores all players' usernames, eg "a b c"
    playersList = models.CharField(max_length=200, default="NONE")
    neededPlayerNum = models.IntegerField(null=True)
    gameMode = models.CharField(max_length=30, default="NONE")  # tubian or tucheng 屠城或者屠边


class Player(models.Model):
    username = models.CharField(max_length=50, primary_key=True)
    game = models.ForeignKey(Game, on_delete=models.SET_NULL, null=True)
    idInGame = models.IntegerField(null=True)
    role = models.CharField(max_length=30, default="NONE")
    # offline, waiting, inGame
    status = models.CharField(max_length=30, default="NONE")
    joinedWaitingRoomTimestamp = models.IntegerField(null=True)
    alive = models.BooleanField(default=True)
    # should be a stringify dictionary to store different roles’ actions
    context = models.CharField(max_length=200, default="NONE")
    isHost = models.BooleanField(default=False)

    def __str__(self):
        return 'Player' + str(self.username) + ": " + "gameStatus: " + str(self.status)

class Message(models.Model):
    text = models.CharField(max_length=200, default="NONE")
