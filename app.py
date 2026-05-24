import os
from flask import Flask, request
import hashlib

app = Flask(__name__)

MERCHANT_PASSWORD_2 = os.environ.get("MERCHANT_PASSWORD_2", "nF0th2bL5vveQs5nlL1q")

def md5(*args):
    return hashlib.md5(":".join(str(a) for a in args).encode()).hexdigest()

@app.route("/")
def index():
    return "OK", 200

@app.route("/robokassa/result", methods=["GET", "POST"])
def result():
    v = request.values
    out_sum = v.get("OutSum", "")
    inv_id  = v.get("InvId", "")
    sig     = v.get("SignatureValue", "")

    print(f"RESULT: OutSum={out_sum} InvId={inv_id} Sig={sig}")

    expected = md5(out_sum, inv_id, MERCHANT_PASSWORD_2)
    print(f"Expected sig: {expected}")

    if expected.lower() != sig.lower():
        return "bad sign", 400

    # TODO: добавить MySQL после того как сервер запустится стабильно
    print(f"PAYMENT OK: InvId={inv_id}")
    return f"OK{inv_id}"

@app.route("/robokassa/success")
def success():
    return "<h1>Оплата прошла! Вернитесь в игру.</h1>"

@app.route("/robokassa/fail")
def fail():
    return "<h1>Оплата отменена.</h1>"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
