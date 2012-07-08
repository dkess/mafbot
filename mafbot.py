#!/usr/bin/env python
# MafBot by Nisani

import os
import sys
import time
import socket
import urllib
import random

if (len(sys.argv) == 1):
    print("No server specified.")
    exit()

class Utils:
    @classmethod
    def get_username(cls, message):
        return message[1:message.find("!")].lower()
    @classmethod
    def notify_user(cls, user, message):
        meta["sock"].send("NOTICE %s :%s\r\n" % (user, message))
    @classmethod
    def respond(cls, message):
        meta["sock"].send("PRIVMSG %s :%s: %s\r\n" % (meta["data"].split(' ')[2], meta["user"], message))
        print("Said: \"%s\"" % message)
    @classmethod
    def say(cls, message):
        meta["sock"].send("PRIVMSG %s :%s\r\n" % (meta["data"].split(' ')[2],message))

class Player:
    pass

pwfile = open('./nickserv_passwd')


meta = {}
meta["botname"]  = "MafBot"
meta["ircname"]  = "Nisani"
meta["passwd"]   = pwfile.read()
meta["data"]     = ""
meta["message"]  = ""
meta["user"]     = ""
meta["quotedburl"] = "http://awfulnet.org/quotes/index.php"
meta["server"]   = sys.argv[1]
meta["sock"]     = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
meta["channel"] = sys.argv[2]
meta["blockquoters"] = {}
meta["userinfo"] = {}

pwfile.closed

players = {}

###############
# Game states:
# 0 - No game
# 1 - Day
# 2 - Night
meta["gamestate"] = 0
meta["cycle"] = 0

#Load users
for user in [f for f in os.listdir("./") if os.path.isfile(os.path.join("./", f)) and f.endswith(".user")]:
    f = open("./%s" % user)
    meta["userinfo"][user[:-5]] = f.read()
    f.close()

##########
#COMMANDS
def add_(*arg):
    if len(arg) >= 1:
        info = ' '.join(arg)
        f = open("./%s.user" % meta["user"].lower(), 'w')
        f.write(info)
        f.close()
        meta["userinfo"][meta["user"].lower()] = info
def help_(*arg):
    if len(arg) == 0:
        Utils.respond("Commands: %s" % ', '.join([x for x in commands]))
        Utils.respond("say \""+meta["botname"]+" help <commandname>\" for help with a specific command.")
    else:
        target = arg[0].lower()
    if target == "add":
        Utils.notify_user(meta["user"], "Command `add <info>`: Used to store personal info.")
    if target == "help":
        Utils.notify_user(meta["user"], "Command `help [command]`: Displays help on a command. If no command is specified, displays command list.")
    if target == "info":
        Utils.notify_user(meta["user"], "Command `info <user>`: Displays personal info for <user>.")
    if target == "join":
        Utils.notify_user(meta["user"], "Command `join <#channel> [#channel] [#channel]...`: Tells %s to join all of the listed channels.")
def info_(*arg):
    if len(arg) != 0:
        who = arg[0].lower()
        if (who in meta["userinfo"]):
            Utils.notify_user(meta["user"], "%s: %s" % (who, meta["userinfo"][who]))
        else:
            Utils.notify_user(meta["user"], "Invalid target \"%s\"." % who)
def join_(*arg):
    # only add them to the player list if there is not a current game going on
    if meta["gamestate"] == 0:
        if meta["user"] in players:
            Utils.say(meta["user"] + ", you are already in the game!")
        else:
            print meta["user"], "has been added"
            Utils.say(meta["user"] + " has joined the game")
            players[meta["user"]] = Player()
            meta["sock"].send("MODE %s +v %s\r\n" % (meta["data"].split(' ')[2],meta["user"]))

def players_(*arg):
    Utils.respond(" ".join(players.keys()))

def changegame(state):
    meta["gamestate"] = state
    if state == 1:
        for p in players.keys():
            if players[p].alive == 1:
                meta["sock"].send("MODE %s +v %s\r\n" % (meta["data"].split(' ')[2],p))
            elif players[p].alive == -1:
                Utils.say("%s has died!" % p)
                players[p].alive = 0
        meta["cycle"] += 1
        Utils.say("It is now Day %d." % meta["cycle"])
    if state == 2:
        for p in players.keys():
            meta["sock"].send("MODE %s -v %s\r\n" % (meta["data"].split(' ')[2],p))
        Utils.say("It is now Night %d." % meta["cycle"])

def endgame():
    meta["gamestate"] = 0
    meta["sock"].send("MODE %s -m\r\n" % meta["data"].split(' ')[2])
    for p in players.keys():
        meta["sock"].send("MDOE %s -v %s\r\n" % (meta["data"].split(' ')[2],p))

voters = set()
min_voters = 2
min_players = 4
def start_(*arg):
    if(len(players) < min_players):
        Utils.say("You need at least 5 players to start a game!")
    else:
        voters.add(meta["user"])
        if len(voters) < min_voters:
            voters.add(meta["user"])
            Utils.say("%s wants to start, need %d more people" % (meta["user"],min_voters - len(voters)))
        else:
            Utils.say("Game is now starting!")
            Utils.say("Alerting players: %s" % " ".join(players.keys()))
            meta["sock"].send("MODE %s +m\r\n" % meta["data"].split(' ')[2])
            playernames = players.keys()
            random.shuffle(playernames)
            # Send out role PMs
            for p in list(enumerate(playernames)):
                if p[0] == 0:
                    players[p[1]].role = "Goon"
                    players[p[1]].alignment = "m"
                    Utils.notify_user(p[1], "You are a Mafia goon! Your goal is to outnumber the town.")
                else:
                    players[p[1]].role = "Townie"
                    players[p[1]].role = "t"
                    Utils.notify_user(p[1], "You are a vanilla Townie! Your goal is to eliminate the Mafia!")
                players[p[1]].alive = 1
            changegame(2)

def admineval(*arg):
    if meta["user"] == "nisani":
        Utils.say(eval(arg[0]))

def adminexec(*arg):
    print "executing", arg[0]
    exec arg[0]

commands = {"add":add_, "help":help_, "info":info_, "join":join_, "players": players_, "start": start_, "eval": admineval, "exec": adminexec}
#COMMANDS
##########

#Connect to IRC server
try:
    meta["sock"].connect((meta["server"], 6667))
except:
    print("\nERROR: Connection to %s could not be established." % meta["server"])
    exit()
print("\nConnection established with %s on port 6667." % meta["server"])

#Change nickname
meta["sock"].send("USER %s 0 * :%s\r\nNICK %s\r\n" % (meta["botname"], meta["ircname"], meta["botname"]))
#Main loop
while (1):
    try:
        meta["data"] = meta["sock"].recv(512)
        if (meta["data"] != ''):
            print(meta["data"])
        if (meta["data"][:5] == "PING "):
            meta["sock"].send("PONG "+meta["data"][5:]+"\r\n")
        if ("\nPING " in meta["data"]):
            meta["sock"].send("PONG "+meta["data"][meta["data"].find("\nPING ")+7:]+"\r\n")
        if (meta["data"].split(' ')[1] == "001"):
            meta["sock"].send("MODE "+meta["botname"]+" +B\r\n"+''.join(["JOIN %s\r\n" % meta["channel"]]))
            meta["sock"].send("PRIVMSG nickserv :identify %s\r\n" % meta["passwd"])
        #If receiving PRIVMSG from a user
        if (meta["data"].split(' ')[1] == "PRIVMSG"):
            meta["user"] = Utils.get_username(meta["data"])
            meta["message"] = meta["data"][meta["data"].find(":", 1)+1:].rstrip().split(' ')
            if meta["user"] in meta["blockquoters"]:
                if meta["message"][0] == "quoteend":
                    quote_(meta["blockquoters"][meta["user"]])
                    del meta["blockquoters"][meta["user"]]
                else:
                    meta["blockquoters"][meta["user"]] += ' '.join(meta["message"])+'\n'
            elif meta["message"][0].lower().startswith('!'):
                try:
                    commands[meta["message"][0][1:].lower()](*meta["message"][1:])
                except KeyError:
                    pass
        # if a user changes nick
        if (meta["data"].split(' ')[1] == "NICK"):
            print "detected nick change"
            try:
                players.remove(Utils.get_username(meta["data"]))
                print "adding player"
                players.add(meta["data"].split(' ')[2][1:])
            # If the player isn't in the playerlist, do nothing
            except KeyError:
                Utils.say("player not in game")
    except:
        pass
