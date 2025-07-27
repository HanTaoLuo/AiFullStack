import pygame
import sys
import random
import time
from pygame.locals import *

# 初始化
pygame.init()
pygame.mixer.init()

# 常量定义
BOARD_SIZE = 15
GRID_SIZE = 40
PIECE_RADIUS = 18
MARGIN = 40
WIDTH = BOARD_SIZE * GRID_SIZE + 2 * MARGIN
HEIGHT = BOARD_SIZE * GRID_SIZE + 2 * MARGIN + 60
FPS = 30

# 颜色
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
BOARD_COLOR = (220, 179, 92)
LINE_COLOR = (0, 0, 0)
HIGHLIGHT_COLOR = (255, 0, 0)
TEXT_COLOR = (50, 50, 50)
PANEL_COLOR = (240, 240, 240)

# 创建游戏窗口
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption('Gomoku')
clock = pygame.time.Clock()

# 加载音效
try:
    place_sound = pygame.mixer.Sound("place.wav")
    win_sound = pygame.mixer.Sound("win.wav")
except:
    print("音效文件未找到，游戏将继续但没有音效")
    place_sound = None
    win_sound = None


# 游戏状态
class GameState:
    def __init__(self):
        self.board = [[0 for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
        self.current_player = 1  # 1 for black, 2 for white
        self.game_over = False
        self.winner = 0
        self.winning_line = []
        self.mode = "menu"  # menu, pvp, pve
        self.ai_difficulty = "medium"  # easy, medium, hard
        self.sound_on = True
        self.move_history = []
        self.last_move = None

    def reset(self):
        self.board = [[0 for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
        self.current_player = 1
        self.game_over = False
        self.winner = 0
        self.winning_line = []
        self.move_history = []
        self.last_move = None

    def make_move(self, row, col):
        if self.game_over or self.board[row][col] != 0:
            return False

        self.board[row][col] = self.current_player
        self.move_history.append((row, col, self.current_player))
        self.last_move = (row, col)

        if self.check_win(row, col):
            self.game_over = True
            self.winner = self.current_player
            if self.sound_on and win_sound:
                win_sound.play()
        elif self.is_board_full():
            self.game_over = True

        self.current_player = 3 - self.current_player  # Switch player (1->2, 2->1)

        if self.sound_on and place_sound:
            place_sound.play()

        return True

    def undo_move(self):
        if len(self.move_history) == 0:
            return False

        row, col, player = self.move_history.pop()
        self.board[row][col] = 0
        self.current_player = player
        self.game_over = False
        self.winner = 0
        self.winning_line = []

        if len(self.move_history) > 0:
            self.last_move = (self.move_history[-1][0], self.move_history[-1][1])
        else:
            self.last_move = None

        return True

    def check_win(self, row, col):
        directions = [(1, 0), (0, 1), (1, 1), (1, -1)]  # 水平, 垂直, 对角线, 反对角线
        player = self.board[row][col]

        for dr, dc in directions:
            count = 1
            line = [(row, col)]

            # 正向检查
            r, c = row + dr, col + dc
            while 0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE and self.board[r][c] == player:
                count += 1
                line.append((r, c))
                r += dr
                c += dc

            # 反向检查
            r, c = row - dr, col - dc
            while 0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE and self.board[r][c] == player:
                count += 1
                line.append((r, c))
                r -= dr
                c -= dc

            if count >= 5:
                self.winning_line = line
                return True

        return False

    def is_board_full(self):
        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                if self.board[row][col] == 0:
                    return False
        return True


# AI逻辑
class AI:
    def __init__(self, difficulty="medium"):
        self.difficulty = difficulty

    def make_move(self, game_state):
        if self.difficulty == "easy":
            return self.easy_ai(game_state)
        elif self.difficulty == "medium":
            return self.medium_ai(game_state)
        else:
            return self.hard_ai(game_state)

    def easy_ai(self, game_state):
        # 随机落子，但会阻止玩家即将获胜的情况
        empty_cells = [(r, c) for r in range(BOARD_SIZE) for c in range(BOARD_SIZE) if game_state.board[r][c] == 0]

        # 检查是否有立即获胜的机会
        for r, c in empty_cells:
            game_state.board[r][c] = 2
            if game_state.check_win(r, c):
                game_state.board[r][c] = 0
                return r, c
            game_state.board[r][c] = 0

        # 检查是否需要阻止玩家
        for r, c in empty_cells:
            game_state.board[r][c] = 1
            if game_state.check_win(r, c):
                game_state.board[r][c] = 0
                return r, c
            game_state.board[r][c] = 0

        # 随机选择
        return random.choice(empty_cells)

    def medium_ai(self, game_state):
        # 简单的评估函数
        def evaluate_position(r, c, player):
            directions = [(1, 0), (0, 1), (1, 1), (1, -1)]
            score = 0

            for dr, dc in directions:
                # 四个方向
                line = 1

                # 正向
                i, j = r + dr, c + dc
                while 0 <= i < BOARD_SIZE and 0 <= j < BOARD_SIZE and game_state.board[i][j] == player:
                    line += 1
                    i += dr
                    j += dc

                # 反向
                i, j = r - dr, c - dc
                while 0 <= i < BOARD_SIZE and 0 <= j < BOARD_SIZE and game_state.board[i][j] == player:
                    line += 1
                    i -= dr
                    j -= dc

                if line >= 5:
                    return 100000  # 获胜

                # 根据连子数给分
                if line == 4:
                    score += 1000
                elif line == 3:
                    score += 100
                elif line == 2:
                    score += 10
                elif line == 1:
                    score += 1

            return score

        empty_cells = [(r, c) for r in range(BOARD_SIZE) for c in range(BOARD_SIZE) if game_state.board[r][c] == 0]

        # 检查是否有立即获胜的机会
        for r, c in empty_cells:
            game_state.board[r][c] = 2
            if game_state.check_win(r, c):
                game_state.board[r][c] = 0
                return r, c
            game_state.board[r][c] = 0

        # 检查是否需要阻止玩家
        for r, c in empty_cells:
            game_state.board[r][c] = 1
            if game_state.check_win(r, c):
                game_state.board[r][c] = 0
                return r, c
            game_state.board[r][c] = 0

        # 评估每个空位
        best_score = -1
        best_move = None

        for r, c in empty_cells:
            # 进攻得分
            attack_score = evaluate_position(r, c, 2)
            # 防守得分
            defense_score = evaluate_position(r, c, 1)
            total_score = attack_score + defense_score * 0.8  # 稍微偏重防守

            if total_score > best_score:
                best_score = total_score
                best_move = (r, c)

        return best_move

    def hard_ai(self, game_state):
        # 使用极小化极大算法和alpha-beta剪枝
        def minimax(board, depth, alpha, beta, is_maximizing):
            # 评估函数
            def evaluate():
                score = 0

                # 检查所有可能的五子连线
                for r in range(BOARD_SIZE):
                    for c in range(BOARD_SIZE):
                        if board[r][c] == 0:
                            continue

                        # 四个方向
                        directions = [(1, 0), (0, 1), (1, 1), (1, -1)]

                        for dr, dc in directions:
                            line = 1
                            player = board[r][c]

                            # 正向
                            i, j = r + dr, c + dc
                            while 0 <= i < BOARD_SIZE and 0 <= j < BOARD_SIZE and board[i][j] == player:
                                line += 1
                                i += dr
                                j += dc

                            # 反向
                            i, j = r - dr, c - dc
                            while 0 <= i < BOARD_SIZE and 0 <= j < BOARD_SIZE and board[i][j] == player:
                                line += 1
                                i -= dr
                                j -= dc

                            if line >= 5:
                                if player == 2:  # AI获胜
                                    return 100000
                                else:  # 玩家获胜
                                    return -100000

                            # 根据连子数给分
                            if player == 2:  # AI
                                if line == 4:
                                    score += 1000
                                elif line == 3:
                                    score += 100
                                elif line == 2:
                                    score += 10
                            else:  # 玩家
                                if line == 4:
                                    score -= 1200  # 更重视防守
                                elif line == 3:
                                    score -= 120
                                elif line == 2:
                                    score -= 12

                return score

            # 终止条件
            if depth == 0:
                return evaluate()

            # 检查游戏是否结束
            game_over = True
            for r in range(BOARD_SIZE):
                for c in range(BOARD_SIZE):
                    if board[r][c] == 0:
                        game_over = False
                        break
                if not game_over:
                    break

            if game_over:
                return evaluate()

            if is_maximizing:
                max_eval = -float('inf')
                for r in range(BOARD_SIZE):
                    for c in range(BOARD_SIZE):
                        if board[r][c] == 0:
                            board[r][c] = 2
                            eval = minimax(board, depth - 1, alpha, beta, False)
                            board[r][c] = 0
                            max_eval = max(max_eval, eval)
                            alpha = max(alpha, eval)
                            if beta <= alpha:
                                return max_eval
                return max_eval
            else:
                min_eval = float('inf')
                for r in range(BOARD_SIZE):
                    for c in range(BOARD_SIZE):
                        if board[r][c] == 0:
                            board[r][c] = 1
                            eval = minimax(board, depth - 1, alpha, beta, True)
                            board[r][c] = 0
                            min_eval = min(min_eval, eval)
                            beta = min(beta, eval)
                            if beta <= alpha:
                                return min_eval
                return min_eval

        # 检查是否有立即获胜的机会
        empty_cells = [(r, c) for r in range(BOARD_SIZE) for c in range(BOARD_SIZE) if game_state.board[r][c] == 0]

        for r, c in empty_cells:
            game_state.board[r][c] = 2
            if game_state.check_win(r, c):
                game_state.board[r][c] = 0
                return r, c
            game_state.board[r][c] = 0

        # 检查是否需要阻止玩家
        for r, c in empty_cells:
            game_state.board[r][c] = 1
            if game_state.check_win(r, c):
                game_state.board[r][c] = 0
                return r, c
            game_state.board[r][c] = 0

        # 使用极小化极大算法
        best_score = -float('inf')
        best_move = None

        # 限制搜索深度以提高性能
        search_depth = 2 if len(game_state.move_history) < 10 else 3

        for r, c in empty_cells:
            game_state.board[r][c] = 2
            score = minimax(game_state.board, search_depth, -float('inf'), float('inf'), False)
            game_state.board[r][c] = 0

            if score > best_score:
                best_score = score
                best_move = (r, c)

        return best_move


# 绘制函数
def draw_board(game_state):
    # 绘制棋盘背景
    screen.fill(BOARD_COLOR)

    # 绘制棋盘网格
    for i in range(BOARD_SIZE):
        # 横线
        pygame.draw.line(screen, LINE_COLOR,
                         (MARGIN, MARGIN + i * GRID_SIZE),
                         (WIDTH - MARGIN, MARGIN + i * GRID_SIZE), 2)
        # 竖线
        pygame.draw.line(screen, LINE_COLOR,
                         (MARGIN + i * GRID_SIZE, MARGIN),
                         (MARGIN + i * GRID_SIZE, HEIGHT - MARGIN - 60), 2)

    # 绘制棋子
    for row in range(BOARD_SIZE):
        for col in range(BOARD_SIZE):
            if game_state.board[row][col] == 1:  # 黑子
                pygame.draw.circle(screen, BLACK,
                                   (MARGIN + col * GRID_SIZE, MARGIN + row * GRID_SIZE),
                                   PIECE_RADIUS)
            elif game_state.board[row][col] == 2:  # 白子
                pygame.draw.circle(screen, WHITE,
                                   (MARGIN + col * GRID_SIZE, MARGIN + row * GRID_SIZE),
                                   PIECE_RADIUS)
                pygame.draw.circle(screen, LINE_COLOR,
                                   (MARGIN + col * GRID_SIZE, MARGIN + row * GRID_SIZE),
                                   PIECE_RADIUS, 1)

    # 标记最后一步
    if game_state.last_move:
        row, col = game_state.last_move
        pygame.draw.circle(screen, (255, 0, 0) if game_state.board[row][col] == 1 else (0, 0, 255),
                           (MARGIN + col * GRID_SIZE, MARGIN + row * GRID_SIZE), 5)

    # 高亮显示获胜连线
    if game_state.winning_line:
        for row, col in game_state.winning_line:
            pygame.draw.circle(screen, HIGHLIGHT_COLOR,
                               (MARGIN + col * GRID_SIZE, MARGIN + row * GRID_SIZE),
                               PIECE_RADIUS // 2)

    # 绘制顶部信息面板
    pygame.draw.rect(screen, PANEL_COLOR, (0, HEIGHT - 60, WIDTH, 60))

    # 显示当前玩家
    font = pygame.font.SysFont('Arial', 24)
    player_text = f"Current: {'Black ●' if game_state.current_player == 1 else 'White ○'}"
    if game_state.game_over:
        if game_state.winner == 1:
            player_text = "Black ● Wins!"
        elif game_state.winner == 2:
            player_text = "White ○ Wins!"
        else:
            player_text = "Game Over - Draw"

    text_surface = font.render(player_text, True, TEXT_COLOR)
    screen.blit(text_surface, (20, HEIGHT - 50))

    # 绘制按钮
    button_font = pygame.font.SysFont('Arial', 18)

    # 悔棋按钮
    pygame.draw.rect(screen, (200, 200, 200), (WIDTH - 280, HEIGHT - 50, 80, 30))
    undo_text = button_font.render("Undo", True, TEXT_COLOR)
    screen.blit(undo_text, (WIDTH - 260, HEIGHT - 45))

    # 重新开始按钮
    pygame.draw.rect(screen, (200, 200, 200), (WIDTH - 180, HEIGHT - 50, 100, 30))
    restart_text = button_font.render("Restart", True, TEXT_COLOR)
    screen.blit(restart_text, (WIDTH - 165, HEIGHT - 45))

    # 菜单按钮
    pygame.draw.rect(screen, (200, 200, 200), (WIDTH - 70, HEIGHT - 50, 60, 30))
    menu_text = button_font.render("Menu", True, TEXT_COLOR)
    screen.blit(menu_text, (WIDTH - 55, HEIGHT - 45))


def draw_menu(game_state):
    screen.fill(PANEL_COLOR)

    title_font = pygame.font.SysFont('Arial', 48)
    title_text = title_font.render("GOMOKU", True, TEXT_COLOR)
    screen.blit(title_text, (WIDTH // 2 - title_text.get_width() // 2, 50))

    button_font = pygame.font.SysFont('Arial', 32)

    # PvP按钮
    pygame.draw.rect(screen, (200, 200, 200), (WIDTH // 2 - 150, 150, 300, 50))
    pvp_text = button_font.render("Player vs Player", True, TEXT_COLOR)
    screen.blit(pvp_text, (WIDTH // 2 - pvp_text.get_width() // 2, 160))

    # PvE按钮
    pygame.draw.rect(screen, (200, 200, 200), (WIDTH // 2 - 150, 220, 300, 50))
    pve_text = button_font.render("Player vs Computer", True, TEXT_COLOR)
    screen.blit(pve_text, (WIDTH // 2 - pve_text.get_width() // 2, 230))

    # 设置按钮
    pygame.draw.rect(screen, (200, 200, 200), (WIDTH // 2 - 150, 290, 300, 50))
    settings_text = button_font.render("Settings", True, TEXT_COLOR)
    screen.blit(settings_text, (WIDTH // 2 - settings_text.get_width() // 2, 300))

    # 退出按钮
    pygame.draw.rect(screen, (200, 200, 200), (WIDTH // 2 - 150, 360, 300, 50))
    quit_text = button_font.render("Quit", True, TEXT_COLOR)
    screen.blit(quit_text, (WIDTH // 2 - quit_text.get_width() // 2, 370))


def draw_settings(game_state):
    screen.fill(PANEL_COLOR)

    title_font = pygame.font.SysFont('Arial', 48)
    title_text = title_font.render("SETTINGS", True, TEXT_COLOR)
    screen.blit(title_text, (WIDTH // 2 - title_text.get_width() // 2, 50))

    option_font = pygame.font.SysFont('Arial', 24)
    button_font = pygame.font.SysFont('Arial', 20)

    # AI难度设置
    difficulty_text = option_font.render("AI Difficulty:", True, TEXT_COLOR)
    screen.blit(difficulty_text, (50, 120))

    # 简单难度按钮
    pygame.draw.rect(screen, (200, 200, 200) if game_state.ai_difficulty != "easy" else (150, 200, 150),
                     (50, 160, 100, 40))
    easy_text = button_font.render("Easy", True, TEXT_COLOR)
    screen.blit(easy_text, (75, 170))

    # 中等难度按钮
    pygame.draw.rect(screen, (200, 200, 200) if game_state.ai_difficulty != "medium" else (150, 200, 150),
                     (170, 160, 100, 40))
    medium_text = button_font.render("Medium", True, TEXT_COLOR)
    screen.blit(medium_text, (180, 170))

    # 困难难度按钮
    pygame.draw.rect(screen, (200, 200, 200) if game_state.ai_difficulty != "hard" else (150, 200, 150),
                     (290, 160, 100, 40))
    hard_text = button_font.render("Hard", True, TEXT_COLOR)
    screen.blit(hard_text, (310, 170))

    # 音效设置
    sound_text = option_font.render("Sound:", True, TEXT_COLOR)
    screen.blit(sound_text, (50, 220))

    # 开启音效按钮
    pygame.draw.rect(screen, (200, 200, 200) if not game_state.sound_on else (150, 200, 150),
                     (50, 260, 100, 40))
    on_text = button_font.render("On", True, TEXT_COLOR)
    screen.blit(on_text, (80, 270))

    # 关闭音效按钮
    pygame.draw.rect(screen, (200, 200, 200) if game_state.sound_on else (150, 200, 150),
                     (170, 260, 100, 40))
    off_text = button_font.render("Off", True, TEXT_COLOR)
    screen.blit(off_text, (200, 270))

    # 返回按钮
    pygame.draw.rect(screen, (200, 200, 200), (WIDTH // 2 - 100, HEIGHT - 100, 200, 50))
    back_text = option_font.render("Back to Menu", True, TEXT_COLOR)
    screen.blit(back_text, (WIDTH // 2 - back_text.get_width() // 2, HEIGHT - 90))


# 主游戏循环
def main():
    game_state = GameState()
    ai = AI(game_state.ai_difficulty)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == QUIT:
                running = False

            elif event.type == MOUSEBUTTONDOWN:
                x, y = event.pos

                if game_state.mode == "menu":
                    # 检查菜单按钮点击
                    if 150 <= y <= 200:  # PvP
                        if WIDTH // 2 - 150 <= x <= WIDTH // 2 + 150:
                            game_state.mode = "pvp"
                            game_state.reset()
                    elif 220 <= y <= 270:  # PvE
                        if WIDTH // 2 - 150 <= x <= WIDTH // 2 + 150:
                            game_state.mode = "pve"
                            game_state.reset()
                    elif 290 <= y <= 340:  # Settings
                        if WIDTH // 2 - 150 <= x <= WIDTH // 2 + 150:
                            game_state.mode = "settings"
                    elif 360 <= y <= 410:  # Quit
                        if WIDTH // 2 - 150 <= x <= WIDTH // 2 + 150:
                            running = False

                elif game_state.mode == "settings":
                    # 检查设置选项
                    if 160 <= y <= 200:  # AI难度
                        if 50 <= x <= 150:  # Easy
                            game_state.ai_difficulty = "easy"
                            ai.difficulty = "easy"
                        elif 170 <= x <= 270:  # Medium
                            game_state.ai_difficulty = "medium"
                            ai.difficulty = "medium"
                        elif 290 <= x <= 390:  # Hard
                            game_state.ai_difficulty = "hard"
                            ai.difficulty = "hard"
                    elif 260 <= y <= 300:  # 音效
                        if 50 <= x <= 150:  # On
                            game_state.sound_on = True
                        elif 170 <= x <= 270:  # Off
                            game_state.sound_on = False
                    elif HEIGHT - 100 <= y <= HEIGHT - 50:  # 返回
                        if WIDTH // 2 - 100 <= x <= WIDTH // 2 + 100:
                            game_state.mode = "menu"

                elif game_state.mode in ["pvp", "pve"] and not game_state.game_over:
                    # 检查棋盘点击
                    if MARGIN <= x <= WIDTH - MARGIN and MARGIN <= y <= HEIGHT - MARGIN - 60:
                        col = round((x - MARGIN) / GRID_SIZE)
                        row = round((y - MARGIN) / GRID_SIZE)
                        if 0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE:
                            if game_state.mode == "pvp" or (
                                    game_state.mode == "pve" and game_state.current_player == 1):
                                game_state.make_move(row, col)

                    # 检查按钮点击
                    if HEIGHT - 60 <= y <= HEIGHT - 30:
                        if WIDTH - 280 <= x <= WIDTH - 200:  # Undo
                            game_state.undo_move()
                        elif WIDTH - 180 <= x <= WIDTH - 80:  # Restart
                            game_state.reset()
                        elif WIDTH - 70 <= x <= WIDTH - 10:  # Menu
                            game_state.mode = "menu"

                # 在PvE模式下，如果是AI的回合，则让AI走棋
                if game_state.mode == "pve" and not game_state.game_over and game_state.current_player == 2:
                    row, col = ai.make_move(game_state)
                    game_state.make_move(row, col)

        # 绘制当前界面
        if game_state.mode == "menu":
            draw_menu(game_state)
        elif game_state.mode == "settings":
            draw_settings(game_state)
        else:
            draw_board(game_state)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()