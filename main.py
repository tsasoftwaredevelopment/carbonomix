from turtle import title
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition, SlideTransition
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.animation import Animation
from kivy.uix.floatlayout import FloatLayout
from kivy.properties import StringProperty, BooleanProperty, NumericProperty, ListProperty
from kivy.uix.popup import Popup
from kivy.metrics import dp

from kivymd.app import MDApp
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.snackbar import Snackbar
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.list import OneLineAvatarIconListItem
from kivy.factory import Factory
from kivymd.uix.button import MDFlatButton
from kivymd.uix.snackbar import BaseSnackbar

from database import update, query, create_tables, update_footprint, get_footprint, get_current_values, categories, category_names

from kivy.garden.matplotlib.backend_kivyagg import FigureCanvasKivyAgg
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta, date

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
    
class EditListItem(OneLineAvatarIconListItem):
    pass
        

class EditPopup(Popup):
    pass
        
    
class EditPopupCheckbox(Popup):
    pass

class ExitScreen(Screen):
    pass

class MainScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.update_values()
        self.display_menu = MDDropdownMenu(
            caller=self.ids.constraint,
            items=[
                {
                    "text": option,
                    "viewclass": "OneLineListItem",
                    "on_release": lambda x=option: self.choose_constraint(x)
                } for option in ("Past Month", "Past Year", "All")
            ],
            width_mult=2,
            max_height=dp(150),
        )

    def choose_constraint(self, option):
        self.display_menu.dismiss()
        self.ids.constraint.text = option
        self.display_values()
    
    @staticmethod
    def edit_title(category):
        if category_names.index(category) > 5:
            EditPopupCheckbox(title=category).open()
        else:
            EditPopup(title=category).open()
        
    def display_footprint(self):
        return str(get_footprint())

    def update_values(self):
        values = get_current_values()
        format = tuple(category_names[i] + ": " +
                       ("${:.2f}", "${:.2f}", "${:.2f}", "{:.2f} mpg", "{:.0f}", "{:.0f}", "{:s}", "{:s}")[i] for i in
                       range(len(categories)))

        for i in range(len(values)):
            self.ids.info_list.children[-(i + 1)].text = format[i].format(
                values[i] if i <= 5 else "Yes" if values[i] == 1 else "No")

    def display_values(self):
        self.ids.statistics.bind(minimum_height=self.ids.statistics.setter('height'))
        first_constraint = "AND submitted_at > NOW() - INTERVAL '1 "
        delta_time = False
        if self.ids.constraint.text == "All":
            first_constraint = ""
        elif self.ids.constraint.text == "Past Month":
            first_constraint += "month'"
            delta_time = timedelta(days=(date.today().replace(day=1) - timedelta(days=1)).day)
        elif self.ids.constraint.text == "Past Year":
            first_constraint += "year'"
            delta_time = timedelta(days=365 if date.today().year % 4 != 0 and date.today().year % 400 != 0 else 366)

        for i in range(len(self.ids.statistics.children) - 1, -1, -1):
            if self.ids.statistics.children[i] == self.ids.change_constraint:
                continue
            self.ids.statistics.remove_widget(self.ids.statistics.children[i])

        footprint_data = query(
            f"""
            SELECT submitted_at, footprint
            FROM footprints
            WHERE user_id = %s
            ORDER BY submitted_at DESC
            """,
            (1,)
        ).fetchall()
        fig, ax = plt.subplots()
        dates, values = [], []
        plot_dates, plot_values = [], []
        end_index, increase = None, None
        for i in range(len(footprint_data)):
            tz = footprint_data[i][0].tzinfo
            if not delta_time or footprint_data[i][0] > datetime.now(tz) - delta_time:
                plot_dates.append(footprint_data[i][0])
                plot_values.append(footprint_data[i][1])
            dates.append(footprint_data[i][0])
            values.append(footprint_data[i][1])
            if end_index is None and dates[-1].month == datetime.now(tz).month - 1:
                end_index = i  # Exclusive.
            if end_index is not None and (dates[-1].month == datetime.now(tz).month - 2 or i == len(footprint_data) - 1):
                this_month = sum(values[:end_index]) / end_index
                last_month = sum(values[end_index:i]) / (end_index - i) if i != len(footprint_data) - 1 else sum(
                    values[end_index:i + 1]) / (end_index - i + 1)
                increase = (this_month - last_month) / last_month * 100
        ax.plot(plot_dates, plot_values, '-o', color='#2e43ff', markersize=2)
        plt.ylabel('Carbon Footprint')
        plt.xlabel("Date")
        plt.subplots_adjust(left=0.2, right=0.95, top=0.9, bottom=0.3)
        ax.set_xticklabels(dates, rotation=45, ha='right')
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y %b-%d'))
        self.ids.statistics.add_widget(
            GraphItem(FigureCanvasKivyAgg(plt.gcf()), round(increase or 0), "Carbon Footprint"))
        plt.close(fig)

        data = query(
            f"""
            SELECT category_id, submitted_at, value
            FROM input_values
            WHERE user_id = %s AND category_id <= 6 {first_constraint}
            ORDER BY category_id, submitted_at DESC
            """,
            (1,)
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
            plt.ylabel(category_names[i] + (" ($)" if i <= 3 else " (mpg)" if i == 4 else ""))
            plt.xlabel("Date")
            plt.subplots_adjust(left=0.2, right=0.95, top=0.9, bottom=0.3)
            ax.set_xticklabels(dates, rotation=45, ha='right')
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y %b-%d'))
            self.ids.statistics.add_widget(
                GraphItem(FigureCanvasKivyAgg(plt.gcf()), round(increase or 0, 2), category_names[i]))
            plt.close(fig)


class GraphItem(MDBoxLayout):
    increase = NumericProperty(0)
    category = StringProperty()

    def __init__(self, graph, increase, category, **kwargs):
        super().__init__(**kwargs)
        graph.stretch_to_fit = True
        self.increase = float(increase)
        self.category = category
        self.add_widget(graph)
        if category == "Carbon Footprint":
            self.children[1].secondary_text = self.children[1].secondary_text[:-6] + "month."

        
        
        
        

        

class QuestionLayout(FloatLayout):
    question = StringProperty()
    is_final = BooleanProperty(False)
    text_input = BooleanProperty(True)
    is_dollar_value = BooleanProperty(True)


class MenuHeader(MDBoxLayout):
    pass


class CustomSnackbar(BaseSnackbar):
    text = StringProperty(None)
    icon = StringProperty(None)
    font_size = NumericProperty("15sp")


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
                "on_release": lambda x="Placeholder": self.menu_callback2(x),
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

        snackbar = CustomSnackbar(
            text = text_item,
            bg_color = (50/255, 100/255, 50/255, 1),
            icon = "information",
            snackbar_x = "10dp",
            snackbar_y = "10dp",
            duration = 2,
            buttons = [MDFlatButton(text="[color=#ffffff]OK[/color]", text_color=(1,1,1,1))]
            )
        snackbar.size_hint_x = (
            Window.width - (snackbar.snackbar_x * 2)
        ) / Window.width
        
        snackbar.open()

        Clock.schedule_once(close_application, 4)

    def menu_callback2(self, text_item):
        snackbar = CustomSnackbar(
            text = text_item,
            bg_color = (50/255, 100/255, 50/255, 1),
            icon = "information",
            snackbar_x = "10dp",
            snackbar_y = "10dp",
            duration = 2,
            buttons = [MDFlatButton(text="[color=#ffffff]OK[/color]", text_color=(1,1,1,1))]
            )
        snackbar.size_hint_x = (
            Window.width - (snackbar.snackbar_x * 2)
        ) / Window.width
        
        snackbar.open()


if __name__ == '__main__':
    create_tables()
    CarbonomixApp().run()
