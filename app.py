import hashlib
import os
import pymysql
from flask import Flask, request, jsonify

app = Flask(__name__)

# ============================
# НАСТРОЙКИ — ЗАПОЛНИ СВОИМИ ДАННЫМИ
# ============================
MERCHANT_LOGIN   = "ВАШ_ЛОГИН_ROBOKASSA"
MERCHANT_PASSWORD_1 = "ВАШ_ПАРОЛЬ_1"
MERCHANT_PASSWORD_2 = "ВАШ_ПАРОЛЬ_2"

DB_HOST = "IP_ТВОЕГО_GAME_СЕРВЕРА"   # или адрес MySQL
DB_USER = "root"
DB_PASS = ""
DB_NAME = "flamerp"
DB_PORT = 3306
# ============================


def get_db():
    return pymysql.connect(
        host=DB_HOST, user=DB_USER, password=DB_PASS,
        database=DB_NAME, port=DB_PORT, charset="utf8"
    )


def calculate_signature(*args) -> str:
    return hashlib.md5(":".join(str(a) for a in args).encode()).hexdigest()


@app.route("/robokassa/result", methods=["POST", "GET"])
def result_url():
    """
    Robokassa вызывает этот URL после успешной оплаты.
    Мы проверяем подпись и добавляем FC в очередь в MySQL.
    """
    params = request.values  # работает и для GET и для POST

    out_sum   = params.get("OutSum", "")
    inv_id    = params.get("InvId", "")
    signature = params.get("SignatureValue", "")

    # Проверка подписи (используем Password2 для ResultURL)
    expected = calculate_signature(out_sum, inv_id, MERCHANT_PASSWORD_2)
    if expected.lower() != signature.lower():
        print(f"[ROBOKASSA] Неверная подпись! Ожидали {expected}, получили {signature}")
        return "bad sign", 400

    # InvId имеет формат: STEAMID64_AMOUNT, например: 76561198000000000_100
    try:
        steamid64, fc_amount = inv_id.split("_")
        fc_amount = int(fc_amount)
    except Exception as e:
        print(f"[ROBOKASSA] Не удалось разобрать InvId: {inv_id} — {e}")
        return "bad inv_id", 400

    # Записываем в очередь MySQL — GMod сервер подберёт и начислит
    try:
        db = get_db()
        with db.cursor() as cur:
            # Таблица создаётся автоматически при первом запуске GMod аддона
            cur.execute(
                "INSERT INTO fl_donate_queue (steamid, amount, processed) VALUES (%s, %s, 0)",
                (steamid64, fc_amount)
            )
        db.commit()
        db.close()
        print(f"[ROBOKASSA] Начислено {fc_amount} FC для {steamid64}")
    except Exception as e:
        print(f"[ROBOKASSA] Ошибка MySQL: {e}")
        return "db error", 500

    # Обязательный ответ для Robokassa
    return f"OK{inv_id}"


@app.route("/robokassa/success", methods=["GET"])
def success_url():
    """Страница куда попадает пользователь после успешной оплаты."""
    params = request.values
    out_sum   = params.get("OutSum", "")
    inv_id    = params.get("InvId", "")
    signature = params.get("SignatureValue", "")

    expected = calculate_signature(out_sum, inv_id, MERCHANT_PASSWORD_1)
    if expected.lower() != signature.lower():
        return "Ошибка проверки платежа!", 400

    try:
        steamid64, fc_amount = inv_id.split("_")
    except Exception:
        return "Ошибка!", 400

    return f"""
    <html><head><meta charset="utf-8">
    <title>Оплата прошла успешно!</title>
    <style>
        body {{ font-family: Arial; background: #1a1a2e; color: #eee; 
               display:flex; align-items:center; justify-content:center; height:100vh; margin:0; }}
        .box {{ background: #16213e; border-radius:12px; padding:40px; text-align:center; }}
        h1 {{ color: #e94560; }} .amount {{ font-size:2em; color:#0f3460; 
        background:#e94560; padding:10px 24px; border-radius:8px; display:inline-block; }}
    </style></head><body>
    <div class="box">
        <h1>✅ Оплата прошла успешно!</h1>
        <p>Вы пополнили баланс на <span class="amount">{fc_amount} FC</span></p>
        <p style="color:#aaa; margin-top:20px;">FC будут начислены в течение 30 секунд.<br>
        Вернитесь в игру!</p>
    </div></body></html>
    """


@app.route("/robokassa/fail", methods=["GET"])
def fail_url():
    return """
    <html><head><meta charset="utf-8"><title>Оплата отменена</title>
    <style>body{{font-family:Arial;background:#1a1a2e;color:#eee;
    display:flex;align-items:center;justify-content:center;height:100vh;margin:0;}}
    .box{{background:#16213e;border-radius:12px;padding:40px;text-align:center;}}
    h1{{color:#e94560;}}</style></head><body>
    <div class="box"><h1>❌ Оплата отменена</h1>
    <p>Вы можете попробовать снова в игре командой <b>!donate</b></p>
    </div></body></html>
    """


@app.route("/")
def index():
    return "FlameRP Donate Server — OK", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
