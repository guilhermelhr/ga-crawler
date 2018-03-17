# -*- coding: utf-8 -*-
import scrapy
import re
import json
import os
import errno
import threading
import requests

lock = threading.Lock()
video_regex = re.compile(b"\"profile\"[^}]+")

class GaSpider(scrapy.Spider):
    name = 'ga'
    allowed_domains = ['gamesacademy.com.br', 'gamersclub.com.br', 'vimeo.com']
        
    def start_requests(self):
        yield scrapy.Request(url='https://www.gamesacademy.com.br/change/counter-strike-global-offensive', callback=self.after_gameselect)

    def after_gameselect(self, response):
        return [scrapy.FormRequest(url='https://www.gamesacademy.com.br/auth/login',
                    formdata = {
                        'email': 'exemplo@exemplo.com',
                        'password': 'senha',
                        'remember': '1',
                        '_token': ''
                    },
                    callback = self.after_login)]


    def after_login(self, response):
        for topico in response.css('.list-category-itens a::attr(href)'):
            if topico is not None:
                yield response.follow(topico, callback=self.parse_topico)
        

    def parse_topico(self, response):
        for aula in response.css('.video-list a::attr(href)'):
            if aula is not None:
                yield response.follow(aula, callback=self.parse_aula)

    def parse_aula(self, response):
        iframe = response.css('iframe::attr(src)').extract_first()
        numero_aula = response.url.split('/')[-1]
        nome_curso = response.url.split('/')[-3]

        if nome_curso == 'mapa-nova-inferno': #nome do mapa
            yield response.follow(
                iframe,
                callback=self.parse_iframe,
                meta={'numero_aula' : numero_aula, 'nome_curso' : nome_curso})

    def parse_iframe(self, response):
        nome_curso = response.meta.get('nome_curso')
        numero_aula = response.meta.get('numero_aula')

        videos = video_regex.findall(response.body, re.IGNORECASE)
        video_jsons = []

        for video in videos:
            iframe_json = json.loads('{' + video.decode("utf-8") + '}')
            if 'url' in iframe_json:
                video_jsons.append(iframe_json)

        

        for video_json in video_jsons:
            if video_json['quality'] == '720p': #resolucao do video
                filename = '{0}/{0}-{1}.mp4'.format(nome_curso, numero_aula)

                if os.path.isfile(filename):
                    print("Skipping " + filename)
                    continue

                if not os.path.exists(os.path.dirname(filename)):
                    try:
                        os.makedirs(os.path.dirname(filename))
                    except OSError as exc:
                        if exc.errno != errno.EEXIST:
                            raise
                
                r = requests.get(video_json['url'])

                lock.acquire()

                print("Downloading " + filename)

                with open(filename, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=255):
                        if chunk:
                            f.write(chunk)

                print("Done downloading " + filename)

                lock.release()
            
        
        
