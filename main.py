from selenium import webdriver
from selenium.webdriver.common.by import By
import asyncio
import ast
import bs4
import aiohttp
import threading


vacancies_url = 'https://spb.hh.ru/search/vacancy?resume=c6f3d876ff0ba2033d0039ed1f6a6f4e386247&search_field=company_name&search_field=description&search_field=name&forceFiltersSaving=true&enable_snippets=false&salary=80000&from=resumelist'
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:110.0) Gecko/20100101 Firefox/110.0'}

try:
    with open('cookies.txt') as file:
        cookies = ast.literal_eval(file.read())
        aiocookies = {}
        for c in cookies:
            aiocookies[c['name']] = c['value']
except FileNotFoundError:
    exit("You need to insert cookies (as selenium's .get_cookies() in cookies.txt file)!")
except SyntaxError:
    exit('Invalid cookies!')

try:
    with open('letter.txt') as file:
        letter = file.read()
except FileNotFoundError:
    exit("You need write a letter and put it in letter.txt!")


class Vacancy:
    all = []
    ALLOW_WORDS = ['Python']
    DENY_WORDS = ['Senior', 'Lead', 'Нейрон', 'Лид', 'Детей', 'Преподаватель', 'Наставник']

    ALLOW_WORDS += list(map(lambda s: s.lower(), ALLOW_WORDS))
    DENY_WORDS += list(map(lambda s: s.lower(), DENY_WORDS))

    def __init__(self, soup: bs4.Tag):
        self.name = soup.find('a', class_="serp-item__title").text
        self.link = soup.find('a', class_="serp-item__title").get('href')
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
                self.all.append(self)
                break

    def __str__(self):
        return self.name


async def generate_queries():
    gather = []

    async with aiohttp.ClientSession(headers=headers, cookies=aiocookies) as session:
        first_page = await session.get(vacancies_url)
        num = int(bs4.BeautifulSoup(await first_page.text(), 'lxml').find(attrs={'data-qa': "pager-block"}).find_all('span', attrs={
            'class': ['pager-item-not-in-short-range']})[-1].find('a', attrs={'data-qa': "pager-page"}).text)
        print(f'Pages: {num}')
        for i in range(1, num + 1):
            gather.append(session.get(vacancies_url + f'&page={i}'))
        gather = await asyncio.gather(*gather)
        gather.append(first_page)
        for g in gather:
            vacancies = bs4.BeautifulSoup(await g.text(), 'lxml').find_all(class_="serp-item")
            for vac in vacancies:
                Vacancy(vac)
    print(f'Got {len(Vacancy.all)} vacancies')


def firefox_driver(obj_for_driver):
    driver = webdriver.Firefox()
    driver.get('https://spb.hh.ru/account/login?backurl=%2F&hhtmFrom=main')
    driver.delete_all_cookies()
    for c in cookies:
        driver.add_cookie(c)
    driver.get('https://spb.hh.ru')
    obj_for_driver['driver'] = driver


def send_letter(driver: webdriver.Firefox, vac: Vacancy):
    driver.get(vac.link)
    experience = driver.find_element(By.XPATH, '/html/body/div[5]/div/div[3]/div[1]/div/div/div/div/div[1]/div[1]/div[1]/div/p[1]/span').text
    if experience == '1–3':
        button = driver.find_element(By.XPATH, '/html/body/div[5]/div/div[3]/div[1]/div/div/div/div/div[1]/div[1]/div[1]/div/div[3]/div[2]/div/div[1]/a')
        button.click()


def main():
    obj_for_driver = {}
    t1 = threading.Thread(target=firefox_driver, args=(obj_for_driver,))
    t1.start()
    # asyncio.run(generate_queries())
    t1.join()
    obj_for_driver['driver'].get('https://spb.hh.ru/vacancy/72216524?from=vacancy_search_list')
    for vac in Vacancy.all:
        send_letter(obj_for_driver['driver'], vac)


if __name__ == '__main__':
    main()

