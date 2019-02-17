#!/usr/bin/python
from http.server import BaseHTTPRequestHandler,HTTPServer
from os import curdir, sep
import cgi
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import webbrowser
import datetime as dt     
import matplotlib.pyplot as plt

PORT_NUMBER = 8080

#This class will handles any incoming request from
#the browser 
class myHandler(BaseHTTPRequestHandler):
    
    #Handler for the GET requests
    def do_GET(self):
        if self.path=="/":
            self.path="/index.html"

        try:
            #Check the file extension required and
            #set the right mime type

            sendReply = False
            if self.path.endswith(".html"):
                mimetype='text/html'
                sendReply = True
            if self.path.endswith(".png"):
                mimetype='image/png'
                sendReply = True
            if self.path.endswith(".jpg"):
                mimetype='image/jpg'
                sendReply = True
            if self.path.endswith(".gif"):
                mimetype='image/gif'
                sendReply = True
            if self.path.endswith(".js"):
                mimetype='application/javascript'
                sendReply = True
            if self.path.endswith(".css"):
                mimetype='text/css'
                sendReply = True
            if self.path.endswith(".csv"):
                mimetype='text/plain'
                sendReply = True


            if sendReply == True:
                #Open the static file requested and send it
                self.send_response(200)
                self.send_header('Content-type',mimetype)
                self.end_headers()
                if mimetype.startswith('image'):
                    f = open(curdir + sep + self.path, "rb")
                    self.wfile.write(f.read())
                else:
                    f = open(curdir + sep + self.path, "r") 
                    self.wfile.write(f.read().encode('utf-8'))
                f.close()
            return

        except IOError:
            self.send_error(404,'File Not Found: %s' % self.path)

    #Handler for the POST requests
    def do_POST(self):
        if self.path=="/send":
            form = cgi.FieldStorage(
                fp=self.rfile, 
                headers=self.headers,
                environ={'REQUEST_METHOD':'POST',
                         'CONTENT_TYPE':self.headers['Content-Type'],
            })

            df_scores = pd.read_csv("./scores.csv", header=0)
            datetime = pd.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            player1 = form["player1"].value
            player2 = form["player2"].value
            player3 = form["player3"].value
            player4 = form["player4"].value
            score1 = form["score1"].value
            score2 = form["score2"].value

            players = []
            players.append(player1) if player1 != "NULL" else False
            players.append(player2) if player2 != "NULL" else False
            players.append(player3) if player3 != "NULL" else False
            players.append(player4) if player4 != "NULL" else False


            # Some sanity checks
            if len(players) == 2 and player1 == "NULL" and player2 == "NULL":
                print("Aborting: one-sided kicker was provided")
                return
            if len(players) == 2 and player3 == "NULL" and player4 == "NULL":
                print("Aborting: one-sided kicker was provided")
                return
            if len(players) == 3:
                print("Aborting: three players match cannot be rated")
                return
            if len(players) == 0:
                print("Aborting: no player...")
                return
            if len(players) == 1:
                print("Aborting: only one player...")
                return
            if score1 == 0 and score2 == 0:
                print("Aborting: 0-0 match...")
                return

            new_score_entry = {
                "datetime": datetime,\
                "player1": player1,  \
                "player2": player2,  \
                "player3": player2,  \
                "player4": player2,  \
                "score1" : score1,   \
                "score2" : score2    \
            }

            scores = []
            scores.append(int(score1))
            scores.append(int(score2))

            df_scores.loc[len(df_scores)]=new_score_entry
            df_scores.to_csv("./scores.csv", sep=",", header=True, index=False)
            
            dateparse = lambda x: pd.datetime.strptime(x, '%Y-%m-%d %H:%M:%S')
            df_elos = pd.read_csv("./elos.csv", header=0, parse_dates=['datetime'], date_parser=dateparse)
        
            fig, axes = plt.subplots(nrows=1, ncols=1)
            #df_elos.loc[df_elos['player'] == "Julien"].plot(x='datetime')

            elos = []

            for player in players:
                elo_values = df_elos[(df_elos['datetime'] == df_elos['datetime'].max()) & (df_elos['player'] == player)].elo.values
                elo = int(elo_values[0]) if elo_values.size == 1 else 1000
                elos.append(elo)

            
            expected_scores = []
            updated_elos = []

            if len(players) == 2:
                expected_scores.append(1 / (1 + 10**((elos[1] - elos[0])/500)))
                expected_scores.append(1 / (1 + 10**((elos[0] - elos[1])/500)))
                if scores[0] > scores[1]:
                    updated_elos.append(elos[0] + 100 * ((max(scores) / (max(scores) + min(scores))) - expected_scores[0]))
                    updated_elos.append(elos[1] + 100 * (1 - (max(scores) / ((max(scores) + min(scores)))) - expected_scores[1])) 
                else:
                    updated_elos.append(elos[0] + 100 * ((1 - (max(scores) / ((max(scores) + min(scores)))) - expected_scores[0])))
                    updated_elos.append(elos[1] + 100 * ((max(scores) / (max(scores) + min(scores))) - expected_scores[1]))
            else:
                expected_scores.append(1 / (1 + 10**(((((elos[2] + elos[3]) / 2) - ((elos[0] + elos[1])) / 2)) / 500)))
                expected_scores.append(1 / (1 + 10**(((((elos[0] + elos[1]) / 2) - ((elos[2] + elos[3])) / 2)) / 500)))
                if scores[0] > scores[1]:
                    updated_elos.append(elos[0] + 100 * ((max(scores) / (max(scores) + min(scores))) - expected_scores[0]))
                    updated_elos.append(elos[1] + 100 * ((max(scores) / (max(scores) + min(scores))) - expected_scores[0]))
                    updated_elos.append(elos[2] + 100 * ((1 - (max(scores)/(max(scores) + min(scores)))) - expected_scores[1])) 
                    updated_elos.append(elos[3] + 100 * ((1 - (max(scores)/(max(scores) + min(scores)))) - expected_scores[1])) 
                else:
                    updated_elos.append(elos[0] + 100 * ((max(scores) / (max(scores) + min(scores))) - expected_scores[0]))
                    updated_elos.append(elos[1] + 100 * ((max(scores) / (max(scores) + min(scores))) - expected_scores[0]))
                    updated_elos.append(elos[2] + 100 * ((1 - (max(scores) / (max(scores) + min(scores)))) - expected_scores[1]))
                    updated_elos.append(elos[3] + 100 * ((1 - (max(scores) / (max(scores) + min(scores)))) - expected_scores[1]))
                
            for player,updated_elo in zip(players,updated_elos):

                new_elo_entry = {
                    "datetime": datetime,   \
                    "player"  : player,    \
                    "elo"     : int(updated_elo) \
                }

                df_elos.loc[len(df_elos)]=new_elo_entry

            df_elos.to_csv("./elos.csv", sep=",", header=True, index=False)
 
            plt.savefig('./elos.png')

            self.send_response(200)
            self.end_headers()
            return            
                        
try:
    #Create a web server and define the handler to manage the
    #incoming request
    server = HTTPServer(('', PORT_NUMBER), myHandler)
    print('Started httpserver on port ' , PORT_NUMBER)
    webbrowser.open("localhost:8080", new=0, autoraise=True)
    #Wait forever for incoming http requests
    server.serve_forever()

except KeyboardInterrupt:
    print('^C received, shutting down the web server')
    server.socket.close()
    

