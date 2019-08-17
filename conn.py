# -*- coding: utf-8 -*-
# Usado para manipular partes diferentes do ambiente
# de tempo de execução do Python
import sys
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

Base = declarative_base()


# Classes que correspondem as tabelas do banco
class Usuario(Base):
    '''
    Esta classe implementa um usuario basico e dispoe
    dos atributos serializados.
    '''
    __tablename__ = 'usuario'

    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False)
    nickname = Column(String(80), nullable=False)
    password = Column(String(250))
    last_name = Column(String(80), nullable=False)
    email = Column(String(80), nullable=False)
    token = Column(String(200))

    @property
    def serialize(self):
        obj = {
            'id': self.id,
            'name': self.name,
            'nickname': self.nickname,
            'password': self.password,
            'last_name': self.last_name,
            'email': self.email
        }
        return obj


class Categoria(Base):
    ''' Esta classe implementa a categoria dos catalogo e dispoe
        dos atributos serializados.
    '''
    __tablename__ = 'categoria'

    # Especificando as colunas da tabela
    id = Column(Integer, primary_key=True)
    nome = Column(String(80), nullable=False)
    descricao = Column(String(250), nullable=False)

    usuario_id = Column(Integer, ForeignKey('usuario.id'))
    usuario = relationship(Usuario)

    usuario_id = Column(Integer, ForeignKey('usuario.id'))

    @property
    def serialize(self):
        obj = {
            'id': self.id,
            'nome': self.nome,
            'descricao': self.descricao
        }
        return obj


class Item(Base):
    ''' Esta classe implementa os itens do catalogo e dispoe
        dos atributos serializados.
    '''
    __tablename__ = 'item'

    id = Column(Integer, primary_key=True)
    nome = Column(String(80), nullable=False)
    descricao = Column(String(250))

    categoria_id = Column(Integer, ForeignKey('categoria.id'))
    categoria = relationship(Categoria)

    usuario_id = Column(Integer, ForeignKey('usuario.id'))
    usuario = relationship(Usuario)

    @property
    def serialize(self):
        obj = {
            'id': self.id,
            'nome': self.nome,
            'descricao': self.descricao
        }
        return obj


engine = create_engine('sqlite:///catalogo.db')
Base.metadata.create_all(engine)
