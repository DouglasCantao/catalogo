from flask import Flask, render_template, request
from flask import session, redirect, jsonify, url_for, flash, g
import hashlib
import os

from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker
from conn import Base, Categoria, Item, Usuario

from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2

from google.oauth2 import id_token
from google.auth.transport import requests

import json

from flask import make_response
import requests as py_requests

from functools import wraps

app = Flask(__name__)

secret_key = os.urandom(24)

# Conectar ao banco de dados e iniciar a sessao
engine = create_engine('sqlite:///catalogo.db')
Base.metadata.bind = engine


DBSession = sessionmaker(bind=engine)
# s = DBSession()

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Catalogo"


@app.route('/gcon/<token>', methods=['POST'])
def gcon(token):
    s = DBSession()
    try:
        # Passar client id para verificacao.
        idinfo = id_token.verify_oauth2_token(token, requests.Request(),
                                              CLIENT_ID)

        if idinfo['iss'] not in ['accounts.google.com',
                                 'https://accounts.google.com']:
            raise ValueError('Wrong issuer.')

        # ID token valido. Recuperar informacoes disponiveis.
        userid = idinfo['sub']
        session['email'] = idinfo['email']
        session['name'] = idinfo['name']
        session['token'] = token

        usuario = s.query(Usuario).filter_by(email=idinfo['email']).one()

        if usuario.token is None:
            usuario.token = idinfo['sub']
            s.add(usuario)
            s.commit()
            return redirect(url_for('show_categorias'))

        elif usuario.token != idinfo['sub']:

            usuario = Usuario()
            usuario.email = idinfo['email']
            usuario.name = idinfo['given_name']
            usuario.token = idinfo['sub']
            usuario.nickname = ''
            usuario.last_name = idinfo['family_name']
            s.add(usuario)
            s.commit()

            return redirect(url_for('show_categorias'))
    except ValueError:
        # Invalid token
        pass
    return redirect(url_for('login'))


def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            redirect(url_for('login'))


@login_required
@app.route('/logout/')
def logout():
    session.clear()
    return redirect(url_for('show_categorias'))


@app.route('/login/', methods=['GET', 'POST'])
def login():
    s = DBSession()

    if request.method == 'POST':
        session.pop('user', None)
        nickname = request.form.get("nickname", False)
        pwd = request.form.get("inputPwd", False)

        if check_hashed_pwd(nickname, pwd):
            usuario = s.query(Usuario).filter_by(nickname=nickname).one()
            session['user'] = usuario.nickname
            session['name'] = usuario.name
            session['id'] = usuario.id
            session['logged_in'] = True

            return redirect(url_for('show_categorias'))

    return render_template('login.html', STATE=state)


# Encriptar a senha do usuario
def create_hashed_pwd(pwd):
    pwd_hash = hashlib.sha256(pwd.encode()).hexdigest()
    return pwd_hash


# Verificar password
def check_hashed_pwd(nickname, pwd):
    s = DBSession()
    if s.query(Usuario).filter_by(nickname=nickname).first():
        user = s.query(Usuario).filter_by(nickname=nickname).one()
        pwd_to_check = hashlib.sha256(pwd.encode()).hexdigest()

        if user.password == pwd_to_check:
            return True

    return False


@app.route('/')
@app.route('/catalogo/')
def show_categorias():
    s = DBSession()
    categorias = s.query(Categoria).all()
    return render_template('index.html', categorias=categorias)


@app.route('/items/<int:id_categoria>/')
def show_items(id_categoria):
    s = DBSession()
    categorias = s.query(Categoria).all()
    categoria = s.query(Categoria).filter_by(id=id_categoria).one()
    items = s.query(Item).filter_by(categoria_id=id_categoria).all()
    result = s.query(Categoria).join(Item).filter(id == id_categoria).all()
    return render_template('show_items.html', items=items,
                           categorias=categorias,
                           categoria=categoria)


@app.route('/item/<int:id_item>/')
def show_item_descricao(id_item):
    s = DBSession()
    item = s.query(Item).filter_by(id=id_item).one()
    return render_template('item_descricao.html', item=item)


@app.route('/registrar/', methods=['GET', 'POST'])
def registrar():
    s = DBSession()
    if request.method == 'POST':
        nickname = request.form.get("inputUserName", False)
        name = request.form.get("imputName", False)
        last_name = request.form.get("inputLastName", False)
        email = request.form.get("inputEmail", False)

        pwd1 = request.form.get("inputPwd", False)
        pwd2 = request.form.get("inputPwd2", False)
        if pwd1 is not None and pwd2 is not None:
            novo_usuario = Usuario(name=name,
                                   nickname=nickname,
                                   password=create_hashed_pwd(pwd1),
                                   last_name=last_name,
                                   email=email)
            s.add(novo_usuario)
            s.commit()
            session['user'] = nickname
            session['name'] = name
            session['logged_in'] = True
            return redirect(url_for('show_categorias'))

    return render_template('registrar.html')


@login_required
@app.route('/categorias/', methods=['GET'])
def mostrar_categoria():
    s = DBSession()
    if 'user' in session:
        nickname = session['user']
        user = s.query(Usuario).filter_by(nickname=nickname).one()
    else:
        return redirect(url_for('login'))

    if s.query(Categoria).filter_by(usuario_id=user.id).first() is not None:
        categorias = s.query(Categoria).filter_by(usuario_id=user.id).all()
    else:
        categorias = []

    return render_template('criar_catalogo.html', categorias=categorias)


@login_required
@app.route('/criarcategoria/', methods=['POST'])
def criar_categoria():
    s = DBSession()
    if 'user' in session:
        nickname = session['user']
        user = s.query(Usuario).filter_by(nickname=nickname).one()
    else:
        return redirect(url_for('login'))

    if request.method == 'POST':
        nome = request.form.get("inputCategoria", False)
        descricao = request.form.get("inputDescricao", False)

        if nome is not None:
            categoria = Categoria(nome=nome,
                                  descricao=descricao,
                                  usuario_id=user.id)
            s.add(categoria)
            s.commit()
        else:
            flash('Informe um nome para a categoria!')

    return redirect(url_for('mostrar_categoria'))


@login_required
@app.route('/adicionaritem/', methods=['GET', 'POST', 'DELETE'])
def adicionar_item():
    s = DBSession()
    if 'user' in session:
        nickname = session['user']
        user = s.query(Usuario).filter_by(nickname=nickname).one()
    else:
        return redirect(url_for('login'))

    if s.query(Categoria).all() is not None:
        categorias = s.query(Categoria).all()
    else:
        categorias = []

    if s.query(Item).filter_by(usuario_id=user.id).first() is not None:
        items = s.query(Item, Categoria).join(Categoria).filter(
            Item.usuario_id == user.id).all()
    else:
        items = []

    if request.method == 'POST':
        nome_item = request.form.get("inputItem", False)
        descricao = request.form.get("inputDescricao", False)
        categoria_id = request.form.get("inputCategoria", False)

        if nome_item is not None and categoria_id is not None:
            novo_item = Item(nome=nome_item,
                             descricao=descricao,
                             categoria_id=categoria_id,
                             usuario_id=user.id)
            s.add(novo_item)
            s.commit()

            return redirect(url_for('adicionar_item'))

    return render_template('adicionar_item.html', categorias=categorias,
                           items=items)


@app.route('/removeitem/<int:id_item>', methods=['DELETE'])
def remove_item(id_item):
    s = DBSession()
    if request.method == 'DELETE' and id_item is not None:

        item = s.query(Item).filter_by(id=id_item).one()
        s.delete(item)
        s.commit()
        return redirect(url_for('adicionar_item'))


@app.route('/editaritem/<int:id_item>', methods=['POST'])
def editar_item(id_item):
    s = DBSession()

    json = request.get_json()

    nome_item = json["nome_item"]
    descricao = json["descricao"]
    categoria_id = json["categoria_id"]

    item = s.query(Item).filter_by(id=id_item).one()
    item.nome = nome_item
    item.descricao = descricao
    item.categoria_id = categoria_id
    s.add(item)
    s.commit()

    return 'OK', 200


@app.route('/removecategoria/<int:id_categoria>', methods=['DELETE'])
def remove_categoria(id_categoria):
    s = DBSession()
    if request.method == 'DELETE' and id_categoria is not None:

        categoria = s.query(Categoria).filter_by(id=id_categoria).one()
        s.delete(categoria)
        s.commit()
    return 'OK', 200


@app.route('/editarcategoria/<int:id_categoria>', methods=['POST'])
def editar_categoria(id_categoria):
    s = DBSession()
    json = request.get_json()
    nome = json["cat_nome"]
    descricao = json["cat_descricao"]

    categoria = s.query(Categoria).filter_by(id=id_categoria).one()
    categoria.nome = nome
    categoria.descricao = descricao
    s.add(categoria)
    s.commit()

    return redirect(url_for('mostrar_categoria'))


if __name__ == '__main__':
    app.secret_key = secret_key
    app.debug = True
    app.run(host='0.0.0.0', port=80)
