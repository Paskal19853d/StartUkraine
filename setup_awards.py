"""
setup_awards.py — масове завантаження зображень нагород і заповнення БД.
Запуск: python setup_awards.py
"""
import subprocess, hashlib, os, time, sys
import pymysql
from dotenv import load_dotenv

load_dotenv()
BASE = os.path.dirname(os.path.abspath(__file__))
AWARDS_DIR = os.path.join(BASE, "img", "awards")
os.makedirs(AWARDS_DIR, exist_ok=True)

# ─── Повний список нагород ────────────────────────────────────────────────────
# (name_uk, local_file, wiki_filename, category, sort_order, description)
AWARDS = [
    # ── ВИЩІ ЗВАННЯ ──────────────────────────────────────────────────────────
    ("Герой України (посмертно)",
     "hero_ukraine.png",
     "Medal_of_Golden_Star_Ukraine.jpg",
     "hero", 1,
     "За здійснення видатного подвигу або визначний особистий внесок у захист суверенітету та територіальної цілісності України"),

    # ── ОРДЕНИ ───────────────────────────────────────────────────────────────
    ("Орден Свободи",
     "order_freedom.png",
     "Freedom_order.jpg",
     "order", 10,
     "За особливі заслуги перед Україною у захисті державного суверенітету, зміцненні демократії, прав і свобод людини"),

    ("Орден Героїв Небесної Сотні",
     "order_heavenly_hundred.png",
     "Орден_Героїв_Небесної_Сотні.PNG",
     "order", 11,
     "За особисту мужність і героїзм, виявлені під час захисту демократичних цінностей та прав людини"),

    ("Орден «За мужність» I ступеня",
     "order_courage_1.png",
     "Mugnist-1.jpg",
     "order", 20,
     "За особисту мужність і героїзм, виявлені в бойових діях при захисті державного суверенітету та територіальної цілісності України"),

    ("Орден «За мужність» II ступеня",
     "order_courage_2.png",
     "Mugnist-2.jpg",
     "order", 21,
     "За мужність і відвагу в бойових діях, самовіддане виконання військового обов'язку"),

    ("Орден «За мужність» III ступеня",
     "order_courage_3.png",
     "Mugnist-3.jpg",
     "order", 22,
     "За особисту мужність і стійкість, виявлені при виконанні військового та громадянського обов'язку"),

    ("Орден Богдана Хмельницького I ступеня",
     "order_khmelnytsky_1.png",
     "Order_of_Bohdan_Khmelnytsky_1st_Class_of_Ukraine.png",
     "order", 30,
     "За видатні заслуги у зміцненні обороноздатності держави, вагомий внесок у розвиток Збройних Сил України"),

    ("Орден Богдана Хмельницького II ступеня",
     "order_khmelnytsky_2.png",
     "Order_of_Bohdan_Khmelnytsky_2nd_Class_of_Ukraine.png",
     "order", 31,
     "За значний внесок у зміцнення обороноздатності держави та розвиток Збройних Сил України"),

    ("Орден Богдана Хмельницького III ступеня",
     "order_khmelnytsky_3.png",
     "Order_of_Bohdan_Khmelnytsky_3rd_Class_of_Ukraine.png",
     "order", 32,
     "За мужність і відвагу при виконанні бойових завдань, сумлінну військову службу"),

    ("Орден Данила Галицького",
     "order_galician.png",
     "Order_of_Danylo_Halytsky_of_Ukraine.png",
     "order", 40,
     "За визначні заслуги у захисті державного суверенітету, зміцненні обороноздатності та безпеки України"),

    ("Орден «За заслуги» I ступеня",
     "order_merit_1.png",
     "Zasluhy-1.jpg",
     "order", 50,
     "За видатні заслуги перед Україною у сфері державного будівництва, зміцнення обороноздатності та безпеки"),

    ("Орден «За заслуги» II ступеня",
     "order_merit_2.png",
     "Zasluhy-2.jpg",
     "order", 51,
     "За значний внесок у розбудову України, зміцнення її обороноздатності та безпеки"),

    ("Орден «За заслуги» III ступеня",
     "order_merit_3.png",
     "Zasluhy-3.jpg",
     "order", 52,
     "За заслуги перед державою, вагомий внесок у розвиток суспільства"),

    ("Орден князя Ярослава Мудрого I ступеня",
     "order_yaroslav_1.png",
     "Mudryj-1.jpg",
     "order", 60,
     "За визначний особистий внесок у державне будівництво та зміцнення міжнародного авторитету України"),

    ("Орден князя Ярослава Мудрого II ступеня",
     "order_yaroslav_2.png",
     "Mudryj-2.jpg",
     "order", 61,
     "За значний внесок у зміцнення державності, розвиток суспільства та міжнародного співробітництва"),

    ("Орден князя Ярослава Мудрого III ступеня",
     "order_yaroslav_3.png",
     "Mudryj-3.jpg",
     "order", 62,
     "За заслуги у розвитку науки, освіти, культури та зміцненні держави"),

    ("Орден князя Ярослава Мудрого IV ступеня",
     "order_yaroslav_4.png",
     "Mudryj-4.jpg",
     "order", 63,
     "За заслуги перед Україною у сфері державотворення та суспільного розвитку"),

    ("Орден князя Ярослава Мудрого V ступеня",
     "order_yaroslav_5.png",
     "Mudryj-5.jpg",
     "order", 64,
     "За багаторічну сумлінну службу та вагомий особистий внесок у розвиток держави"),

    # ── ХРЕСТИ ───────────────────────────────────────────────────────────────
    ("Хрест бойових заслуг",
     "cross_combat.png",
     "Cross_of_Combat_Merit_2.jpg",
     "cross", 100,
     "За особисту мужність і умілі дії в боях при захисті державного суверенітету та територіальної цілісності України"),

    ("Хрест хоробрих",
     "cross_brave.png",
     "Відзнака_ГК_ЗСУ_ХрестХоробрих-1.png",
     "cross", 101,
     "За особисту мужність і відвагу, виявлені при виконанні бойових завдань"),

    # ── МЕДАЛІ ───────────────────────────────────────────────────────────────
    ("Медаль «Захиснику Вітчизни»",
     "medal_defender.png",
     "Ukraine-Defender_of_the_Motherland_Medal.PNG",
     "medal", 200,
     "За захист державного суверенітету та територіальної цілісності України, зразкове виконання військового обов'язку"),

    ("Медаль «За поранення»",
     "medal_wound.png",
     "Wound_Medal_(Ukraine).png",
     "medal", 201,
     "Вручається військовослужбовцям, які отримали поранення (контузію, травму, каліцтво) під час виконання бойових завдань"),

    ("Медаль «За військову службу Україні»",
     "medal_service.png",
     "За_військову_службу_Україні.jpg",
     "medal", 210,
     "За зразкове виконання військового обов'язку, бездоганну службу та вагомий внесок у зміцнення обороноздатності держави"),

    ("Медаль «За бездоганну службу» I ступеня",
     "medal_flawless.png",
     "Bezdog-1.jpg",
     "medal", 220,
     "За бездоганну довготривалу військову службу та зразкове виконання службових обов'язків"),

    ("Медаль «За бездоганну службу» II ступеня",
     "medal_flawless_2.png",
     "Bezdog-2.jpg",
     "medal", 221,
     "За бездоганну довготривалу військову службу та зразкове виконання службових обов'язків"),

    ("Медаль «За бездоганну службу» III ступеня",
     "medal_flawless_3.png",
     "Bezdog-3.jpg",
     "medal", 222,
     "За бездоганну довготривалу військову службу та зразкове виконання службових обов'язків"),

    ("Медаль «За врятоване життя»",
     "medal_lifesaving.png",
     "Za_vryatovane_zhyttya.jpg",
     "medal", 230,
     "За особисту мужність і самопожертву, виявлені при рятуванні людей від загибелі"),

    # ── ВІДЗНАКИ / НАГРУДНІ ЗНАКИ ────────────────────────────────────────────
    ("Нагрудний знак «За воїнську доблесть»",
     "badge_valor.png",
     "Military_Valor_Badge_of_the_Ukrainian_Armed_Forces.png",
     "badge", 300,
     "За мужність, ініціативність та самовіддане виконання обов'язку у захисті державного суверенітету"),

    ("Відзнака «За вірність присязі»",
     "badge_oath.png",
     None,   # немає на Wikimedia
     "badge", 301,
     "За вірне служіння Батьківщині та неухильне виконання Військової присяги"),

    ("Відзнака «За заслуги перед ЗСУ»",
     "badge_zsu.png",
     "За_заслуги_перед_Збройними_Силами_України.png",
     "badge", 302,
     "За заслуги перед Збройними Силами України у зміцненні обороноздатності держави"),

    ("Відзнака Президента «За участь в АТО»",
     "badge_ato.png",
     "Uchastnyk-ato.png",
     "badge", 303,
     "Відзнака Президента України учасникам антитерористичної операції"),
]

# ─── Завантаження зображень ───────────────────────────────────────────────────
def md5_wiki_path(filename):
    """Обчислює CDN шлях для Wikimedia Commons."""
    h = hashlib.md5(filename.encode('utf-8')).hexdigest()
    from urllib.parse import quote
    enc = quote(filename)
    return f"{h[0]}/{h[:2]}/{enc}"

def curl_download(url, out_path, retries=2):
    for attempt in range(retries):
        if attempt > 0:
            time.sleep(5)
        r = subprocess.run(
            ["curl", "-s", "-L", "-o", out_path, "-w", "%{http_code}",
             "-H", "User-Agent: Mozilla/5.0", "--max-time", "20", url],
            capture_output=True, text=True
        )
        code = r.stdout.strip()
        if os.path.exists(out_path):
            size = os.path.getsize(out_path)
            if size > 5000 and code == "200":
                return True, size
        if os.path.exists(out_path):
            os.remove(out_path)
    return False, 0

def download_all():
    print("\n═══ ЗАВАНТАЖЕННЯ ЗОБРАЖЕНЬ ═══")
    ok, skip, fail = 0, 0, 0
    for name, local_file, wiki_file, *_ in AWARDS:
        out = os.path.join(AWARDS_DIR, local_file)
        if os.path.exists(out) and os.path.getsize(out) > 5000:
            print(f"  SKIP  {local_file}  (вже є)")
            skip += 1
            continue
        if wiki_file is None:
            print(f"  NOPIC {local_file}  (немає на Wikimedia)")
            skip += 1
            continue
        # Спробуємо CDN thumb (PNG 120px для SVG)
        path = md5_wiki_path(wiki_file)
        cdn = f"https://upload.wikimedia.org/wikipedia/commons/{path}"
        success, size = curl_download(cdn, out)
        if success:
            print(f"  OK    {local_file}  ({size:,} b)")
            ok += 1
        else:
            # Fallback: Special:FilePath через commons
            from urllib.parse import quote
            fp_url = f"https://commons.wikimedia.org/wiki/Special:FilePath/{quote(wiki_file)}"
            success, size = curl_download(fp_url, out)
            if success:
                print(f"  OK*   {local_file}  ({size:,} b via FilePath)")
                ok += 1
            else:
                print(f"  FAIL  {local_file}  ← {wiki_file}")
                fail += 1
        time.sleep(0.8)
    print(f"\n  Завантажено: {ok}, пропущено: {skip}, помилки: {fail}")
    return fail

# ─── БД: таблиця awards_catalog ──────────────────────────────────────────────
def setup_db():
    print("\n═══ БАЗА ДАНИХ ═══")
    db = pymysql.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASS", "root"),
        database=os.getenv("DB_NAME", "zoryana_pamyat"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor
    )
    with db.cursor() as c:
        # Створюємо таблицю
        c.execute("""
            CREATE TABLE IF NOT EXISTS awards_catalog (
              id          INT AUTO_INCREMENT PRIMARY KEY,
              name        VARCHAR(200) NOT NULL,
              img_file    VARCHAR(200) NOT NULL,
              category    VARCHAR(30)  NOT NULL DEFAULT 'military',
              description TEXT,
              sort_order  INT          NOT NULL DEFAULT 0,
              UNIQUE KEY uq_img (img_file)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        print("  Таблицю awards_catalog створено/оновлено.")

        # Вставляємо/оновлюємо всі нагороди
        inserted, updated = 0, 0
        for name, local_file, _, category, sort_order, desc in AWARDS:
            c.execute("""
                INSERT INTO awards_catalog (name, img_file, category, description, sort_order)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                  name=VALUES(name),
                  category=VALUES(category),
                  description=VALUES(description),
                  sort_order=VALUES(sort_order)
            """, (name, local_file, category, desc, sort_order))
            if c.rowcount == 1:
                inserted += 1
            else:
                updated += 1

        db.commit()
        print(f"  Вставлено: {inserted}, оновлено: {updated} записів.")

        # Перевіряємо
        c.execute("SELECT COUNT(*) AS cnt FROM awards_catalog")
        cnt = c.fetchone()["cnt"]
        print(f"  Всього в awards_catalog: {cnt} нагород.")
    db.close()

if __name__ == "__main__":
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  Зоряна Пам'ять — setup_awards.py")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    fails = download_all()
    setup_db()
    print("\n✓ Готово!")
    if fails:
        print(f"  ⚠ {fails} зображень не завантажено — перевір img/awards/")
