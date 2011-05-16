#!/usr/bin/env python

from modules import config, login           # 'real' modules
from modules import indexPage, detailPage   #pages

import cherrypy
import os

c = config.Config()
c.loadconfig()

global_config = {
    "server.socket_host" : str(c.get("host")),
    "server.socket_port" : c.get("port"),
}
app_config = {
    "/css" : {
        "tools.staticdir.on" : True,
        "tools.staticdir.root" : os.getcwd(),
        "tools.staticdir.dir" : "static/css/",
    },
    "/javascript" : {
        "tools.staticdir.on" : True,
        "tools.staticdir.root" : os.getcwd(),
        "tools.staticdir.dir" : "static/javascript",
    },
    "/images" : {
        "tools.staticdir.on" : True,
        "tools.staticdir.root" : os.getcwd(),
        "tools.staticdir.dir" : "static/images",
    }
}

class mainHandler:
    def index(self, password=None, view=None, sortby=None, reverse=None):
        #check cookies
        L = login.Login()
        client_cookie = cherrypy.request.cookie
        Lcheck = L.checkLogin(client_cookie)
        if not Lcheck and not password:
            return L.loginHTML()
        elif not Lcheck and password:
            #check password
            Pcheck = L.checkPassword(password)
            if Pcheck:
                #set a cookie
                cherrypy.response.cookie = L.sendCookie()
            else:
                return L.loginHTML("Incorrect Password")
                
        Index = indexPage.Index()
        return Index.index(password, view, sortby, reverse)
        
    index.exposed = True
    
    def detail(self, view=None, torrent_id=None):
        #check cookies
        L = login.Login()
        client_cookie = cherrypy.request.cookie
        Lcheck = L.checkLogin(client_cookie)
        if not Lcheck and not password:
            return L.loginHTML()
        elif not Lcheck and password:
            #check password
            Pcheck = L.checkPassword(password)
            if Pcheck:
                #set a cookie
                cherrypy.response.cookie = L.sendCookie()
            else:
                return L.loginHTML("Incorrect Password")
        
        Detail = detailPage.Detail()
        if not torrent_id:
            return "ERROR/Not Implemented"
        elif not view or view == "info":
            return Detail.main(torrent_id)
        elif view == "peers":
            return Detail.peers(torrent_id)
        elif view == "files":
            return Detail.files(torrent_id)
        elif view == "trackers":
            return Detail.trackers(torrent_id)
    detail.exposed = True

if __name__ == "__main__":
    cherrypy.config.update(global_config)
    cherrypy.quickstart(mainHandler(), config=app_config)