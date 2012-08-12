#!/usr/bin/env python
# MafBot by Nisani

import os
import sys
import time
import socket
import urllib
import random
import math
import traceback

if (len(sys.argv) == 1):
    print("No server specified.")
    exit()

class Utils:
    @classmethod
    def get_username(cls, message):
        return message[1:message.find("!")].lower()
    @classmethod
    def notify_user(cls, user, message):
        meta["sock"].send("PRIVMSG %s :%s\r\n" % (user, message))
    @classmethod
    def respond(cls, message):
        meta["sock"].send("PRIVMSG %s :%s\r\n" % (meta["data"].split(' ')[2], message))
        print("Said: \"%s\"" % message)
    @classmethod
    def say(cls, message):
        meta["sock"].send("PRIVMSG %s :%s\r\n" % (meta["channel"],message))

class Player:
    target = ''
    def __init__(self):
        self.voters = set()

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
meta["scumkp"] = 0
meta["nightkills"] = set()

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

def addvoice(target):
    if type(target) is list:
        meta["sock"].send("MODE %s +%s %s\r\n" % (meta["channel"],'v'*(len(target)),' '.join(target)))
    elif type(target) is str:
        meta["sock"].send("MODE %s +v %s\r\n" % (meta["channel"], target))

def joingame(user):
    global players
    if user in players:
        return False
    else:
        players[user] = Player()
        addvoice(user)
        return True

def alive(playerlist):
    o = []
    for p in playerlist.keys():
        if playerlist[p].alive == 1:
            o.append(p)
    return o

def checkactions():
    print "checking actions"
    for p in alive(players):
        if players[p].role == "Detective":
            if players[p].target:
                pass
            else:
                print "no dt check"
                return 0
    if len(meta["nightkills"]) < meta["scumkp"]:
        print "not enough kills"
        return 0
    print "done"
    return 1

def checkvotes():
    print "checking votes"
    print alive(players)
    for p in alive(players):
        # If the player has acquired simple majority
        print p+"'s voters:", len(players[p].voters), "amount needed:",math.ceil(float(len(alive(players)))/2)
        if len(players[p].voters) >= math.ceil(float(len(alive(players)))/2):
            return p
    return ''

def changegame(state):
    global players
    print "changing game", state
    meta["gamestate"] = state
    
    # reset vote counts
    for p in players:
        players[p].voters = set()

    # First check for win conditions, but only if the game is in progress
    if(state >= 0):
        scum = []
        town = []
        for p in alive(players):
            if players[p].alignment == 'm':
                scum += [p]
            else:
                town += [p]
        if scum:
            if len(scum) >= len(town):
                state = 0
                Utils.say("Mafia has won!")
                Utils.say("Congratulations to %s!" % ' '.join(scum))
            if scum == 1:
                meta["scumkp"] = 1
        else:
            state = 0
            Utils.say("Town has won!")
            Utils.say("Congratulations to %s!" % ' and '.join(town))

    if state == 1:
        meta["gamestate"] = 1
        print "going to day phase"
        # Give the detective the result
        for p in players:
            if players[p].role == "Detective":
                Utils.notify_user(p,"%s's role is %s" % (players[p].target, players[players[p].target].role))
                players[p].target = ''
        if len(meta["nightkills"]) > 1:
            playerstring = ''
            for p in meta["nightkills"]:
                playerstring += "%s the %s, " % (p, players[p].role)
                players[p].alive = 0
            meta["nightkills"] = set()
            Utils.say("%shave died!" % playerstring)
        else:
            target = meta["nightkills"].pop()
            Utils.say("%s the %s has died!" % (target, players[target].role))
            players[target].alive = 0
        meta["sock"].send("MODE %s +%s %s\r\n" % (meta["channel"],'v'*(len(alive(players))),' '.join(alive(players))))
        meta["cycle"] += 1
        Utils.say("It is now Day %d. With %d players it is %d to lynch." % (meta["cycle"], len(alive(players)),math.ceil(float(len(alive(players))))))
    if state == 2 or state == -1:
        if state == -1:
            meta["cycle"] = 0
        meta["gamestate"] = 2
        meta["sock"].send("MODE %s -%s %s\r\n" % (meta["channel"],'v'*len(players),' '.join(players.keys())))
        Utils.say("It is now Night %d." % meta["cycle"])
    if state == 0:
        meta["gamestate"] = 0
        meta["scumkp"] = 0
        meta["nightkills"] = set()
        print "ending game"
        meta["sock"].send("MODE %s -%s %s\r\n" % (meta["channel"], 'v'*len(players),' '.join(players.keys())))
        meta["sock"].send("MODE %s -m\r\n" % meta["channel"])
        players = {}

voters = set()
min_voters = 2
min_players = 4
def startgame(*arg):
    global players
    global voters
    voters = set()
    Utils.say("Game is now starting!")
    Utils.say("Alerting players: %s" % " ".join(players.keys()))
    meta["sock"].send("MODE %s +m\r\n" % meta["channel"])
    playernames = players.keys()
    random.shuffle(playernames)
    scum = []
    try:
        scum.append(playernames[0])
        meta["scumkp"] += 1
        scum.append(playernames[7])
        if len(playernames) > 8:
            meta["scumkp"] += 1
        scum.append(playernames[11])
    except IndexError:
        pass
    print("Mafia:", scum)
    # Send out role PMs
    playerlist = list(enumerate(playernames))
    for p in playerlist:
        if p[0] == 0 or p[0] == 7 or p[0] == 11:
            players[p[1]].role = "Goon"
            players[p[1]].alignment = "m"
            Utils.notify_user(p[1], "You are a Mafia goon! Your goal is to outnumber the town.")
            Utils.notify_user(p[1], "To kill (during the night), PM %s with !kill <target>" % meta["botname"])
            if len(scum) > 1:
                Utils.notify_user(p[1], "The first kills you or your teammates send in will be used-- discuss with your team first!")
                Utils.notify_user(p[1], "Your teammates are %s and you have %d killing power per night." % (' '.join(scum), meta["scumkp"]))
            else:
                Utils.notify_user(p[1], "You *must* choose someone to kill every night")
        elif p[0] == 8:
            players[p[1]].role = "Detective"
            players[p[1]].alignment = "t"
            Utils.notify_user(p[1], "You are a detective! Your goal is to eliminate the Mafia!")
            Utils.notify_user(p[1], "Each night you can investigate a player. You can check someone with /msg %s !check <playername>" % meta["botname"])
        else:
            players[p[1]].role = "Townie"
            players[p[1]].alignment = "t"
            Utils.notify_user(p[1], "You are a vanilla Townie! Your goal is to eliminate the Mafia!")
            players[p[1]].target = meta["botname"]
        players[p[1]].alive = 1
    changegame(-1)

def votecount():
    for p in players.keys():
        if len(players[p].voters):
            Utils.respond("%s: %s" % (p, ' '.join(players[p].voters)))

def modkill(target):
    try:
        players[target].alive = 0
        randomnumber = randint(0,2)
        if randomnumber == 0:
            Utils.say("%s has been struck by lightning!", target)
        elif randomnumber == 1:
            Utils.say("%s was attacked by bears!", target)
        elif randomnumber == 2:
            Utils.say("God came down and smit %s! Atheists: 0 Theists: 1", target)
    except:
        pass

def unvote(voter):
    for p in players.keys():
        players[p].voters.discard(voter)

def addvote(voter, votee):
    unvote(voter)
    if votee in alive(players):
        players[votee].voters.add(voter)
        return 1
    else:
        return 0

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
        #If a message is received
        if (meta["data"].split(' ')[1] == "PRIVMSG"):
            meta["user"] = Utils.get_username(meta["data"])
            user = Utils.get_username(meta["data"])
            meta["message"] = meta["data"][meta["data"].find(":", 1)+1:].rstrip().split(' ')
            message = meta["data"][meta["data"].find(":", 1)+1:].rstrip().split(' ')
            # Commands that can be sent in-channel or in a private message
            # !alive tells who is alive, !players shows all players including dead ones
            # Result is always sent as a private message to prevent everyone from being hilighted
            if message[0] == '!alive' and meta["gamestate"] != 0 and len(alive(players)):
                Utils.notify_user(user," ".join(alive(players)))
            if message[0] == '!players' and len(players):
                Utils.notify_user(user," ".join(players))
            if message[0] == '!votecount':
                votecount()
            if message[0] == '!eval' and user == "nisani":
                Utils.say(eval(' '.join(message[1:])))
            
            # Commands that can only be sent in channel
            if meta["data"].split(' ')[2] == meta["channel"]:
                if message[0] == '!join' and meta["gamestate"] == 0:
                    if joingame(user):
                        Utils.say(user + " has joined the game!")
                    else:
                        Utils.say(user + ", you are already in the game!")
                if message[0] == '!leave' and meta["gamestate"] == 0:
                    try:
                        del players[user]
                    except KeyError:
                        Utils.say("You can't leave unless you've joined!")
                
                elif message[0] == '!start' and meta["gamestate"] == 0:
                    if len(players) < 6:
                        Utils.say("You need at least 6 players to start a game!")
                    else:
                        voters.add(user)
                        if len(voters) <  min_voters:
                            Utils.say("%s wants to start, need %d more people" % (user,min_voters - len(voters)))
                        else:
                            startgame()

                elif message[0] == '!vote' and meta["gamestate"] == 1 and players[user].alive:
                    if addvote(user, message[1].lower()):
                        lynchtarget = checkvotes()
                        if lynchtarget:
                            print lynchtarget, " to be lynched"
                            players[lynchtarget].alive = 0
                            Utils.say("%s has been lynched!" % lynchtarget)
                            Utils.say("Their rolse was %s." % players[lynchtarget].role)
                            changegame(2)
                    else:
                        Utils.say("That player is not in the game!")

                elif message[0] == '!unvote' and meta["gamestate"] == 1:
                    unvote(user)
            else:
                # Commands that can only be sent through PMs (night actions)
                if meta["gamestate"] == 2:
                    if message[0].lower() == '!kill' and players[user].alignment == 'm' and players[user].alive:
                        if message[1].lower() in alive(players) and players[message[1].lower()].alignment != 'm':
                            meta["nightkills"].add(message[1].lower())
                            Utils.notify_user(user,"Action received-- %d KP left!" % (meta["scumkp"] - len(meta["nightkills"])))
                        else:
                            Utils.notify_user(user,"Invalid target!")
                
                    elif message[0].lower() == '!check' and players[user].role == "Detective":
                        if message[1].lower() in alive(players) and message[1].lower() != user:
                            players[user].target = message[1].lower()
                            Utils.notify_user(user,"Action received!")
                        else:
                            Utils.notify_user(user,"Invalid target!")
                    if checkactions():
                        changegame(1)

        # if a user changes nick
        if (meta["data"].split(' ')[1] == "NICK"):
            print "detected nick change"
            oldnick = Utils.get_username(meta["data"])
            newnick = meta["data"].split(' ')[2][1:].rstrip()
            try:
                del players[oldnick]
                players[newnick] = players[oldnick]
                for p in players:
                    if players[p].target == oldnick:
                        players[p].target = newnick
                    try:
                        players[p].remove(oldnick)
                        players[p].add(newnick)
                    except KeyError:
                        pass
                try:
                    meta["nightkills"].remove(oldnick)
                    meta["nightkills"].add(newnick)
                except KeyError:
                    pass
            # If the player isn't in the playerlist, do nothing
            except KeyError:
                pass
        # if someone leaves the channel
        if meta["data"].split(' ')[1] == "PART":
            try:
                del players[Utils.get_username(meta["data"])]
                print "deleted %s from the playerlist for leaving the channel" % Utils.get_username(meta["data"])
            except KeyError:
                pass
    except:
        print(sys.exc_info())
        traceback.print_stack()
