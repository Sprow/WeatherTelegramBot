from telegram.ext import Updater, CommandHandler
import threading
from datetime import datetime
from pytz import timezone

from db import Storage
from parse import ParseWeather

# import logging


class WeatherTelegramBot:
    def __init__(self, api_key):
        # logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
        # logger = logging.getLogger(__name__)
        self.datetime_now = datetime.now(timezone('Europe/Kiev'))
        self.dict_of_available_cities = {
            "Vinnitsa": "Винница",
            "Dnipropetrovsk": "Днепропетровск",
            "Bilatserkva": "Белая Церковь",
            "Donetsk": "Донецк",
            "Zhytomyr": "Житомир",
            "Zaporizhzhia": "Запорожье",
            "Ivanofrankivsk": "Ивано-Франковск",
            "Kyiv": "Киев",
            "Kirovohrad": "Кировоград",
            "Luhansk": "Луганск",
            "Lutsk": "Луцк",
            "Lviv": "Львов",
            "Mikolaiv": "Николаев",
            "Odesa": "Одесса",
            "Poltava": "Полтава",
            "Rivne": "Ровно",
            "Simferopol": "Симферополь",
            "Sumy": "Сумы",
            "Ternopil": "Тернополь",
            "Uzhgorod": "Ужгород",
            "Kharkiv": "Харьков",
            "Kherson": "Херсон",
            "Khmelnytskyi": "Хмельницк",
            "Chercasy": "Черкассы",
            "Chernigiv": "Чернигов",
            "Chernivtsi": "Черновцы",
            "Brovary": "Браворы",
            "Bucha": "Буча",
            "Fastiv": "Фастов",
        }
        self.list_of_set_city_commands = ['set_Vinnitsa', 'set_Dnipropetrovsk', 'set_Bilatserkva', 'set_Donetsk',
                                          'set_Zhytomyr', 'set_Zaporizhzhia', 'set_Ivanofrankivsk', 'set_Kyiv',
                                          'set_Kirovohrad', 'set_Luhansk', 'set_Lutsk', 'set_Lviv', 'set_Mikolaiv',
                                          'set_Odesa', 'set_Poltava', 'set_Rivne', 'set_Simferopol', 'set_Sumy',
                                          'set_Ternopil', 'set_Uzhgorod', 'set_Kharkiv', 'set_Kherson',
                                          'set_Khmelnytskyi', 'set_Chercasy', 'set_Chernigiv', 'set_Chernivtsi',
                                          'set_Brovary', 'set_Bucha', 'set_Fastiv']
        self.storage = Storage()
        self.parse_weather = ParseWeather()
        self.cities_to_parse = self.storage.cities_where_users_live_list()
        self.updater = Updater(api_key)
        self.dp = self.updater.dispatcher
        self.dp.add_handler(CommandHandler('start', self.start))
        self.dp.add_handler(CommandHandler('help', self.help))
        self.dp.add_handler(CommandHandler('w', self.weather_for_12_hours))
        self.dp.add_handler(CommandHandler('w24', self.weather_for_24_hours))
        self.dp.add_handler(CommandHandler('r', self.rain_for_12_hours))
        self.dp.add_handler(CommandHandler('r24', self.rain_for_24_hours))
        self.dp.add_handler(CommandHandler('set', self.set_weather_posting_time))
        self.dp.add_handler(CommandHandler(self.list_of_set_city_commands, self.set_city))
        self.dp.add_handler(CommandHandler('city_list', self.show_city_list))
        self.updater.start_polling()

        self.scan_db(self.updater.bot)
        self.rain_notification(self.updater.bot)
        self.parse_all_cities_where_users_live()

    def start(self, bot, update):  # /start
        self.storage.add_user(update.message.from_user.id)
        update.message.reply_text('Для того что бы включить предупреждение о дождях выберите город \n'
                                  '/city_list - покажет вам список доступных городов \n'
                                  'когда вы выберите город вы также сможете установить \n'
                                  'время для ежедневной рассылки прогноза погоды \n'
                                  'для этого напишите /set часы минуты'
                                  'остальные команды вы можете узнать написав /help')

    def scan_db(self, bot):
        user_list = self.storage.user_notification_scan()
        if len(user_list) != 0:
            hour_now = self.datetime_now.hour
            if 24 - hour_now > 12:
                hours_limit = 24 - hour_now
            else:
                hours_limit = 12
            for user in user_list:
                text_message = self.storage.weather_for_x_hours(hours_limit, user[0])
                bot.send_message(chat_id=user[0], text=text_message)

        threading.Timer(60.0, lambda: self.scan_db(self.updater.bot)).start()

    def parse_all_cities_where_users_live(self):
        for city in self.cities_to_parse.copy():
            self.parse_weather.parse(city)
        threading.Timer(360.0, self.parse_all_cities_where_users_live).start()

    def rain_notification(self, bot):
        minutes_now = int(self.datetime_now.strftime("%M"))
        if 50 <= minutes_now <= 59:
            result = self.storage.rain_search()
            if result:
                users, dict_of_messages = result[0], result[1]
                # print(users, '\n')
                # print(dict_of_messages)
                for user in users:
                    bot.send_message(chat_id=user[0], text=dict_of_messages[user[1]])
        threading.Timer(120.0, lambda: self.rain_notification(self.updater.bot)).start()

    def help(self, bot, update):  # /help
        update.message.reply_text('/w - погода на 12 часов \n'
                                  '/w24 - погода на 24 часа \n'
                                  '/r - дожди в ближайшие 12 часов \n'
                                  '/r24 - дожди в ближайшие 24 часа \n'
                                  '/city_list - список городов \n'
                                  '/set часы минуты - устанавливает время рассылки прогноза погоды на день')
        self.storage.add_user(update.message.from_user.id)

    def weather_for_12_hours(self, bot, update):  # /w
        update.message.reply_text(self.storage.weather_for_x_hours(12, update.message.from_user.id))
        self.storage.add_user(update.message.from_user.id)

    def weather_for_24_hours(self, bot, update):  # /w24
        update.message.reply_text(self.storage.weather_for_x_hours(24, update.message.from_user.id))
        self.storage.add_user(update.message.from_user.id)

    def rain_for_12_hours(self, bot, update):  # /r
        update.message.reply_text(self.storage.rain_for_x_hours(12, update.message.from_user.id))
        self.storage.add_user(update.message.from_user.id)

    def rain_for_24_hours(self, bot, update):  # /r24
        update.message.reply_text(self.storage.rain_for_x_hours(24, update.message.from_user.id))
        self.storage.add_user(update.message.from_user.id)

    def set_weather_posting_time(self, bot, update):  # /set hours min
        self.storage.add_user(update.message.from_user.id)
        set_error_massage = 'неправильный ввод \n ' \
                            '/set часы минуты \n ' \
                            'Пример: /set 14 30 - устанавливает время ежедневной рассылки на 14:30 \n' \
                            'или /set 0 если хотите отменить рассылку \n'

        args = update.message.text.split()[1:]
        if len(args) == 1:
            if args[0] == '0':
                self.storage.change_weather_posting_time(update.message.from_user.id, None)
                update.message.reply_text('теперь вам не будет приходить ежедневый прогоз погоды')
            else:
                update.message.reply_text(set_error_massage)
        else:
            try:
                hours = int(args[0])
                minuts = int(args[1])

                if 0 <= hours <= 23 and 0 <= minuts <= 59:
                    result = hours * 100 + minuts
                    self.storage.change_weather_posting_time(update.message.from_user.id, result)
                    update.message.reply_text(
                        'Время ежедневной рассылки прогноза погоды {}:{}'.format(args[0], args[1]))
                else:
                    update.message.reply_text(set_error_massage)
            except(ValueError, IndexError):
                update.message.reply_text(set_error_massage)

    def set_city(self, bot, update):
        city = update.message.text.split('_')[1]
        if city not in self.cities_to_parse:
            self.cities_to_parse.add(city)
            self.parse_weather.parse(city)

        is_deleted = self.storage.change_city(update.message.from_user.id, city)
        if is_deleted:
            self.cities_to_parse.remove(is_deleted)  # remove old user city because no one use it

        update.message.reply_text('Вы выбрали город {}'.format(self.dict_of_available_cities[city]))
        self.rain_for_12_hours(bot, update)

    def show_city_list(self, bot, update):
        city_list_massege = 'Вам будет приходить оповещения по выбраному городу \n'
        for key, val in self.dict_of_available_cities.items():
            city_list_massege += '/set_' + key + ' - ' + val + '\n'
        update.message.reply_text(city_list_massege)

    def wait(self):
        self.updater.idle()

bot = WeatherTelegramBot('886635819:AAHxeR4XaURy33uPnCgGfWGoPUeaApqShO8')
bot.wait()

# if __name__ == '__main__':
#     try:
#         # bot = WeatherTelegramBot('your api key')
#         bot = WeatherTelegramBot('886635819:AAHxeR4XaURy33uPnCgGfWGoPUeaApqShO8')
#         bot.wait()
#     except KeyboardInterrupt:
#         exit()
