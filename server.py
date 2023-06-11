import logging
from concurrent import futures

import grpc
import mafia_pb2_grpc as mafia_pb2_grpc
import mafia_pb2 as mafia_pb2

logger = logging.getLogger(__name__)

class MafiaService(mafia_pb2_grpc.MafiaServicer):
    def __init__(self):
        self.users_room = {}
        self.users_notification = {}
        self.ready_players = {}
        self.game_id = 0
        self.notifications = {}
        self.inf = 1000000

    def SubscribeToNotifications(self, request, context):
        logger.log(level=logging.WARNING, msg=f"user {request.name} SubscribeToNotifications for room: {request.game_id}")
        while True:
            if (self.inf == self.users_notification[request.name]) or (self.users_notification[request.name] >= len(self.notifications[self.users_room[request.name]])):
                continue
            logger.log(level=logging.WARNING, msg=f"{self.inf} {self.users_notification[request.name]} {len(self.notifications[self.users_room[request.name]])}")
            logger.log(level=logging.WARNING, msg=f"{type(self.inf)} {type(self.users_notification[request.name])} {type(len(self.notifications[self.users_room[request.name]]))}")
            num = self.users_notification[request.name]
            notif = self.notifications[self.users_room[request.name]]
            if (len(notif[num]) == 3):
                if notif[num][2] == request.name:
                    yield mafia_pb2.SubscribeResponse(connecte=notif[num][0], 
                                                    name=notif[num][1], 
                                                    exite=mafia_pb2.Exite(dead=True, name=notif[num][2])
                    )
                    self.users_room.remove(request.name)
                    self.users_notification.remove(request.name)
            else:
                yield mafia_pb2.SubscribeResponse(connecte=notif[num][0], 
                                                name=notif[num][1], 
                                                exite=mafia_pb2.Exite(dead=False, name="")
                )
            self.users_notification[request.name] += 1

    def DeadSignal(self, request, context):
        self.notifications[self.users_room[request.name]].append([True, request.name, request.name])
        return mafia_pb2.Empty()

    def DisconectRoom(self, request, context):
        logger.log(level=logging.WARNING, msg=f"user {request.name} DisconectRoom {request.game_id}")
        self.users_notification[request.name] = self.inf
        self.ready_players[request.game_id].remove(request.name)
        self.notifications[request.game_id].append([False, request.name])
        return mafia_pb2.Empty()
    
    def ConnectRoom(self, request, context):
        logger.log(level=logging.WARNING, msg=f" ConnectRoom received")
        if (request.game_id.strip() == ""):
            self.game_id += 1
            request.game_id = str(self.game_id)
            logger.log(level=logging.WARNING, msg=f"SERVER: user {request.name} create the game {request.game_id}")
        else:
            logger.log(level=logging.WARNING, msg=f"SERVER: user {request.name} try to sing up in game {request.game_id}")
        if request.game_id in self.ready_players:
            self.ready_players[request.game_id].append(request.name)
            self.notifications[request.game_id].append([True, request.name])
        else:
            self.ready_players[request.game_id] = [request.name]
            self.notifications[request.game_id] = []
        self.users_room[request.name] = request.game_id
        self.users_notification[request.name] = len(self.notifications[request.game_id])
        return mafia_pb2.SingUpResponse(game_id=request.game_id, players=self.ready_players[request.game_id])

    def GoSingUp(self, request, context):
        logger.log(level=logging.WARNING, msg=f"user {request.name} GoSingUp received")
        if (request.game_id.strip() == ""):
            self.game_id += 1
            request.game_id = str(self.game_id)
            logger.log(level=logging.WARNING, msg=f"SERVER: user {request.name} create the game {request.game_id}")
        else:
            logger.log(level=logging.WARNING, msg=f"SERVER: user {request.name} try to sing up in game {request.game_id}")
        if request.game_id in self.ready_players:
            self.ready_players[request.game_id].append(request.name)
            self.notifications[request.game_id].append([True, request.name])
        else:
            self.ready_players[request.game_id] = [request.name]
            self.notifications[request.game_id] = []
        self.users_room[request.name] = request.game_id
        self.users_notification[request.name] = len(self.notifications[request.game_id])
        return mafia_pb2.SingUpResponse(game_id=request.game_id, players=self.ready_players[request.game_id])


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=5))
    mafia_pb2_grpc.add_MafiaServicer_to_server(MafiaService(), server)
    server.add_insecure_port('[::]:8000')
    server.start()
    server.wait_for_termination()


if __name__ == '__main__':
    serve()