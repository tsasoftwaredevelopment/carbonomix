from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.clock import Clock
from kivy.core.window import Window


class StartingScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        for child in self.children:
            if child.__class__.__name__ == 'Label':
                self.text = child
                child.opacity = 0

    def fade_text(self, add: float):
        self.text.opacity += add


class WelcomeScreen(Screen):
    pass


class CarbonomixApp(App):
    def build(self):
        Window.size = (400, 600)

        fade = FadeTransition()

        sm = ScreenManager(transition=fade)
        starting_screen = StartingScreen(name='starting')
        sm.add_widget(starting_screen)
        sm.add_widget(WelcomeScreen(name='welcome'))

        def start_app(dt):
            sm.current = 'welcome'

        def fade_in_text(dt):
            starting_screen.fade_text(1/20.0)

        for i in range(20):
            Clock.schedule_once(fade_in_text, 1 + i * 0.1)

        fade.duration = 1
        Clock.schedule_once(start_app, 3.4)

        return sm


if __name__ == '__main__':
    CarbonomixApp().run()
    pass
