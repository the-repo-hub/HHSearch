from selenium.webdriver import Firefox
import asyncio
import ast
from selenium.webdriver.common.by import By
import bs4
import aiohttp


class Vacancy:
    all = []
    ALLOW_WORDS = ['Middle', 'Python', 'Backend']
    DENY_WORDS = ['Senior', 'Java', 'Lead', 'JS', 'Нейрон', 'Goolang', 'PHP', 'C++', 'Ведущий', 'C#']

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
    vacancies_url = 'https://spb.hh.ru/search/vacancy?resume=c6f3d876ff0ba2033d0039ed1f6a6f4e386247&search_field=company_name&search_field=description&search_field=name&forceFiltersSaving=true&enable_snippets=false&salary=80000&from=resumelist'
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:110.0) Gecko/20100101 Firefox/110.0'}

    with open('cookies.txt') as file:
        cookies = {}
        for c in ast.literal_eval(file.read()):
            cookies[c['name']] = c['value']

    async with aiohttp.ClientSession(headers=headers, cookies=cookies) as session:
        first_page = await session.get(vacancies_url)
        num = int(bs4.BeautifulSoup(await first_page.text(), 'lxml').find(attrs={'data-qa': "pager-block"}).find_all('span', attrs={
            'class': ['pager-item-not-in-short-range']})[-1].find('a', attrs={'data-qa': "pager-page"}).text)

        for i in range(1, num + 1):
            gather.append(session.get(vacancies_url + f'&page={i}'))
        gather = await asyncio.gather(*gather)
        gather.append(first_page)
        for g in gather:
            vacancies = bs4.BeautifulSoup(await g.text(), 'lxml').find_all(class_="serp-item")
            for vac in vacancies:
                Vacancy(vac)
        d = 3


def firefox_driver():
    driver = Firefox()
    driver.get('https://spb.hh.ru/account/login?backurl=%2F&hhtmFrom=main')
    vacancies_url = 'https://spb.hh.ru/search/vacancy?resume=c6f3d876ff0ba2033d0039ed1f6a6f4e386247&search_field=company_name&search_field=description&search_field=name&forceFiltersSaving=true&enable_snippets=false&salary=80000&from=resumelist'

    with open('cookies.txt') as cookies:
        for c in ast.literal_eval(cookies.read()):
            driver.add_cookie(c)

    driver.get(vacancies_url)


if __name__ == '__main__':
    #main()
    asyncio.run(generate_queries())
    print(Vacancy.all)

