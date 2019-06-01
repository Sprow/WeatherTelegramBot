import requests
import bs4
import re
from db import Storage

#  url example  'https://www.meteoprog.ua/ru/meteograms/CITY/'
#  url example  'https://www.meteoprog.ua/ru/meteograms/Kyiv/'


class ParseWeather:
    def __init__(self):
        self.storage = Storage()

    def parse(self, city):
        if city:
            url = 'https://www.meteoprog.ua/ru/meteograms/' + city
            data = requests.get(url)
            b = bs4.BeautifulSoup(data.text, "html.parser")
            table = b.select('tbody .temp', limit=48)  # weather for 48 hours
            weather_comment = []
            temperature = []
            for i in table:
                weather_for_one_hour = re.search(r'title="([^"]*)', str(i))
                weather_comment.append(weather_for_one_hour.group(1))
                temperature_for_one_hour = re.search(r'meteoTemp">(.[\d]*)', str(i))
                temperature.append(str(temperature_for_one_hour.group(1)))

            self.storage.seed_weather_table(weather_comment, temperature, city)
