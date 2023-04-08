from selenium import webdriver
from selenium.webdriver.common.by import By
import asyncio
import ast
import bs4
import aiohttp
import threading
from selenium.common.exceptions import NoSuchElementException, ElementNotInteractableException
import os
from typing import Union


vacancies_url = 'https://spb.hh.ru/search/vacancy?experience=between1And3&resume=c6f3d876ff0ba2033d0039ed1f6a6f4e386247&search_field=name&search_field=company_name&search_field=description&forceFiltersSaving=true&enable_snippets=false&salary=60000&ored_clusters=true'
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:110.0) Gecko/20100101 Firefox/110.0'}
obj_dict = {'untypical': []}


try:
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cookies.txt')) as cookies_file:
        cookies = ast.literal_eval(cookies_file.read())
        aiocookies = {}
        for c in cookies:
            aiocookies[c['name']] = c['value']
except FileNotFoundError:
    exit("You need to insert cookies (as selenium's .get_cookies() in cookies.txt file)!")
except SyntaxError:
    exit('Invalid cookies!')

try:
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'letter.txt')) as file:
        letter = file.read()
except FileNotFoundError:
    exit("You need write a letter and put it in letter.txt!")


def up_low(lst):
    res = []
    for string in lst:
        res.extend([string.upper(), string.lower()])
    return lst + res


class Vacancy:
    all = {}
    VACANCY_FOR_SEND = 'Программист Python'

    ALLOW_WORDS = up_low(['Python'])
    DENY_WORDS = up_low(['Senior', 'Lead', 'Нейрон', 'Лид', 'Детей', 'Преподаватель', 'Наставник', 'Автор', 'Репетитор'])

    def __init__(self, soup: bs4.Tag):
        self.name = soup.find('a', class_="serp-item__title").text
        self.link = soup.find('a', class_="serp-item__title").get('href')
        self.id = int(self.link.split('?')[0].split('/')[-1])
        if self.all.get(self.id):
            return
        try:
            self.salary = soup.find('span', class_="bloko-header-section-3").text
        except AttributeError:
            self.salary = None
        try:
            self.company = soup.find('a', class_="bloko-link_kind-tertiary").text
        except AttributeError:
            self.company = None
        self.place = soup.find('div', class_="bloko-text", attrs={'data-qa': "vacancy-serp__vacancy-address"}).text

        for allow in self.ALLOW_WORDS:
            flag = False
            if allow in self.name:
                flag = True
                for deny in self.DENY_WORDS:
                    if deny in self.name:
                        flag = False
            if flag:
                self.all[self.id] = self
                break

    def __str__(self):
        return self.name


async def generate_queries():
    gather = []

    async with aiohttp.ClientSession(headers=headers, cookies=aiocookies) as session:
        first_page = await session.get(vacancies_url)
        num = int(
            bs4.BeautifulSoup(await first_page.text(), 'html.parser').find(attrs={'data-qa': "pager-block"}).find_all('span',
                                                                                                               attrs={
                                                                                                                   'class': [
                                                                                                                       'pager-item-not-in-short-range']})[
                -1].find('a', attrs={'data-qa': "pager-page"}).text)
        print(f'Pages: {num}')
        for i in range(1, num + 1):
            gather.append(session.get(vacancies_url + f'&page={i}'))
        gather = await asyncio.gather(*gather)
        gather.append(first_page)
        for g in gather:
            vacancies = bs4.BeautifulSoup(await g.text(), 'html.parser').find_all(class_="serp-item")
            for vac in vacancies:
                Vacancy(vac)
    print(f'Got {len(Vacancy.all)} vacancies')


def firefox_driver():
    driver = webdriver.Firefox()
    driver.get('https://spb.hh.ru/account/login?backurl=%2F&hhtmFrom=main')
    driver.delete_all_cookies()
    for c in cookies:
        driver.add_cookie(c)
    driver.get('https://spb.hh.ru')

    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cookies.txt'), 'w') as cookies_file:
        cookies_file.write(driver.get_cookies().__str__())

    obj_dict['driver'] = driver


def send_letter(driver: webdriver.Firefox, vac: Vacancy) -> Union[str, bool]:
    driver.get(vac.link)
    print(f'On {vac.name} page. Link: {vac.link}')
    try:
        button = driver.find_element(By.CSS_SELECTOR, 'a[data-qa="vacancy-response-link-top"]')

    except NoSuchElementException:
        print(f'Failed! Reason: Уже откликался')
        return 'Already responded'

    experience = driver.find_element(By.CSS_SELECTOR, 'span[data-qa="vacancy-experience"]')
    if experience.text != '1–3 года':
        print(f'Failed! Reason: experience == {experience}')
        return 'Not that experience'

    else:
        button.click()
        driver.implicitly_wait(10)
        summaries = driver.find_elements(By.CSS_SELECTOR, 'input[class="bloko-radio__input"]')
        for summary in summaries:
            if summary.text == Vacancy.VACANCY_FOR_SEND:
                summary.click()
        try:
            letter_btn = driver.find_element(By.CSS_SELECTOR, 'button[data-qa="vacancy-response-letter-toggle"]')
            letter_btn.click()
            driver.implicitly_wait(10)
            driver.find_element(By.CSS_SELECTOR, 'textarea[data-qa="vacancy-response-popup-form-letter-input"]').send_keys(
                letter)
            apply = driver.find_element(By.CSS_SELECTOR, 'button[data-qa="vacancy-response-submit-popup"]')
            # apply.click()
        except NoSuchElementException:
            obj_dict['untypical'].append(vac)
            print('Incomplete! Reason: untypical letter')
            return 'Untypical letter'
        except ElementNotInteractableException:
            pass
        return True


def main():
    t1 = threading.Thread(target=firefox_driver, args=(obj_dict,))
    t1.start()
    asyncio.run(generate_queries())
    t1.join()
    for vac_id, vac in Vacancy.all.items():
        send_letter(obj_dict['driver'], vac)
    obj_dict['driver'].close()
    for vac in obj_dict['untypical']:
        print(vac, vac.link)


if __name__ == '__main__':
    main()
