from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.animation import Animation
from kivy.uix.floatlayout import FloatLayout
from kivy.properties import StringProperty, BooleanProperty
from kivymd.app import MDApp
from kivymd.theming import ThemeManager
from kivy.lang import Builder
from kivy.factory import Factory
from kivymd.uix.menu import MDDropdownMenu
from kivy.metrics import dp
from kivymd.uix.snackbar import Snackbar
from kivymd.uix.boxlayout import MDBoxLayout
from database import update, query


DEBUG = False

# Temporary values.
carbon_footprint = 39792.59
electric_bill, gas_bill, oil_bill, mileage, flights_below_4, flights_over_4, recycle_newspaper, recycle_aluminum_tin = 101.2, 87.72, 52.4, 9201, 2, 1, True, False
# TODO: Change these values to match the values from the user.


class StartingScreen(Screen):
    pass


class WelcomeScreen(Screen):
    def submit(self):
        print(self.ids.electric_bill)


class MainScreen(Screen):
    pass


class QuestionLayout(FloatLayout):
    question = StringProperty()
    is_final = BooleanProperty(False)
    text_input = BooleanProperty(True)
    is_dollar_value = BooleanProperty(True)


class MenuHeader(MDBoxLayout):
    pass


class CarbonomixApp(MDApp):
    def build(self):
        Window.size = (400, 600)
        Window.clearcolor = (189/255, 1, 206/255, 1)

        fade = FadeTransition()
        fade.duration = 0 if DEBUG else 1.5

        sm = ScreenManager(transition=fade)
        starting_screen = StartingScreen(name='starting')
        welcome_screen = WelcomeScreen(name='welcome')
        main_screen = MainScreen(name='main')
        sm.add_widget(starting_screen)
        sm.add_widget(welcome_screen)
        sm.add_widget(main_screen)

        menu_items = [
            {
                "viewclass": "OneLineListItem",
                "text": f"Item {i}",
                "height": dp(40),
                "on_release": lambda x=f"Item {i}": self.menu_callback(x),
             } for i in range(2)
        ]
        self.menu = MDDropdownMenu(
            header_cls = MenuHeader(),
            items = menu_items,
            width_mult = 4,
        )

        def start_app(dt=None):
            sm.current = 'welcome'
            widgets = (welcome_screen.ids.welcome_text, welcome_screen.ids.please_answer_text, welcome_screen.ids.questions)
            animation = Animation(
                opacity=1, duration=2 if not DEBUG else 0
            )
            index = 0

            def animate(dt):
                nonlocal index
                animation.start(widgets[index])
                index += 1

            for i in range(len(widgets)):
                Clock.schedule_once(animate, (1 + i * 0.7) if not DEBUG else 0)

        def fade_in_text(dt=None):
            Animation(
                opacity=1, duration=0.75
            ).start(starting_screen.ids.title)

        if not DEBUG:
            Clock.schedule_once(fade_in_text, .8)
            Clock.schedule_once(start_app, 3.4)
        else:
            start_app()

        return sm
    
    def callback(self, button):
        self.menu.caller = button
        self.menu.open()

    def menu_callback(self, text_item):
        self.menu.dismiss()
        Snackbar(text=text_item).open()



if __name__ == '__main__':
    CarbonomixApp().run()
    pass
