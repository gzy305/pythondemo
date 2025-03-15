from flask import Flask, render_template, jsonify, request, session
import random
import json

app = Flask(__name__)
app.secret_key = 'doudizhu_game_secret_key'

# 定义扑克牌
def create_deck():
    suits = ["♠", "♥", "♣", "♦"]
    values = ["3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A", "2"]
    cards = []

    # 生成扑克牌
    for value in values:
        for suit in suits:
            cards.append({"value": value, "suit": suit})

    # 添加大小王
    cards.append({"value": "Joker", "suit": "Small"})
    cards.append({"value": "Joker", "suit": "Big"})

    return cards

# 计算牌的权重，用于排序和比较
def card_weight(card):
    values = {"3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9, "10": 10,
              "J": 11, "Q": 12, "K": 13, "A": 14, "2": 15}

    if card["value"] == "Joker" and card["suit"] == "Small":
        return 16
    elif card["value"] == "Joker" and card["suit"] == "Big":
        return 17
    else:
        return values[card["value"]]

# 判断牌型
def identify_card_pattern(cards):
    if not cards:
        return "Invalid"

    # 单牌
    if len(cards) == 1:
        return "Single"

    # 对子
    if len(cards) == 2 and cards[0]["value"] == cards[1]["value"]:
        return "Pair"

    # 三张
    if len(cards) == 3 and cards[0]["value"] == cards[1]["value"] == cards[2]["value"]:
        return "Triplet"

    # 三带一
    if len(cards) == 4:
        values = [card["value"] for card in cards]
        for value in set(values):
            if values.count(value) == 3:
                return "Triplet_with_Single"

    # 三带对
    if len(cards) == 5:
        values = [card["value"] for card in cards]
        value_counts = {v: values.count(v) for v in set(values)}
        if 3 in value_counts.values() and 2 in value_counts.values():
            return "Triplet_with_Pair"

    # 炸弹
    if len(cards) == 4 and cards[0]["value"] == cards[1]["value"] == cards[2]["value"] == cards[3]["value"]:
        return "Bomb"

    # 王炸
    if len(cards) == 2 and "Joker" in [cards[0]["value"], cards[1]["value"]]:
        if "Small" in [cards[0]["suit"], cards[1]["suit"]] and "Big" in [cards[0]["suit"], cards[1]["suit"]]:
            return "Rocket"

    # 顺子 (5张或更多的连续单牌)
    if len(cards) >= 5:
        values = [card["value"] for card in cards]
        if "2" not in values and "Joker" not in values:  # 2和王不能加入顺子
            weights = [card_weight(card) for card in cards]
            weights.sort()
            if len(set(weights)) == len(weights):  # 确保没有重复
                is_consecutive = True
                for i in range(1, len(weights)):
                    if weights[i] != weights[i-1] + 1:
                        is_consecutive = False
                        break
                if is_consecutive:
                    return "Straight"

    # 其他牌型可以继续添加，如：连对、飞机等

    return "Invalid"

# 比较两手牌的大小
def compare_cards(previous_cards, current_cards):
    previous_pattern = identify_card_pattern(previous_cards)
    current_pattern = identify_card_pattern(current_cards)

    # 王炸最大
    if current_pattern == "Rocket":
        return True

    # 炸弹可以打任何非炸弹牌型
    if current_pattern == "Bomb" and previous_pattern != "Bomb" and previous_pattern != "Rocket":
        return True

    # 牌型相同，比较大小
    if current_pattern == previous_pattern:
        # 对于单牌、对子、三张、炸弹等简单牌型
        if current_pattern in ["Single", "Pair", "Triplet", "Bomb"]:
            return card_weight(current_cards[0]) > card_weight(previous_cards[0])

        # 对于顺子，比较最大牌
        if current_pattern == "Straight" and len(current_cards) == len(previous_cards):
            current_max = max([card_weight(card) for card in current_cards])
            previous_max = max([card_weight(card) for card in previous_cards])
            return current_max > previous_max

        # 其他复杂牌型可以继续添加

    return False

# 初始化游戏
@app.route('/init_game', methods=['POST'])
def init_game():
    deck = create_deck()
    random.shuffle(deck)

    # 分配牌给三个玩家
    player_hands = [[] for _ in range(3)]
    for i, card in enumerate(deck[:-3]):  # 留3张牌作为底牌
        player_hands[i % 3].append(card)

    # 底牌
    landlord_cards = deck[-3:]

    # 为每个玩家的牌排序
    for hand in player_hands:
        hand.sort(key=card_weight)

    # 保存游戏状态到会话
    session['player_hands'] = player_hands
    session['landlord_cards'] = landlord_cards
    session['current_player'] = 0  # 从第一个玩家开始
    session['landlord'] = None  # 地主未确定
    session['last_played'] = []  # 最后一次出的牌
    session['last_player'] = None  # 最后一次出牌的玩家
    session['pass_count'] = 0  # 连续不出的次数

    return jsonify({
        'player_hands': player_hands,
        'landlord_cards': landlord_cards,
        'current_player': 0
    })

# 叫地主
@app.route('/bid_landlord', methods=['POST'])
def bid_landlord():
    data = request.get_json()
    player_id = data.get('player_id')
    bid = data.get('bid')  # True表示叫地主，False表示不叫

    if session.get('landlord') is not None:
        return jsonify({'error': 'Landlord already determined'}), 400

    if bid:
        session['landlord'] = player_id
        # 地主获得底牌
        player_hands = session.get('player_hands')
        player_hands[player_id].extend(session.get('landlord_cards'))
        player_hands[player_id].sort(key=card_weight)
        session['player_hands'] = player_hands

        return jsonify({
            'landlord': player_id,
            'player_hands': player_hands,
            'landlord_cards': session.get('landlord_cards')
        })
    else:
        # 如果不叫地主，轮到下一个玩家
        next_player = (player_id + 1) % 3
        session['current_player'] = next_player

        return jsonify({
            'current_player': next_player
        })

# 出牌
@app.route('/play_cards', methods=['POST'])
def play_cards():
    data = request.get_json()
    player_id = data.get('player_id')
    card_indices = data.get('card_indices')  # 选择出的牌的索引

    if session.get('landlord') is None:
        return jsonify({'error': 'Landlord not determined yet'}), 400

    if player_id != session.get('current_player'):
        return jsonify({'error': 'Not your turn'}), 400

    player_hands = session.get('player_hands')
    player_hand = player_hands[player_id]

    # 如果选择不出牌
    if not card_indices:
        if session.get('last_player') == player_id:
            return jsonify({'error': 'You must play cards as you are the last player'}), 400

        # 记录连续不出的次数
        session['pass_count'] = session.get('pass_count', 0) + 1

        # 如果连续两人都不出，则最后出牌的玩家获得出牌权
        if session.get('pass_count') == 2:
            session['current_player'] = session.get('last_player')
            session['pass_count'] = 0
            session['last_played'] = []
        else:
            session['current_player'] = (player_id + 1) % 3

        return jsonify({
            'current_player': session.get('current_player'),
            'pass_count': session.get('pass_count')
        })

    # 获取玩家选择的牌
    selected_cards = [player_hand[i] for i in card_indices]

    # 验证牌型
    card_pattern = identify_card_pattern(selected_cards)
    if card_pattern == "Invalid":
        return jsonify({'error': 'Invalid card pattern'}), 400

    # 如果有人已经出过牌，需要比较大小
    last_played = session.get('last_played')
    if last_played and session.get('pass_count') < 2:
        if not compare_cards(last_played, selected_cards):
            return jsonify({'error': 'Your cards are not bigger than the last played cards'}), 400

    # 从玩家手牌中移除已出的牌
    for index in sorted(card_indices, reverse=True):
        player_hand.pop(index)

    # 更新游戏状态
    session['player_hands'] = player_hands
    session['last_played'] = selected_cards
    session['last_player'] = player_id
    session['pass_count'] = 0

    # 检查玩家是否已经出完牌
    if not player_hand:
        winner = "地主" if player_id == session.get('landlord') else "农民"
        return jsonify({
            'game_over': True,
            'winner': winner,
            'winner_id': player_id
        })

    # 轮到下一个玩家
    session['current_player'] = (player_id + 1) % 3

    return jsonify({
        'current_player': session.get('current_player'),
        'last_played': selected_cards,
        'player_hands': player_hands
    })

# 渲染游戏页面
@app.route('/')
def index():
    return render_template('doudizhu.html')

if __name__ == '__main__':
    app.run(debug=True)