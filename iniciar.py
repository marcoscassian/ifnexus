import sqlite3

BANCO = 'schema.sql'

conexao = sqlite3.connect('banco.db')

with open(BANCO, 'r') as f:
    conexao.executescript(f.read())

conexao.close()
