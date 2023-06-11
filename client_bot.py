import sys
import grpc
import random
import mafia_pb2_grpc as mafia_pb2_grpc
import mafia_pb2 as mafia_pb2
from threading import Thread
from mimesis import Generic
from mimesis.locales import Locale

class UnaryClient:
    def __init__(self, host, port, players):
        self.host = host
        self.server_port = port
        self.chanel = grpc.insecure_channel(f'{self.host}:{self.server_port}')
        self.notifications = None
        self.stub = mafia_pb2_grpc.MafiaStub(self.chanel)
        self.room_users = []
        self.role = None
        self.players = players

    def subscribe_to_notifications(self):
        self.notifications = grpc.insecure_channel(f'{self.host}:{self.server_port}')
        try:
            for notification in self.stub.SubscribeToNotifications(
                            mafia_pb2.SubscribeRequest(name=self.name, game_id=self.game_id)):            
                if (notification.msg == f"__DEAD__ {self.name}"):
                    return
                elif notification.msg.split()[0] == "__DEAD__":
                    continue
                elif notification.msg.split()[0] == "__ADD__":
                    if notification.msg.split()[2] not in self.room_users:
                        self.room_users.append(notification.msg.split()[2])
                elif notification.msg.split()[0] == "__DISC__":
                    if notification.msg.split()[2] not in self.room_users:
                        self.room_users.remove(notification.msg.split()[2])
        except Exception as e:
            sys.exit()

    def run_night(self, city):
        if self.role is not None:
            if self.role == "mafia":
                res = random.randint(0, len(city)-1)
                self.stub.KillCitizen(mafia_pb2.KillCitizenRequest(game_id=self.game_id, name=city[res]))
            if self.role == "commissar":
                res = random.randint(0, len(city)-1)
                self.stub.CheckCitizen(mafia_pb2.CheckCitizenRequest(game_id=self.game_id, name=city[res]))
        response = self.stub.GetNightResult(mafia_pb2.GetNightResultRequest(game_id=self.game_id))
        if response.is_end:
            self.notifications.close()
            self.chanel.close()
            sys.exit()
        city = response.city
        if (self.role is not None) and (self.name not in city):
            self.role = None
        self.run_day(city)

    def run_day(self, city):
        response = None
        if self.role is not None:
            res = random.randint(0, len(city)-1)
            response = self.stub.CityVoting(mafia_pb2.CityVotingRequest(game_id=self.game_id, name=self.name, vote=city[res]))
        else:
            response = self.stub.CityVoting(mafia_pb2.CityVotingRequest(game_id=self.game_id, name=self.name, vote=self.name))
        if response.is_end:
            self.notifications.close()
            self.chanel.close()
            sys.exit()
        city = response.city
        if (self.role is not None) and (self.name not in city):
            self.role = None
        self.run_night(city)


    def register_user(self, name, game_id):
        self.name = name
        self.game_id = game_id
        response = self.stub.GoSingUp(mafia_pb2.SingUp(name=self.name, game_id=self.game_id))
        self.game_id = response.game_id
        new_thread = Thread(target=self.subscribe_to_notifications)
        new_thread.start()
        for player in response.players:
            self.room_users.append(player)
            if player == self.name:
                continue
        while True:
            if len(self.room_users) == self.players:
                response = self.stub.GetRole(mafia_pb2.SingUp(name=self.name, game_id=game_id))
                self.role = response.role
                self.run_day(self.room_users)

def go(game_id, host, port, players):
    client = UnaryClient(host, port, players)
    name = Generic(locale=Locale.EN).person.username()
    client.register_user(name, game_id)

if __name__ == "__main__":
    args = sys.argv
    if len(args) != 6:
        print("wrong number of arguments")
        sys.exit()
    bots = int(args[5])
    for i in range(bots):
        new_thread = Thread(target=go, args=(args[1], args[2], args[3], int(args[4])))
        new_thread.start()
    

