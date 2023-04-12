from sqlalchemy import MetaData, Table, String, Integer, Column
from sqlalchemy.engine import create_engine


def create_table():
    table_name = 'Vacancies'
    engine = create_engine('mysql+mysqlconnector://debian:debian@localhost/hhsearchbase')
    meta = MetaData()
    table = Table(table_name,
                  meta,
                  Column('pk', Integer, primary_key=True, autoincrement=True),
                  Column('name', String(255)),
                  Column('link', String(255)),
                  Column('id', Integer),
                  Column('salary', String(255)),
                  Column('place', String(255)),
                  Column('company', String(255)),
                  Column('status', String(100))
                  )
    meta.drop_all(bind=engine, tables=(table,))
    meta.create_all(bind=engine, tables=(table,))


if __name__ == '__main__':
    create_table()