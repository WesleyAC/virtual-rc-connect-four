#!/usr/bin/env python3

# THIS CODE IS VERY HACKY

from actioncable.connection import Connection
from actioncable.subscription import Subscription

import requests

import time
import copy
import json

config = None
with open("config.json", "r") as config_file:
    config = json.loads(config_file.read())

cookie=config["cookie"]
csrf=config["csrf"]

connection = Connection(
    url="wss://recurse.rctogether.com/cable",
    origin="https://recurse.rctogether.com",
    cookie=cookie)
connection.connect()

gwc_subscription = Subscription(connection, identifier={"channel": "GridWorldChannel"})

all_people = {}

world = None
players = []
turn = 0

def gwc_on_receive(message):
    global world
    global players
    global all_people
    if message["type"] == "world":
        world = message["payload"]
    elif message["type"] == "entity" and message["payload"]["type"] == "Avatar":
        avatar_id = message["payload"]["id"]
        if "person_name" in message["payload"]:
            all_people[avatar_id] = message["payload"]["person_name"]
        x = message["payload"]["pos"]["x"]
        y = message["payload"]["pos"]["y"]
        d = message["payload"]["direction"]
        if y == region_y-1 and x >= region_x and x < region_x+region_w and d == "down":
            if len(players) < 2:
                players.append(avatar_id)
                typewriter(world, p_x[turn], p_y[turn], " " + all_people[avatar_id].split(" ")[0])
            if players[turn] == avatar_id:
                move(x-region_x)
    elif message["type"] == "entity" and message["payload"]["type"] == "Wall":
        x = message["payload"]["pos"]["x"]
        y = message["payload"]["pos"]["y"]
        c = message["payload"]["wall_text"]
        if x == status_x and y == status_y and (c == "r" or c == "R"):
            modify_status("⌛")
            reset_board()
            modify_status("")

gwc_subscription.on_receive(callback=gwc_on_receive)
gwc_subscription.create()

while world is None:
    time.sleep(0.05)

region_x = 3
region_y = 33
region_w = 7
region_h = 7

status_x = 2
status_y = 32

p_x = [1, 1]
p_y = [40, 41]

x = region_x
y = region_y
walls = [[world["entities"][f"{x+region_x},{y+region_y}"][0]["id"] for x in range(region_w)] for y in range(region_h)]

for person in filter(lambda x: x["type"] == "Avatar", map(lambda x: x[0], world["entities"].values())):
    all_people[person["id"]] = person["person_name"]

def modify_status(char):
    wall_id = world["entities"][f"{status_x},{status_y}"][0]["id"]
    _modify_wall(wall_id, char)

def modify_wall(walls, x, y, char):
    _modify_wall(walls[y][x], char)

def typewriter(world, x, y, text):
    for i,c in enumerate(text):
        xy = f"{x+i},{y}"
        if xy in world["entities"]:
            wall_id = world["entities"][xy][0]["id"]
            _modify_wall(wall_id, c)

def _modify_wall(wall_id, char):
    url = f"https://recurse.rctogether.com/walls/{wall_id}"
    headers = {
        "X-CSRF-Token": csrf,
        "Content-Type": "application/json",
        "Origin": "https://recurse.rctogether.com",
        "Referer": "https://recurse.rctogether.com/",
        "Host": "recurse.rctogether.com",
        "Cookie": cookie
    }
    payload = {"wall":{"wall_text": char}}
    r = requests.patch(url, headers=headers, json=payload)

old_board = None
board = None

def update_board(new_board):
    global old_board
    for y in range(region_h):
        for x in range(region_w):
            if old_board is None or old_board[y][x] != new_board[y][x]:
                modify_wall(walls, x, y, new_board[y][x])
    old_board = copy.deepcopy(board)

def reset_board():
    global board
    global old_board
    global turn
    global players
    old_board = None
    board = copy.deepcopy([[" " for _ in range(region_w)] for _ in range(region_h)])
    turn = 0
    players = copy.deepcopy([])
    update_board(board)
    typewriter(world, p_x[0], p_y[0], " "*10)
    typewriter(world, p_x[1], p_y[1], " "*10)

def move(x):
    global board
    global turn
    if check_win(board):
        return
    for i,row in enumerate(reversed(board)):
        if row[x] == " ":
            board[region_h-1-i][x] = "X" if turn == 0 else "O"
            turn = (turn+1)%2
            update_turn_pointer()
            update_board(board)
            winner = check_win(board)
            if check_win(board) is not None:
                typewriter(world, p_x[turn], p_y[turn], " ")
                typewriter(world, p_x[(turn+1)%2], p_y[(turn+1)%2], "✨")
            return

def update_turn_pointer():
    typewriter(world, p_x[turn], p_y[turn], "▶")
    typewriter(world, p_x[(turn+1)%2], p_y[(turn+1)%2], " ")

def check_win(board):
    for row in board:
        if "XXXX" in "".join(row):
            return "X"
        if "OOOO" in "".join(row):
            return "O"
    for x in range(len(board[0])):
        col = "".join(map(lambda row: row[x], board))
        if "XXXX" in col:
            return "X"
        if "OOOO" in col:
            return "O"
    for y in range(len(board) - 3):
        for x in range(len(board[0]) - 3):
            diag_right_win = check_diagonal_right(board, x, y)
            if diag_right_win:
                return diag_right_win
        for x in range(3, len(board[0])):
            diag_left_win = check_diagonal_left(board, x, y)
            if diag_left_win:
                return diag_left_win


def check_diagonal_right(board, start_x, start_y):
    coords = [(start_x + i, start_y + i) for i in range(4)]
    if all(board[x][y] == "X" for (x, y) in coords):
        return "X"
    if all(board[x][y] == "O" for (x, y) in coords):
        return "O"

def check_diagonal_left(board, start_x, start_y):
    coords = [(start_x - i, start_y + i) for i in range(4)]
    if all(board[x][y] == "X" for (x, y) in coords):
        return "X"
    if all(board[x][y] == "O" for (x, y) in coords):
        return "O"

while True:
    time.sleep(1)

gwc_subscription.remove()
connection.disconnect()
