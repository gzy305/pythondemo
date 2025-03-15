from flask import Flask, render_template, request, jsonify, session
import random
import json
import os
import time
import collections
import itertools

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
        self.last_action = None  # 最后一个动作
        self.waiting_for_action = False  # 是否等待玩家操作（碰、杠、胡）
        self.possible_actions = {}  # 可能的操作
        self.wall_count = 0  # 开杠次数，用于岭上开花
        self.last_drawn_tile = None  # 最后摸到的牌
        self.initialize_game()

    def initialize_game(self):
        # 创建牌堆
        self.create_tiles()
        # 洗牌
        self.shuffle_tiles()
        # 创建四个玩家
        self.players = [
            {
                "name": "玩家",
                "type": "human",
                "hand": [],
                "discarded": [],
                "ready": False,
                "melds": [],  # 已经组合的牌（碰、杠）
                "score": 0,   # 玩家分数
                "winning_hand": None,  # 胡牌时的牌型
                "is_waiting": False    # 是否听牌
            },
            {
                "name": "东家",
                "type": "ai",
                "hand": [],
                "discarded": [],
                "ready": False,
                "melds": [],
                "score": 0,
                "winning_hand": None,
                "is_waiting": False
            },
            {
                "name": "南家",
                "type": "ai",
                "hand": [],
                "discarded": [],
                "ready": False,
                "melds": [],
                "score": 0,
                "winning_hand": None,
                "is_waiting": False
            },
            {
                "name": "西家",
                "type": "ai",
                "hand": [],
                "discarded": [],
                "ready": False,
                "melds": [],
                "score": 0,
                "winning_hand": None,
                "is_waiting": False
            }
        ]
        # 发牌
        self.deal_tiles()
        # 设置游戏状态
        self.game_state = "playing"
        self.current_player = 0
        self.waiting_for_action = False
        self.possible_actions = {}
        self.wall_count = 0
        self.last_drawn_tile = None

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

    # 检查是否可以碰牌
    def can_pong(self, player_idx, discarded_tile):
        hand = self.players[player_idx]["hand"]
        count = sum(1 for tile in hand if tile.suit == discarded_tile.suit and tile.value == discarded_tile.value)
        return count >= 2

    # 检查是否可以杠牌
    def can_kong(self, player_idx, discarded_tile=None):
        hand = self.players[player_idx]["hand"]

        # 明杠（其他玩家打出的牌）
        if discarded_tile:
            count = sum(1 for tile in hand if tile.suit == discarded_tile.suit and tile.value == discarded_tile.value)
            return count >= 3

        # 暗杠（自己摸到的牌）
        counter = collections.Counter([(tile.suit, tile.value) for tile in hand])
        return 4 in counter.values()

    # 检查是否可以加杠（在碰牌基础上加一张）
    def can_add_kong(self, player_idx, new_tile):
        melds = self.players[player_idx]["melds"]
        for meld in melds:
            if meld["type"] == "pong":
                meld_tile = meld["tiles"][0]  # 碰牌组合中的一张牌
                if meld_tile.suit == new_tile.suit and meld_tile.value == new_tile.value:
                    return True
        return False

    # 检查是否能胡牌
    def can_win(self, player_idx, tile=None):
        player = self.players[player_idx]
        hand = player["hand"].copy()

        # 如果指定了牌，添加到手牌中检查
        if tile:
            hand.append(tile)

        # 计算手牌中每种牌的数量
        counter = collections.Counter([(t.suit, t.value) for t in hand])

        # 提取已有的碰、杠组合
        triplets = len([m for m in player["melds"] if m["type"] in ["pong", "kong"]])

        # 检查是否符合胡牌条件（基本的4组+1对将）
        return self.is_valid_hand(counter, triplets)

    # 验证手牌是否符合胡牌规则
    def is_valid_hand(self, counter, existing_triplets=0):
        # 总共需要4组+1对将
        # 已有的碰杠组合 + 手牌中还需要的组合数 = 4
        remaining_sets_needed = 4 - existing_triplets

        # 尝试找出所有可能的对子（将）
        pairs = [key for key, count in counter.items() if count >= 2]

        # 对每个可能的对子，检查剩余的牌是否能组成顺子或刻子
        for pair in pairs:
            # 创建一个新的计数器副本
            temp_counter = counter.copy()
            # 减去一个对子
            temp_counter[pair] -= 2

            # 如果能用剩余的牌组成所需数量的顺子或刻子
            if self.can_form_sets(temp_counter, remaining_sets_needed):
                return True

        return False

    # 检查是否能组成指定数量的顺子或刻子
    def can_form_sets(self, counter, sets_needed):
        if sets_needed == 0:
            # 检查是否所有牌都用完了
            return all(count == 0 for count in counter.values())

        # 尝试找出刻子（三张相同的牌）
        for key, count in list(counter.items()):
            if count >= 3:
                # 减去一个刻子
                counter_copy = counter.copy()
                counter_copy[key] -= 3

                # 递归检查剩余的牌
                if self.can_form_sets(counter_copy, sets_needed - 1):
                    return True

        # 尝试找出顺子（三张连续的牌）
        # 注意：顺子只能在筒、条、万中形成
        for suit in ["筒", "条", "万"]:
            for value in range(1, 8):  # 最大是7，因为需要连续3张
                if all((suit, value + i) in counter and counter[(suit, value + i)] > 0 for i in range(3)):
                    # 减去一个顺子
                    counter_copy = counter.copy()
                    for i in range(3):
                        counter_copy[(suit, value + i)] -= 1

                    # 递归检查剩余的牌
                    if self.can_form_sets(counter_copy, sets_needed - 1):
                        return True

        return False

    # 进行碰牌操作
    def do_pong(self, player_idx):
        # 从玩家手中移除两张相同的牌
        hand = self.players[player_idx]["hand"]
        matching_tiles = [tile for tile in hand
                          if tile.suit == self.last_discarded.suit and tile.value == self.last_discarded.value]

        # 移除两张牌
        for i in range(2):
            hand.remove(matching_tiles[i])

        # 创建碰牌组合
        pong_meld = {
            "type": "pong",
            "tiles": [matching_tiles[0], matching_tiles[1], self.last_discarded],
            "from_player": self.current_player
        }

        # 添加到玩家的组合中
        self.players[player_idx]["melds"].append(pong_meld)

        # 更新游戏状态
        self.waiting_for_action = False
        self.current_player = player_idx
        self.last_discarded = None

        return pong_meld

    # 进行明杠操作（他人打出的牌）
    def do_kong(self, player_idx):
        # 从玩家手中移除三张相同的牌
        hand = self.players[player_idx]["hand"]
        matching_tiles = [tile for tile in hand
                          if tile.suit == self.last_discarded.suit and tile.value == self.last_discarded.value]

        # 移除三张牌
        for i in range(3):
            hand.remove(matching_tiles[i])

        # 创建杠牌组合
        kong_meld = {
            "type": "kong",
            "tiles": matching_tiles + [self.last_discarded],
            "from_player": self.current_player,
            "is_concealed": False  # 明杠
        }

        # 添加到玩家的组合中
        self.players[player_idx]["melds"].append(kong_meld)

        # 更新游戏状态
        self.waiting_for_action = False
        self.current_player = player_idx
        self.wall_count += 1
        self.last_discarded = None

        # 补牌（从牌尾摸一张）
        self.draw_replacement_tile(player_idx)

        return kong_meld

    # 进行暗杠操作（自己手里的四张）
    def do_concealed_kong(self, player_idx, tile_key):
        hand = self.players[player_idx]["hand"]
        suit, value = tile_key

        # 找出四张相同的牌
        matching_tiles = [tile for tile in hand
                          if tile.suit == suit and tile.value == value]

        # 确保有四张
        if len(matching_tiles) != 4:
            return None

        # 从手牌中移除
        for tile in matching_tiles:
            hand.remove(tile)

        # 创建暗杠组合
        kong_meld = {
            "type": "kong",
            "tiles": matching_tiles,
            "from_player": None,
            "is_concealed": True  # 暗杠
        }

        # 添加到玩家的组合中
        self.players[player_idx]["melds"].append(kong_meld)

        # 补牌
        self.wall_count += 1
        self.draw_replacement_tile(player_idx)

        return kong_meld

    # 进行加杠操作
    def do_add_kong(self, player_idx, tile_idx):
        # 获取要加杠的牌
        tile = self.players[player_idx]["hand"][tile_idx]

        # 查找对应的碰牌组合
        for meld in self.players[player_idx]["melds"]:
            if (meld["type"] == "pong" and
                    meld["tiles"][0].suit == tile.suit and
                    meld["tiles"][0].value == tile.value):

                # 从手牌中移除这张牌
                self.players[player_idx]["hand"].pop(tile_idx)

                # 将碰牌组合升级为杠
                meld["type"] = "kong"
                meld["tiles"].append(tile)
                meld["is_concealed"] = False

                # 补牌
                self.wall_count += 1
                self.draw_replacement_tile(player_idx)

                return meld

        return None

    # 补牌（杠后摸牌）
    def draw_replacement_tile(self, player_idx):
        if not self.tiles:
            self.game_state = "draw"
            return None

        # 从牌尾摸一张
        new_tile = self.tiles.pop()
        self.players[player_idx]["hand"].append(new_tile)
        self.sort_hand(self.players[player_idx]["hand"])
        return new_tile

    # 进行胡牌操作
    def do_win(self, player_idx):
        player = self.players[player_idx]

        # 如果是自摸
        if player_idx == self.current_player:
            # 计算分数
            score = 10  # 基础分
            # 加上自摸额外分
            score += 5
            # 如果是杠上开花
            if self.last_action == "kong":
                score += 5

            player["score"] += score
            player["winning_hand"] = "自摸"

        # 如果是点炮
        else:
            # 计算分数
            score = 5  # 基础分
            player["score"] += score
            player["winning_hand"] = "点炮"

            # 对点炮者减分
            self.players[self.current_player]["score"] -= score

        # 更新游戏状态
        self.game_state = "win"
        self.waiting_for_action = False

        return {"winner": player_idx, "score": score}

    # 检查玩家可执行的操作
    def check_player_actions(self, player_idx):
        actions = {}

        # 如果有其他玩家打出的牌
        if self.last_discarded and self.current_player != player_idx:
            # 检查是否可以碰
            if self.can_pong(player_idx, self.last_discarded):
                actions["pong"] = True

            # 检查是否可以杠
            if self.can_kong(player_idx, self.last_discarded):
                actions["kong"] = True

            # 检查是否可以胡
            if self.can_win(player_idx, self.last_discarded):
                actions["win"] = True

        # 如果是玩家自己的回合且刚摸到牌
        elif self.current_player == player_idx and self.last_drawn_tile:
            # 检查是否可以暗杠
            if self.can_kong(player_idx):
                # 找出可以暗杠的牌
                hand = self.players[player_idx]["hand"]
                counter = collections.Counter([(tile.suit, tile.value) for tile in hand])
                kong_options = [key for key, count in counter.items() if count == 4]
                if kong_options:
                    actions["concealed_kong"] = kong_options

            # 检查是否可以加杠
            for i, tile in enumerate(self.players[player_idx]["hand"]):
                if self.can_add_kong(player_idx, tile):
                    if "add_kong" not in actions:
                        actions["add_kong"] = []
                    actions["add_kong"].append(i)

            # 检查是否可以自摸
            if self.can_win(player_idx):
                actions["self_win"] = True

        return actions

    def draw_tile(self, player_idx):
        if not self.tiles:
            self.game_state = "draw"
            return None

        new_tile = self.tiles.pop()
        self.players[player_idx]["hand"].append(new_tile)
        self.sort_hand(self.players[player_idx]["hand"])
        self.last_drawn_tile = new_tile
        self.last_action = "draw"

        # 检查玩家可执行的操作
        if player_idx == 0:  # 如果是人类玩家
            self.possible_actions = self.check_player_actions(player_idx)

        return new_tile

    def discard_tile(self, player_idx, tile_idx):
        player = self.players[player_idx]
        discarded_tile = player["hand"].pop(tile_idx)
        player["discarded"].append(discarded_tile)
        self.last_discarded = discarded_tile
        self.last_drawn_tile = None
        self.last_action = "discard"

        # 重置可能的操作
        self.possible_actions = {}

        # 检查其他玩家的可能操作
        for i, other_player in enumerate(self.players):
            if i != player_idx:
                actions = self.check_player_actions(i)
                if actions:
                    # 如果是人类玩家有操作
                    if i == 0 and other_player["type"] == "human":
                        self.waiting_for_action = True
                        self.possible_actions = actions
                    # AI玩家自动执行最优操作
                    elif other_player["type"] == "ai":
                        self.handle_ai_action(i, actions)

        return discarded_tile

    def handle_ai_action(self, ai_idx, actions):
        # AI决策优先级：胡 > 杠 > 碰 > 摸牌出牌
        if "win" in actions:
            time.sleep(1)  # 模拟思考
            self.do_win(ai_idx)
            return True

        if "kong" in actions:
            time.sleep(1)
            self.do_kong(ai_idx)
            return True

        if "pong" in actions:
            # 根据策略决定是否碰牌
            if self.ai_should_pong(ai_idx):
                time.sleep(1)
                self.do_pong(ai_idx)
                # AI出牌
                self.ai_discard(ai_idx)
                return True

        return False

    def ai_should_pong(self, ai_idx):
        # 简单策略：70%概率碰牌
        return random.random() < 0.7

    def ai_play(self, player_idx):
        # 检查是否有可执行的动作（针对上一家打出的牌）
        actions = self.check_player_actions(player_idx)
        if self.handle_ai_action(player_idx, actions):
            return

        # 没有特殊操作，正常摸牌
        drawn_tile = self.draw_tile(player_idx)
        if not drawn_tile or self.game_state != "playing":
            return

        time.sleep(0.8)  # 思考时间

        # 再次检查摸牌后的可执行动作
        actions = self.check_player_actions(player_idx)

        # 处理自摸、暗杠等操作
        if "self_win" in actions:
            self.do_win(player_idx)
            return

        if "concealed_kong" in actions:
            # 70%概率进行暗杠
            if random.random() < 0.7:
                self.do_concealed_kong(player_idx, actions["concealed_kong"][0])
                # 杠后出牌
                self.ai_discard(player_idx)
                return

        if "add_kong" in actions:
            # 80%概率进行加杠
            if random.random() < 0.8:
                self.do_add_kong(player_idx, actions["add_kong"][0])
                # 杠后出牌
                self.ai_discard(player_idx)
                return

        # 正常出牌
        self.ai_discard(player_idx)

    def ai_discard(self, ai_idx):
        # 改进的AI出牌策略
        hand = self.players[ai_idx]["hand"]
        if not hand:
            return None

        # 计算每种牌的数量
        counter = collections.Counter([(tile.suit, tile.value) for tile in hand])

        # 计算每张牌的价值
        tile_values = {}
        for i, tile in enumerate(hand):
            key = (tile.suit, tile.value)

            # 初始值
            value = 0

            # 成对/成组的牌更有价值
            if counter[key] == 2 or counter[key] == 3:
                value += 5 * counter[key]

            # 连续的牌更有价值（仅适用于筒、条、万）
            if tile.suit in ["筒", "条", "万"]:
                # 检查相邻的牌
                for offset in [-2, -1, 1, 2]:
                    neighbor_key = (tile.suit, tile.value + offset)
                    if neighbor_key in counter:
                        # 相邻牌价值更高
                        if abs(offset) == 1:
                            value += 3
                        else:
                            value += 1

            # 字牌、箭牌单独算价值
            if tile.suit in ["风", "箭"]:
                if counter[key] == 1:  # 单张字牌价值低
                    value -= 2
                else:  # 多张字牌价值高
                    value += 3 * counter[key]

            tile_values[i] = value

        # 选择价值最低的牌丢弃
        discard_idx = min(tile_values, key=tile_values.get)

        return self.discard_tile(ai_idx, discard_idx)

    def next_turn(self):
        # 如果正在等待玩家操作，不进入下一回合
        if self.waiting_for_action:
            return

        # 如果游戏结束，不进入下一回合
        if self.game_state != "playing":
            return

        self.current_player = (self.current_player + 1) % 4

        # 如果是AI玩家的回合
        if self.players[self.current_player]["type"] == "ai":
            self.ai_play(self.current_player)
            # 如果游戏还在进行，继续到下一个玩家
            if self.game_state == "playing" and not self.waiting_for_action:
                self.next_turn()

    def get_game_state(self, player_idx=0):
        return {
            "game_state": self.game_state,
            "current_player": self.current_player,
            "player_hand": [tile.to_dict() for tile in self.players[player_idx]["hand"]],
            "player_discarded": [tile.to_dict() for tile in self.players[player_idx]["discarded"]],
            "player_melds": [
                {
                    "type": meld["type"],
                    "tiles": [tile.to_dict() for tile in meld["tiles"]],
                    "from_player": meld["from_player"],
                    "is_concealed": meld.get("is_concealed", False)
                } for meld in self.players[player_idx]["melds"]
            ],
            "player_score": self.players[player_idx]["score"],
            "player_winning_hand": self.players[player_idx]["winning_hand"],
            "opponents": [
                {
                    "name": player["name"],
                    "discarded": [tile.to_dict() for tile in player["discarded"]],
                    "hand_count": len(player["hand"]),
                    "melds": [
                        {
                            "type": meld["type"],
                            "tiles": [tile.to_dict() for tile in meld["tiles"]],
                            "from_player": meld["from_player"],
                            "is_concealed": meld.get("is_concealed", False)
                        } for meld in player["melds"]
                    ],
                    "score": player["score"],
                    "winning_hand": player["winning_hand"]
                } for i, player in enumerate(self.players) if i != player_idx
            ],
            "tiles_left": len(self.tiles),
            "last_discarded": self.last_discarded.to_dict() if self.last_discarded else None,
            "possible_actions": self.possible_actions if player_idx == 0 else {},
            "waiting_for_action": self.waiting_for_action
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
    if not game:
        return jsonify({"success": False, "message": "游戏未开始"})

    if game.game_state != "playing":
        return jsonify({"success": False, "message": "游戏已结束", "game_state": game.get_game_state()})

    if game.current_player != 0:
        return jsonify({"success": False, "message": "不是你的回合"})

    if game.waiting_for_action:
        return jsonify({"success": False, "message": "请先执行操作（碰、杠、胡）", "game_state": game.get_game_state()})

    tile = game.draw_tile(0)
    if tile:
        return jsonify({
            "success": True,
            "tile": tile.to_dict(),
            "game_state": game.get_game_state(),
            "possible_actions": game.possible_actions
        })
    else:
        game.game_state = "draw"
        return jsonify({
            "success": False,
            "message": "没有牌了，游戏结束平局",
            "game_state": game.get_game_state()
        })

@app.route('/discard_tile', methods=['POST'])
def discard_tile():
    global game
    if not game:
        return jsonify({"success": False, "message": "游戏未开始"})

    if game.game_state != "playing":
        return jsonify({"success": False, "message": "游戏已结束", "game_state": game.get_game_state()})

    if game.current_player != 0:
        return jsonify({"success": False, "message": "不是你的回合"})

    tile_idx = int(request.json.get('tile_idx'))
    game.discard_tile(0, tile_idx)

    # 如果没有等待玩家操作，进入下一回合
    if not game.waiting_for_action:
        game.next_turn()

    return jsonify({
        "success": True,
        "game_state": game.get_game_state(),
        "possible_actions": game.possible_actions
    })

@app.route('/pong', methods=['POST'])
def pong():
    global game
    if not game or game.game_state != "playing" or not game.waiting_for_action:
        return jsonify({"success": False, "message": "无法进行碰牌操作"})

    if "pong" not in game.possible_actions:
        return jsonify({"success": False, "message": "无法碰牌"})

    meld = game.do_pong(0)

    return jsonify({
        "success": True,
        "meld": {
            "type": meld["type"],
            "tiles": [tile.to_dict() for tile in meld["tiles"]]
        },
        "game_state": game.get_game_state()
    })

@app.route('/kong', methods=['POST'])
def kong():
    global game
    if not game or game.game_state != "playing":
        return jsonify({"success": False, "message": "无法进行杠牌操作"})

    # 明杠（其他玩家打出的牌）
    if game.waiting_for_action and "kong" in game.possible_actions:
        meld = game.do_kong(0)

        return jsonify({
            "success": True,
            "meld": {
                "type": meld["type"],
                "tiles": [tile.to_dict() for tile in meld["tiles"]],
                "is_concealed": meld["is_concealed"]
            },
            "game_state": game.get_game_state()
        })

    # 暗杠（自己手里的四张）
    if game.current_player == 0 and "concealed_kong" in game.possible_actions:
        tile_key = request.json.get('tile_key')
        # 将字符串键转换为元组
        suit, value = tile_key.split(',')
        if value.isdigit():
            value = int(value)
        meld = game.do_concealed_kong(0, (suit, value))

        if meld:
            return jsonify({
                "success": True,
                "meld": {
                    "type": meld["type"],
                    "tiles": [tile.to_dict() for tile in meld["tiles"]],
                    "is_concealed": meld["is_concealed"]
                },
                "game_state": game.get_game_state()
            })

    # 加杠
    if game.current_player == 0 and "add_kong" in game.possible_actions:
        tile_idx = int(request.json.get('tile_idx'))
        meld = game.do_add_kong(0, tile_idx)

        if meld:
            return jsonify({
                "success": True,
                "meld": {
                    "type": meld["type"],
                    "tiles": [tile.to_dict() for tile in meld["tiles"]],
                    "is_concealed": meld["is_concealed"]
                },
                "game_state": game.get_game_state()
            })

    return jsonify({"success": False, "message": "无法杠牌"})

@app.route('/win', methods=['POST'])
def win():
    global game
    if not game or game.game_state != "playing":
        return jsonify({"success": False, "message": "无法胡牌"})

    # 他人点炮
    if game.waiting_for_action and "win" in game.possible_actions:
        result = game.do_win(0)

        return jsonify({
            "success": True,
            "result": result,
            "game_state": game.get_game_state()
        })

    # 自摸
    if game.current_player == 0 and "self_win" in game.possible_actions:
        result = game.do_win(0)

        return jsonify({
            "success": True,
            "result": result,
            "game_state": game.get_game_state()
        })

    return jsonify({"success": False, "message": "无法胡牌"})

@app.route('/pass_action', methods=['POST'])
def pass_action():
    global game
    if not game or game.game_state != "playing" or not game.waiting_for_action:
        return jsonify({"success": False, "message": "无操作可跳过"})

    # 重置等待状态
    game.waiting_for_action = False
    game.possible_actions = {}

    # 进入下一回合
    game.next_turn()

    return jsonify({
        "success": True,
        "game_state": game.get_game_state()
    })

if __name__ == '__main__':
    app.run(debug=True)