from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.clock import Clock
from kivy.graphics.texture import Texture
import cv2
import numpy as np
import time

class LaserTagGame(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'

        # Игровые настройки матча
        self.player_hp = 100
        self.player_score = 0
        self.enemy_score = 0
        self.max_wins = 3
        self.current_round = 1
        self.last_hit_time = 0
        self.shield_duration = 2.0  # 2 секунды бессмертия после урона
        self.round_duration = 60    # Раунд длится 60 секунд
        self.start_round_time = time.time()

        # Верхнее табло (Раунд и Общий счет)
        self.info_label = Label(
            text=f"ROUND {self.current_round}   |   YOU: {self.player_score}  ENEMY: {self.enemy_score}",
            size_hint_y=0.1, font_size='18sp'
        )
        self.add_widget(self.info_label)

        # Окно, куда будет выводиться видео с камеры
        self.img_widget = Image(size_hint_y=0.8)
        self.add_widget(self.img_widget)

        # Нижнее табло (Жизни и Таймер раунда)
        self.status_label = Label(
            text=f"HP: {self.player_hp}   |   TIME: {self.round_duration}s",
            size_hint_y=0.1, font_size='20sp'
        )
        self.add_widget(self.status_label)

        # Включаем камеру (0 - задняя камера телефона)
        self.capture = cv2.VideoCapture(0)
        
        # Запускаем игровой цикл (обновление картинки и логики 30 раз в секунду)
        Clock.schedule_interval(self.update, 1.0 / 30.0)

    def update(self, dt):
        ret, frame = self.capture.read()
        if not ret:
            return

        # Переворачиваем картинку, чтобы на телефоне она не была боком
        frame = cv2.flip(frame, 0)
        
        current_time = time.time()
        time_passed = current_time - self.start_round_time
        time_left = max(0, int(self.round_duration - time_passed))

        # Проверяем, активен ли щит бессмертия прямо сейчас
        is_shield_active = (current_time - self.last_hit_time) < self.shield_duration

        # Обрабатываем кадр: ищем яркую точку от фонарика врага
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 245, 255, cv2.THRESH_BINARY)
        bright_pixels = np.sum(thresh == 255)

        # Нанесение урона (если нашли фонарик и щит отключен)
        if bright_pixels > 8000 and not is_shield_active and self.player_hp > 0 and time_left > 0:
            self.player_hp -= 20
            self.last_hit_time = current_time  # Включаем щит

        # КОНЕЦ РАУНДА ВАРИАНТ А: Время вышло, ты выжил 60 секунд (Очко тебе)
        if time_left <= 0 and self.player_hp > 0:
            self.player_score += 1
            self.reset_round()

        # КОНЕЦ РАУНДА ВАРИАНТ Б: Твои ХП упали до нуля (Очко врагу)
        if self.player_hp <= 0:
            self.enemy_score += 1
            self.reset_round()

        # Эффект щита: подкрашиваем экран в синеватый цвет при уроне
        if is_shield_active:
            frame[:, :, 0] = cv2.add(frame[:, :, 0], 40)

        # Обновляем тексты на экране телефона
        self.info_label.text = f"ROUND {self.current_round}   |   YOU: {self.player_score}  ENEMY: {self.enemy_score}"
        shield_text = " [SHIELD]" if is_shield_active else ""
        self.status_label.text = f"HP: {self.player_hp}{shield_text}   |   TIME: {time_left}s"

        # Превращаем кадр OpenCV в формат, который понимает Kivy, и выводим на экран
        buf = frame.tobytes()
        texture = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt='bgr')
        texture.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')
        self.img_widget.texture = texture

    def reset_round(self):
        # Проверяем, набрал ли кто-то 3 очка для победы в матче
        if self.player_score >= self.max_wins or self.enemy_score >= self.max_wins:
            self.info_label.text = "MATCH OVER!"
            if self.player_score >= self.max_wins:
                self.status_label.text = "YOU ARE THE CHAMPION!"
            else:
                self.status_label.text = "ENEMY WINS THE MATCH!"
            Clock.unschedule(self.update)
            self.capture.release()
        else:
            # Если игра продолжается — сбрасываем ХП и таймер для нового раунда
            self.player_hp = 100
            self.current_round += 1
            self.start_round_time = time.time()
            self.last_hit_time = 0

class LaserTagApp(App):
    def build(self):
        return LaserTagGame()

    def on_stop(self):
        if hasattr(self, 'root') and self.root.capture:
            self.root.capture.release()

if __name__ == '__main__':
    LaserTagApp().run()
