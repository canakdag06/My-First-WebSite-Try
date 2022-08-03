from ast import keyword
from email import message
import re
from typing import Text
from unicodedata import name
from unittest import result
from wsgiref.validate import validator
from click import confirm
from flask import Flask, flash, render_template, redirect, url_for, session, logging,request
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from functools import wraps


#Kullanıcı Giriş Decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session:
            return f(*args, **kwargs)
        else:
            flash("Bu sayfayı görüntülemek için giriş yapmalısınız.","danger")
            return redirect(url_for("login"))
    return decorated_function

#Kullanıcı Kayıt Formu
class RegisterForm(Form):
    name = StringField("Ad Soyad", validators=[validators.Length(min = 4, max = 25, message="4-25 karakter girebilirsiniz")])
    username = StringField("Kullanıcı Adı: ", validators=[validators.Length(min = 5, max = 35, message="5-35 karakter girebilirsiniz")])
    email = StringField("Email: ",[validators.Email(message="Lütfen geçerli bir mail adresi girin.")])
    password = PasswordField("Parola: ", validators = [
        validators.DataRequired(message = "Lütfen bir parola belirleyin."),
        validators.EqualTo(fieldname = "confirm", message="Parolanız uyuşmuyor.")
    ])
    confirm = PasswordField("Parola Doğrula")

#Login Formu
class LoginForm(Form):
    username = StringField("Kullanıcı Adı")
    password = PasswordField("Parola")


app = Flask(__name__)
app.secret_key = "canblog"

app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = ""
app.config["MYSQL_DB"] = "canblog"
app.config["MYSQL_CURSORCLASS"] = "DictCursor"

mysql = MySQL(app)



@app.route("/")
def index():
    return render_template("index.html")
    
@app.route("/about")
def about():
    return render_template("about.html")

#Makale Sayfası
@app.route("/articles")
def articles():
    cursor = mysql.connection.cursor()
    sorgu = "SELECT * FROM articles"
    result = cursor.execute(sorgu)
    if result > 0:
        articles = cursor.fetchall()
        return render_template("articles.html",articles = articles)
    else:
        return render_template("articles.html")

@app.route("/dashboard")
@login_required
def dashboard():
    cursor = mysql.connection.cursor()
    sorgu = "SELECT * FROM articles WHERE author = %s"
    result = cursor.execute(sorgu,(session["username"],))

    if result > 0:
        articles = cursor.fetchall()
        return render_template("dashboard.html", articles = articles)
    else:
        return render_template("dashboard.html")


#Kayıt Olma
@app.route("/register", methods = ["GET","POST"])
def register():
    form = RegisterForm(request.form)

    if request.method == "POST" and form.validate():
        name = form.name.data
        username = form.username.data
        email = form.email.data
        password = form.password.data
        
        cursor = mysql.connection.cursor()
        sorgu = "INSERT INTO user(name,email,username,password) VALUES(%s,%s,%s,%s)"
        cursor.execute(sorgu,(name,email,username,password))
        mysql.connection.commit()
        cursor.close()
        flash("Başarıyla Kayıt Oldunuz.","success")
        return redirect(url_for("login"))
    else:
        return render_template("register.html", form = form)
"""
@app.route("/article/<string:id>")
def detail(id):
    return "Article ID:" + id
"""
#Login
@app.route("/login",methods = ["GET","POST"])
def login():
    form = LoginForm(request.form)
    if request.method == "POST":
        username = form.username.data
        password_entered = form.password.data

        cursor = mysql.connection.cursor()
        sorgu = "SELECT * FROM user WHERE username = %s"
        result = cursor.execute(sorgu,(username,))
        if result > 0:
            data = cursor.fetchone()
            real_password = data["password"]
            if password_entered == real_password:
                flash("Başarıyla giriş yapıldı.","success")

                session["logged_in"] = True
                session["username"] = username
                return redirect(url_for("index"))
            else:
                flash("Yanlış parola girdiniz.","danger")
                return redirect(url_for("login"))
        else:
            flash("Böyle bir kullanıcı yok.","danger")
            return redirect(url_for("login"))
    return render_template("login.html", form = form)


#Detay Sayfası
@app.route("/article/<string:id>")
def article(id):
    cursor = mysql.connection.cursor()
    sorgu = "SELECT * FROM articles WHERE id = %s"
    result = cursor.execute(sorgu,(id,))
    if result > 0:
        article = cursor.fetchone()
        return render_template("article.html", article = article)
    else:
        return render_template("article.html")

#Logout
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

#Makale Ekleme
@app.route("/addarticle", methods = ["GET","POST"])
@login_required
def addarticle():
    form = ArticleForm(request.form)
    if request.method == "POST" and form.validate():
        title = form.title.data
        content = form.content.data
        cursor = mysql.connection.cursor()
        sorgu = "INSERT INTO articles(title,author,content) VALUES(%s,%s,%s)"
        cursor.execute(sorgu,(title,session["username"],content))
        mysql.connection.commit()
        cursor.close()
        flash("Makale başarıyla kaydedildi.","success")
        return redirect(url_for("dashboard"))
    return render_template("addarticle.html", form = form)

#Makale Silme
@app.route("/delete/<string:id>")
@login_required
def delete(id):
    cursor = mysql.connection.cursor()
    sorgu = "SELECT * FROM articles WHERE author = %s and id = %s"
    result = cursor.execute(sorgu, (session["username"],id))

    if result > 0:
        sorgu2 = "DELETE FROM articles WHERE id = %s"
        cursor.execute(sorgu2,(id,))
        mysql.connection.commit()
        return redirect(url_for("dashboard"))
    else:
        flash("Böyle bir makale veya bu makaleyi silmeye yetkiniz yok","danger")
        return redirect(url_for("index"))

#Makale Güncelleme
@app.route("/edit/<string:id>", methods = ["GET","POST"])
@login_required
def update(id):
    if request.method == "GET":
        cursor = mysql.connection.cursor()
        sorgu = "SELECT * FROM articles WHERE id = %s and author = %s"
        result = cursor.execute(sorgu,(id, session["username"]))

        if result == 0:
            flash("Böyle bir makale veya bu makaleyi güncelleme yetkiniz yok","danger")
            return redirect(url_for("index"))
        else:
            article = cursor.fetchone()
            form = ArticleForm()
            form.title.data = article["title"]
            form.content.data = article["content"]
            return render_template("update.html", form = form)
    else: # POST REQUEST
        form = ArticleForm(request.form)
        newTitle = form.title.data
        newContent = form.content.data
        sorgu2 = "UPDATE articles SET title = %s,content = %s WHERE id = %s"
        cursor = mysql.connection.cursor()
        cursor.execute(sorgu2,(newTitle,newContent,id))
        mysql.connection.commit()
        flash("Makale güncellendi","success")
        return redirect(url_for("dashboard"))

#Makale Form
class ArticleForm(Form):
    title = StringField("Makale Başlığı", validators=[validators.length(min = 5, max = 100)])
    content = TextAreaField("Makale İçeriği", validators=[validators.length(min=10)])

#Arama URL
@app.route("/search", methods = ["GET","POST"])
def search():
    if request.method == "GET":
        return redirect(url_for("index"))
    else:
        keyword = request.form.get("keyword")
        cursor = mysql.connection.cursor()
        sorgu = "SELECT * FROM articles WHERE title LIKE '%"+ keyword +"%'"
        result = cursor.execute(sorgu)
        
        if result == 0:
            flash("Aranan kriterlere uygun makale bulunamadı.","warning")
            return redirect(url_for("articles"))
        else:
            articles = cursor.fetchall()
            return render_template("articles.html",articles = articles)

if __name__ == "__main__":
    app.run(debug=True)
