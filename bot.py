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
handler = logging.FileHandler(filename='cartographer.log', encoding='utf-8', mode='a')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)
logger.info('--- start bot ---\n')

# Get params
TOKEN = os.getenv('CARTOGRAPHER_TOKEN')
if TOKEN == None:
    print("Token is not setted")
    logger.error("Token is not setted")
    exit()

NEWS_CHANNEL_ID = os.getenv("CARTOGRAPHER_NEWS_CHANNEL_ID")
if NEWS_CHANNEL_ID == None:
    print("News channel id is not setted")
    logger.error("News channel id is not setted")
    exit()
NEWS_CHANNEL_ID = int(NEWS_CHANNEL_ID)

INFO_CHANNEL_ID = os.getenv("CARTOGRAPHER_INFO_CHANNEL_ID")
if INFO_CHANNEL_ID == None:
    print("Info channel id is not setted")
    logger.error("Info channel id is not setted")
    exit()
INFO_CHANNEL_ID = int(INFO_CHANNEL_ID)

# Bot 
bot = commands.Bot(command_prefix='!')

class MyCog(commands.Cog):
    def __init__(self):
        self.bot = bot
        self.config_file_path = "cartographer.json"
        self.config = {
            "last_post": ""
        }
        self.news_updater.start()

    def cog_unload(self):
        self.news_updater.cancel()

    @tasks.loop(minutes=5.0)
    async def news_updater(self):
        logger.info("Udpating news from 'Клуб народкой карты'")
        news_channel = bot.get_channel(NEWS_CHANNEL_ID)
        if news_channel == None:
            return
        base_url = 'https://yandex.ru'
        URL = 'https://yandex.ru/blog/narod-karta'
        page = requests.get(URL)
        soup = BeautifulSoup(page.content, 'html.parser')
        posts = []
        self.load()    
        logger.info("Last loaded post: %s" % self.config["last_post"])

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
            if self.config["last_post"] == em.url:
                new_posts.clear()
                logger.debug("Finded last published post '%s'. Cleanup list." % em.title)

        logger.debug("New posts count: %d" % len(new_posts))

        for em in new_posts:
            await news_channel.send(embed=em)
            self.config["last_post"] = em.url
            logger.debug(" - %s" % em.title)

        logger.info("List new post updated")

        self.save()

    @news_updater.before_loop
    async def before_news_updater(self):
        await bot.wait_until_ready()

    def save(self):
        with open(self.config_file_path, "w") as write_file:
            json.dump(self.config, write_file, indent=4)

    def load(self):
        if not os.path.exists(self.config_file_path):
            logger.warning('Config file not found. Using default values')
            return

        with open(self.config_file_path, "r") as read_file:
            self.config = json.load(read_file)

@bot.event
async def on_ready():
    logger.info("--- Logged in as '%s'" % bot.user.name )

@bot.command(name='правила')
async def search_in_rules(ctx, arg):
    if ctx.channel.id != INFO_CHANNEL_ID:
        return

    logger.info("Search in mapping rules. Request: '%s'" % arg)
    base_url = 'https://yandex.ru'
    URL = 'https://yandex.ru/support/search-results/?service=nmaps&query='
    search = "+".join(arg.split())
    page = requests.get(URL + search)
    soup = BeautifulSoup(page.content, 'html.parser')
    
    count = 5
    search_results = soup.find_all(class_='results__item')
    logger.info("Getted result")
    await ctx.send(content='Получены результаты поиска выдаю не больше %d:' % count)
    for result in search_results:
        em = discord.Embed()
        em.title = result.find('div', class_='results__title').text
        em.url = base_url + result['data-document']
        em.description = result.find('div', class_='results__text').text
        await ctx.send(embed=em)
        count -= 1
        if count == 0:
            break

bot.add_cog(MyCog())
bot.run(TOKEN)