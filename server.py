import logging
import random
import copy
from concurrent import futures
from threading import Lock

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
        self.inf = -1
        self.games_role_map = {}
        self.games_role = {}
        self.games_vote = {}
        self.games_alive = {}
        self.games_ans = {}


    def GetNightResult(self, request, context):
        is_mafia_alive = False
        for i in self.games_alive[request.game_id]:
            if self.games_role_map[request.game_id][i] == "mafia":
                is_mafia_alive = True
        if not is_mafia_alive:
            return mafia_pb2.GetNightResultResponse(is_end=True, end="citizens won", city=self.games_alive[request.game_id])
        if len(self.games_alive[request.game_id]) <= 2:
            return mafia_pb2.GetNightResultResponse(is_end=True, end="the mafia won", city=self.games_alive[request.game_id])
        return mafia_pb2.GetNightResultResponse(is_end=False, end="", city=self.games_alive[request.game_id])


    def CheckCitizen(self, request, context):
        is_mafia = False
        if self.games_role_map[request.game_id][request.name] == "mafia":
            is_mafia = True
        if is_mafia:
            self.notifications[self.users_room[request.name]].append(f"The mafia is {request.name}")
        return mafia_pb2.Empty()

    def KillCitizen(self, request, context):
        self.notifications[self.users_room[request.name]].append(f"The mafia killed the user {request.name}")
        self.games_alive[request.game_id].remove(request.name)
        return mafia_pb2.Empty()

    def CityVoting(self, request, context):
        logger.log(level=logging.WARNING, msg=f"game: {request.game_id} user {request.name} vote for: {request.vote}")
        self.games_vote[request.game_id].append(request.vote)
        while True:
            if len(self.games_vote[request.game_id]) < len(self.games_alive[request.game_id]):
                continue
            lock = Lock()
            with lock:
                if len(self.games_vote[request.game_id]) > 0:
                    tmp = {}
                    for i in self.games_vote[request.game_id]:
                        if i in tmp:
                            tmp[i] += 1
                        else:
                            tmp[i] = 1
                    mmax = 0
                    self.games_ans[request.game_id] = ""
                    for name, num in tmp.items():
                        if mmax < num:
                            mmax = num
                            self.games_ans[request.game_id] = name
                    if mmax * 2 > len(self.games_vote[request.game_id]):
                        killed = self.games_ans[request.game_id]
                        self.games_alive[request.game_id].remove(killed)
                        self.notifications[self.users_room[request.name]].append(f"by voting, a player {self.games_ans[request.game_id]} was kicked out")
                    self.games_vote[request.game_id] = []

            if self.games_role_map[request.game_id][self.games_ans[request.game_id]] == "mafia":
                return mafia_pb2.CityVotingResponse(is_end=True, end="citizens won", city=self.games_alive[request.game_id])
            if len(self.games_alive[request.game_id]) <= 2:
                return mafia_pb2.CityVotingResponse(is_end=True, end="the mafia won", city=self.games_alive[request.game_id])
            return mafia_pb2.CityVotingResponse(is_end=False, end="", city=self.games_alive[request.game_id])

    def GetRole(self, request, context):
        logger.log(level=logging.WARNING, msg=f"user {request.name} GetRole, game: {request.game_id}")
        lock = Lock()
        with lock:
            if request.game_id not in self.games_role:
                self.games_role[request.game_id] = ["citizen", "citizen", "mafia", "commissar"]
                self.games_alive[request.game_id] = copy.deepcopy(self.ready_players[request.game_id])
                self.games_role_map[request.game_id] = {}
                random.shuffle(self.games_role[request.game_id])
            for i in range(len(self.ready_players[request.game_id])):
                self.games_role_map[request.game_id][self.ready_players[request.game_id][i]] = self.games_role[request.game_id][i]
                if request.name == self.ready_players[request.game_id][i]:
                    logger.log(level=logging.WARNING, msg=f"game: {request.game_id} user {request.name} get role: {self.games_role[request.game_id][i]}")
                    return mafia_pb2.GetRoleResponse(role=self.games_role[request.game_id][i])

    def SubscribeToNotifications(self, request, context):
        logger.log(level=logging.WARNING, msg=f"user {request.name} SubscribeToNotifications for room: {request.game_id}")
        while True:
            if (self.inf == self.users_notification[request.name]) or (self.users_notification[request.name] >= len(self.notifications[self.users_room[request.name]])):
                continue
            # logger.log(level=logging.WARNING, msg=f"{self.inf} {self.users_notification[request.name]} {len(self.notifications[self.users_room[request.name]])}")
            # logger.log(level=logging.WARNING, msg=f"{type(self.inf)} {type(self.users_notification[request.name])} {type(len(self.notifications[self.users_room[request.name]]))}")
            num = self.users_notification[request.name]
            notif = self.notifications[self.users_room[request.name]]
            yield mafia_pb2.SubscribeResponse(msg=notif[num])
            self.users_notification[request.name] += 1

    def DeadSignal(self, request, context):
        self.notifications[self.users_room[request.name]].append(f"__DEAD__ {request.name}")
        return mafia_pb2.Empty()
    
    def DisconectRoom(self, request, context):
        logger.log(level=logging.WARNING, msg=f"user {request.name} DisconectRoom {request.game_id}")
        self.users_notification[request.name] = self.inf
        self.ready_players[request.game_id].remove(request.name)
        self.notifications[request.game_id].append(f"__ADD__ User {request.name} disconnected the game")
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
            self.notifications[request.game_id].append(f"__ADD__ User {request.name} connected the game")
        else:
            self.ready_players[request.game_id] = [request.name]
            self.notifications[request.game_id] = []
            self.games_vote[request.game_id] = []
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
            self.notifications[request.game_id].append(f"__ADD__ User {request.name} connected the game")
        else:
            self.ready_players[request.game_id] = [request.name]
            self.notifications[request.game_id] = []
            self.games_vote[request.game_id] = []
        self.users_room[request.name] = request.game_id
        self.users_notification[request.name] = len(self.notifications[request.game_id])
        return mafia_pb2.SingUpResponse(game_id=request.game_id, players=self.ready_players[request.game_id])


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=12))
    mafia_pb2_grpc.add_MafiaServicer_to_server(MafiaService(), server)
    server.add_insecure_port('[::]:8000')
    server.start()
    server.wait_for_termination()


if __name__ == '__main__':
    serve()