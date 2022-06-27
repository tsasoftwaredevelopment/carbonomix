from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition, SlideTransition
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.animation import Animation
from kivy.uix.floatlayout import FloatLayout
from kivy.properties import StringProperty, BooleanProperty, NumericProperty
from kivy.uix.popup import Popup
from kivy.metrics import dp

from kivymd.app import MDApp
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.list import IRightBodyTouch, OneLineAvatarIconListItem, TwoLineAvatarIconListItem, ThreeLineAvatarIconListItem
from kivymd.uix.button import MDFlatButton, MDRaisedButton
from kivymd.uix.snackbar import BaseSnackbar
from kivymd.uix.datatables import MDDataTable
from kivymd.uix.pickers import MDDatePicker
from kivymd.uix.selectioncontrol import MDCheckbox

from database import close, update, query, create_tables, update_footprint, get_footprint, get_current_values, categories, category_names, category_value_formats

from kivy.garden.matplotlib.backend_kivyagg import FigureCanvasKivyAgg
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta, date

from programs import program_text


# DEBUG = True means you're testing.
DEBUG = True
# Set this to True if you want to see the questions again on the welcome screen.
always_show_questions = False
# Change this to 5 or something to see the weekly text rotate every 5 seconds instead.
week_interval = 7 * 24 * 60 * 60

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

        update_footprint(values=values)
        FootprintPopup().open()
        sm.transition = SlideTransition(direction='left')


class CarbonCarousel(MDCard):
    program_number = NumericProperty(0)

    def open_p1(self, program):
        sm.current = "p1"
        sm.current_screen.set_program(program)
        if query(
                """
                SELECT COUNT(program_id)
                FROM completed_tasks
                WHERE program_id = %s
                """,
                (program,)
        ).fetchone()[0] == 5 * 4:
            ProgramCompletePopup().open()

    def open_explanations(self):
        sm.current = 'explanation'


class ChallengePopup(Popup):
    pass


class FootprintPopup(Popup):
    def display_footprint(self):
        return "{:,.2f}".format(get_footprint())


class InfoPopup(Popup):
    def to_main(self):
        sm.current = "main"


class ProgramCompletePopup(Popup):
    def to_main(self):
        sm.current = "main"


class TaskScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def set_program(self, program):
        self.program = program

    def set_week(self, week):
        self.week = week
        self.add_task_list()

    def add_task_list(self):
        self.ids.screen_of_tasks.clear_widgets()
        self.checked = query(
            """
            SELECT task_id
            FROM completed_tasks
            WHERE user_id = %s
            AND program_id = %s
            AND week_id = %s
            """,
            (1, self.program, self.week)
        )
        self.checked = list(c[0] for c in self.checked)
        if len(self.checked) == 5:
            WeekCompletePopup().open()
        for task in range(5):
            task_item = TaskListItem(task=task + 1, text="[size=13]" + program_text[self.program][self.week][task + 1] + "[/size]", is_checked=task + 1 in self.checked)
            self.ids.screen_of_tasks.add_widget(task_item)

    def to_p1(self):
        sm.current = 'p1'


class TaskListItem(ThreeLineAvatarIconListItem):
    is_checked = BooleanProperty(False)

    def __init__(self, task, **kwargs):
        super().__init__(**kwargs)
        self.task = task

    def if_active(self, state):
        if state:
            self.parent.parent.checked.append(self.task)
            command = """
                    INSERT INTO completed_tasks (user_id, program_id, week_id, task_id)
                    VALUES (%s, %s, %s, %s)
                    """
            if len(self.parent.parent.checked) == 5:
                WeekCompletePopup().open()
                if query(
                        """
                        SELECT COUNT(program_id)
                        FROM completed_tasks
                        WHERE program_id = %s
                        """,
                        (self.parent.parent.program,)
                ).fetchone()[0] == 5 * 4:
                    ProgramCompletePopup().open()
        else:
            self.parent.parent.checked.remove(self.task)
            command = """
                DELETE FROM completed_tasks
                WHERE user_id = %s
                AND program_id = %s
                AND week_id = %s
                AND task_id = %s
                """

        update(command, (1, self.parent.parent.program, self.parent.parent.week, self.task))


class RightCheckbox(IRightBodyTouch, MDCheckbox):
    pass


class P1ListItem(OneLineAvatarIconListItem):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.program = None

    def screen_select(self):
        sm.current = 'task'
        sm.current_screen.set_program(self.program)
        sm.current_screen.set_week(int(self.text.split(" ")[-1]))


class WeekCompletePopup(Popup):
    pass


class EditListItem(OneLineAvatarIconListItem):
    pass


class CategoryPopup(Popup):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ids.category_dropdown.text = category_names[0]
        self.category_menu = MDDropdownMenu(
            caller=self.ids.label,
            items=[
                {
                    "text": category,
                    "viewclass": "OneLineListItem",
                    "on_release": lambda x=category: self.change_category(x)
                } for category in category_names
            ],
            width_mult=4,
            max_height=dp(300),
        )

    def change_category(self, category):
        self.category_menu.dismiss()
        self.ids.category_dropdown.text = category


class EditPopup(Popup):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ids.update_button.bind(on_release=self.update_values)

    def update_values(self, button=None, mouse=None):
        if not self.ids.new_value.text:
            return
        self.dismiss()
        update_footprint((float(self.ids.new_value.text),), (categories[category_names.index(self.title)],))
        sm.get_screen("main").update_values()


class EditPopupCheckbox(Popup):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ids.update_button.bind(on_release=self.update_values)

    def update_values(self, button=None, mouse=None):
        if self.ids.edit_yes.state == self.ids.edit_no.state:
            return
        self.dismiss()
        update_footprint((self.ids.edit_yes.state == 'down',), (categories[category_names.index(self.title)],))
        sm.get_screen("main").update_values()


class ProgramOneScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.week_items = []
        self.add_list()

    def add_list(self):
        self.ids.p1_list.add_widget(OneLineAvatarIconListItem())
        for i in range(1, 5):
            self.week_items.append(P1ListItem(text="[size=20]" + "Week " + str(i)))
            self.ids.p1_list.add_widget(self.week_items[-1])

    def set_program(self, program):
        self.ids.program_screen_title.text = ("Environmental Philantrophy", "Destination Clean Drip", "Redefine Recycling")[program - 1]
        for item in self.week_items:
            item.program = program

    def to_main(self):
        sm.current = "main"


class ExitScreen(Screen):
    pass


class MainScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_tab = "home"
        self.update_values()
        self.display_menu = MDDropdownMenu(
            caller=self.ids.constraint,
            items=[
                {
                    "text": option,
                    "viewclass": "OneLineListItem",
                    "on_release": lambda x=option: self.choose_constraint(x)
                } for option in ("Past Year", "Past 10 Years", "All")  # ("Past Month", "Past Year", "All")
            ],
            width_mult=3,
            max_height=dp(150),
        )

    def new_data_table_size(self):
        new_values = (
                ("Category", max(Window.width * 0.099, dp(55))),  # 44 without checks.
                ("Value", max(Window.width * 0.054, 24)),
                ("Date", max(Window.width * 0.045, 20)),
        )
        return new_values

    def choose_constraint(self, option):
        self.display_menu.dismiss()
        self.ids.constraint.text = option
        self.display_values()

    @staticmethod
    def edit_title(category):
        if category_names.index(category) > 5:
            pop_up = EditPopupCheckbox()
        else:
            pop_up = EditPopup()
            if category_names.index(category) > 2:
                pop_up.ids.new_value.hint_text = "#"
        pop_up.title = category
        pop_up.open()

    def update_values(self):
        self.ids.footprint_label.text = "Carbon Footprint: {:,.2f} lbs CO2 per year".format(get_footprint() or 0)
        values = get_current_values()
        format = tuple(category_names[i] + ": " +
                       category_value_formats[i] for i in
                       range(len(categories)))

        for i in range(len(values)):
            self.ids.info_list.children[-(i + 1)].text = format[i].format(
                values[i] if i <= 5 else "Yes" if values[i] == 1 else "No")

    def display_values(self):
        self.ids.statistics.bind(minimum_height=self.ids.statistics.setter('height'))
        first_constraint = "AND submitted_at > NOW() - INTERVAL '"
        delta_time = False
        if self.ids.constraint.text == "All":
            first_constraint = ""
        elif self.ids.constraint.text == "Past Month":
            first_constraint += "1 month'"
            delta_time = timedelta(days=(date.today().replace(day=1) - timedelta(days=1)).day)
        elif self.ids.constraint.text == "Past Year":
            first_constraint += "1 year'"
            delta_time = timedelta(days=365 if date.today().year % 4 != 0 and date.today().year % 400 != 0 else 366)
        elif self.ids.constraint.text == "Past 10 Years":
            first_constraint += "10 year'"
            delta_time = timedelta(days=365.25 * 10)  # Eventually incorporate leap years.

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

        start_month, start_date, increase = None, None, None
        if len(footprint_data) > 0:
            tz = footprint_data[0][0].tzinfo
            current_date = footprint_data[0][0].year * 100 + footprint_data[0][0].month
        else:
            tz, current_date = None, None

        for i in range(len(footprint_data)):
            if not delta_time or footprint_data[i][0] > datetime.now(tz) - delta_time:
                plot_dates.append(footprint_data[i][0])
                plot_values.append(footprint_data[i][1])
            dates.append(footprint_data[i][0])
            values.append(footprint_data[i][1])
            if start_month is None and dates[-1].year * 100 + dates[-1].month < current_date:
                start_month = i
                start_date = dates[-1].year * 100 + dates[-1].month
            if start_month is not None and increase is None and (dates[-1].year * 100 + dates[-1].month < start_date or i == len(footprint_data) - 1):
                if start_month == i:
                    i += 1
                this_month = sum(values[:start_month]) / len(values[:start_month])
                last_month = sum(values[start_month:i]) / len(values[start_month:i])
                increase = (this_month - last_month) / last_month * 100

        if len(plot_dates) != 0:
            ax.plot(plot_dates, plot_values, '-o', color='#2e43ff', markersize=2)
            plt.ylabel("Carbon Footprint (lbs CO2 / year)")
            plt.xlabel("Date")
            plt.subplots_adjust(left=0.2, right=0.95, top=0.9, bottom=0.3)
            ax.set_xticklabels(ax.get_xticks(), rotation=45, ha='right')
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%b-%d %Y'))
            self.ids.statistics.add_widget(
                GraphItem(FigureCanvasKivyAgg(plt.gcf()), round(increase or 0, 2), "Carbon Footprint"))
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
            if self.ids.constraint.text == "Past Year" and i > 2:
                break
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
                        if data[index][2] != 0:
                            increase = (last_value - data[index][2]) / data[index][2] * 100
                        else:
                            increase = 100
                    if last_value is None:
                        last_value = data[index][2]
                    index += 1
                else:
                    break

            if len(dates) != 0:
                ax.plot(dates, values, '-o', color='#2e43ff', markersize=2)
                plt.ylabel(category_names[i] + (" ($)" if i <= 3 else " (mpg)" if i == 4 else ""))
                plt.xlabel("Date")
                plt.subplots_adjust(left=0.2, right=0.95, top=0.9, bottom=0.3)
                ax.set_xticklabels(ax.get_xticks(), rotation=45, ha='right')
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%b-%d %Y'))
                self.ids.statistics.add_widget(
                    GraphItem(FigureCanvasKivyAgg(plt.gcf()), round(increase or 0, 2), category_names[i]))
            plt.close(fig)

    def get_data_table_row_data(self):
        data = query(
            """
            SELECT category_id, value, submitted_at
            FROM input_values
            WHERE user_id = %s
            ORDER BY submitted_at DESC, category_id, value DESC
            """,
            (1,)
        ).fetchall()
        row_data = ((category_names[row[0] - 1], category_value_formats[row[0] - 1].format(
            row[1] if row[0] < 7 else "Yes" if row[1] == 1 else "No"), row[2].strftime("%b-%d %Y")) for row in data)

        return row_data

    def get_first_index(self):
        current_rows_text = self.data_table.children[0].children[0].children[2].text.split(" ")[0].split("-")
        current_rows_text = tuple(int(x) for x in current_rows_text)
        return current_rows_text[0]

    def on_row_press(self, table, row):
        first_index = self.get_first_index()
        index = first_index + row.index // (self.data_table.table_data.rows_num - 2)
        if row.ids.check.state == "down":
            self.selected_rows.append((index, row))
        else:
            if (index, row) in self.selected_rows:
                self.selected_rows.remove((index, row))

    def display_data_table(self):
        self.data_table = MDDataTable(
            check=True,
            use_pagination=True,
            pos_hint={'center_x': 0.5, 'center_y': 0.57},
            size_hint=(0.95, 0.8),
            column_data=self.new_data_table_size(),
            row_data=self.get_data_table_row_data(),
            elevation=5,
        )
        self.data_table.bind(on_row_press=self.on_row_press)

        self.data_table.children[0].children[2].children[0].children[-1].children[1].remove_widget(self.data_table.children[0].children[2].children[0].children[-1].children[1].children[1])
        self.data_table.children[0].children[2].children[0].children[-1].children[1].children[0].text = " " * 12 + self.data_table.children[0].children[2].children[0].children[-1].children[1].children[0].text
        self.ids.data_table.add_widget(self.data_table)
        self.selected_rows = []

    def data_table_button_pressed(self, function):
        rows = self.selected_rows
        self.ids.error_text.text = "   "
        if len(rows) == 0 and function != "Add":
            self.ids.error_text.text += "Please select a row."
            return
        elif function == "Edit" and len(rows) > 1:
            self.ids.error_text.text += "Please only select one row to edit."
            return

        if function != "Add":
            self.selected_rows = []
            self.data_table.table_data.select_all("normal")

        if function == "Delete":
            indices = [row[0] for row in rows]
            dates = update(
                f"""
                DELETE FROM input_values
                WHERE user_id = %s AND (category_id, value, submitted_at) IN (
                    SELECT category_id, value, submitted_at
                    FROM (
                        SELECT *, ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY submitted_at DESC, category_id, value DESC) as row_number
                        FROM input_values
                    ) as ranked
                    WHERE row_number IN ({", ".join(str(index) for index in indices)})
                )
                RETURNING submitted_at, category_id, value
                """,
                (1,)
            ).fetchall()

            for i in range(len(dates)):
                if i > 0 and dates[i][0] == dates[i - 1][0]:
                    continue
                submitted_at_max = query(
                    """
                    SELECT submitted_at
                    FROM input_values
                    WHERE user_id = %s AND category_id = %s AND submitted_at >= %s
                    LIMIT 1
                    """,
                    (1, dates[i][1], dates[i][0])
                ).fetchone()
                submitted_at_max = submitted_at_max[0] if submitted_at_max else datetime.now(dates[i][0].tzinfo)
                update(
                    """
                    DELETE FROM footprints
                    WHERE user_id = %s AND submitted_at >= %s AND submitted_at < %s
                    """,
                    (1, dates[i][0], submitted_at_max)
                )
                update_footprint(tuple(), tuple(), dates[i][0])
                if dates[i][0] != submitted_at_max:
                    update_footprint(tuple(), tuple(), submitted_at_max)

            indices.sort(reverse=True)
            for index in indices:
                self.data_table.remove_row(self.data_table.row_data[index - 1])
        elif function == "Edit":
            index = rows[0][0]
            category_index = category_names.index(rows[0][1].text)
            if category_index <= 5:
                pop_up = EditPopup()
                if category_index > 2:
                    pop_up.ids.new_value.hint_text = "#"
            else:
                pop_up = EditPopupCheckbox()

            pop_up.title = rows[0][1].text

            def edit_value(button=None):
                if isinstance(pop_up, EditPopup):
                    if not pop_up.ids.new_value.text:
                        return
                    new_value = pop_up.ids.new_value.text
                elif isinstance(pop_up, EditPopupCheckbox):
                    if pop_up.ids.edit_yes.state == pop_up.ids.edit_no.state:
                        return
                    new_value = pop_up.ids.edit_yes.state == 'down'

                pop_up.dismiss()
                old_data = self.data_table.row_data[index - 1]
                self.data_table.update_row(old_data, (old_data[0], category_value_formats[category_index].format(float(new_value) if category_index <= 5 else "Yes" if new_value else "No"), old_data[2]))
                dates = update(
                    """
                    UPDATE input_values
                    SET value = %s
                    WHERE user_id = %s AND (category_id, value, submitted_at) IN (
                        SELECT category_id, value, submitted_at
                        FROM (
                            SELECT *, ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY submitted_at DESC, category_id, value DESC) as row_number
                            FROM input_values
                        ) as ranked
                        WHERE row_number = %s
                    )
                    RETURNING submitted_at
                    """,
                    (float(new_value), 1, index)
                ).fetchall()

                for i in range(len(dates)):
                    if i > 0 and dates[i][0] == dates[i - 1][0]:
                        continue
                    update(
                        """
                        DELETE FROM footprints
                        WHERE user_id = %s AND submitted_at = %s
                        """,
                        (1, dates[i][0])
                    )
                    update_footprint(tuple(), tuple(), dates[i][0])

            pop_up.children[0].children[0].children[0].children[0].unbind(on_release=pop_up.update_values)
            pop_up.children[0].children[0].children[0].children[0].bind(on_release=edit_value)
            pop_up.open()
        elif function == "Add":
            date_dialog = MDDatePicker(
                max_date=date.today(),
                min_date=date(date.today().year - 20, 1, 1),
                min_year=date.today().year - 20,
                max_year=date.today().year,
                primary_color=(113/255, 201/255, 135/255, 1),
                selector_color=(113/255, 201/255, 135/255, 1),
                text_button_color=(0, 0, 0, 1),
            )

            date_dialog.children[0].remove_widget(date_dialog.children[0].children[7])
            for date_item in date_dialog.children[0].children[2].children:
                try:
                    if date_item.is_today:
                        date_item.is_today = False
                        date_item.children[0].text_color = (0, 0, 0, 1)
                        break
                except AttributeError:
                    continue

            def on_save(instance, date_value, date_range):
                tz = query(
                    """
                    SELECT submitted_at
                    FROM footprints
                    WHERE user_id = %s
                    LIMIT 1
                    """,
                    (1,)
                ).fetchone()[0].tzinfo
                date_value = datetime.combine(date_value, datetime.max.time()) if date_value != date.today() else datetime.now(tz)
                choose_category = CategoryPopup()

                def on_category_select(instance=None):
                    category_index = category_names.index(choose_category.ids.category_dropdown.text)
                    if category_index <= 5:
                        pop_up = EditPopup()
                        if category_index > 2:
                            pop_up.ids.new_value.hint_text = "#"
                    else:
                        pop_up = EditPopupCheckbox()

                    pop_up.title = category_names[category_index]
                    pop_up.open()
                    choose_category.dismiss()

                    def add_value(button=None):
                        if isinstance(pop_up, EditPopup):
                            if not pop_up.ids.new_value.text:
                                return
                            new_value = pop_up.ids.new_value.text
                        elif isinstance(pop_up, EditPopupCheckbox):
                            if pop_up.ids.edit_yes.state == pop_up.ids.edit_no.state:
                                return
                            new_value = pop_up.ids.edit_yes.state == 'down'

                        pop_up.dismiss()

                        update(
                            """
                            INSERT INTO input_values (user_id, category_id, value, submitted_at)
                            VALUES (%s, %s, %s, %s)
                            """,
                            (1, category_index + 1, float(new_value), date_value)
                        )
                        update_footprint(tuple(), tuple(), date_value)
                        new_row = (category_names[category_index], category_value_formats[category_index].format(float(new_value) if category_index <= 5 else "Yes" if new_value else "No"), date_value.strftime("%b-%d %Y"))
                        self.data_table.row_data = self.get_data_table_row_data()

                    pop_up.children[0].children[0].children[0].children[0].unbind(on_release=pop_up.update_values)
                    pop_up.children[0].children[0].children[0].children[0].bind(on_release=add_value)

                choose_category.ids.continue_button.bind(on_release=on_category_select)
                choose_category.open()

            date_dialog.bind(on_save=on_save)
            date_dialog.open()

    def info_popup_open(self):
        InfoPopup().open()


class TableButton(MDRaisedButton):
    pass


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
        program_one = ProgramOneScreen(name='p1')
        task_screen = TaskScreen(name="task")
        sm.add_widget(starting_screen)
        sm.add_widget(welcome_screen)
        sm.add_widget(main_screen)
        sm.add_widget(program_one)
        sm.add_widget(task_screen)

        menu_items = [
            {
                "viewclass": "OneLineListItem",
                "text": "Exit App",
                "height": dp(40),
                "on_release": lambda x="Exit App": self.exit_app(x),
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

        self.snackbar = CustomSnackbar(
            text="",
            bg_color=(50 / 255, 100 / 255, 50 / 255, 1),
            icon="information",
            snackbar_x="10dp",
            snackbar_y="10dp",
            duration=2,
            buttons=[MDFlatButton(text="[color=#ffffff]OK[/color]", text_color=(1, 1, 1, 1))]
        )
        self.snackbar.size_hint_x = (Window.width - (self.snackbar.snackbar_x * 2)) / Window.width

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

    def open_menu(self, button):
        self.menu.caller = button
        self.menu.open()

    def exit_app(self, text_item):
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

        self.snackbar.text = text_item
        self.snackbar.open()

        Clock.schedule_once(close_application, 4)
        close()

    def menu_callback2(self, text_item):
        self.snackbar.text = text_item
        self.snackbar.open()


if __name__ == '__main__':
    create_tables()
    CarbonomixApp().run()
