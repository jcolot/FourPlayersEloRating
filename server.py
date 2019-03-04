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
            if score1 == "0" and score2 == "0":
                print("Aborting: 0-0 match...")
                return

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
            #df_scores.replace({pd.np.nan: 'NULL'})
            df_scores = df_scores.where((pd.notnull(df_scores)), 'NULL')
            dateparse = lambda x: pd.datetime.strptime(x, '%Y-%m-%d %H:%M:%S')
            df_elos = pd.DataFrame(columns=['datetime','match_number','player','elo'])

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

                print(players)
                print(scores)
                for player in players:
                    df_elos_player = df_elos[df_elos['player'] == player]
                    print(df_elos_player.head())
                    elo_values = df_elos_player[df_elos_player.index == df_elos_player.index.max()].elo.values
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
                    
                print("Player is " + players[1] + " " + str(elo) + " " + str(elos[1]) + " " +str(updated_elos[1]))
                for player,updated_elo in zip(players,updated_elos): 
                    print(player)
                    new_elo_entry = {
                        "datetime":     match_datetime,     \
                        "match_number": score_row.Index,    \
                        "player"  :     player,             \
                        "elo"     :     int(updated_elo)    \
                    }

                    df_elos.loc[len(df_elos)]=new_elo_entry

                df_elos.to_csv("./elos.csv", sep=",", header=True, index=False, date_format="%Y-%m-%d %H:%M:%S")

            df_players = pd.read_csv("./players.csv", names=["player"])

            fig, ax = plt.subplots(figsize=(8,6))
            
            #for index,row in df_players.iterrows():
            #    if (df_elos.player == row.player).any():
            #        df_elos_to_plot = df_elos[df_elos.player == row.player].groupby(by=df_elos.datetime.dt.date).max()
            #        df_elos_to_plot = df_elos_to_plot.drop(["player"], axis=1)
            #        df_elos_to_plot["datetime"] = df_elos_to_plot["datetime"].dt.date
            #        df_elos_to_plot = df_elos_to_plot[df_elos_to_plot.datetime != datetime_now.date()]
            #        df_elo_today = df_elos[df_elos.player == row.player]
            #        df_elo_today = df_elo_today[df_elo_today.datetime == df_elo_today.datetime.max()]
            #        df_elo_today["datetime"] = datetime_now
            #        df_elo_today["datetime"] = df_elo_today["datetime"].dt.date
            #        df_elo_today = df_elo_today.drop(["player"], axis=1)
            #        df_elos_to_plot = df_elos_to_plot.append(df_elo_today)
            #        df_elos_to_plot.plot(x="datetime", y="elo", ax=ax, label=row.player)
            #        print(df_elo_today.head(20))
            #        print(df_elos_to_plot.head(20))
            #        plt.legend()
            #plt.savefig("./elos.png")

            #df_elos.sort_values("datetime")

            for index,row in df_players.iterrows():
                if (df_elos.player == row.player).any():
                    #df_elos[df_elos.player == row.player].plot(use_index=True, y="elo", ax=ax, label=row.player)
                    df_elos[df_elos.player == row.player].plot(x="match_number", y="elo", ax=ax, label=row.player)
                    plt.legend()
            plt.savefig("./elos.png")

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