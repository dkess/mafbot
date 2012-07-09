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
        meta["sock"].send("PRIVMSG %s :%s\r\n" % (meta["channel"],message))

class Player:
    target = ''
    voters = set()

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
            meta["sock"].send("MODE %s +v %s\r\n" % (meta["channel"],meta["user"]))

def players_(*arg):
    Utils.respond(" ".join(players.keys()))

def checkactions():
    print "checking"
    for p in players.keys():
        if players[p].alive:
            currenttarget = players[p].target
            if currenttarget:
                if players[p].role == "Goon":
                    try:
                        if players[currenttarget].alive == 1:
                            players[currenttarget].alive = 0
                        players[currenttarget].alive -= 1
                    except:
                        e = sys.exc_info()[0]
                        Utils.say(e)
            else:
                print "failed at", p
                return 0
    print "done"
    return 1

def changegame(state):
    meta["gamestate"] = state
    if state == 1:
        for p in players.keys():
            if players[p].alive == 1:
                meta["sock"].send("MODE %s +v %s\r\n" % (meta["channel"],p))
            elif players[p].alive < 0:
                Utils.say("%s has died!" % p)
                players[p].alive = 0
        meta["cycle"] += 1
        Utils.say("It is now Day %d." % meta["cycle"])
    if state == 2:
        for p in players.keys():
            meta["sock"].send("MODE %s -v %s\r\n" % (meta["channel"],p))
        Utils.say("It is now Night %d." % meta["cycle"])

def endgame():
    meta["gamestate"] = 0
    meta["sock"].send("MODE %s -m\r\n" % meta["channel"])
    for p in players.keys():
        meta["sock"].send("MDOE %s -v %s\r\n" % (meta["channel"],p))
    players = {}

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
            meta["sock"].send("MODE %s +m\r\n" % meta["channel"])
            playernames = players.keys()
            random.shuffle(playernames)
            # Send out role PMs
            for p in list(enumerate(playernames)):
                if p[0] == 0:
                    players[p[1]].role = "Goon"
                    players[p[1]].alignment = "m"
                    Utils.notify_user(p[1], "You are a Mafia goon! Your goal is to outnumber the town.")
                    Utils.notify_user(p[1], "To kill (during the night), PM %s with !kill <target>" % meta["botname"])
                    Utils.notify_user(p[1], "You *must* choose someone to kill every night")
                else:
                    players[p[1]].role = "Townie"
                    players[p[1]].alignment = "t"
                    Utils.notify_user(p[1], "You are a vanilla Townie! Your goal is to eliminate the Mafia!")
                    players[p[1]].target = meta["botname"]
                players[p[1]].alive = 1
            changegame(2)

def votecount_(*arg):
    for p in players.keys():
        if len(players[p].voters):
            Utils.say("%s: %s" % (p, ' '.join(players[p].voters)))

def admineval(*arg):
    #if meta["user"] == "nisani":
    Utils.say(eval(' '.join(arg)))

def adminexec(*arg):
    print "executing", arg[0]
    exec ' '.join(list(arg))

def vote_(*arg):
    pass

commands = {"add":add_, "help":help_, "info":info_, "join":join_, "players": players_, "start": start_, "eval": admineval, "exec": adminexec, "votecount": votecount_, "vote": vote_}
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
            if meta["message"][0].lower().startswith('!'):
                # Is the command an action?
                if meta["gamestate"] == 2:
                    if meta["message"][0][1:].lower() == 'kill':
                        if players[meta["user"]].alignment == 'm':
                            if meta["data"].split(' ')[4].rstrip().lower() in players.keys():
                                players[meta["user"]].target = meta["data"].split(' ')[4].rstrip()
                                meta["sock"].send("NOTICE %s :Action received!\r\n" % meta["user"])
                                if checkactions():
                                    changegame(1)
                            else:
                                meta["sock"].send("NOTICE %s :That player does not exist!\r\n" % meta["user"])
                elif meta["gamestate"] == 1:
                    if meta["message"][0][1:].lower() == 'vote':
                        if meta["data"].split(' ')[2][0] == '#':
                            try:
                                players[meta["message"][1]].voters.add(meta["user"])
                            except:
                                Utils.say(sys.exc_info())

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
