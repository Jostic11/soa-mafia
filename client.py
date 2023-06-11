import sys
import grpc
import mafia_pb2_grpc as mafia_pb2_grpc
import mafia_pb2 as mafia_pb2
from simple_term_menu import TerminalMenu
from art import tprint
from threading import Thread

class UnaryClient:
    def __init__(self):
        self.host = "0.0.0.0"
        self.server_port = "8000"
        self.chanel = grpc.insecure_channel(f'{self.host}:{self.server_port}')
        self.stub = mafia_pb2_grpc.MafiaStub(self.chanel)
        self.room_users = []
        self.role = None

    def subscribe_to_notifications(self):
        self.notifications = grpc.insecure_channel(f'{self.host}:{self.server_port}')
        for notification in self.stub.SubscribeToNotifications(
                        mafia_pb2.SubscribeRequest(name=self.name, game_id=self.game_id)):            
            if (notification.msg == f"__DEAD__ {self.name}"):
                return
            if notification.msg.split()[0] == "__DEAD__":
                continue
            if notification.msg.split()[0] == "__ADD__":
                if notification.msg.split()[2] not in self.room_users:
                    self.room_users.append(notification.msg.split()[2])
            print(notification.msg)

    def disconect_game(self):
        print("You left the lobby")
        self.stub.DisconectRoom(mafia_pb2.SingUp(name=self.name, game_id=self.game_id))
        self.room_users.clear()

    def connect_game(self, game_id):
        response = self.stub.ConnectRoom(mafia_pb2.SingUp(name=self.name, game_id=game_id))
        self.room_users.append(self.name)
        self.game_id = response.game_id
        print(f"You have connected to the room {response.game_id}")

    def run_night(self, city):
        if self.role is not None:
            print("The city is falling asleep")
            if self.role == "mafia":
                print("Choose the player you want to kill:")
                menu = TerminalMenu(city)
                res = menu.show()
                self.stub.KillCitizen(mafia_pb2.KillCitizenRequest(game_id=self.game_id, name=city[res]))
            if self.role == "commissar":
                print("Select the player you would like to test:")
                menu = TerminalMenu(city)
                res = menu.show()
                self.stub.CheckCitizen(mafia_pb2.CheckCitizenRequest(game_id=self.game_id, name=city[res]))
            response = self.stub.GetNightResult(mafia_pb2.GetNightResultRequest(game_id=self.game_id))
            if response.is_end:
                tprint(f"{response.end}")
                sys.exit()
            city = response.city
            self.run_day(city)

    def run_day(self, city):
        if self.role is not None:
            print("The city is waking up")
            print("Vote for who you think is the mafia:")
            menu = TerminalMenu(city)
            res = menu.show()
            response = self.stub.CityVoting(mafia_pb2.CityVotingRequest(game_id=self.game_id, name=self.name, vote=city[res]))
            if response.is_end:
                tprint(f"{response.end}")
                sys.exit()
            city = response.city
            if self.name not in city:
                self.role = None
                print("You were killed by voting")
            self.run_night(city)


    def register_user(self, name, game_id):
        self.name = name
        self.game_id = game_id
        response = self.stub.GoSingUp(mafia_pb2.SingUp(name=self.name, game_id=self.game_id))
        self.game_id = response.game_id
        print(f"User has been added to the lobby {response.game_id}")
        new_thread = Thread(target=self.subscribe_to_notifications)
        new_thread.start()
        print("User is subscribed to lobby notifications")
        for player in response.players:
            self.room_users.append(player)
            if player == self.name:
                continue
            print(f"Player {player} already in the lobby")
        if len(self.room_users) < 4:
            print("After connecting 4 players, the game will automatically start")
        else:
            response = self.stub.GetRole(mafia_pb2.SingUp(name=self.name, game_id=game_id))
            self.role = response.role
            self.run_day(self.room_users)
        while True:
            if len(self.room_users) == 4:
                response = self.stub.GetRole(mafia_pb2.SingUp(name=self.name, game_id=game_id))
                self.role = response.role
                self.run_day(self.room_users)
            choice = ["List of participants in the room", "Change the room", "Exit the game", "Refresh"]
            menu = TerminalMenu(choice)
            res = menu.show()
            if res == 0:
                print(f"There are currently {len(self.room_users)} users in the lobby")
                for i in self.room_users:
                    print(i)
            elif res == 1:
                print("Enter the ID of the game you want to connect to, or leave this field empty, we will create a game for you")
                game_id = str(input())
                self.disconect_game()
                response = self.connect_game(game_id)
            elif res == 2:
                self.stub.DeadSignal(mafia_pb2.SingUp(name=self.name, game_id=game_id))
                print("You are leaving the game, goodbye!")
                self.disconect_game()
                new_thread.join()
                sys.exit()
            else:
                continue


if __name__ == "__main__":
    tprint("SOA-MAFIA")
    client = UnaryClient()
    print("Enter your name:")
    client.name = str(input())
    print("Enter the ID of the game you want to connect to, or leave this field empty, we will create a game for you")
    client.game_id = str(input())
    client.register_user(client.name, client.game_id)

