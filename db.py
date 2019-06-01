import psycopg2
from datetime import datetime, timedelta
import os


class Storage:
    def __init__(self):
        # self.conn = psycopg2.connect(dbname='weather',
        #                              user='postgres',
        #                              password='your db pass',
        #                              host='127.0.0.1')    # use for localhost

        #  this one for heroku
        self.DATABASE_URL = os.environ['DATABASE_URL']
        self.conn = psycopg2.connect(self.DATABASE_URL, sslmode='require')

        cursor = self.conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS weather (id smallint, comment varchar(150),"
                       " temperature smallint , dateRow timestamp, rain boolean, city varchar(30));")
        cursor.execute("CREATE TABLE IF NOT EXISTS user_list (user_id int primary key, notification_time smallint,"
                       " last_sent timestamp, last_sent_rain timestamp, city varchar(30));")
        cursor.close()
        self.conn.commit()

    def seed_weather_table(self, weather_comment, temperature, city):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM weather WHERE city=%s", (city,))
        if len(cursor.fetchall()) != 0:
            for i in range(48):  # i - weather for one hour
                if weather_comment[i].find('дождь') != -1:
                    rain = True
                else:
                    rain = False

                if i < 24:
                    today = datetime.now()
                    date = str(today.replace(hour=i, minute=0, second=0, microsecond=0))
                else:
                    tomorrow = datetime.now() + timedelta(1)
                    date = str(tomorrow.replace(hour=i-24, minute=0, second=0, microsecond=0))

                cursor.execute("UPDATE weather SET comment=%s, temperature=%s, daterow=%s, rain=%s "
                               "WHERE city=%s AND id=%s",
                               (weather_comment[i], temperature[i], date, rain, city, str(i+1)))
        else:
            for i in range(48):  # i - weather for one hour
                if weather_comment[i].find('дождь') != -1:
                    rain = True
                else:
                    rain = False
                if i < 24:
                    today = datetime.now()
                    date = str(today.replace(hour=i, minute=0, second=0, microsecond=0))
                else:
                    tomorrow = datetime.now() + timedelta(1)
                    date = str(tomorrow.replace(hour=i - 24, minute=0, second=0, microsecond=0))

                cursor.execute("INSERT INTO weather VALUES (%s, %s, %s, %s, %s, %s)",
                               (str(i+1), weather_comment[i], temperature[i], date, rain, city,))

        cursor.close()
        self.conn.commit()

    def weather_for_x_hours(self, hours_limit, user_id):
        cursor = self.conn.cursor()
        time = datetime.now() - timedelta(hours=1)

        cursor.execute("SELECT city FROM user_list WHERE user_id=%s", (user_id,))
        city = cursor.fetchone()[0]
        if city is None:
            error_message = 'У вас не выбаран город \n' \
                            'напишите /city_list для ознакомления со списком городов'
            return error_message

        cursor.execute("SELECT dateRow, temperature, comment, rain FROM weather "
                       "WHERE dateRow >= %s AND city=%s LIMIT %s", (time, city, hours_limit))
        records = cursor.fetchall()
        date = datetime.now().strftime("%m/%d/%Y, %H:%M")
        weather_str = 'Дата: ' + date + '\n'
        for i in records:
            time = i[0].strftime("%H:%M")
            if i[1] > 0:
                temperature = '+' + str(i[1]) + '°'
            else:
                temperature = str(i[1]) + '°'
            comment = i[2]
            if i[3]:
                is_rain = '☂'
            else:
                is_rain = ''

            weather_str += time + ' | ' + temperature + ' | ' + comment + ' ' + is_rain + '\n'

        cursor.close()
        return weather_str

    def rain_for_x_hours(self, hours_limit, user_id):
        cursor = self.conn.cursor()
        time = datetime.now() - timedelta(hours=1)
        time_plus_x_hours = time + timedelta(hours=hours_limit)

        cursor.execute("SELECT city FROM user_list WHERE user_id=%s", (user_id,))
        city = cursor.fetchone()[0]
        if city is None:
            error_message = 'У вас не выбаран город \n' \
                            'напишите /city_list для ознакомления со списком городов'
            return error_message

        cursor.execute("SELECT dateRow, temperature, comment FROM weather WHERE "
                       "rain = TRUE AND city=%s AND dateRow BETWEEN %s AND %s;", (city, time, time_plus_x_hours))
        records = cursor.fetchall()
        date = datetime.now().strftime("%m/%d/%Y, %H:%M")
        rain_str = 'Дата: ' + date + '\n'
        if records:
            for i in records:
                time = i[0].strftime("%H:%M")
                if i[1] > 0:
                    temperature = '+' + str(i[1]) + '°'
                else:
                    temperature = str(i[1]) + '°'
                comment = i[2]
                is_rain = '☂'

                rain_str += time + ' | ' + temperature + ' | ' + comment + ' ' + is_rain + '\n'
        else:
            rain_str += 'в ближайшие {} часов дождя не будет'.format(hours_limit)
        cursor.close()
        return rain_str

    def add_user(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO user_list (user_id, notification_time) VALUES (%s, 0)"
                       " ON CONFLICT (user_id) DO NOTHING", (user_id,))
        cursor.close()
        self.conn.commit()

    def change_weather_posting_time(self, user_id, time):
        datetime_now = datetime.now()
        time_now = datetime_now.hour*100+datetime_now.minute
        cursor = self.conn.cursor()
        cursor.execute("UPDATE user_list SET notification_time=%s WHERE user_id=%s", (time, user_id))
        if time_now <= time:
            cursor.execute("UPDATE user_list SET last_sent=NULL WHERE user_id=%s", (user_id,))
        cursor.close()
        self.conn.commit()

    def change_city(self, user_id, city):
        cursor = self.conn.cursor()
        cursor.execute("SELECT city FROM user_list WHERE user_id=%s", (user_id,))
        old_user_city = cursor.fetchone()[0]
        cursor.execute("UPDATE user_list SET city=%s, last_sent_rain=NULL WHERE user_id=%s", (city, user_id))
        cursor.execute("SELECT user_id FROM user_list WHERE city=%s LIMIT 1", (old_user_city,))
        if cursor.fetchone() is None:
            cursor.execute("DELETE FROM weather WHERE city=%s", (old_user_city,))
            cursor.close()
            self.conn.commit()
            return old_user_city
        cursor.close()
        self.conn.commit()
        return False

    def user_notification_scan(self):
        dn = datetime.now()
        one_day_ago = dn - timedelta(days=1)
        time_now = dn.hour*100+dn.minute
        cursor = self.conn.cursor()
        cursor.execute("SELECT user_id FROM user_list WHERE last_sent<%s OR last_sent IS NULL "
                       "AND notification_time BETWEEN 1 AND %s",
                       (one_day_ago, time_now))
        records = cursor.fetchall()
        if records:
            for user in records:
                cursor.execute("UPDATE user_list SET last_sent=%s WHERE user_id=%s",
                               (dn, user[0]))
        cursor.close()
        self.conn.commit()
        return records

    def cities_where_users_live_list(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT DISTINCT city FROM user_list")
        records = cursor.fetchall()
        set_of_cities = set()
        if len(records) > 0:
            [set_of_cities.add(i[0]) for i in records]

        return set_of_cities

    def rain_search(self):
        cursor = self.conn.cursor()
        dn = datetime.now()
        min_time = dn - timedelta(minutes=5, hours=1)
        max_time = dn + timedelta(minutes=5) - timedelta(hours=1)
        min_time2 = dn - timedelta(minutes=5)
        max_time2 = dn + timedelta(minutes=5)

        cursor.execute("SELECT city FROM weather WHERE rain = TRUE AND"
                       " city NOT IN (SELECT city FROM weather WHERE dateRow BETWEEN %s AND %s AND rain is TRUE) "
                       "AND dateRow BETWEEN %s AND %s",
                       (min_time, max_time, min_time2, max_time2))
        rain = cursor.fetchall()
        if len(rain) != 0:
            one_hour_ago = dn - timedelta(hours=1)
            cursor.execute("SELECT user_id, city FROM user_list WHERE last_sent_rain<%s OR last_sent_rain IS NULL",
                           (one_hour_ago,))

            users_that_need_notification = cursor.fetchall()
            dict_of_messages = {}
            cursor.execute("UPDATE user_list SET last_sent_rain=%s WHERE "
                           "user_id IN (SELECT user_id FROM user_list "
                           "WHERE last_sent_rain<%s OR last_sent_rain IS NULL)", (dn, one_hour_ago))
            for user in users_that_need_notification:
                dict_of_messages[user[1]] = ''

            for key, val in dict_of_messages.items():
                rain = True
                message = 'Скоро дождь \n'
                n = 1
                if rain:
                    hours_from_now = datetime.now() + timedelta(hours=n)
                    cursor.execute("SELECT dateRow, temperature, comment, id, rain FROM weather "
                                   "WHERE dateRow > %s LIMIT 2", (hours_from_now,))
                    records = cursor.fetchall()

                    time = records[0][0].strftime("%H:%M")
                    if records[0][1] > 0:
                        temperature = '+' + str(records[0][1]) + '°'
                    else:
                        temperature = str(records[0][1]) + '°'
                    comment = records[0][2]
                    is_rain = '☂'

                    message += time + ' | ' + temperature + ' | ' + comment + ' ' + is_rain + '\n'
                    n += 1
                    if len(records) == 1:
                        rain = False
                    else:
                        if records[1][4] is False:
                            rain = False
                    dict_of_messages[key] = message

            return users_that_need_notification, dict_of_messages
