from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException, TimeoutException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver import Chrome
from csv import writer, reader
from os import path, remove
from cnf import Config
from re import findall
from collections import deque
from time import sleep
from article import Article
from patent import Patent
from parsers import Parser
from bs4 import BeautifulSoup
import json
# =================
import os
import sys
import urllib
import pydub
import speech_recognition as sr
import re
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
import random
import time
from datetime import datetime
import requests
import stem.process
from stem import Signal
from stem.control import Controller

"""
Кейс 1. Научный кейс (Держатель кейса:
МГУТУ им. К.Г. Разумовского):
Цель – с проектировать и написать парсер информации с сайта
www.elibrary.ru.
Задачи – парсер должен классифицировать по двум критериям
(статья или патент). Собирать информацию об статье (Название
статьи, ФИО авторов, ISBN,). Собирать информацию об патенте
(Название патента, ФИО авторов, тип патента, номер патента,
номер заявки, дата регистрации, патентообладатели)
Сохранение данных в формате: CSV, XLS (таблица excel), TXT.
Ссылка на ресурс
ISSN/ISBN
БД
(https://www.elibrary.ru/org_items.asp?orgsid=1020 )
*Примечание нужно чтобы парсер переходил по ссылкам на
страницы и забирал информацию оттуда.
"""


class ParserElibrary(Parser):
    def __init__(self):
        self.driver = Service(Config.path_to_chrome_driver)
        self.browser = Chrome(service=self.driver)
        self.wait = WebDriverWait(self.browser, Config.waiting_time)
        self.articles = []
        self.patents = []
        self.article_links = deque()
        self.patent_links = deque()
        if Config.maximize_window:
            self.browser.maximize_window()

    def create_tor_proxy(self, socks_port, control_port):
        TOR_PATH = os.path.normpath(os.getcwd() + "\\tor\\tor.exe")
        try:
            tor_process = stem.process.launch_tor_with_config(
                config={
                    'SocksPort': str(socks_port),
                    'ControlPort': str(control_port),
                    'MaxCircuitDirtiness': '300',
                },
                init_msg_handler=lambda line: print(line) if re.search('Bootstrapped', line) else False,
                tor_cmd=TOR_PATH
            )
            print("[INFO] Tor connection created.")
        except:
            tor_process = None
            print("[INFO] Using existing tor connection.")

        return tor_process

    def delay(self, waiting_time=5):
        self.browser.implicitly_wait(waiting_time)

    def skip_reCapcha(self):
        SOCKS_PORT = 41293
        CONTROL_PORT = 41294
        USER_AGENT_LIST = [
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.1.1 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:77.0) Gecko/20100101 Firefox/77.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:77.0) Gecko/20100101 Firefox/77.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36',
        ]
        activate_tor = False
        tor_process = None
        user_agent = random.choice(USER_AGENT_LIST)
        if activate_tor:
            print('[INFO] TOR has been activated. Using this option will change your IP address every 60 secs.')
            print(
                '[INFO] Depending on your luck you might still see: Your Computer or Network May Be Sending Automated Queries.')
            tor_process = self.create_tor_proxy(SOCKS_PORT, CONTROL_PORT)
            PROXIES = {
                "http": f"socks5://127.0.0.1:{SOCKS_PORT}",
                "https": f"socks5://127.0.0.1:{SOCKS_PORT}"
            }
            response = requests.get("http://ip-api.com/json/", proxies=PROXIES)
        else:
            response = requests.get("http://ip-api.com/json/")
        result = json.loads(response.content)
        print('[INFO] IP Address [%s]: %s %s' % (
            datetime.now().strftime("%d-%m-%Y %H:%M:%S"), result["query"], result["country"]))

        # main program
        # auto locate recaptcha frames
        try:
            self.delay()
            frames = self.browser.find_elements(By.TAG_NAME, "iframe")
            recaptcha_control_frame = None
            recaptcha_challenge_frame = None
            for index, frame in enumerate(frames):
                # print(frame.get_attribute("title"))
                if re.search('reCAPTCHA', frame.get_attribute("title")):
                    recaptcha_control_frame = frame

                if re.search('recaptcha challenge', frame.get_attribute("title")):
                    recaptcha_challenge_frame = frame
            if not (recaptcha_control_frame and recaptcha_challenge_frame):
                print("[ERR] Unable to find recaptcha. Abort solver.")
                sys.exit()
            # switch to recaptcha frame
            self.delay()
            frames = self.browser.find_elements(By.TAG_NAME, "iframe")
            self.browser.switch_to.frame(recaptcha_control_frame)
            # click on checkbox to activate recaptcha
            self.browser.find_element(By.CLASS_NAME, "recaptcha-checkbox-border").click()

            # switch to recaptcha audio control frame
            self.delay()
            self.browser.switch_to.default_content()
            frames = self.browser.find_elements(By.TAG_NAME, "iframe")
            self.browser.switch_to.frame(recaptcha_challenge_frame)

            # click on audio challenge
            time.sleep(10)
            self.browser.find_element(By.ID, "recaptcha-audio-button").click()

            # switch to recaptcha audio challenge frame
            self.browser.switch_to.default_content()
            frames = self.browser.find_elements(By.TAG_NAME, "iframe")
            self.browser.switch_to.frame(recaptcha_challenge_frame)

            # get the mp3 audio file
            self.delay()
            src = self.browser.find_element(By.ID, "audio-source").get_attribute("src")
            print(f"[INFO] Audio src: {src}")

            path_to_mp3 = os.path.normpath(os.path.join(os.getcwd(), "sample.mp3"))
            path_to_wav = os.path.normpath(os.path.join(os.getcwd(), "sample.wav"))

            # download the mp3 audio file from the source
            urllib.request.urlretrieve(src, path_to_mp3)
        except:
            # if ip is blocked.. renew tor ip
            print("[INFO] IP address has been blocked for recaptcha.")
            sys.exit()
            # load downloaded mp3 audio file as .wav
        try:
            sound = pydub.AudioSegment.from_mp3(path_to_mp3)
            sound.export(path_to_wav, format="wav")
            sample_audio = sr.AudioFile(path_to_wav)
        except Exception:
            sys.exit(
                "[ERR] Please run program as administrator or download ffmpeg manually, "
                "https://blog.gregzaal.com/how-to-install-ffmpeg-on-windows/"
            )

        # translate audio to text with google voice recognition
        self.delay()
        r = sr.Recognizer()
        with sample_audio as source:
            audio = r.record(source)
        key = r.recognize_google(audio)
        print(f"[INFO] Recaptcha Passcode: {key}")

        # key in results and submit
        self.delay()
        self.browser.find_element(By.ID, "audio-response").send_keys(key.lower())
        self.browser.find_element(By.ID, "audio-response").send_keys(Keys.ENTER)
        time.sleep(5)
        self.browser.switch_to.default_content()
        time.sleep(5)
        self.browser.find_element(By.ID, "recaptcha-demo-submit").click()

    def load_page_with_waiting(self, url) -> bool:
        res = True
        self.browser.get(url)
        try:
            self.wait.until(EC.presence_of_element_located((By.XPATH, '/html/body')))
            # print("Page is ready!")
            try:
                self.browser.find_element(By.CLASS_NAME, 'midtext')
                self.skip_reCapcha()
                # self.wait.until(
                #     EC.frame_to_be_available_and_switch_to_it((
                #         By.CSS_SELECTOR,
                #         "iframe[name^='a-'][src^='https://www.google.com/recaptcha/api2/anchor?']")))
                # self.wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="recaptcha-anchor"]/div[1]'))).click()
                #
                # self.wait.until(EC.presence_of_element_located((By.XPATH, "//div[@class='recaptcha-checkbox-border']"))).click()

                # self.wait.until(EC.frame_to_be_available_and_switch_to_it((By.CSS_SELECTOR, "div.recaptcha-checkbox-border")))
                # self.wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[1]/form/input[2]"))).click()
                # self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.recaptcha-checkbox-border"))).click()
            except NoSuchElementException:
                pass
        except TimeoutException:
            print("Timed out waiting for page to load")
            # print("Loading took too much time!")
            res = False
        except NoSuchElementException:
            pass
        return res

    def is_name(self, data):
        if data.previous.find('РЕДАКТОРЫ:'):
            return True
        else:
            return False

    def save_articles(self):
        while self.article_links:
            url_page = self.article_links.popleft()
            assert self.load_page_with_waiting(url_page)
            # self.browser.get(url_page)
            # print(browser.page_source)
            html_page = self.browser.page_source.upper()
            soup = BeautifulSoup(html_page, 'lxml')
            # print(soup.get_text)

            # reCapcha
            # try:
            #     self.browser.find_element(By.CLASS_NAME, 'midtext')
            #     self.wait.until(
            #         EC.frame_to_be_available_and_switch_to_it((
            #             By.CSS_SELECTOR,
            #             "iframe[name^='a-'][src^='https://www.google.com/recaptcha/api2/anchor?']")))
            #     self.wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="recaptcha-anchor"]/div[1]')))
            #     # self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "recaptcha-checkbox-border"))).click()
            #
            #     btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[1]/form/input[2]")))
            #     # btn = self.browser.find_element(By.XPATH, "/html/body/div[1]/form/input[2]")
            #     btn.click()
            # except NoSuchElementException:
            #     pass

            # вытянуть body в нем найти class="midtext"
            # если есть то нажть на класс "recaptcha-checkbox-border"
            # затем на "/html/body/div[1]/form/input[2]" (<input type="submit" value="Продолжить">)

            article_title = self.browser.find_element(By.XPATH, '/html/body/table/tbody/tr/td/table[1]/tbody/tr/td[2]/'
                                                                'table/tbody/tr[2]/td[1]/table[2]/tbody/tr/td[2]/span/b/p')

            full_name_of_authors = []
            isbn = None

            data = soup.find_all('div', style='DISPLAY: INLINE-BLOCK; WHITE-SPACE: NOWRAP')
            data = list(filter(self.is_name, data))
            for i in data:
                name = i.find('font', color="#00008F")
                full_name_of_authors.append(name.text.replace('&NBSP;', ''))

            # isbn
            try:
                idx_isbn = html_page.index('ISBN'.upper())
                isbn = html_page[idx_isbn + 33:idx_isbn + 33 + 17]
                # print(html_page[idx_isbn + 33:idx_isbn + 33 + 17])
            except ValueError:
                pass
            # issn
            # if :
            self.articles.append(Article(article_title.text, full_name_of_authors, isbn))

    def save_patents(self):
        while self.patent_links:
            url_page = self.patent_links.popleft()
            assert self.load_page_with_waiting(url_page)

            html_page = self.browser.page_source.upper()
            soup = BeautifulSoup(html_page, 'lxml')

            patent_name = self.browser.find_element(By.XPATH, '/html/body/table/tbody/tr/td/table[1]/tbody/tr/td[2]/'
                                                              'table/tbody/tr[2]/td[1]/table[2]/tbody/tr/td[2]/span/b/p')

            full_name_of_authors = []

            data = soup.find_all('div', style='DISPLAY: INLINE-BLOCK; WHITE-SPACE: NOWRAP')
            data = list(filter(self.is_name, data))
            for i in data:
                name = i.find('font', color="#00008F")
                full_name_of_authors.append(name.text.replace('&NBSP;', ''))

            # тип патента
            patent_type = None
            try:
                idx_patent_type = html_page.index('Тип:'.upper())
                # print('html_page[idx_patent_type:idx_patent_type + 124]')
                patent_type = findall(fr'>(.+)</', html_page[idx_patent_type:idx_patent_type + 256])[0]
                print(f'{patent_type=}\n')
            except ValueError:
                pass
            except IndexError:
                pass

            #  номер патента
            patent_number = None
            try:
                idx_patent_number = html_page.index('Номер патента:'.upper())
                patent_number = html_page[idx_patent_number + 42:idx_patent_number + 42 + 23].replace('&NBSP;', ' ')
                print(f'{patent_number=}\n')
            except ValueError:
                pass

            # номер заявки
            request_number = None
            try:
                idx_request_number = html_page.index('Номер&nbsp;заявки:'.upper())
                request_number = findall(fr'>(\d+)</FONT',
                                         html_page[idx_request_number:
                                                   idx_request_number + 256].replace('&NBSP;', ' '))[0]
                print(f'{request_number=}\n')
            except ValueError:
                pass
            except IndexError:
                pass

            # дата регистрации
            registration_date = None
            try:
                idx_registration_date = html_page.index('Дата&nbsp;регистрации:'.upper())
                registration_date = findall(fr'>(.{10})</FONT',
                                         html_page[idx_registration_date:
                                                   idx_registration_date + 256].replace('&NBSP;', ' '))[0]
                print(f'{registration_date=}\n')
            except ValueError:
                pass
            except IndexError:
                pass

            # патентообладатели
            # # self.patent_holders = patent_holders
            patent_holders = None
            # try:
            #     idx_patent_holders = html_page.index('Дата публикации:'.upper())
            #     request_number = html_page[idx_patent_holders + 42:idx_patent_holders + 42 + 23].replace('&NBSP;', ' ')
            #     print(f'{patent_number=}\n')
            # except ValueError:
            #     pass

            self.patents.append(Patent(patent_name.text,
                                       full_name_of_authors,
                                       patent_type,
                                       patent_number,
                                       request_number,
                                       registration_date,
                                       patent_holders))

    def run(self):
        # browser.get(Config.url)
        assert self.load_page_with_waiting(Config.url)

        while Config.number_of_patents > len(self.patent_links) or Config.number_of_articles > len(self.article_links):

            table_with_data = \
                self.browser.find_element(By.XPATH, '//*[@id="restab"]').find_element(By.TAG_NAME, 'tbody')
            rows_data = table_with_data.find_elements(By.TAG_NAME, 'tr')

            idx = 3
            while idx < len(rows_data) and \
                    (Config.number_of_patents > len(self.patent_links) or
                     Config.number_of_articles > len(self.article_links)):
                # print(rows_data[idx].get_attribute('id'))
                header = rows_data[idx].find_element(By.TAG_NAME, 'a')
                # print(tag_a.text)
                link = header.get_attribute('href')
                if link.startswith('http://') or link.startswith('https://'):
                    # print(link)

                    fonts = rows_data[idx].find_elements(By.XPATH, './td[2]/font')
                    if len(fonts) > 1 and fonts[1] and 'Патент'.upper() in fonts[1].text.upper():
                        # патен
                        if Config.number_of_patents > len(self.patent_links):
                            self.patent_links.append(link)
                    else:
                        # статья
                        if Config.number_of_articles > len(self.article_links):
                            self.article_links.append(link)
                    idx += 1
            self.browser.find_element(By.XPATH, '//*[@id="pages"]/table/tbody/tr/td[13]/a').click()

        # print(f'{len(self.patent_links)=}\n{len(self.article_links)=}')

        self.save_articles()

        self.save_patents()

        self.browser.quit()
        self.save_to_csv()

        # class='recaptcha-checkbox-border'
        # '/html/body/div[1]/form/input[2]'
        # <input type="submit" value="Продолжить">

        # имя_узла	Выбирает все узлы с именем имя_узла
        # /      	Выбирает от корневого узла
        # //    	Выбирает узлы в документе от текущего узла, который соответствует выбору, независимо от того, где они находятся
        # .	        Выбирает текущий узел
        # ..	    Выбирает родителя текущего узла
        # @	        Выбирает атрибуты

    def save_to_csv(self):
        def save_to_csv_articles():
            with open(Config.path_to_save + fr'\articles.csv', 'w', encoding='UTF8', newline='') as f:
                json.dump([i.to_list() for i in self.articles], f, ensure_ascii=False, indent=2)

        def save_to_csv_patents():
            with open(Config.path_to_save + fr'\patents.csv', 'w', encoding='UTF8', newline='') as f:
                json.dump([i.to_list() for i in self.patents], f, ensure_ascii=False, indent=2)

        save_to_csv_articles()
        save_to_csv_patents()

    def save_to_xls(self):
        pass

    def save_to_txt(self):
        pass


if __name__ == '__main__':
    parser_elibrary = ParserElibrary()
    parser_elibrary.run()
