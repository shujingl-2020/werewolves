# Generated by Django 3.2.9 on 2021-11-15 03:42

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Game',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('step', models.CharField(default='NONE', max_length=200)),
                ('isEnd', models.BooleanField(default=True, max_length=200)),
                ('playersList', models.CharField(default='NONE', max_length=200)),
                ('neededPlayerNum', models.IntegerField(null=True)),
                ('gameMode', models.CharField(default='NONE', max_length=30)),
            ],
        ),
        migrations.CreateModel(
            name='Message',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.CharField(default='NONE', max_length=200)),
            ],
        ),
        migrations.CreateModel(
            name='Player',
            fields=[
                ('username', models.CharField(max_length=50, primary_key=True, serialize=False)),
                ('idInGame', models.IntegerField(null=True)),
                ('role', models.CharField(default='NONE', max_length=30)),
                ('status', models.CharField(default='NONE', max_length=30)),
                ('joinedWaitingRoomTimestamp', models.IntegerField(null=True)),
                ('alive', models.BooleanField(default=True)),
                ('context', models.CharField(default='NONE', max_length=200)),
                ('isHost', models.BooleanField(default=False)),
                ('game', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='werewolves.game')),
            ],
        ),
    ]