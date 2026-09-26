import pygame
from settings import SCREEN_WIDTH, COLOR_WHITE, COLOR_RED, COLOR_YELLOW, COLOR_GREEN, COLOR_BLACK
from arcade_font import get_arcade_font

class HUD:
    """
    Administra la interfaz de usuario durante el combate: puntuación arcade (1P / TOP / 2P),
    barras de vida, barras de ultimate (Special Meter), nombres con tipografía arcade SF2,
    temporizador de 99s, contador de rounds y banners de combate ("START !", "ROUND 1", "FIGHT!", "K.O.", "YOU WIN").
    """
    def __init__(self):
        pygame.font.init()
        self.font_small = pygame.font.Font(None, 24)
        self.font_tiny = pygame.font.Font(None, 18)
        self.font_medium = pygame.font.Font(None, 40)
        self.font_timer = pygame.font.Font(None, 54)
        self.font_large = pygame.font.Font(None, 72)
        self.arcade_font = get_arcade_font()
        self.p1_score = 12000
        self.p2_score = 8500
        self.top_score = 50000

    def draw_scores(self, screen):
        """Dibuja el encabezado de puntuación auténtico de arcade Street Fighter II."""
        if self.arcade_font and self.arcade_font.loaded:
            # 1P Score
            self.arcade_font.render_to(screen, (50, 10), f"1P {self.p1_score:06d}", scale=0.6)
            # High Score (TOP)
            self.arcade_font.render_to(screen, (SCREEN_WIDTH // 2, 10), f"TOP {self.top_score:06d}", scale=0.6, align="center")
            # 2P Score
            self.arcade_font.render_to(screen, (SCREEN_WIDTH - 50, 10), f"2P {self.p2_score:06d}", scale=0.6, align="right")
        else:
            p1_s = self.font_small.render(f"1P {self.p1_score:06d}", True, COLOR_YELLOW)
            top_s = self.font_small.render(f"TOP {self.top_score:06d}", True, COLOR_WHITE)
            p2_s = self.font_small.render(f"2P {self.p2_score:06d}", True, COLOR_YELLOW)
            screen.blit(p1_s, (50, 10))
            screen.blit(top_s, (SCREEN_WIDTH // 2 - top_s.get_width() // 2, 10))
            screen.blit(p2_s, (SCREEN_WIDTH - 50 - p2_s.get_width(), 10))

    def draw_health_bar(self, screen, fighter, x, y, width=450, height=30, is_p2=False):
        """Dibuja la barra de vida de un personaje con nombre en fuente arcade SF2."""
        ratio = max(0.0, min(1.0, fighter.health / fighter.max_health))

        bg_rect = pygame.Rect(x, y, width, height)
        pygame.draw.rect(screen, (40, 40, 50), bg_rect)
        pygame.draw.rect(screen, COLOR_WHITE, bg_rect, 3)

        if ratio > 0.5:
            bar_color = COLOR_GREEN
        elif ratio > 0.2:
            bar_color = COLOR_YELLOW
        else:
            bar_color = COLOR_RED

        fill_w = int(width * ratio)

        if fill_w > 0:
            if not is_p2:
                fill_rect = pygame.Rect(x + 2, y + 2, fill_w - 4, height - 4)
            else:
                fill_rect = pygame.Rect(x + width - fill_w + 2, y + 2, fill_w - 4, height - 4)

            pygame.draw.rect(screen, bar_color, fill_rect)

        # Nombre del personaje en tipografía arcade SF2
        fighter_name = fighter.name.upper()
        if self.arcade_font and self.arcade_font.loaded:
            if not is_p2:
                self.arcade_font.render_to(screen, (x, y - 28), fighter_name, scale=0.7)
            else:
                self.arcade_font.render_to(screen, (x + width, y - 28), fighter_name, scale=0.7, align="right")
        else:
            name_surface = self.font_small.render(fighter_name, True, COLOR_WHITE)
            if not is_p2:
                screen.blit(name_surface, (x, y - 24))
            else:
                screen.blit(name_surface, (x + width - name_surface.get_width(), y - 24))

    def draw_special_meter(self, screen, fighter, x, y, width=350, height=14, is_p2=False):
        """Dibuja la barra de energía para Ultimate (Special Meter)."""
        ratio = max(0.0, min(1.0, fighter.special_meter / fighter.max_special_meter))

        bg_rect = pygame.Rect(x, y, width, height)
        pygame.draw.rect(screen, (30, 30, 40), bg_rect)
        pygame.draw.rect(screen, COLOR_WHITE, bg_rect, 2)

        fill_w = int(width * ratio)
        if fill_w > 0:
            if not is_p2:
                fill_rect = pygame.Rect(x + 1, y + 1, fill_w - 2, height - 2)
            else:
                fill_rect = pygame.Rect(x + width - fill_w + 1, y + 1, fill_w - 2, height - 2)

            color = (255, 215, 0) if ratio >= 1.0 else (40, 180, 255)
            pygame.draw.rect(screen, color, fill_rect)

        if ratio >= 1.0:
            lbl = self.font_tiny.render("MAX - SPECIAL READY!", True, (255, 220, 50))
            if not is_p2:
                screen.blit(lbl, (x, y + height + 2))
            else:
                screen.blit(lbl, (x + width - lbl.get_width(), y + height + 2))

    def draw_round_wins(self, screen, wins, x, y, is_p2=False):
        """Dibuja las marcas de rounds ganados."""
        radius = 8
        spacing = 24
        for i in range(2):
            cx = x + (i * spacing) if not is_p2 else x - (i * spacing)
            cy = y
            if i < wins:
                pygame.draw.circle(screen, COLOR_YELLOW, (cx, cy), radius)
                pygame.draw.circle(screen, COLOR_WHITE, (cx, cy), radius, 2)
            else:
                pygame.draw.circle(screen, (60, 60, 80), (cx, cy), radius)
                pygame.draw.circle(screen, COLOR_WHITE, (cx, cy), radius, 1)

    def draw_timer(self, screen, seconds_left):
        """Dibuja el temporizador de 99s con números arcade."""
        timer_bg = pygame.Rect(SCREEN_WIDTH // 2 - 40, 35, 80, 50)
        pygame.draw.rect(screen, (20, 20, 30), timer_bg)
        pygame.draw.rect(screen, COLOR_YELLOW, timer_bg, 2)

        timer_str = f"{max(0, int(seconds_left)):02d}"
        if self.arcade_font and self.arcade_font.loaded:
            self.arcade_font.render_to(screen, (SCREEN_WIDTH // 2, 60), timer_str, scale=1.1, align="center")
        else:
            color = COLOR_RED if seconds_left <= 10 else COLOR_WHITE
            txt_surf = self.font_timer.render(timer_str, True, color)
            screen.blit(txt_surf, (SCREEN_WIDTH // 2 - txt_surf.get_width() // 2, 42))

    def draw_banner(self, screen, text, subtext=None, color=COLOR_YELLOW):
        """Dibuja el banner central en pantalla con tipografía auténtica SF2."""
        overlay = pygame.Surface((SCREEN_WIDTH, 140), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 190))
        screen.blit(overlay, (0, 290))

        if self.arcade_font and self.arcade_font.loaded:
            # Banner principal en escala grande arcade SF2
            self.arcade_font.render_to(screen, (SCREEN_WIDTH // 2, 335), text, scale=1.5, align="center")
            if subtext:
                self.arcade_font.render_to(screen, (SCREEN_WIDTH // 2, 395), subtext, scale=0.75, align="center")
        else:
            txt_surf = self.font_large.render(text, True, color)
            screen.blit(txt_surf, (SCREEN_WIDTH // 2 - txt_surf.get_width() // 2, 305))
            if subtext:
                sub_surf = self.font_medium.render(subtext, True, COLOR_WHITE)
                screen.blit(sub_surf, (SCREEN_WIDTH // 2 - sub_surf.get_width() // 2, 380))

    def draw(self, screen, player1, player2, timer_seconds, p1_wins, p2_wins, match_banner=None):
        """Renderiza el HUD completo del combate."""
        # Puntuaciones arcade superiores
        self.draw_scores(screen)

        # Barras de salud
        self.draw_health_bar(screen, player1, x=50, y=50, width=450, height=30, is_p2=False)
        self.draw_health_bar(screen, player2, x=SCREEN_WIDTH - 500, y=50, width=450, height=30, is_p2=True)

        # Barras de Special Meter (Ultimate)
        self.draw_special_meter(screen, player1, x=50, y=85, width=350, height=14, is_p2=False)
        self.draw_special_meter(screen, player2, x=SCREEN_WIDTH - 400, y=85, width=350, height=14, is_p2=True)

        # Indicadores de victorias (Rounds)
        self.draw_round_wins(screen, p1_wins, x=50, y=118, is_p2=False)
        self.draw_round_wins(screen, p2_wins, x=SCREEN_WIDTH - 50, y=118, is_p2=True)

        # Temporizador
        self.draw_timer(screen, timer_seconds)

        # Banners
        if match_banner:
            self.draw_banner(screen, match_banner[0], match_banner[1], match_banner[2] if len(match_banner) > 2 else COLOR_YELLOW)

