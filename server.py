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
            self.path = self.path.split("?")[0]

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
            df_scores.score1.astype(int)
            df_scores.score2.astype(int)
            datetime_now = pd.datetime.now()

            player1 = form["player1"].value
            player2 = form["player2"].value
            player3 = form["player3"].value
            player4 = form["player4"].value
            score1 = int(form["score1"].value)
            score2 = int(form["score2"].value)

            players = []
            players.append(player1) if player1 != "NULL" else False
            players.append(player2) if player2 != "NULL" else False
            players.append(player3) if player3 != "NULL" else False
            players.append(player4) if player4 != "NULL" else False

            proceed = True

            # Some sanity checks
            if len(players) == 2 and player1 == "NULL" and player2 == "NULL":
                print("Aborting: one-sided kicker was provided")
                proceed = False
            if len(players) == 2 and player3 == "NULL" and player4 == "NULL":
                print("Aborting: one-sided kicker was provided")
                proceed = False
            if len(players) == 3:
                print("Aborting: three players match cannot be rated")
                proceed = False
            if len(players) == 0:
                print("Aborting: no player...")
                proceed = False
            if len(players) == 1:
                print("Aborting: only one player...")
                proceed = False
            if score1 == "0" and score2 == "0":
                print("Aborting: 0-0 match...")
                proceed = False

            if proceed:
                new_score_entry = {
                    "datetime": datetime_now,\
                    "player1": player1,  \
                    "player2": player2,  \
                    "player3": player3,  \
                    "player4": player4,  \
                    "score1" : score1,   \
                    "score2" : score2    \
                }

                scores = []
                scores.append(int(score1))
                scores.append(int(score2))

                df_scores.loc[len(df_scores)]=new_score_entry
                df_scores.to_csv("./scores.csv", sep=",", header=True, index=False, date_format="%Y-%m-%d %H:%M:%S")
            df_scores = df_scores.where((pd.notnull(df_scores)), 'NULL')
            dateparse = lambda x: pd.datetime.strptime(x, '%Y-%m-%d %H:%M:%S')
            df_elos = pd.DataFrame(columns=['datetime','match_number','player','elo'])

            df_players = pd.read_csv("./players.csv", names=["player"])

            for index, row in df_players.iterrows(): 
                new_elo_entry = {
                    "datetime":     pd.datetime.strptime("1970-01-01 00:00:00", '%Y-%m-%d %H:%M:%S'), \
                    "match_number": 0,      \
                    "player"  :     row[0], \
                    "elo"     :     1000    \
                }
                df_elos.loc[len(df_elos)]=new_elo_entry


            # Rating based on https://math.stackexchange.com/questions/838809/rating-system-for-2-vs-2-2-vs-1-and-1-vs-1-game
            for score_row in df_scores.itertuples():
                players = []
                elos = []
                scores = []
                players.append(score_row.player1) if score_row.player1 != 'NULL' else False
                players.append(score_row.player2) if score_row.player2 != 'NULL' else False
                players.append(score_row.player3) if score_row.player3 != 'NULL' else False
                players.append(score_row.player4) if score_row.player4 != 'NULL' else False
                match_datetime = score_row.datetime
                scores.append(score_row.score1) 
                scores.append(score_row.score2) 

                for player in players:
                    df_elos_player = df_elos[df_elos['player'] == player]
                    elo_values = df_elos_player[df_elos_player.index == df_elos_player.index.max()].elo.values
                    elo = int(elo_values[0]) if elo_values.size == 1 else 1000
                    elos.append(elo)

                updated_elos = []
                actual_score = scores[0] / (scores[0] + scores[1])

                if len(players) == 2:
                    expected_score = 1 / (1 + 10**((elos[1] - elos[0])/2000))
                    updated_elos.append(elos[0] + 5 * max(scores) * (actual_score - expected_score))
                    updated_elos.append(elos[1] + 5 * max(scores) * (expected_score - actual_score)) 
                else:
                    expected_score = 1 / (1 + 10**(((((elos[2] + elos[3]) / 2) - ((elos[0] + elos[1])) / 2)) / 2000))
                    updated_elos.append(elos[0] + 2.5 * max(scores) * (actual_score - expected_score))
                    updated_elos.append(elos[1] + 2.5 * max(scores) * (actual_score - expected_score))
                    updated_elos.append(elos[2] + 2.5 * max(scores) * (expected_score - actual_score)) 
                    updated_elos.append(elos[3] + 2.5 * max(scores) * (expected_score - actual_score)) 
                    
                for player,updated_elo in zip(players,updated_elos): 
                    new_elo_entry = {
                        "datetime":     match_datetime,     \
                        "match_number": score_row.Index + 1,\
                        "player"  :     player,             \
                        "elo"     :     int(updated_elo)    \
                    }

                    df_elos.loc[len(df_elos)]=new_elo_entry

                df_elos.to_csv("./elos.csv", sep=",", header=True, index=False, date_format="%Y-%m-%d %H:%M:%S")


            plt.style.use('fivethirtyeight')
            fig, ax = plt.subplots(figsize=(10,6))
           
            color_sequence = ['#1f77b4', '#aec7e8', '#ff7f0e', '#ffbb78', '#2ca02c',
                    '#98df8a', '#d62728', '#ff9896', '#9467bd', '#c5b0d5',
                    '#8c564b', '#c49c94', '#e377c2', '#f7b6d2', '#7f7f7f',
                    '#c7c7c7', '#bcbd22', '#dbdb8d', '#17becf', '#9edae5']

 
            for index,row in df_players.iterrows():
                if (df_elos.player == row.player).any():
                    df_elos[df_elos.player == row.player].plot(x="match_number", y="elo", color=color_sequence[index], ax=ax, label=row.player)

            plt.xlabel('Match number')
            lgd = plt.legend(loc='center left', bbox_to_anchor=(1, 0.5))
            plt.savefig("./elos.png", bbox_extra_artists=(lgd,), bbox_inches='tight')

            self.send_response(200)
            self.end_headers()
            return            
                        
try:
    #Create a web server and define the handler to manage the
    #incoming request
    server = HTTPServer(('', PORT_NUMBER), myHandler)
    print('Started httpserver on port ' , PORT_NUMBER)
    webbrowser.open("http://localhost:8080", new=0, autoraise=True)
    #Wait forever for incoming http requests
    server.serve_forever()

except KeyboardInterrupt:
    print('^C received, shutting down the web server')
    server.socket.close()
