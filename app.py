from flask import Flask, render_template, request, jsonify, session
import random
import json
import os
import time

app = Flask(__name__)
app.secret_key = os.urandom(24)

# 麻将牌定义
class Tile:
    def __init__(self, suit, value):
        self.suit = suit  # 牌的类型：筒、条、万、风、箭
        self.value = value  # 牌的数值

    def __str__(self):
        return f"{self.suit}_{self.value}"

    def to_dict(self):
        return {
            'suit': self.suit,
            'value': self.value,
            'id': f"{self.suit}_{self.value}"
        }

# 游戏类
class MahjongGame:
    def __init__(self):
        self.tiles = []  # 牌堆
        self.players = []  # 玩家
        self.current_player = 0  # 当前玩家索引
        self.game_state = "waiting"  # 游戏状态
        self.last_discarded = None  # 最后一张弃牌
        self.initialize_game()

    def initialize_game(self):
        # 创建牌堆
        self.create_tiles()
        # 洗牌
        self.shuffle_tiles()
        # 创建四个玩家
        self.players = [
            {"name": "玩家", "type": "human", "hand": [], "discarded": [], "ready": False},
            {"name": "东家", "type": "ai", "hand": [], "discarded": [], "ready": False},
            {"name": "南家", "type": "ai", "hand": [], "discarded": [], "ready": False},
            {"name": "西家", "type": "ai", "hand": [], "discarded": [], "ready": False}
        ]
        # 发牌
        self.deal_tiles()
        # 设置游戏状态
        self.game_state = "playing"
        self.current_player = 0

    def create_tiles(self):
        self.tiles = []
        # 筒、条、万，各9种，每种4张
        for suit in ["筒", "条", "万"]:
            for value in range(1, 10):
                for _ in range(4):
                    self.tiles.append(Tile(suit, value))

        # 风牌：东、南、西、北，每种4张
        for value in ["东", "南", "西", "北"]:
            for _ in range(4):
                self.tiles.append(Tile("风", value))

        # 箭牌：中、发、白，每种4张
        for value in ["中", "发", "白"]:
            for _ in range(4):
                self.tiles.append(Tile("箭", value))

    def shuffle_tiles(self):
        random.shuffle(self.tiles)

    def deal_tiles(self):
        # 每个玩家发13张牌
        for _ in range(13):
            for player in self.players:
                player["hand"].append(self.tiles.pop())

        # 给每个玩家的手牌排序
        for player in self.players:
            self.sort_hand(player["hand"])

    def sort_hand(self, hand):
        # 按照牌的类型和数值排序
        def sort_key(tile):
            suit_order = {"筒": 0, "条": 1, "万": 2, "风": 3, "箭": 4}

            if tile.suit in ["风", "箭"]:
                value_order = {"东": 1, "南": 2, "西": 3, "北": 4, "中": 1, "发": 2, "白": 3}
                return suit_order[tile.suit], value_order.get(tile.value, 0)
            else:
                return suit_order[tile.suit], tile.value

        hand.sort(key=sort_key)

    def draw_tile(self, player_idx):
        if not self.tiles:
            return None

        new_tile = self.tiles.pop()
        self.players[player_idx]["hand"].append(new_tile)
        self.sort_hand(self.players[player_idx]["hand"])
        return new_tile

    def discard_tile(self, player_idx, tile_idx):
        player = self.players[player_idx]
        discarded_tile = player["hand"].pop(tile_idx)
        player["discarded"].append(discarded_tile)
        self.last_discarded = discarded_tile
        return discarded_tile

    def ai_play(self, player_idx):
        # 简单AI逻辑：摸一张牌，然后随机丢弃一张
        self.draw_tile(player_idx)
        time.sleep(1)  # 添加延迟，让AI思考的过程更自然

        # 简单策略：丢弃最后一张牌（刚摸到的）
        discarded_idx = len(self.players[player_idx]["hand"]) - 1

        # 更复杂的策略可以在这里实现，例如：
        # 1. 优先保留成对的牌
        # 2. 优先保留连续的牌
        # 3. 丢弃孤立的牌

        return self.discard_tile(player_idx, discarded_idx)

    def next_turn(self):
        self.current_player = (self.current_player + 1) % 4

        # 如果是AI玩家的回合
        if self.players[self.current_player]["type"] == "ai":
            self.ai_play(self.current_player)
            self.next_turn()  # 继续到下一个玩家

    def get_game_state(self, player_idx=0):
        return {
            "game_state": self.game_state,
            "current_player": self.current_player,
            "player_hand": [tile.to_dict() for tile in self.players[player_idx]["hand"]],
            "player_discarded": [tile.to_dict() for tile in self.players[player_idx]["discarded"]],
            "opponents": [
                {
                    "name": player["name"],
                    "discarded": [tile.to_dict() for tile in player["discarded"]],
                    "hand_count": len(player["hand"])
                } for i, player in enumerate(self.players) if i != player_idx
            ],
            "tiles_left": len(self.tiles),
            "last_discarded": self.last_discarded.to_dict() if self.last_discarded else None
        }

# 初始化游戏
game = None

@app.route('/')
def index():
    return render_template('mahjong.html')

@app.route('/start_game', methods=['POST'])
def start_game():
    global game
    game = MahjongGame()
    return jsonify(game.get_game_state())

@app.route('/draw_tile', methods=['POST'])
def draw_tile():
    global game
    if game and game.game_state == "playing" and game.current_player == 0:
        tile = game.draw_tile(0)
        if tile:
            return jsonify({"success": True, "tile": tile.to_dict(), "game_state": game.get_game_state()})
        else:
            game.game_state = "draw"
            return jsonify({"success": False, "message": "没有牌了，游戏结束平局", "game_state": game.get_game_state()})
    return jsonify({"success": False, "message": "不是你的回合"})

@app.route('/discard_tile', methods=['POST'])
def discard_tile():
    global game
    if game and game.game_state == "playing" and game.current_player == 0:
        tile_idx = int(request.json.get('tile_idx'))
        game.discard_tile(0, tile_idx)
        game.next_turn()
        return jsonify({"success": True, "game_state": game.get_game_state()})
    return jsonify({"success": False, "message": "不是你的回合"})

if __name__ == '__main__':
    app.run(debug=True)