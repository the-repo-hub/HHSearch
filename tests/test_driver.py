import unittest
from main import send_letter, HHDriver


class Vacancy:
    VACANCY_FOR_SEND = 'Программист Python'
    all = {}

    def __init__(self, name, link):
        self.name = name
        self.link = link


class TestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.driver = HHDriver()

    def test_1(self):
        vac = Vacancy('Junior Python разработчик', 'https://spb.hh.ru/vacancy/78636365?from=vacancy_search_list')
        self.assertTrue(send_letter(self.driver, vac))

    def test_2(self):
        vac = Vacancy('Junior Python developer', 'https://spb.hh.ru/vacancy/78581805?from=vacancy_search_list')
        self.assertTrue(send_letter(self.driver, vac))

    def test_3(self):
        vac = Vacancy('Middle python developer', 'https://spb.hh.ru/vacancy/77996426?from=vacancy_search_list')
        self.assertEqual(send_letter(self.driver, vac), 'Untypical letter')

    def test_4(self):
        vac = Vacancy('Middle Automation Game QA Engineer (Python 3)', 'https://spb.hh.ru/vacancy/77493156?from=vacancy_search_list')
        self.assertTrue(send_letter(self.driver, vac))

    def test_5(self):
        vac = Vacancy('Backend Developer (Junior+/Middle)', 'https://hh.ru/vacancy/78741079?hhtmFrom=chat')
        self.assertEqual(send_letter(self.driver, vac), 'Already responded')

    def test_accepted(self):
        vac = Vacancy('Системный программист (Linux)', 'https://spb.hh.ru/vacancy/76289848?hhtmFrom=chat')
        self.assertEqual(send_letter(self.driver, vac), 'Already responded')

    def test_12(self):
        vac = Vacancy('Backend-разработчик / Разработчик Python page.', 'https://spb.hh.ru/vacancy/77874699?from=vacancy_search_list')
        self.assertEqual(send_letter(self.driver, vac), 'Archived')

    def test_23(self):
        vac = Vacancy('Python разработчик веб-приложений (fullstack) page', 'https://spb.hh.ru/vacancy/78254984?from=vacancy_search_list')
        self.assertEqual(send_letter(self.driver, vac), 'Untypical letter')

    def test_34(self):
        vac = Vacancy('Python-developer (FastApi)', 'https://spb.hh.ru/vacancy/77848012?from=vacancy_search_list')
        self.assertTrue(send_letter(self.driver, vac))


if __name__ == '__main__':
    unittest.main()
