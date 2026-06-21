# 🔒 ПОЛНЫЙ АНАЛИЗ БЕЗОПАСНОСТИ ПРОЕКТА StartUkraine

---

## 📋 ВВЕДЕНИЕ

**Проект:** StartUkraine (Мемориальный проект Украины)  
**Анализ дата:** 2025  
**Статус:** ⚠️ ТРЕБУЕТ СРОЧНЫХ ИСПРАВЛЕНИЙ  
**Риск:** 🔴 **КРИТИЧЕСКИЙ** - Обнаружены уязвимости, позволяющие ИНЪЕКЦИИ И МАНИПУЛЯЦИИ  

---

## 🎯 ИТОГОВАЯ ОЦЕНКА

| Категория | Уровень | Статус |
|-----------|---------|--------|
| **XSS (Cross-Site Scripting)** | 🔴 КРИТИЧЕСКИЙ | Активен в 3+ endpoints |
| **SQL Injection** | 🟢 ЗАЩИЩЕНО | Используются параметризованные запросы |
| **CSRF (Cross-Site Request Forgery)** | 🟠 ВЫСОКИЙ | Отсутствуют CSRF токены в POST/PUT/DELETE |
| **Authentication** | 🟠 СРЕДНИЙ | Нет валидации email, слабая политика паролей |
| **Authorization** | 🟢 ЗАЩИЩЕНО | require_admin() функция работает |
| **Rate Limiting** | 🟢 ЗАЩИЩЕНО | На месте (но недокументировано) |
| **Информационное раскрытие** | 🟠 ВЫСОКИЙ | Stack traces видны, error messages подробны |
| **Input Validation** | 🟠 ВЫСОКИЙ | Минимальная валидация, нет sanitization |
| **Dependency Security** | 🟢 НИЗКИЙ | Зависимости относительно новые |
| **Infrastructure** | 🟠 ВЫСОКИЙ | SQLite в продакшене неподходящий |

---

## 🔴 КРИТИЧЕСКИЕ УЯЗВИМОСТИ

### **1. XSS (Cross-Site Scripting) - Injection**

#### Проблема:
Backend возвращает **UNESCAPED** JSON с user-input данными. Если другой frontend не escapeит - будет XSS.

#### Локация:
```
Файл: Paskal.py
Line: 319-333 (get_people endpoint)
Line: 327 (search endpoint)
Line: 354-365 (add_person endpoint)

Поля в опасности:
- descr (Description - САМАЯ ОПАСНАЯ!)
- first, last (Names)
- mid (Military ID)
- grp (Group/Unit)
- loc (Location)
- bury (Burial place)
```

#### Доказательство (PoC):
```bash
# 1. Заполнить memorial с XSS payload:
curl -X POST http://localhost:8000/api/people \
  -H "Content-Type: application/json" \
  -d '{
    "last": "Test",
    "first": "User",
    "descr": "<img src=x onerror=\"alert(document.cookie)\">"
  }'

# 2. Получить данные (UNESCAPED!):
curl http://localhost:8000/api/people | jq .[0].descr
# Результат: "<img src=x onerror=\"alert(document.cookie)\">"  ← СТРАШНО!

# 3. Если другой frontend не escapeит → XSS exploit работает!
```

#### Последствия:
- ✅ Кража cookies/session tokens
- ✅ Перенаправление на phishing сайты
- ✅ Модификация контента страницы
- ✅ Кража данных юзера
- ✅ Распространение вредоноса между юзерами

#### Исправление:

**Шаг 1:** Добавить escaping функцию (line ~50):
```python
import html as _html_esc

def _escape_for_json(text: str | None) -> str | None:
    """Escapeить HTML спецсимволы для безопасного JSON"""
    if not text or not isinstance(text, str):
        return text
    return _html_esc.escape(text, quote=True)
```

**Шаг 2:** Escapeить в get_people (line 319-333):
```python
@app.get("/api/people")
def get_people():
    db=get_db()
    people = db.execute("SELECT * FROM memorials WHERE approved=1").fetchall()
    # ✅ Escapeить все текстовые поля
    result = []
    for row in people:
        escaped_row = dict(row)
        for field in ['last', 'first', 'mid', 'grp', 'loc', 'bury', 'circ', 'descr']:
            if escaped_row.get(field):
                escaped_row[field] = _escape_for_json(escaped_row[field])
        result.append(escaped_row)
    return result
```

**Шаг 3:** Escapeить в search (line 327-333):
```python
@app.get("/api/search")
def search(q:str):
    if len(q)<2: return []
    db=get_db()
    results = db.execute(
        "SELECT * FROM memorials WHERE (last LIKE ? OR first LIKE ? OR mid LIKE ?) AND approved=1",
        (f"%{q}%", f"%{q}%", f"%{q}%")
    ).fetchall()
    
    # ✅ Escapeить результаты
    escaped_results = []
    for row in results:
        escaped_row = dict(row)
        for field in ['last', 'first', 'mid', 'grp', 'loc', 'bury', 'circ', 'descr']:
            if escaped_row.get(field):
                escaped_row[field] = _escape_for_json(escaped_row[field])
        escaped_results.append(escaped_row)
    return escaped_results
```

**Шаг 4:** Escapeить в add_person (line 354-365):
```python
@app.post("/api/people")
def add_person(p:PersonIn):
    db=get_db()
    
    # ✅ Escapeить перед сохранением (ОПЦИОНАЛЬНО - но рекомендуется!)
    # Или escapeить только при возврате в JSON (как в GET методах)
    
    db.execute(
        """INSERT INTO memorials 
        (last,first,mid,birth,death,loc,bury,circ,descr,photo,color,pos_x,pos_y,grp)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (p.last, p.first, p.mid, p.birth, p.death, p.loc, p.bury, 
         p.circ, p.descr, p.photo, p.color, p.pos_x, p.pos_y, p.grp)
    )
    db.commit()
    inserted_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    
    # ✅ Escapeить в response
    result = db.execute("SELECT * FROM memorials WHERE id=?", (inserted_id,)).fetchone()
    escaped_row = dict(result)
    for field in ['last', 'first', 'mid', 'grp', 'loc', 'bury', 'circ', 'descr']:
        if escaped_row.get(field):
            escaped_row[field] = _escape_for_json(escaped_row[field])
    
    return escaped_row
```

---

### **2. CSRF (Cross-Site Request Forgery)**

#### Проблема:
**ВСЕ** POST/PUT/DELETE endpoints **НЕ ЗАЩИЩЕНЫ** от CSRF атак!

#### Локация:
```
Файл: Paskal.py
Endpoints БЕЗ защиты:
- POST /api/people (line 354)
- POST /api/like/{mid} (line 367)
- POST /api/auth/register (line 379)
- POST /api/auth/login (line 391)
- POST /api/admin/approve/{mid} (line 421)
- DELETE /api/admin/memorial/{mid} (line 428)
- PUT /api/admin/memorial/{mid} (line 435)
- POST /api/admin/ban/{uid} (line 462)
- POST /api/admin/unban/{uid} (line 469)
- PUT /api/admin/color (line 476)
- PUT /api/admin/colors/batch (line 483)
- PUT /api/admin/label/{lid} (line 491)
```

#### Доказательство (PoC):
```html
<!-- Злоумышленник создает такую страницу: attack.html -->
<html>
<body onload="document.forms[0].submit()">
  <form action="http://localhost:8000/api/admin/ban/1" method="POST">
    <input type="hidden" name="email" value="admin@admin.com">
    <input type="hidden" name="password" value="Admin">
  </form>
</body>
</html>

<!-- Если админ откроет эту страницу → юзер будет забанен без его ведома! -->
```

#### Последствия:
- ✅ Несанкционированное банирование/разбан юзеров
- ✅ Несанкционированное удаление memorials
- ✅ Несанкционированное изменение colors/labels
- ✅ Несанкционированная регистрация ботов

#### Исправление:

**Вариант 1: Использовать SameSite cookies (ПРОСТОЙ)**
```python
# В CORS настройке (line ~220 или где инициализируется app):
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "your-domain.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Убедиться что session cookies имеют SameSite=Strict:
# response.set_cookie("session", value, samesite="Strict", secure=True, httponly=True)
```

**Вариант 2: Использовать CSRF токены (НАДЕЖНЕЕ)**

Добавить функцию генерации токенов (line ~50):
```python
import secrets

_csrf_token_store = {}  # В продакшене использовать Redis!

def generate_csrf_token():
    """Генерировать CSRF токен"""
    token = secrets.token_urlsafe(32)
    _csrf_token_store[token] = int(time.time())
    return token

def validate_csrf_token(token: str):
    """Проверить CSRF токен"""
    if token not in _csrf_token_store:
        raise HTTPException(403, "Invalid CSRF token")
    
    # Токен действителен 1 час
    if int(time.time()) - _csrf_token_store[token] > 3600:
        del _csrf_token_store[token]
        raise HTTPException(403, "CSRF token expired")
    
    del _csrf_token_store[token]  # One-time use
    return True
```

Добавить endpoint для получения токена:
```python
@app.get("/api/csrf-token")
def get_csrf_token():
    return {"csrf_token": generate_csrf_token()}
```

Добавить проверку в ВСЕ POST/PUT/DELETE endpoints:
```python
@app.post("/api/people")
def add_person(p:PersonIn, csrf_token: str):
    validate_csrf_token(csrf_token)  # ✅ Проверка!
    # ... rest of code
```

---

### **3. Слабая аутентификация**

#### Проблема #1: Нет валидации email
```python
# Текущий код (line 379-390):
@app.post("/api/auth/register")
def register(u:UserReg):
    if len(u.password)<6: raise HTTPException(400,"Пароль мінімум 6 символів")   
    db=get_db()
    try:
        db.execute("INSERT INTO users (name,email,password,is_admin) VALUES (?,?,?,0)",
                   (u.name, u.email, hash_pass(u.password)))
        # ❌ ПРОБЛЕМА: Не проверяется формат email!
        # ❌ Можно регистрировать: "notanemail", "   ", "admin@admin.com"
```

#### Исправление #1:
```python
import re

EMAIL_REGEX = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

def validate_email(email: str):
    if not re.match(EMAIL_REGEX, email):
        raise HTTPException(400, "Невалідна email адреса")

@app.post("/api/auth/register")
def register(u:UserReg):
    validate_email(u.email)  # ✅ Добавить проверку
    if len(u.password)<6: 
        raise HTTPException(400,"Пароль мінімум 6 символів")
    
    # ✅ Также добавить проверку что email не зареєстрирован
    existing = db.execute("SELECT id FROM users WHERE email=?", (u.email,)).fetchone()
    if existing:
        raise HTTPException(400, "Email вже зареєстрирован")
    
    db.execute("INSERT INTO users (name,email,password,is_admin) VALUES (?,?,?,0)",
               (u.name, u.email, hash_pass(u.password)))
    db.commit()
```

#### Проблема #2: Слабая политика паролей
```python
# Текущие требования: мінімум 6 символів
# ❌ Это ОЧЕНЬ слабо! Легко bruteforce
```

#### Исправление #2:
```python
PASSWORD_REGEX = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$'

def validate_password(password: str):
    """
    Требования:
    - Мінімум 8 символів
    - Майбутня буква (A-Z)
    - Малая буква (a-z)
    - Цифра (0-9)
    - Спец символ (@$!%*?&)
    """
    if not re.match(PASSWORD_REGEX, password):
        raise HTTPException(400, 
            "Пароль повинен мати 8+ символів, буквы, цифри та спец символи (@$!%*?&)")

# В register функции:
validate_password(u.password)  # ✅ Замінити len(u.password)<6
```

---

### **4. Інформаційне розкриття**

#### Проблема:
Коли happens error - юзер видит **ВЕСЬ stack trace** з деталями базы даних!

#### Последствия:
- ✅ Раскрытие структуры БД
- ✅ Раскрытие путей к файлам
- ✅ Информацию для социального инженерства
- ✅ Hints для атак

#### Исправление:

Добавить глобальный error handler (после инициализации app, ~line 230):
```python
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    import traceback
    
    # Логировать полный error для администраторов
    error_details = traceback.format_exc()
    
    # НО не показывать юзеру
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail}
        )
    
    # Для всех остальных - безопасное сообщение
    return JSONResponse(
        status_code=500,
        content={"detail": "Внутренняя ошибка сервера. Пожалуйста свяжитесь с поддержкой."}
    )
```

---

## 🟠 ВЫСОКИЕ УЯЗВИМОСТИ

### **5. Недостаточная валидация input**

| Поле | Проблема | Fix |
|------|----------|-----|
| `descr` | Нет limit на длину | `max_length=5000` в Pydantic |
| `photo` | Может быть путь к системному файлу | Валидировать только base64 или URLs |
| `name` | Нет санитизации специальных символов | `strip()` и limit на длину |
| `password` | Нет требованиям сложности | Добавить regex validation |
| `email` | Нет формата проверки | Email regex validation |

#### Исправление:
```python
from pydantic import BaseModel, Field, validator

class PersonIn(BaseModel):
    first: str = Field(..., min_length=1, max_length=100)
    last: str = Field(..., min_length=1, max_length=100)
    descr: str = Field(default="", max_length=5000)
    photo: str = Field(default="", regex=r"^(https?://|data:image|$)")  # ✅ Only URLs or data URIs
    mid: str = Field(default="", max_length=50)
    grp: str = Field(default="", max_length=200)
    loc: str = Field(default="", max_length=200)
    bury: str = Field(default="", max_length=200)
    circ: str = Field(default="", max_length=200)
    birth: str = Field(default="")
    death: str = Field(default="")
    color: str = Field(default="#4fc3f7", regex=r"^#[0-9a-fA-F]{6}$")  # ✅ Valid hex color
    pos_x: float = Field(default=0.5, ge=0, le=1)  # ✅ Between 0 and 1
    pos_y: float = Field(default=0.5, ge=0, le=1)  # ✅ Between 0 and 1
```

---

### **6. Використання SQLite в продакшене**

#### Проблема:
SQLite **НЕ підходить** для production з причин:
- Нема concurrency (блокує весь DB на write)
- Нема user permissions
- Нема backup automation
- Нема replication
- Нема network access control

#### Исправление:
```
Мигрировать на:
- PostgreSQL (рекомендуется) - безплатний, надежный
- MySQL 8.0+ - если нужна сумісність
- MariaDB 10.5+ - добра альтернатива MySQL

Шаги:
1. Экспортировать дані з SQLite
2. Создать схему в новой БД
3. Импортировать дані
4. Змінити Paskal.py для использования PSycopg2/pymysql
5. Тестировать
```

---

## 🟢 ЗАЩИЩЕННЫЕ ОБЛАСТИ

### **✅ SQL Injection защита**

Используются **параметризованные запросы** везде:
```python
# ✅ ПРАВИЛЬНО:
c.execute("SELECT * FROM memorials WHERE id=?", (mid,))

# ❌ НЕПРАВИЛЬНО (не используется):
c.execute(f"SELECT * FROM memorials WHERE id={mid}")
```

### **✅ Rate Limiting**

Есть `_RateLimiter` класс который ограничивает частоту запросов.

### **✅ Authorization**

`require_admin()` функция проверяет что юзер админ перед доступом к admin endpoints.

---

## 📋 ПЛАН ДЕЙСТВИЙ (Приоритет исправления)

### **НЕДЕЛЯ 1 (КРИТИЧЕСКИЕ):**
```
1. [2-3 часа] Добавить HTML escaping (XSS fix) 
   - Файл: Paskal.py
   - Endponts: /api/people, /api/search, /api/auth/register

2. [1-2 часа] Добавить CSRF токены
   - Файл: Paskal.py
   - Все POST/PUT/DELETE endpoints

3. [30 мин] Добавить error handler (приховати stack traces)
   - Файл: Paskal.py
   - Global exception handler
```

### **НЕДЕЛЯ 2 (ВЫСОКИЕ):**
```
4. [1-2 часа] Добавить валидацию email и паролей
   - Файл: Paskal.py
   - register endpoint

5. [1-2 часа] Добавить Pydantic validation для всех input моделей
   - Файл: Paskal.py
   - Все model классы

6. [2-3 дня] Мигрировать с SQLite на PostgreSQL/MySQL
   - Требует больше часов на testing
```

### **НЕДЕЛЯ 3+ (ВЫСОКИЕ):**
```
7. [4-8 часов] Добавити HTTPS (TLS/SSL сертификат)
8. [2-3 часа] Настроить WAF (Web Application Firewall)
9. [2-3 часа] Добавити logging для всех security событий
10. [1-2 часа] Регулярна dependency audit (pip-audit)
```

---

## 🛠️ ИНСТРУМЕНТЫ ДЛЯ ТЕСТИРОВАНИЯ

```bash
# 1. OWASP ZAP - автоматическое сканирование
zaproxy --url http://localhost:8000 --report security-report.html

# 2. Burp Suite Community - manuel тестирование
# (Не безплатно для всех функций)

# 3. SQLMap - перевірка SQL injection
sqlmap -u "http://localhost:8000/api/search?q=*" --dbs

# 4. Security headers check
curl -I http://localhost:8000 | grep -i "security\|content"

# 5. Dependency audit
pip install pip-audit
pip-audit

# 6. Manual XSS test
curl -X POST http://localhost:8000/api/people \
  -H "Content-Type: application/json" \
  -d '{
    "last": "<script>alert(1)</script>",
    "first": "Test",
    "descr": "<img src=x onerror=alert(1)>"
  }'
```

---

## 📊 ЧЕКЛИСТ ИСПРАВЛЕНИЙ

### XSS Fixes:
- [ ] Добавлена функция `_escape_for_json()`
- [ ] `/api/people` escapeит текстовые поля
- [ ] `/api/search` escapeит результаты
- [ ] `/api/auth/register` escapeит в response
- [ ] Тестировано з XSS payload
- [ ] card.html и admin.html все ещё работают

### CSRF Fixes:
- [ ] Добавлена функция `generate_csrf_token()`
- [ ] Добавлена функция `validate_csrf_token()`
- [ ] Добавлен endpoint `/api/csrf-token`
- [ ] ВСЕ POST/PUT/DELETE endpoints проверяют CSRF токен
- [ ] Frontend передает CSRF токен в requests

### Authentication Fixes:
- [ ] Добавлена валидация email (regex)
- [ ] Добавлена валидація паролей (сложность)
- [ ] Проверка на дублировані emails перед registro
- [ ] Все Pydantic модели мають constraints

### Error Handling:
- [ ] Добавлен глобальний error handler
- [ ] Stack traces не видны юзерам
- [ ] Admin видит полные error логи

---

## 📝 ВЫВОДЫ

**Статус проекта:** ⚠️ **ТРЕБУЕТ СРОЧНЫХ ИСПРАВЛЕНИЙ**

**Наиболее опасные уязвимости:**
1. 🔴 **XSS в descr полях** - Может привести к краже данных юзеров
2. 🔴 **CSRF атаки** - Могут привести к несанкционированным действиям
3. 🔴 **Слабая аутентификация** - Легко bruteforce пароли

**Рекомендации:**
- ✅ Выполнить все "КРИТИЧЕСКИЕ" исправления ДО production deploy
- ✅ Добавить регулярное security тестирование в CI/CD
- ✅ Обучить team members о OWASP Top 10
- ✅ Использовать security либ как requests-ratelimiter для дополнительной защиты

**Estimated time to fix (all issues):** ~2-3 недели

---

**Созданo:** Copilot Security Audit  
**Версия:** 1.0
