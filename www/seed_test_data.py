"""
Заповнення БД тестовими даними — 100 вигаданих меморіалів
Запуск: python seed_test_data.py
"""
import pymysql
from dotenv import load_dotenv
import os, random, datetime

load_dotenv()

DB_CONFIG = {
    'host': os.getenv('DB_HOST', '127.0.0.1'),
    'port': int(os.getenv('DB_PORT', 3306)),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASS', 'root'),
    'database': os.getenv('DB_NAME', 'zoryana_pamyat'),
    'cursorclass': pymysql.cursors.DictCursor,
    'charset': 'utf8mb4',
}

# ── Вигадані дані ──

FIRST_NAMES_M = [
    "Олександр", "Андрій", "Дмитро", "Максим", "Іван", "Сергій", "Микола",
    "Володимир", "Петро", "Олексій", "Віталій", "Роман", "Тарас", "Юрій",
    "Богдан", "Артём", "Василь", "Григорій", "Данило", "Євген", "Зенон",
    "Ігор", "Кирило", "Лев", "Михайло", "Назар", "Олег", "Павло",
    "Руслан", "Степан", "Тимофій", "Федір", "Ярослав", "Адам", "Борис",
    "Вадим", "Гліб", "Дем'ян", "Едуард", "Захар", "Карл", "Леонід",
    "Марк", "Орест", "Платон", "Святослав", "Устим", "Хома", "Червоний",
    "Шевченко"
]

LAST_NAMES = [
    "Шевченко", "Бондаренко", "Ткаченко", "Кравченко", "Коваленко",
    "Бойко", "Мельник", "Поліщук", "Олійник", "Шульга",
    "Лисенко", "Савченко", "Руденко", "Козак", "Гриценко",
    "Тимченко", "Сидоренко", "Ковальчук", "Козленко", "Дорошенко",
    "Павленко", "Марченко", "Кузьменко", "Іваненко", "Петренко",
    "Степаненко", "Олексієнко", "Морозенко", "Демченко", "Василенко",
    "Захарченко", "Левченко", "Григоренко", "Бондар", "Савчук",
    "Гаврилюк", "Климчук", "Михайленко", "Даниленко", "Панченко",
    "Литвиненко", "Матвієнко", "Герасименко", "Трохименко", "Романенко",
    "Кулик", "Тарасенко", "Семченко", "Кравчук", "Бабенко",
    "Мартиненко", "Гончаренко", "Сидорчук", "Буряк", "Вітченко",
    "Гайдамака", "Демчук", "Єщенко", "Жук", "Зіненко",
    "Корнійчук", "Лазаренко", "Мазур", "Нагнибіда", "Онищенко",
    "Приходько", "Рябченко", "Сафонов", "Третяк", "Усенко",
    "Фещенко", "Харченко", "Цимбал", "Шило", "Щербина"
]

CITIES = [
    "Київ", "Харків", "Одеса", "Дніпро", "Львів", "Запоріжжя", "Вінниця",
    "Полтава", "Чернігів", "Суми", "Житомир", "Рівне", "Луцьк", "Тернопіль",
    "Хмельницький", "Кропивницький", "Миколаїв", "Херсон", "Черкаси",
    "Івано-Франківськ", "Ужгород", "Чернівці", "Біла Церква", "Кременчук",
    "Краматорськ", "Маріуполь", "Сєвєродонецьк", "Бахмут", "Авдіївка",
    "Попасна", "Лисичанськ", "Слов'янськ", "Ізюм", "Куп'янськ", "Балаклія"
]

UNITS = [
    "92 ОМБр", "93 ОМБр", "95 ОДШБр", "10 ОГШБр", "24 ОМБр",
    "28 ОМБр", "30 ОМБр", "53 ОМБр", "54 ОМБр", "57 ОМБр",
    "58 ОМПБр", "59 ОМПБр", "72 ОМБр", "80 ОДШБр", "81 ОАеМБр",
    "91 ОБМП", "92 ОБМП", "128 ОГШБр", "14 ОМБр", "21 ОБМП",
    "Азов", "Донбас", "Айдар", "Дніпро-1", "Полтава",
    "Хартія", "Січ", "Легіон Свободи", "Карпатська Січ", "ОУН"
]

RANKS = [
    "солдат", "молодший сержант", "сержант", "старший сержант",
    "старшина", "молодший лейтенант", "лейтенант", "старший лейтенант",
    "капітан", "майор", "підполковник", "полковник"
]

POSITIONS = [
    "стрілець", "снайпер", "кулеметник", "гранатометник", "механік-водій",
    "навідник", "командир відділення", "командир взводу", "командир роти",
    "медик", "розвідник", "стрілець-помічник", "оператор БПЛА",
    "радист", "сапер", "мінометник", "танкіст", "десантник",
    "штурман", "пілот", "начальник штабу", "комендант"
]

AWARDS = [
    {"name": "Хрест бойових заслуг", "img": "cross_combat.png"},
    {"name": "Хрест хоробрих", "img": "cross_brave.png"},
    {"name": "Орден «За мужність» I ст.", "img": "order_courage_1.png"},
    {"name": "Орден «За мужність» II ст.", "img": "order_courage_2.png"},
    {"name": "Орден «За мужність» III ст.", "img": "order_courage_3.png"},
    {"name": "Орден Богдана Хмельницького", "img": "order_khmelnytsky.png"},
    {"name": "Медаль «За військову службу Україні»", "img": "medal_service.png"},
    {"name": "Медаль «Захиснику Вітчизни»", "img": "medal_defender.png"},
    {"name": "Відзнака «За вірність присязі»", "img": "badge_oath.png"},
    {"name": "Відзнака «За заслуги перед ЗСУ»", "img": "badge_zsu.png"},
    {"name": "Герой України (посмертно)", "img": "hero_ukraine.png"},
    {"name": "Орден Данила Галицького", "img": "order_galician.png"},
    {"name": "Медаль «За бездоганну службу»", "img": "medal_flawless.png"},
    {"name": "Відзнака Президента «За участь в АТО»", "img": "badge_ato.png"},
    {"name": "Нагрудний знак «За воїнську доблесть»", "img": "badge_valor.png"},
]

GROUPS = [
    "Військовий", "Волонтер", "Медик", "Розвідник", "Пілот",
    "Снайпер", "Артилерист", "Танкіст", "Десантник", "Морпіх",
    "ТРО", "Нацгвардія", "Прикордонник", "Поліцейський"
]

COLORS = [
    "#4fc3f7", "#81c784", "#ffb74d", "#e57373", "#ba68c8",
    "#4dd0e1", "#aed581", "#ffd54f", "#ff8a65", "#f06292",
    "#9575cd", "#7986cb", "#4db6ac", "#d4e157", "#ffca28"
]


def random_date(start_year=2022, end_year=2024):
    y = random.randint(start_year, end_year)
    m = random.randint(1, 12)
    d = random.randint(1, 28)
    return datetime.date(y, m, d)


def gen_memorial():
    first = random.choice(FIRST_NAMES_M)
    last = random.choice(LAST_NAMES)
    birth = random_date(1970, 2003)
    death = random_date(2022, 2024)
    city = random.choice(CITIES)
    rank = random.choice(RANKS)
    position = random.choice(POSITIONS)
    unit = random.choice(UNITS)
    group = random.choice(GROUPS)
    color = random.choice(COLORS)
    approved = random.choice([0, 1, 1, 1, 1])  # 80% approved
    pos_x = round(random.uniform(0.1, 0.9), 3)
    pos_y = round(random.uniform(0.1, 0.9), 3)
    likes = random.randint(0, 150)
    rating = round(random.uniform(1.0, 5.0), 2)
    descr = random.choice([
        "",
        "Загинув захищаючи Україну від російських окупантів.",
        "Герой, який віддав життя за свободу нашої держави.",
        "Справжній захисник, який не побоявся стати на захист Батьківщини.",
        "Вічна пам'ять герою! Слава Україні!",
        "Боровся за наше майбутнє. Герої не вмирають!",
    ])
    circ = random.choice([
        "",
        "Повне ім'я: " + first + " " + last + " " + random.choice(["Олександрович", "Іванович", "Петрович", "Миколайович", "Сергійович"]),
    ])
    mid_name = random.choice([
        "",
        random.choice(["Олександрович", "Іванович", "Петрович", "Миколайович", "Сергійович", "Володимирович", "Андрійович"]),
    ])

    return {
        'last': last,
        'first': first,
        'mid': mid_name,
        'birth': birth.isoformat(),
        'death': death.isoformat(),
        'loc': city,
        'bury': random.choice(["Київська область", "Донецька область", "Харківська область", "Львівська область", ""]),
        'circ': circ,
        'descr': descr,
        'photo': '',
        'color': color,
        'video_url': '',
        'rank': rank,
        'position': position,
        'unit': unit,
        'pos_x': pos_x,
        'pos_y': pos_y,
        'grp': group,
        'added_by': 'seed',
        'approved': approved,
        'likes': likes,
        'rating': rating,
    }


def main():
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()

    # Видалити існуючі тестові дані (якщо є)
    cursor.execute("DELETE FROM memorial_awards WHERE memorial_id IN (SELECT id FROM memorials WHERE added_by='seed')")
    cursor.execute("DELETE FROM memorials WHERE added_by='seed'")
    conn.commit()

    print(f"Генерую 100 тестових меморіалів...")

    inserted = 0
    for i in range(100):
        m = gen_memorial()
        try:
            cursor.execute("""
                INSERT INTO memorials
                (last,first,mid,birth,death,loc,bury,circ,descr,photo,color,video_url,`rank`,`position`,`unit`,pos_x,pos_y,grp,added_by,approved,likes,rating)
                VALUES (%(last)s,%(first)s,%(mid)s,%(birth)s,%(death)s,%(loc)s,%(bury)s,%(circ)s,%(descr)s,%(photo)s,%(color)s,%(video_url)s,%(rank)s,%(position)s,%(unit)s,%(pos_x)s,%(pos_y)s,%(grp)s,%(added_by)s,%(approved)s,%(likes)s,%(rating)s)
            """, m)
            mid = cursor.lastrowid

            # Додати 1-3 нагороди (70% отримують нагороди)
            if random.random() < 0.7:
                num_awards = random.randint(1, 3)
                selected = random.sample(AWARDS, num_awards)
                for j, aw in enumerate(selected):
                    cursor.execute(
                        "INSERT INTO memorial_awards (memorial_id,name,img_file,sort_order) VALUES (%s,%s,%s,%s)",
                        (mid, aw['name'], aw['img'], j)
                    )

            inserted += 1
            if (i + 1) % 20 == 0:
                print(f"  ...{i + 1}/100")

        except Exception as e:
            print(f"  Помилка на {i+1}: {e}")
            conn.rollback()

    conn.commit()

    # Статистика
    cursor.execute("SELECT COUNT(*) AS cnt FROM memorials WHERE added_by='seed'")
    total = cursor.fetchone()['cnt']
    cursor.execute("SELECT COUNT(*) AS cnt FROM memorial_awards WHERE memorial_id IN (SELECT id FROM memorials WHERE added_by='seed')")
    awards_count = cursor.fetchone()['cnt']
    cursor.execute("SELECT approved, COUNT(*) AS cnt FROM memorials WHERE added_by='seed' GROUP BY approved")
    by_status = {row['approved']: row['cnt'] for row in cursor.fetchall()}

    print(f"\n✅ Готово!")
    print(f"   Меморіалів додано: {total}")
    print(f"   Нагород додано:    {awards_count}")
    print(f"   Затверджені:       {by_status.get(1, 0)}")
    print(f"   На модерації:      {by_status.get(0, 0)}")

    cursor.close()
    conn.close()


if __name__ == '__main__':
    main()
