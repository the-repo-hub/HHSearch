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


headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:110.0) Gecko/20100101 Firefox/110.0'}


class HHDriver(webdriver.Firefox):
    vacancies_url = 'https://spb.hh.ru/search/vacancy?experience=between1And3&resume=c6f3d876ff0ba2033d0039ed1f6a6f4e386247&search_field=name&search_field=company_name&search_field=description&forceFiltersSaving=true&enable_snippets=false&salary=60000&ored_clusters=true'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.letter = None
        self.pages = None

        try:
            with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cookies.txt')) as cookies_file:
                cookies = ast.literal_eval(cookies_file.read())
        except FileNotFoundError:
            exit("You need to insert cookies (as selenium's .get_cookies() in cookies.txt file)!")
        except SyntaxError:
            exit('Invalid cookies!')

        try:
            with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'letter.txt')) as file:
                self.letter = file.read()
        except FileNotFoundError:
            exit("You need write a letter and put it in letter.txt!")

        self.get('https://spb.hh.ru/account/login?backurl=%2F&hhtmFrom=main')
        self.delete_all_cookies()
        for c in cookies:
            self.add_cookie(c)
        """with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cookies.txt'), 'w') as cookies_file:
            cookies_file.write(self.get_cookies().__str__())"""

    def obtain_all_vacs(self):
        self.get(self.vacancies_url)
        self.pages = int(self.find_elements(By.CSS_SELECTOR, 'span[class="pager-item-not-in-short-range"]')[-1].text)
        for el in self.find_elements(By.CSS_SELECTOR, 'div[data-qa="vacancy-serp__vacancy vacancy-serp__vacancy_standard"]'):
            Vacancy(el)
        for i in range(1, self.pages):
            self.get(self.vacancies_url + f'&page={i}')
            for el in self.find_elements(By.CSS_SELECTOR,
                                         'div[data-qa="vacancy-serp__vacancy vacancy-serp__vacancy_standard"]'):
                Vacancy(el)


class Vacancy:

    @staticmethod
    def up_low(lst):
        res = []
        for string in lst:
            res.extend([string.upper(), string.lower()])
        return lst + res

    all = {}
    VACANCY_FOR_SEND = 'Программист Python'
    ALLOW_WORDS = up_low(['Python'])
    DENY_WORDS = up_low(['Senior', 'Lead', 'Нейрон', 'Лид', 'Детей', 'Преподаватель', 'Наставник', 'Автор', 'Репетитор', 'Perl'])

    def __init__(self, el: WebElement):
        self.name = el.find_element(By.CSS_SELECTOR, 'a[data-qa="serp-item__title"]').text
        self.link = el.find_element(By.CSS_SELECTOR, 'a[data-qa="serp-item__title"]').get_attribute('href')
        self.id = int(self.link.split('?')[0].split('/')[-1])
        if self.all.get(self.id):
            return
        try:
            self.salary = el.find_element(By.CSS_SELECTOR, 'span[class="bloko-header-section-3]"').text
        except NoSuchElementException:
            self.salary = None
        try:
            self.company = el.find_element(By.CSS_SELECTOR, 'a[class="bloko-link_kind-tertiary"]').text
        except NoSuchElementException:
            self.company = None
        self.place = el.find_element(By.CSS_SELECTOR, 'div[class="bloko-text"][data-qa="vacancy-serp__vacancy-address"]').text

        self.description = None

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
                break

    def __str__(self):
        return self.name


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
            button = WebDriverWait(driver, timeout=3).until(lambda d: driver.find_element(By.CSS_SELECTOR, 'button[data-qa="relocation-warning-confirm"]'))
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
            lambda d: driver.find_element(By.CSS_SELECTOR, 'div[class="vacancy-response-popup-resume vacancy-response-popup-resume_selected"]'))
        if summary_selected.find_element(By.TAG_NAME, 'span').text != Vacancy.VACANCY_FOR_SEND:
            summary_selected.click()

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


def run_checker(checker):
    while True:
        checker.obtain_all_vacs()
        time.sleep(120)


def main():
    with HHDriver() as checker:
        checker.obtain_all_vacs()
        with HHDriver() as driver:
            for vac in Vacancy.all.values():
                send_letter(driver, vac)
        t1 = threading.Thread(target=run_checker, args=(checker,))
        t1.start()


if __name__ == '__main__':
    main()
