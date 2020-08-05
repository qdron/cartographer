#!/usr/bin/env python3
# -*- coding: utf-8 -*- 
import discord
import logging
import requests
import json
import os.path
import os
import time
import asyncio
from bs4 import BeautifulSoup
from threading import Thread
from discord.ext import tasks, commands

# Logger
logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
handler = logging.FileHandler(filename='/var/log/cartographer.log', encoding='utf-8', mode='a')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)
logger.info('\n')
logger.info('--- start bot ---')

# Get token
TOKEN = os.getenv('CARTOGRAPHER_TOKEN')
if TOKEN == None:   
    print("Token is not setted")
    logger.error("Token is not setted")
    exit()

# Bot 
bot = commands.Bot(command_prefix='!')

config_file_path = "/etc/app/cartographer.json"
config = {
    "last_post": "",
    "last_post_EN": "",
    "news_channel_id": 0,
    "news_channel_id_EN": 0,
    "info_channel_id": 0,
    "info_channel_id_EN": 0,
    "guild": 0,
    "role_mapmaker": 0,
    "test_channel_id": 0,
}           

def save():
    with open(config_file_path, "w") as write_file:
        json.dump(config, write_file, indent=4)
        logger.info("Config saved")

def load():
    if not os.path.exists(config_file_path):
        logger.warning('Config file not found. Using default values')
        return

    with open(config_file_path, "r") as read_file:
        global config
        config = json.load(read_file)
        logger.info("Config loaded")
        logger.info(config)

class MyCog(commands.Cog):  
    def __init__(self):
        self.bot = bot
        self.news_updater.start()
        self.news_updater_en.start()

    def cog_unload(self):
        self.news_updater.cancel()
        self.news_updater_en.cancel()

    @tasks.loop(minutes=5.0)
    async def news_updater(self):
        logger.info("Udpating news from 'Клуб народкой карты'")
        news_channel = bot.get_channel(config["news_channel_id"])
        if news_channel == None:
            return
        base_url = 'https://yandex.ru'
        URL = 'https://yandex.ru/blog/narod-karta'
        page = requests.get(URL)
        soup = BeautifulSoup(page.content, 'html.parser')
        posts = []
        logger.info("Last loaded post: %s" % config["last_post"])

        for post in soup.find_all(class_='b-post_yablogs-club _init'):
            em = discord.Embed()
            em.title = post.find('div', class_='b-post_yablogs-club__title').text
            avatar = post.find('img', class_='b-round-avatar__image')['src']
            author = post.find('div', class_='b-user-name_yablogs').text
            em.set_author(name=author, icon_url=avatar)
            em.url = base_url + post.find('a', class_='b-post_yablogs-club__title-link')['href']
            em.description = post.find('section', class_='b-article-text_yablogs-club _init').text
            posts.insert(0, em)

        new_posts = []
        for em in posts:
            new_posts.append(em)
            if config["last_post"] == em.url:
                new_posts.clear()
                logger.debug("Finded last published post '%s'. Cleanup list." % em.title)

        logger.debug("New posts count: %d" % len(new_posts))

        for em in new_posts:
            await news_channel.send(embed=em)
            config["last_post"] = em.url
            logger.debug(" - %s" % em.title)

        logger.info("List new post updated")

        save()

    @tasks.loop(hours=3.0)
    async def news_updater_en(self):
        logger.info("Udpating news from 'Changes and additions to the Mapping Rules'" )
        news_channel_en = bot.get_channel(config["news_channel_id_EN"])        
        if news_channel_en == None:
            logger.error("Unspecified en news channel")
            return
        base_url = 'https://yandex.com'
        URL = 'https://yandex.com/support/mapeditor/reliz.html'
        page = requests.get(URL)
        soup = BeautifulSoup(page.content, 'html.parser')
        posts = []
        count = 10
        logger.info("Last loaded post: %s" % config["last_post_EN"])

        for post in soup.find_all(class_='doc-c-list'):
            if (post.name == 'dt'):
                print(post.text)
                em = discord.Embed()
                em.title = post.text
                
            
            if (post.name == 'dd'):
                count = count - 1
                lines = []                
                for paragraph in post.find_all('p'):
                    text = paragraph.text
                    for link in paragraph.find_all('a'):
                        prepared_link = "[" + link.text + "](" + base_url + link['href'] + ")"
                        text = text.replace(link.text, prepared_link)
                    lines.append(text)

                em.description = "\n".join(lines)
                posts.insert(0, em)

            if count == 0:
                break


        new_posts = []
        for em in posts:
            new_posts.append(em)
            if config["last_post_EN"] == em.title:
                new_posts.clear()
                logger.debug("Finded last published post '%s'. Cleanup list." % em.title)

        logger.debug("New posts count: %d" % len(new_posts))

        for em in new_posts:
            await news_channel_en.send(embed=em)
            config["last_post_EN"] = em.title
            logger.debug(" - %s" % em.title)

        logger.info("List new post updated (EN)")

        save()

    @news_updater.before_loop
    async def before_news_updater(self):
        await bot.wait_until_ready()   

    @news_updater_en.before_loop
    async def before_new_updater_en(self):
        await bot.wait_until_ready()   

@bot.event
async def on_ready():
    logger.info("--- Logged in as '%s'" % bot.user.name )

# @bot.event
# async def on_member_join(member):
#     logger.info("New member: '%s'" % member.display_name)
#     server_id = int(config["guild"])
#     guild = bot.get_guild(server_id)
#     if guild == None:
#         logger.error("Get guild failed")
#         return 
#     role_for_newbie = guild.get_role(config["newbie_role"])
#     if role_for_newbie == None:
#         logger.error("Get role failed")
#         return
#     try:
#         await member.add_roles(role_for_newbie, atomic=True)
#     except Exception as ex:
#         logger.error("Error on add roles. {0}".format(ex))
#     else:
#         logger.info("Member '%s' assigned to role: '%s'" % (member.name, role_for_newbie.name))

@bot.command(name='правила')
async def search_in_rules(ctx, *args):
    if ctx.channel.id != config["info_channel_id"] and ctx.channel.id != ["test_channel_id"]:
        return

    logger.info("Search in mapping rules. Request: '%s'" %  ' '.join(args))
    base_url = 'https://yandex.ru'
    URL = 'https://yandex.ru/support/search-results/?service=nmaps&query='
    search = "+".join(args)
    logger.info("search url: %s" % (URL + search))
    page = requests.get(URL + search)
    soup = BeautifulSoup(page.content, 'html.parser')
    
    count = 5
    search_results = soup.find_all(class_='results__item')
    logger.info("Getted result")

    if (len(search_results) == 0):
        await ctx.send(content='Ничего не нашел :face_with_monocle: Попробуйте составить запрос по-другому')
        return

    await ctx.send(content='Вот, что мне удалось найти в Справке (показываю не более %d результатов):' % count)
    for result in search_results:
        em = discord.Embed()
        em.title = result.find('div', class_='results__title').text
        em.url = base_url + result['data-document']
        em.description = result.find('div', class_='results__text').text
        await ctx.send(embed=em)
        count -= 1
        if count == 0:
            break

@bot.command(name='rules')
async def search_in_rules(ctx, *args):
    if ctx.channel.id != config["info_channel_id_EN"]:
        return

    logger.info("Search in mapping rules. Request: '%s'" %  ' '.join(args))
    base_url = 'https://yandex.com'
    URL = 'https://yandex.com/support/search-results/?service=mapeditor&query='
    search = "+".join(args)
    logger.info("search url: %s" % (URL + search))
    page = requests.get(URL + search)
    soup = BeautifulSoup(page.content, 'html.parser')
    
    count = 5
    search_results = soup.find_all(class_='results__item')
    logger.info("Getted result")
    if (len(search_results) == 0):
        await ctx.send(content="I didn't find anything :man_shrugging: Try to write your request differently")
        return    

    await ctx.send(content="Here's what I found in the Support (there are no more than %d results):" % count)
    for result in search_results:
        em = discord.Embed()
        em.title = result.find('div', class_='results__title').text
        em.url = base_url + result['data-document']
        em.description = result.find('div', class_='results__text').text
        await ctx.send(embed=em)
        count -= 1
        if count == 0:
            break


if __name__ == "__main__":
    load()
    bot.add_cog(MyCog())
    bot.run(TOKEN)
    save()
