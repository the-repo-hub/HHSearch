import time
from selenium import webdriver
from selenium.webdriver.common.by import By
import ast
from selenium.common.exceptions import NoSuchElementException, ElementNotInteractableException, TimeoutException
import os
from typing import Union
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.remote.webelement import WebElement
import threading
from sqlalchemy.engine import create_engine
from sqlalchemy import MetaData, select, insert, Row, update
import typing

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:110.0) Gecko/20100101 Firefox/110.0'}
engine = create_engine('mysql+mysqlconnector://debian:debian@localhost/hhsearchbase')
meta = MetaData()
meta.reflect(engine)
table = meta.tables['Vacancies']


def up_low(lst):
    res = []
    for string in lst:
        res.extend([string.upper(), string.lower()])
    return lst + res


class Vacancy:

    @staticmethod
    def add_many(els: list):
        for el in els:
            Vacancy(el)

    all = {}
    VACANCY_FOR_SEND = 'Программист Python'
    ALLOW_WORDS = up_low(['Python'])
    DENY_WORDS = up_low(
        ['Senior', 'Lead', 'Нейрон', 'Лид', 'Детей', 'Преподаватель', 'Наставник', 'Автор', 'Репетитор', 'Perl'])

    def __init__(self, el: typing.Union[WebElement, Row]):
        if isinstance(el, WebElement):
            self.link = el.find_element(By.CSS_SELECTOR, 'a[data-qa="serp-item__title"]').get_attribute('href')
            self.id = int(self.link.split('?')[0].split('/')[-1])
            if self.all.get(self.id):
                return
            self.name = el.find_element(By.CSS_SELECTOR, 'a[data-qa="serp-item__title"]').text
            try:
                self.salary = el.find_element(By.CSS_SELECTOR,
                                              'span[data-qa="vacancy-serp__vacancy-compensation"]').text
            except NoSuchElementException:
                self.salary = None
            try:
                self.company = el.find_element(By.CSS_SELECTOR, 'a[data-qa="vacancy-serp__vacancy-employer"]').text
            except NoSuchElementException:
                self.company = None
            self.place = el.find_element(By.CSS_SELECTOR,
                                         'div[class="bloko-text"][data-qa="vacancy-serp__vacancy-address"]').text

            for allow in self.ALLOW_WORDS:
                flag = False
                if allow in self.name:
                    flag = True
                    for deny in self.DENY_WORDS:
                        if deny in self.name:
                            flag = False
                            break
                if flag:
                    self.all[self.id] = self
                    HHDriver.queue_filter(self)
                    break
        else:
            self.name = el.name
            self.link = el.link
            self.id = el.id
            self.salary = el.salary
            self.company = el.company
            self.place = el.place

    def __str__(self):
        return self.name


class HHDriver(webdriver.Firefox):
    vacancies_url = 'https://spb.hh.ru/search/vacancy?experience=between1And3&resume=c6f3d876ff0ba2033d0039ed1f6a6f4e386247&search_field=name&search_field=company_name&search_field=description&forceFiltersSaving=true&enable_snippets=false&salary=60000&ored_clusters=true'
    cookies_overwritten = False
    queue = {}
    con = engine.connect()

    @classmethod
    def queue_filter(cls, vac: Vacancy):
        stmt = select('*').where(table.c.id == str(vac.id))
        res = cls.con.execute(stmt).fetchone()
        if not res or res.status == 'NULL':
            cls.queue[vac.id] = vac

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.letter = None
        self.pages = None

        try:
            with open(os.path.join(os.path.dirname(os.path.abspath('__file__')), 'cookies.txt')) as cookies_file:
                cookies = ast.literal_eval(cookies_file.read())
        except FileNotFoundError:
            exit("You need to insert cookies (as selenium's .get_cookies() in cookies.txt file)!")
        except SyntaxError:
            exit('Invalid cookies!')

        try:
            with open(os.path.join(os.path.dirname(os.path.abspath('__file__')), 'letter.txt')) as file:
                self.letter = file.read()
        except FileNotFoundError:
            exit("You need write a letter and put it in letter.txt!")

        self.get('https://spb.hh.ru/account/login?backurl=%2F&hhtmFrom=main')
        self.delete_all_cookies()
        for c in cookies:
            self.add_cookie(c)

    def obtain_all_vacs(self):
        self.get(self.vacancies_url)

        if not self.cookies_overwritten:
            with open(os.path.join(os.path.dirname(os.path.abspath('__file__')), 'cookies.txt'), 'w') as cookies_file:
                cookies_file.write(self.get_cookies().__str__())
            self.cookies_overwritten = True

        self.pages = int(self.find_elements(By.CSS_SELECTOR, 'span[class="pager-item-not-in-short-range"]')[-1].text)
        Vacancy.add_many(
            self.find_elements(By.CSS_SELECTOR, 'div[data-qa="vacancy-serp__vacancy vacancy-serp__vacancy_standard"]'))
        for i in range(1, self.pages):
            self.get(self.vacancies_url + f'&page={i}')
            Vacancy.add_many(self.find_elements(By.CSS_SELECTOR,
                                                'div[data-qa="vacancy-serp__vacancy vacancy-serp__vacancy_standard"]'))

        # check for database


def send_letter(driver: HHDriver, vac: Vacancy) -> Union[str, bool]:
    driver.get(vac.link)
    print(f'{vac.name} {vac.link}')
    try:
        button = driver.find_element(By.CSS_SELECTOR, 'a[data-qa="vacancy-response-link-top"]')

    except NoSuchElementException:
        try:
            button = driver.find_element(By.CSS_SELECTOR, 'a[data-qa="vacancy-response-link-view-topic"]')
            print(f'Failed! Reason: {button.text}')
            return 'Already responded'

        except NoSuchElementException:
            print('Failed! Reason: Archived')
            return 'Archived'

    experience = driver.find_element(By.CSS_SELECTOR, 'span[data-qa="vacancy-experience"]')
    if experience.text != '1–3 года':
        print(f'Failed! Reason: experience == {experience}')
        return 'Not that experience'

    else:
        button.click()
        # сообщение с релокацией
        try:
            button = WebDriverWait(driver, timeout=3).until(
                lambda d: driver.find_element(By.CSS_SELECTOR, 'button[data-qa="relocation-warning-confirm"]'))
            button.click()
        except NoSuchElementException:
            pass
        except TimeoutException:
            pass

        # после отклика перекинуло на страницу с полями для ввода
        try:
            WebDriverWait(driver, timeout=3).until(
                lambda d: driver.find_element(By.CSS_SELECTOR, 'div[data-qa="task-body"]'))
            print('Incomplete! Reason: untypical letter')
            return 'Untypical letter'
        except NoSuchElementException:
            pass
        except TimeoutException:
            pass

        # проверить выбранное резюме
        summary_selected = WebDriverWait(driver, timeout=3).until(
            lambda d: driver.find_element(By.CSS_SELECTOR,
                                          'div[class="vacancy-response-popup-resume vacancy-response-popup-resume_selected"]'))
        if summary_selected.find_element(By.TAG_NAME, 'span').text != Vacancy.VACANCY_FOR_SEND:
            button = driver.find_element(By.CSS_SELECTOR, 'div[class="vacancy-response-popup-resume"]').find_element(By.TAG_NAME, 'span')
            button.click()

        try:
            letter_btn = driver.find_element(By.CSS_SELECTOR, 'button[data-qa="vacancy-response-letter-toggle"]')
            letter_btn.click()
        except ElementNotInteractableException:
            pass

        except NoSuchElementException:
            print('Incomplete! Reason: untypical letter')
            return 'Untypical letter'

        driver.find_element(By.CSS_SELECTOR, 'textarea[data-qa="vacancy-response-popup-form-letter-input"]').send_keys(
            driver.letter)
        apply = driver.find_element(By.CSS_SELECTOR, 'button[data-qa="vacancy-response-submit-popup"]')
        # apply.click()
        return True


def run_checker():
    with HHDriver() as checker:
        while True:
            checker.obtain_all_vacs()
            print('run_checker has iterated, waiting..')
            time.sleep(120)


def run_driver():
    with HHDriver() as driver:
        while True:
            if not driver.queue:
                time.sleep(0.5)
            else:
                queue_copy = driver.queue.copy()
                for vac in queue_copy.values():
                    vac: Vacancy
                    result = send_letter(driver, vac)
                    stmt = select('*').where(table.c.id == str(vac.id))
                    if not driver.con.execute(stmt).fetchone():
                        stmt = insert(table).values(link=vac.link,
                                                    id=vac.id,
                                                    name=vac.name,
                                                    salary=vac.salary,
                                                    company=vac.company,
                                                    place=vac.place,
                                                    status=result)
                        driver.con.execute(stmt)
                    else:
                        stmt = update(table).where(table.c.id == str(vac.id)).values(status=result)
                        driver.con.execute(stmt)
                    driver.con.commit()
                    driver.queue.pop(vac.id)


def main():
    try:
        t1 = threading.Thread(target=run_checker)
        t1.start()
        t2 = threading.Thread(target=run_driver)
        t2.start()
    except KeyboardInterrupt:
        print('bye!')


if __name__ == '__main__':
    main()
