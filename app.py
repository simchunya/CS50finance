import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
os.environ['API_KEY'] = 'pk_95efba3bd81e4f2882a6ad9990e38de6'
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY invalid")

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    #Show portfolio of stocks
    user_history = db.execute("SELECT * FROM TxnHistory WHERE PersonID = ? ORDER BY symbol DESC", session["user_id"])
    list_of_stocks =[]
    stock_dict = {'symbol': 0, 'share': 0, 'name': 0, 'price': 0}
    stocks_value = 0

    for txn in user_history:
        stock_details = lookup(txn["Symbol"])
        if stock_details["symbol"] == stock_dict["symbol"]:
            if txn["Type"] == "BUY":
                stock_dict["share"] += int(txn["Shares"])
            if txn["Type"] == "SELL":
                stock_dict["share"] -= int(txn["Shares"])

        else:
            list_of_stocks.append(stock_dict)
            stock_dict = {'symbol': 0, 'share': 0, 'name': 0, 'price': 0}

            stock_dict["symbol"] = stock_details["symbol"]
            stock_dict["share"] = txn["Shares"]
            stock_dict["name"] = stock_details["name"]
            stock_dict["price"] = stock_details["price"]
    list_of_stocks.append(stock_dict)
    list_of_stocks.pop(0)

    current_cash = db.execute("SELECT cash FROM users WHERE username = ?", session["username"])[0]
    for stock in list_of_stocks:
        stocks_value += stock['share'] * stock['price']

    total = current_cash['cash'] + stocks_value
    return render_template("index.html", list_of_stocks=list_of_stocks, current_cash=current_cash, stocks_value=stocks_value, total=total)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        look = lookup(request.form.get("symbol"))
        share = int(request.form.get("shares"))
        if look == None:
            return apology("Invalid SYmbol", 400)
        if share < 1:
            return apology("Y U NO BUY POSITIVE NUMBER", 400)
        #if share != int():
            #return apology("Y U NO BUY WHOLE SHARE", 400)

        session["quote_symbol"] = look["symbol"]
        session["quote_name"] = look["name"]
        session["quote_price"] = look["price"]
        session["price_to_pay"] = session["quote_price"] * share

        current_cash = db.execute("SELECT cash FROM users WHERE username = ?", session["username"])[0]
        if session["price_to_pay"] > current_cash["cash"]:
            return apology("Y U NO MONEY", 400)
        symbol = look["symbol"]
        name = look["name"]
        price = look["price"]
        type = "BUY"
        txndate = datetime.now().date()
        personid = session["user_id"]
        db.execute("INSERT INTO TxnHistory (symbol,name,shares,price,type,txndate,personid) VALUES(?,?,?,?,?,?,?)", symbol, name, share, price, type, txndate, personid)

        #deduct cash
        ans = int(current_cash["cash"] - session["price_to_pay"])
        db.execute("UPDATE users SET cash = ? WHERE username = ?", ans, session["username"])
        return redirect('/')

    elif request.method == 'GET':
        return render_template('buy.html')


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    user_history = db.execute("SELECT * FROM TxnHistory WHERE PersonID = ? ORDER BY txndate DESC", session["user_id"])
    print(user_history)
    return render_template('history.html', user_history = user_history)



@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]
        session["username"] = request.form.get("username")

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == 'POST':
        look = lookup(request.form.get("symbol"))
        print(look)
        if look != None:
            session["quote_symbol"] = look["symbol"]
            session["quote_name"] = look["name"]
            session["quote_price"] = look["price"]
            return render_template("quoted.html")
        else:
            return apology("Invalid Symbol", 400)

    elif request.method == 'GET':
        return render_template('quote.html')



@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == 'POST':
        users = db.execute("SELECT username FROM users")
        for i in users:
            if request.form.get("username") in i['username']:
                return apology("username has already been taken", 400)

        username = request.form.get("username")

        if request.form.get("username") == "" :
            return apology("Please enter a non-empty username", 400)

        if request.form.get("password") == request.form.get("confirmation"):
            hash = generate_password_hash(request.form.get("password"))
        else:
            return apology("password does not match")

        cash = 10000
        # insert registrant

        db.execute("INSERT INTO users (username,hash,cash) VALUES(?,?,?)", username, hash, cash)
        return redirect('/greatsuccess')

    elif request.method == 'GET':
        return render_template('register.html')

@app.route('/greatsuccess', methods=['POST', 'GET'])
def greatsuccess():
        return render_template('great_success.html')


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "POST":
        look = lookup(request.form.get("symbol"))
        share = request.form.get("shares")
        if look == None:
            return apology("Invalid SYmbol", 400)
        if share < 1:
            return apology("Y U NO SELL POSITIVE NUMBER", 400)

        """index()
        if request.form.get("symbol") not in list_of_stocks:
            return apology("You don't own it!", 460)"""

        session["quote_symbol"] = look["symbol"]
        session["quote_name"] = look["name"]
        session["quote_price"] = look["price"]
        session["price_to_pay"] = session["quote_price"] * share

        current_cash = db.execute("SELECT cash FROM users WHERE username = ?", session["username"])[0]
        symbol = look["symbol"]
        name = look["name"]
        price = look["price"]
        type = "SELL"
        txndate = datetime.now().date()
        personid = session["user_id"]
        db.execute("INSERT INTO TxnHistory (symbol,name,shares,price,type,txndate,personid) VALUES(?,?,?,?,?,?,?)", symbol, name, share, price, type, txndate, personid)

        #add cash
        ans = int(current_cash["cash"] + session["price_to_pay"])
        db.execute("UPDATE users SET cash = ? WHERE username = ?", ans, session["username"])
        return redirect('/')

    elif request.method == 'GET':
        return render_template('sell.html')
