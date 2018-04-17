import telebot
from telebot import types
import cherrypy
import requests
import os
import config


bot = telebot.TeleBot(config.token)

url = "https://geocode-maps.yandex.ru/1.x/?format=json&geocode={text}&key={key}&lang={lang}"

@bot.message_handler(commands=['getpid'])
def getpid_message(message):
    markup = types.ReplyKeyboardRemove(selective=True)
    bot.send_message(message.chat.id, str(os.getpid()), reply_markup=markup)


@bot.message_handler(commands=['start', 'help'])
def start_message(message):
    print (message)
    mci = message.chat.id
    ms = message.text
    s = ms.split(' ')
    if len(s) == 2:
        s = (s[1]).split('_')
        if len(s) == 2 and (s[0])[:3] == 'lat' and (s[1])[:3] == 'lon':
            bot.send_location(mci, (s[0])[3:], (s[1])[3:])
    else:
        bot.send_message(message.chat.id, 'Bot able to find a point on the map by place name. Supports inline search.')


@bot.message_handler(content_types=['text'])
def some_text(message):
    mci = message.chat.id
    text = message.text
    bot.send_chat_action(message.chat.id, 'find_location')
    
    request = url.format(text=text, key=config.ya_key, lang='en')
    j = (requests.get(request)).json()
    try:
        city_point = j['response']['GeoObjectCollection'][
            'featureMember'][0]['GeoObject']['Point']['pos']

        lon, lat = city_point.split(' ')

        bot.send_location(mci, lat, lon)
        bot.send_message(mci, 'telegram.me/mapnbot?start=lat'+str(lat)+'_lon'+str(lon), disable_web_page_preview=True)
    except:
        bot.send_message(mci, "Not found.")


@bot.inline_handler(lambda query: len(query.query) > 0)
def no_empty_query(query):
    mci = query.from_user.id
    text = query.query
    btn_list = []

    request = url.format(text=text, key=config.ya_key, lang='en')
    j = (requests.get(request)).json()

    city_list = j['response']['GeoObjectCollection']['featureMember']
    i = 1
    for city in city_list:
        lon, lat = (city['GeoObject']['Point']['pos']).split(' ')
        try:
            name_city = (city['GeoObject']['description']) + \
                ', ' + (city['GeoObject']['name'])
        except:
            name_city = city['GeoObject']['name']

        btn_list.append(types.InlineQueryResultLocation(
            id=str(i), latitude=float(lat), longitude=float(lon), title=name_city))
        i += 1
    try:
        bot.answer_inline_query(inline_query_id=query.id,
                                results=btn_list, cache_time=1)
    except Exception as e:
        print (e)


class WebhookServer(object):

    @cherrypy.expose
    def index(self):
        length = int(cherrypy.request.headers['content-length'])
        json_string = cherrypy.request.body.read(length)
        json_string = json_string.decode("utf-8")
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''

if __name__ == '__main__':
    print ('mapnbot start...')
    if config.isPool:
        bot.polling(none_stop=True)
    else:    
        cherrypy.config.update({
            'server.socket_host': config.socket_host,
            'server.socket_port': config.socket_port,
            'engine.autoreload.on': False
        })
        cherrypy.quickstart(WebhookServer(), '/', {'/': {}})
