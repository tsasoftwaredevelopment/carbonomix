from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.animation import Animation


DEBUG = False


class StartingScreen(Screen):
    pass


class WelcomeScreen(Screen):
    pass


class CarbonomixApp(App):
    def build(self):
        Window.size = (400, 600)
        Window.clearcolor = (189/255, 1, 206/255, 1)

        fade = FadeTransition()
        fade.duration = 0 if DEBUG else 1.5

        sm = ScreenManager(transition=fade)
        starting_screen = StartingScreen(name='starting')
        sm.add_widget(starting_screen)
        sm.add_widget(WelcomeScreen(name='welcome'))

        def start_app(dt=None):
            sm.current = 'welcome'

        def fade_in_text(dt=None):
            Animation(
                opacity=1, duration=2.4
            ).start(starting_screen.ids.title)

        if not DEBUG:
            Clock.schedule_once(fade_in_text, .8)
            Clock.schedule_once(start_app, 3.4)
        else:
            start_app()

        return sm


if __name__ == '__main__':
    CarbonomixApp().run()
    pass
