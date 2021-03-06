#!/usr/bin/env python

""" Copyright (C) 2012 mountainpenguin (pinguino.de.montana@googlemail.com)
    <http://github.com/mountainpenguin/pyrt>
    
    This file is part of pyRT.

    pyRT is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    pyRT is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with pyRT.  If not, see <http://www.gnu.org/licenses/>.
"""

from modules.irclib import irclib
from modules.irclib import ircbot
from modules import websocket
from modules import remotes
from modules import rpc
import multiprocessing
import os
import signal
import json
import re
import traceback

class IRCError(Exception):
    def __init__(self, value):
        self.val = value
    def __str__(self):
        return repr(self.val)
    def __repr__(self):
        return "IRCError: %s" % self.val
    
class SettingsError(Exception):
    def __init__(self, value):
        self.val = value
    def __str__(self):
        return repr(self.val)
    def __repr__(self):
        return "SettingsError: %s" % self.val

class _ModularBot(ircbot.SingleServerIRCBot):
    def shutdown(self, signalnum, stackframe):
        self.RPC.RPCCommand("log", "info", "IRCbot #%d: shutting down", self.PID)
        #if self.IS_REGISTERED:
        #    self.RPC.RPCCommand("deregister", self.config.name, self.PID)
        try:
            os.remove("proc/bots/%d.pid" % self.PID)
        except:
            pass

        self.die("Received SIGTERM")
        sys.exit(0)

    def update(self):
        response = self.RPC.RPCCommand("get_filters", self.config.name)
        if response:
            try:
                unjsoned = json.loads(response.response)
                if type(unjsoned) is dict:
                    self.config.filters = []
                    return
                newf = []
                for f in unjsoned:
                    # f = ( [pos, pos, ...], [neg, neg, ...] )
                    newf.append(([re.compile(x, re.I) for x in f[0]], [re.compile(y, re.I) for y in f[1]], f[2]))
                self.config.filters = newf
            except:
                self.RPC.RPCCommand("log", "error", "%s IRCBot (#%d): recieved filter list but not JSON-encoded (%r)", self.config.name, self.PID, response.__dict__)
                self.config.filters = []

    def __init__(self, net, nick, name, config, **kwargs):
        signal.signal(signal.SIGTERM, self.shutdown)
        self.IS_REGISTERED = False
        self.network = net
        self.nick = nick
        self.name = name
        self.config = config
        self.config.channel = kwargs["channel"]
        sock = websocket.create_connection(self.config.websocketURI)  
        self.PID = os.getpid()
        self.RPC = rpc.RPC(self.config.auth, self.config.name, sock)
        open("proc/bots/%d.pid" % self.PID, "w").write(str(self.PID))
        ircbot.SingleServerIRCBot.__init__(self, net, nick, name)

    def on_nicknameinuse(self, connection, event):
        self.RPC.RPCCommand("log", "error", "%s IRCbot (#%d): started up, but nick '%s' is in use!", self.config.name, self.PID, self.nick)
        self.shutdown(None, None)

    def on_erroneusnickname(self, connection, event):
        self.RPC.RPCCommand("log", "error", "%s IRCbot #%d: started up, but nick '%s' is invalid", self.config.name, self.PID, self.nick)
        self.shutdown(None, None)

    def on_welcome(self, connection, event):
        r = self.RPC.RPCCommand("register", self.PID, self.config.name)
        if not r.response:
            self.RPC.RPCCommand("log", "warning", "%s IRCbot (#%d): started up, but another bot is already registered!", self.config.name, self.PID)
            self.shutdown(None, None)
        self.IS_REGISTERED = True
        connection.join(self.config.channel)
        self.RPC.RPCCommand("log", "info", "%s IRCbot (#%d): connected to IRC successfully", self.config.name, self.PID)
        if hasattr(self.config, "startup"):
            for cmd in self.config.startup:
                try:
                    if "%(settings." in cmd:
                        replacements = re.findall("\%\(settings\.(.*?)\)s", cmd)
                        fmt = {}
                        for repl in replacements:
                            fmt["settings.%s" % (repl)] = self.config[repl]
                        cmd = cmd % fmt
                    connection.send_raw(cmd)
                except:
                    self.RPC.RPCCommand("publicLog", "warning", "%s IRCbot (#%d): command failed", self.config.name, self.PID)
                    self.RPC.RPCCommand("privateLog", "warning", "%s IRCbot (#%d): command '%s' failed\n%s", self.config.name, self.PID, cmd, traceback.format_exc())

    def on_pubmsg(self, connection, event):
        self.update()
        self.RPC.RPCCommand("publicLog", "debug", "%s IRCBot (#%d): message %r", self.config.name, self.PID, event.arguments()[0].encode("string_escape"))
        try:
            for pos, neg, sizelim in self.config.filters:
                contTrue = 0
                #all filters have to match
                for regex in pos:
                    #self.RPC.RPCCommand("publicLog", "debug", "%s IRCBot (#%d): checking +ve filter [%s]", self.config.name, self.PID, regex.pattern)
                    if not regex.search(event.arguments()[0]):
                        #self.RPC.RPCCommand("publicLog","debug", "%s IRCBot (#%d): +ve filter [%s] didn't match", self.config.name, self.PID, regex.pattern)
                        break
                    else:
                        contTrue += 1
                if contTrue != len(pos):
                    continue
                
                #one match = ignore message
                cont = True
                for regex in neg:
                    #self.RPC.RPCCommand("publicLog", "debug", "%s IRCBot (#%d): checking -ve filter [%s]", self.config.name, self.PID, regex.pattern)
                    if regex.search(event.arguments()[0]):
                        #self.RPC.RPCCommand("publicLog","debug", "%s IRCBot (#%d): negative filter [%s] matched", self.config.name, self.PID, regex.pattern)
                        cont = False
                        break
                    else:
                        cont = True
                
                if not cont:
                    continue
                
                #self.RPC.RPCCommand("publicLog", "debug", "%s IRCBot (#%d): checking matcher [%s]", self.config.name, self.PID, self.config.matcher.pattern)
                idmatch = self.config.matcher.search(event.arguments()[0])
                if idmatch:
                    torrentid = idmatch.group(1)
                    #self.RPC.RPCCommand("log", "debug", "%s IRCbot (#%d): got filter match in source handler '%s' for torrentid '%s'", self.config.name, self.PID, self.config.name, torrentid)
                    self.RPC.RPCCommand("fetchTorrent", name=self.config.name, torrentid=torrentid, sizelim=sizelim)
                    return
        except:
            traceback.print_exc()
            pass

    def on_ctcp(self, connection, event):
        pass

class Irc(object):
    def __init__(self, name, log, storage, websocketURI, auth):
        self.STORAGE = storage
        self.NAME = name
        #search for storage settings
        store = storage.getRemoteByName(name)
        siteMod = remotes.getSiteMod(name)
        if not store or not siteMod:
            raise SettingsError("Nothing is stored for name '%s'" % name)

        #network, channel, and port should be stored in 'siteMod'
        #nick should be stored in 'store'

        try:
            self.network = siteMod.IRC_NETWORK
            self.port = siteMod.IRC_PORT
            self.channel = siteMod.IRC_CHANNEL
            matcher = siteMod.IRC_MATCH
        except AttributeError:
            raise SettingsError("IRC methods are not defined for name '%s'" % name)

        if "nick" not in store:
            self.nick = "pyrtBot"
        else:
            self.nick = store.nick

        if hasattr(siteMod, "IRC_COMMANDS"):
            startup = siteMod.IRC_COMMANDS
        else:
            startup = []
        self.name = "pyrt"
        self.log = log
        self.options = store
        self.options.startup = startup
        self.options.websocketURI = websocketURI
        self.options.auth = auth
        self.options.matcher = matcher
        
    def startbot(self):
        bot = _ModularBot([(self.network, self.port)], self.nick, self.name, channel=self.channel, config=self.options)
        bot.start()

    def start(self):
        if not self.STORAGE.isBotActive(self.NAME):
            p = multiprocessing.Process(target=self.startbot)
            p.daemon = True
            p.start()
            signal.signal(signal.SIGCHLD, self.report)
            return p
        else:
            raise IRCError("A bot has already been started!")
        
    def report(self, signalnum, stackframe):
        procs = self.STORAGE.getAllProcs()
        remove = []
        for pid, d in procs.iteritems():
            name, proc = d
            if not proc.is_alive():
                proc.join(timeout=10)
                remove += [pid]
        for pid in remove:
            self.STORAGE.delProc(pid)
