from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition, SlideTransition
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.animation import Animation
from kivy.uix.floatlayout import FloatLayout
from kivy.properties import StringProperty, BooleanProperty, NumericProperty
from kivy.uix.popup import Popup
from kivymd.uix.menu import MDDropdownMenu
from kivy.metrics import dp
from kivymd.uix.snackbar import Snackbar
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.app import MDApp
from database import update, query, create_tables, update_footprint, get_footprint, get_current_values, categories, category_names

from kivy.garden.matplotlib.backend_kivyagg import FigureCanvasKivyAgg
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


# DEBUG = True means you're testing.
DEBUG = False
# Set this to True if you want to see the questions again on the welcome screen.
always_show_questions = False

sm: ScreenManager
plt.rcParams.update({'font.size': 8})


class StartingScreen(Screen):
    pass


class WelcomeScreen(Screen):
    def submit(self):
        values = []
        for value in (
                self.ids.electric_bill, self.ids.gas_bill, self.ids.oil_bill, self.ids.mileage,
                self.ids.flights_below_4,
                self.ids.flights_over_4):
            try:
                values.append(float(value.children[2].text))
            except ValueError:
                self.ids.questions.load_slide(value)
                return
        for value in (self.ids.recycle_newspaper, self.ids.recycle_aluminum_tin):
            if value.children[3].state == value.children[2].state:
                self.ids.questions.load_slide(value)
                return
            values.append(value.children[3].state == 'down')

        # TODO: Add some loading indicator here so the user knows something is happening.
        update_footprint(values=values)
        FootprintPopup().open()
        sm.transition = SlideTransition(direction='left')

        
class FootprintPopup(Popup):
    def display_footprint(self):
        return str(get_footprint())


class ElectricBillEditPopup(Popup):
    pass


class MainScreen(Screen):
    def update_values(self):
        values = get_current_values()
        format = tuple(category_names[i] + ": " + ("${:.2f}", "${:.2f}", "${:.2f}", "{:.2f} mpg", "{:.0f}", "{:.0f}", "{:s}", "{:s}")[i] for i in range(len(categories)))

        for i in range(len(values)):
            self.ids.info_list.children[-(i + 1)].text = format[i].format(values[i] if i <= 5 else "Yes" if values[i] == 1 else "No")

    def display_values(self):
        self.ids.statistics.bind(minimum_height=self.ids.statistics.setter('height'))
        data = query(
            """
            SELECT category_id, submitted_at, value
            FROM (
                SELECT category_id, submitted_at, value,
                    ROW_NUMBER() OVER (PARTITION BY category_id ORDER BY category_id, submitted_at DESC) AS row_number
                FROM input_values
                WHERE category_id <= 6 AND submitted_at > NOW() - interval '1 year'
            ) split
            WHERE row_number <= 100
            """
        ).fetchall()
        index = 0
        for i in range(len(categories) - 2):
            fig, ax = plt.subplots()
            last_value = None
            increase = None
            dates = []
            values = []
            for k in range(index, len(data)):
                if data[index][0] == i + 1:
                    dates.append(data[index][1])
                    values.append(data[index][2])
                    if last_value and increase is None:
                        increase = (last_value - data[index][2]) / data[index][2] * 100
                    if last_value is None:
                        last_value = data[index][2]
                    index += 1
                else:
                    break
            ax.plot(dates, values, '-o', color='#2e43ff', markersize=2)
            ax.set_ylim(bottom=0)
            plt.ylabel(category_names[i] + (" ($)" if i <= 3 else " (mpg)" if i == 4 else ""))
            plt.xlabel("Date")
            plt.subplots_adjust(left=0.2, right=0.9, top=0.9, bottom=0.3)
            ax.set_xticklabels(dates, rotation=45, ha='right')
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y %b-%d'))
            self.ids.statistics.add_widget(GraphItem(FigureCanvasKivyAgg(plt.gcf()), round(increase, 2), category_names[i]))


class GraphItem(MDBoxLayout):
    increase = NumericProperty(0)
    category = StringProperty()

    def __init__(self, graph, increase, category, **kwargs):
        super().__init__(**kwargs)
        graph.stretch_to_fit = True
        self.increase = float(increase)
        self.category = category
        self.add_widget(graph)


class ExitScreen(Screen):
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
        global sm
        Window.size = (400, 600)
        Window.clearcolor = (189 / 255, 1, 206 / 255, 1)

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
                "text": "Exit App",
                "height": dp(40),
                "on_release": lambda x="Exit App": self.menu_callback(x),
            },
            {
                "viewclass": "OneLineListItem",
                "text": "Placeholder",
                "height": dp(40),
                "on_release": lambda x="Placeholder": self.menu_callback(x),
            }
        ]

        self.menu = MDDropdownMenu(
            position="bottom",
            hor_growth="left",
            # background_color = self.theme_cls.primary_color,
            header_cls=MenuHeader(),
            items=menu_items,
            width_mult=4,
        )

        def start_app(dt=None):
            sm.current = 'welcome' if always_show_questions or not query(
                """
                SELECT value
                FROM input_values
                WHERE user_id = %s
                """,
                (1,)
            ).fetchone() else 'main'
            widgets = (
                welcome_screen.ids.welcome_text, welcome_screen.ids.please_answer_text, welcome_screen.ids.questions)
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
        exit_screen = ExitScreen(name='end')
        sm.add_widget(exit_screen)

        def close_application(dt=None):
            CarbonomixApp.get_running_app().stop()
            Window.close()

        def fade_text():
            fade = Animation(opacity=1, duration=2) + Animation(opacity=0, duration=1)
            fade.start(exit_screen.ids.ending_text)

        sm.switch_to(exit_screen, transition=FadeTransition(), duration=0.75)
        fade_text()
        self.menu.dismiss()
        Snackbar(text=text_item).open()

        Clock.schedule_once(close_application, 4)


if __name__ == '__main__':
    create_tables()
    CarbonomixApp().run()
