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
        self.role

    def subscribe_to_notifications(self):
        self.notifications = grpc.insecure_channel(f'{self.host}:{self.server_port}')
        for notification in self.stub.SubscribeToNotifications(
                        mafia_pb2.SubscribeRequest(name=self.name, game_id=self.game_id)):
            if notification.exite.dead:
                return
            if notification.connecte:
                self.room_users.append(notification.name)
                print(f"User {notification.name} connected the game")
            else:
                if notification.name in self.room_users:
                    self.room_users.remove(notification.name)
                print(f"User {notification.name} disconected the game")

    def disconect_game(self):
        print("You left the lobby")
        self.stub.DisconectRoom(mafia_pb2.SingUp(name=self.name, game_id=self.game_id))
        self.room_users.clear()

    def connect_game(self, game_id):
        response = self.stub.ConnectRoom(mafia_pb2.SingUp(name=self.name, game_id=game_id))
        self.room_users.append(self.name)
        self.game_id = response.game_id
        print(f"You have connected to the room {response.game_id}")

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
        print("After connecting 4 players, the game will automatically start")
        while True:
            menu = TerminalMenu(["List of participants in the room", 
                                 "Change the room",
                                 "Exit the game"])
            res = menu.show()
            if res == 0:
                print(f"There are currently {len(self.room_users)} users in the lobby")
                for i in self.room_users:
                    print(i)
            elif res == 1:
                print("Enter the ID of the game you want to connect to, or leave this field empty, we will create a game for you")
                game_id = str(input())
                self.disconect_game()
                self.connect_game(game_id)
            else:
                self.stub.DeadSignal(mafia_pb2.SingUp(name=self.name, game_id=game_id))
                print("You are leaving the game, goodbye!")
                self.disconect_game()
                new_thread.join()
                sys.exit()


if __name__ == "__main__":
    tprint("SOA-MAFIA")
    client = UnaryClient()
    print("Enter your name:")
    client.name = str(input())
    print("Enter the ID of the game you want to connect to, or leave this field empty, we will create a game for you")
    client.game_id = str(input())
    client.register_user(client.name, client.game_id)

