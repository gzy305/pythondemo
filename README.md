# 中国麻将游戏

一个基于Python Flask和JavaScript制作的中国麻将单机游戏，支持人机对战、碰杠胡等规则，具有美观的界面和智能的AI对手。


## 功能特点

- **完整的麻将规则**：
  - 支持碰牌、杠牌（明杠、暗杠、加杠）和胡牌
  - 流局判定
  - 计分系统
  
- **智能AI对手**：
  - 基于策略的AI决策系统
  - AI能够进行碰、杠、胡等操作
  - 优化的出牌算法，模拟真实玩家策略
  
- **美观的用户界面**：
  - 清晰的游戏布局与分区
  - 不同类型牌的颜色区分（筒、条、万、风、箭）
  - 动画和过渡效果
  - 符合中国传统麻将的视觉风格
  
- **游戏体验增强**：
  - 音效反馈系统
  - 按键快捷操作
  - 提示系统
  - 胡牌动画

## 安装与运行

### 前提条件

- Python 3.6+
- Flask

### 安装步骤

1. 克隆仓库到本地：
   ```bash
   git clone https://github.com/your-username/chinese-mahjong.git
   cd chinese-mahjong
   ```

2. 安装所需依赖：
   ```bash
   pip install flask
   ```

3. 创建文件结构：
   ```
   chinese-mahjong/
   ├── app.py
   ├── templates/
   │   └── mahjong.html
   └── static/
       └── sounds/
           ├── draw.mp3
           ├── discard.mp3
           ├── pong.mp3
           ├── kong.mp3
           └── win.mp3
   ```

4. 将代码文件放入对应位置：
   - `app.py` - 主Python程序
   - `templates/mahjong.html` - HTML界面
   - 在static/sounds目录中添加所需音效文件

5. 运行游戏：
   ```bash
   python app.py
   ```

6. 在浏览器中访问：
   ```
   http://127.0.0.1:5000/
   ```

## 游戏玩法

### 基本规则

1. **游戏开始**：点击"开始游戏"按钮，系统自动洗牌并发牌。
2. **摸牌**：点击"摸牌"按钮摸一张牌。
3. **出牌**：选择一张手牌，然后点击"出牌"按钮。
4. **特殊操作**：
   - **碰牌**：当其他玩家打出的牌可以与你手中的两张相同牌组成"碰"时，可以点击"碰"按钮。
   - **杠牌**：
     - **明杠**：当其他玩家打出的牌可以与你手中的三张相同牌组成"杠"时，可以点击"杠"按钮。
     - **暗杠**：当你手中有四张相同的牌时，可以进行暗杠。
     - **加杠**：当你已经碰过一种牌，后来又摸到了第四张时，可以进行加杠。
   - **胡牌**：当你的牌满足胡牌条件时，可以点击"胡"按钮。

### 快捷键

- **空格**：摸牌
- **回车**：出牌
- **P**：碰牌
- **K**：杠牌
- **H**：胡牌
- **ESC**：跳过操作（过）
- **M**：音效静音/取消静音

## 技术栈

- **后端**：Python Flask
- **前端**：HTML, CSS, JavaScript
- **通信**：RESTful API
- **AI算法**：基于策略的决策系统

## 文件结构

```
chinese-mahjong/
├── app.py               # Flask后端，游戏逻辑
├── README.md            # 项目文档
├── templates/
│   └── mahjong.html     # 游戏界面HTML和JavaScript
└── static/
    └── sounds/          # 游戏音效
        ├── draw.mp3     # 摸牌音效
        ├── discard.mp3  # 出牌音效
        ├── pong.mp3     # 碰牌音效
        ├── kong.mp3     # 杠牌音效
        └── win.mp3      # 胡牌音效
```

## 代码结构

### Python 后端 (app.py)

- `Tile` 类：麻将牌的基本类
- `MahjongGame` 类：游戏主类，包含核心逻辑
  - 洗牌、发牌
  - 玩家操作（摸牌、出牌、碰、杠、胡）
  - AI决策
  - 胡牌判定
  - 计分系统
- Flask路由：处理前端请求

### 前端 (mahjong.html)

- HTML：游戏界面结构
- CSS：样式和动画
- JavaScript：
  - 请求处理
  - 界面更新
  - 用户交互
  - 音效系统

## 未来扩展

- **多人在线对战**：实现WebSocket通信，支持多人联网游戏
- **更多麻将规则**：
  - 添加国标麻将规则
  - 添加更多区域变种规则（台湾、日本、美式等）
- **AI改进**：
  - 基于机器学习的AI对手
  - 多级难度设置
- **游戏统计**：
  - 玩家成绩记录
  - 游戏历史回放
- **更多自定义选项**：
  - 自定义规则
  - 自定义界面

## 贡献指南

欢迎贡献代码、报告问题或提供建议！请遵循以下步骤：

1. Fork本项目
2. 创建您的特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交您的更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开一个Pull Request

## 许可证

本项目采用MIT许可证 - 详见 [LICENSE](LICENSE) 文件

## 致谢

- 感谢所有贡献者和支持者
- 音效资源来自[insert source]
- 灵感来源于中国传统麻将
