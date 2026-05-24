import hashlib
import os
import pymysql
from flask import Flask, request

app = Flask(__name__)

MERCHANT_LOGIN      = os.environ.get("MERCHANT_LOGIN",      "GCore_project")
MERCHANT_PASSWORD_1 = os.environ.get("MERCHANT_PASSWORD_1", "Rl5vaXHuKxg9M12s0QJX")
MERCHANT_PASSWORD_2 = os.environ.get("MERCHANT_PASSWORD_2", "Ypuoa136zNSyCg3VseA1")

DB_HOST = os.environ.get("DB_HOST", "clustdb2.masspas.com")
DB_USER = os.environ.get("DB_USER", "u4717_WlSZyh1Kpa")
DB_PASS = os.environ.get("DB_PASS", "e7jUq^u9A@SStK3mLVMid!ft")
DB_NAME = os.environ.get("DB_NAME", "s4717_flamerp")
DB_PORT = int(os.environ.get("DB_PORT", "3306"))


def get_db():
    return pymysql.connect(
        host=DB_HOST, user=DB_USER, password=DB_PASS,
        database=DB_NAME, port=DB_PORT, charset="utf8",
        connect_timeout=5
    )


def calculate_signature(*args) -> str:
    return hashlib.md5(":".join(str(a) for a in args).encode()).hexdigest()


@app.route("/")
def index():
    return "FlameRP Donate — OK", 200


@app.route("/robokassa/result", methods=["POST", "GET"])
def result_url():
    params    = request.values
    out_sum   = params.get("OutSum", "")
    inv_id    = params.get("InvId", "")
    signature = params.get("SignatureValue", "")

    print(f"[Robokassa] ResultURL hit: OutSum={out_sum} InvId={inv_id} Sig={signature}")

    # Проверка подписи
    expected = calculate_signature(out_sum, inv_id, MERCHANT_PASSWORD_2)
    if expected.lower() != signature.lower():
        print(f"[Robokassa] BAD SIGN: expected={expected} got={signature}")
        return "bad sign", 400

    try:
        db = get_db()
        with db.cursor(pymysql.cursors.DictCursor) as cur:
            cur.execute(
                "SELECT steamid, fc_amount FROM fl_robokassa_orders WHERE inv_id = %s",
                (inv_id,)
            )
            row = cur.fetchone()

        if not row:
            print(f"[Robokassa] Order not found: inv_id={inv_id}")
            db.close()
            return "order not found", 404

        steamid64 = row["steamid"]
        fc_amount = int(row["fc_amount"])

        with db.cursor() as cur:
            cur.execute(
                "INSERT INTO fl_donate_queue (steamid, amount, processed) VALUES (%s, %s, 0)",
                (steamid64, fc_amount)
            )
        db.commit()
        db.close()

        print(f"[Robokassa] OK: {fc_amount} FC -> {steamid64}")

    except Exception as e:
        print(f"[Robokassa] DB ERROR: {e}")
        return f"db error: {e}", 500

    return f"OK{inv_id}"


@app.route("/robokassa/success")
def success_url():
    return """<html><head><meta charset="utf-8"><title>Оплата прошла!</title>
    <style>body{font-family:Arial;background:#1a1a2e;color:#eee;display:flex;
    align-items:center;justify-content:center;height:100vh;margin:0}
    .box{background:#16213e;border-radius:12px;padding:40px;text-align:center}
    h1{color:#4caf50}</style></head><body><div class="box">
    <h1>✅ Оплата прошла!</h1>
    <p>FC будут начислены в течение 30 секунд.</p>
    <p style="color:#aaa">Вернитесь в игру!</p>
    </div></body></html>"""


@app.route("/robokassa/fail")
def fail_url():
    return """<html><head><meta charset="utf-8"><title>Отменено</title>
    <style>body{font-family:Arial;background:#1a1a2e;color:#eee;display:flex;
    align-items:center;justify-content:center;height:100vh;margin:0}
    .box{background:#16213e;border-radius:12px;padding:40px;text-align:center}
    h1{color:#e94560}</style></head><body><div class="box">
    <h1>❌ Оплата отменена</h1>
    <p>Попробуйте снова командой <b>!donate</b> в игре.</p>
    </div></body></html>"""


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
