-- ============================================================
-- Модуль «Подарунки загиблому» (Gifts-for-fallen.md, етапи 3–9):
-- тексти сторінки card?slug= (секція gifts) + розділ адмінки (секція admin).
-- Без цієї міграції сторінка показує вбудовані українські тексти.
-- Виконати в PhpMyAdmin: база zoryana_pamyat -> SQL
-- ============================================================

INSERT INTO i18n_translations (lang, section, `key`, value) VALUES
('uk','gifts','gifts.button','Подарунки загиблому'),
('uk','gifts','gifts.title','Подарунки загиблому'),
('uk','gifts','gifts.subtitle','Оберіть подарунок — його буде покладено біля свічки памʼяті'),
('uk','gifts','gifts.loading','Завантаження…'),
('uk','gifts','gifts.empty','Каталог подарунків поки порожній'),
('uk','gifts','gifts.error_load','Не вдалося завантажити каталог. Спробуйте пізніше'),
('uk','gifts','gifts.place','Покласти подарунок'),
('uk','gifts','gifts.admin_note','Тестове розміщення адміністратором — без оплати'),
('uk','gifts','gifts.login_note','Щоб покласти подарунок, увійдіть через Google'),
('uk','gifts','gifts.login_btn','Увійти через Google'),
('uk','gifts','gifts.soon','Оплата подарунків незабаром запрацює. Дякуємо, що вшановуєте памʼять'),
('uk','gifts','gifts.placed','Подарунок покладено біля свічки'),
('uk','gifts','gifts.error_place','Не вдалося покласти подарунок. Спробуйте пізніше'),
('uk','gifts','gifts.back','← До каталогу'),
('uk','gifts','gifts.close','Закрити'),
('uk','gifts','gifts.more','ще {n}'),
('uk','admin','adm.card.gifts_module','Модуль «Подарунки загиблому»'),
('uk','admin','adm.card.gifts_module_desc','Кнопка й каталог подарунків біля свічки. Поки без оплати: класти подарунки може лише адміністратор')
ON DUPLICATE KEY UPDATE value = VALUES(value), section = VALUES(section);

INSERT INTO i18n_translations (lang, section, `key`, value) VALUES
('en','gifts','gifts.button','Gifts for the fallen'),
('en','gifts','gifts.title','Gifts for the fallen'),
('en','gifts','gifts.subtitle','Choose a gift — it will be placed by the memorial candle'),
('en','gifts','gifts.loading','Loading…'),
('en','gifts','gifts.empty','The gift catalog is empty for now'),
('en','gifts','gifts.error_load','Could not load the catalog. Please try again later'),
('en','gifts','gifts.place','Place the gift'),
('en','gifts','gifts.admin_note','Test placement by the administrator — no payment'),
('en','gifts','gifts.login_note','Sign in with Google to place a gift'),
('en','gifts','gifts.login_btn','Sign in with Google'),
('en','gifts','gifts.soon','Gift payments are coming soon. Thank you for honouring their memory'),
('en','gifts','gifts.placed','The gift has been placed by the candle'),
('en','gifts','gifts.error_place','Could not place the gift. Please try again later'),
('en','gifts','gifts.back','← Back to the catalog'),
('en','gifts','gifts.close','Close'),
('en','gifts','gifts.more','+{n} more'),
('en','admin','adm.card.gifts_module','“Gifts for the fallen” module'),
('en','admin','adm.card.gifts_module_desc','Gift button and catalog by the candle. No payment yet: only the administrator can place gifts')
ON DUPLICATE KEY UPDATE value = VALUES(value), section = VALUES(section);

-- Розділ адмінки «Подарунки загиблому» (етап 4)
INSERT INTO i18n_translations (lang, section, `key`, value) VALUES
('uk','admin','nav.gifts','Подарунки загиблому'),
('uk','admin','adm.gifts.tab_catalog','Каталог'),
('uk','admin','adm.gifts.tab_categories','Категорії'),
('uk','admin','adm.gifts.tab_placements','Замовлення'),
('uk','admin','adm.gifts.tab_settings','Налаштування'),
('uk','admin','adm.gifts.add_gift','Додати подарунок'),
('uk','admin','adm.gifts.add_category','Додати категорію'),
('uk','admin','adm.gifts.show_inactive','Показувати вимкнені'),
('uk','admin','adm.gifts.col_name','Назва'),
('uk','admin','adm.gifts.col_category','Категорія'),
('uk','admin','adm.gifts.col_price','Ціна'),
('uk','admin','adm.gifts.col_placed','Розміщено'),
('uk','admin','adm.gifts.col_order','Порядок'),
('uk','admin','adm.gifts.col_active','Активний'),
('uk','admin','adm.gifts.col_code','Код'),
('uk','admin','adm.gifts.col_count','Подарунків'),
('uk','admin','adm.gifts.col_date','Дата'),
('uk','admin','adm.gifts.col_memorial','Меморіал'),
('uk','admin','adm.gifts.col_gift','Подарунок'),
('uk','admin','adm.gifts.col_user','Користувач'),
('uk','admin','adm.gifts.col_status','Статус'),
('uk','admin','adm.gifts.col_sum','Сума'),
('uk','admin','adm.gifts.pl_search','Меморіал, ID або email…')
ON DUPLICATE KEY UPDATE value = VALUES(value), section = VALUES(section);

INSERT INTO i18n_translations (lang, section, `key`, value) VALUES
('en','admin','nav.gifts','Gifts for the fallen'),
('en','admin','adm.gifts.tab_catalog','Catalog'),
('en','admin','adm.gifts.tab_categories','Categories'),
('en','admin','adm.gifts.tab_placements','Orders'),
('en','admin','adm.gifts.tab_settings','Settings'),
('en','admin','adm.gifts.add_gift','Add gift'),
('en','admin','adm.gifts.add_category','Add category'),
('en','admin','adm.gifts.show_inactive','Show disabled'),
('en','admin','adm.gifts.col_name','Name'),
('en','admin','adm.gifts.col_category','Category'),
('en','admin','adm.gifts.col_price','Price'),
('en','admin','adm.gifts.col_placed','Placed'),
('en','admin','adm.gifts.col_order','Order'),
('en','admin','adm.gifts.col_active','Active'),
('en','admin','adm.gifts.col_code','Code'),
('en','admin','adm.gifts.col_count','Gifts'),
('en','admin','adm.gifts.col_date','Date'),
('en','admin','adm.gifts.col_memorial','Memorial'),
('en','admin','adm.gifts.col_gift','Gift'),
('en','admin','adm.gifts.col_user','User'),
('en','admin','adm.gifts.col_status','Status'),
('en','admin','adm.gifts.col_sum','Amount'),
('en','admin','adm.gifts.pl_search','Memorial, ID or email…')
ON DUPLICATE KEY UPDATE value = VALUES(value), section = VALUES(section);

-- Купівля подарунка (етап 5)
INSERT INTO i18n_translations (lang, section, `key`, value) VALUES
('uk','gifts','gifts.buy','Купити за {price}'),
('uk','gifts','gifts.confirm_text','Подарунок «{gift}» для меморіалу «{name}». Сума до сплати: {price}.'),
('uk','gifts','gifts.confirm_btn','Підтвердити покупку'),
('uk','gifts','gifts.confirm_back','Назад'),
('uk','gifts','gifts.order_created','Замовлення створено'),
('uk','gifts','gifts.order_no','Замовлення № {n}'),
('uk','gifts','gifts.order_note','Оплату через ПриватБанк буде підключено найближчим часом. Подарунок зʼявиться біля свічки одразу після оплати.'),
('uk','gifts','gifts.my_orders','Мої замовлення'),
('uk','gifts','gifts.no_orders','Для цього меморіалу у вас ще немає замовлень'),
('uk','gifts','gifts.cancel_order','Скасувати'),
('uk','gifts','gifts.cancel_confirm','Скасувати це замовлення?'),
('uk','gifts','gifts.error_order','Не вдалося створити замовлення. Спробуйте пізніше'),
('uk','gifts','gifts.buy_off','Купівля подарунків зараз недоступна'),
('uk','gifts','gifts.place_test','Покласти без оплати (тест)'),
('uk','gifts','gifts.status.created','Створено, очікує оплати'),
('uk','gifts','gifts.status.pending','Очікує підтвердження оплати'),
('uk','gifts','gifts.status.paid','Оплачено'),
('uk','gifts','gifts.status.cancelled','Скасовано'),
('uk','gifts','gifts.status.error','Помилка оплати'),
('uk','gifts','gifts.status.unknown','Статус уточнюється'),
('uk','admin','adm.gifts.buy_toggle','Купівля доступна'),
('uk','admin','adm.gifts.buy_toggle_desc','Авторизовані відвідувачі можуть оформити замовлення подарунка. Поки оплату не підключено, замовлення чекають оплати й біля свічки не зʼявляються')
ON DUPLICATE KEY UPDATE value = VALUES(value), section = VALUES(section);

INSERT INTO i18n_translations (lang, section, `key`, value) VALUES
('en','gifts','gifts.buy','Buy for {price}'),
('en','gifts','gifts.confirm_text','Gift “{gift}” for the memorial of {name}. Amount to pay: {price}.'),
('en','gifts','gifts.confirm_btn','Confirm purchase'),
('en','gifts','gifts.confirm_back','Back'),
('en','gifts','gifts.order_created','Order created'),
('en','gifts','gifts.order_no','Order No. {n}'),
('en','gifts','gifts.order_note','Payment via PrivatBank will be available soon. The gift will appear by the candle right after payment.'),
('en','gifts','gifts.my_orders','My orders'),
('en','gifts','gifts.no_orders','You have no orders for this memorial yet'),
('en','gifts','gifts.cancel_order','Cancel'),
('en','gifts','gifts.cancel_confirm','Cancel this order?'),
('en','gifts','gifts.error_order','Could not create the order. Please try again later'),
('en','gifts','gifts.buy_off','Gift purchases are unavailable right now'),
('en','gifts','gifts.place_test','Place without payment (test)'),
('en','gifts','gifts.status.created','Created, awaiting payment'),
('en','gifts','gifts.status.pending','Awaiting payment confirmation'),
('en','gifts','gifts.status.paid','Paid'),
('en','gifts','gifts.status.cancelled','Cancelled'),
('en','gifts','gifts.status.error','Payment error'),
('en','gifts','gifts.status.unknown','Status being verified'),
('en','admin','adm.gifts.buy_toggle','Purchases available'),
('en','admin','adm.gifts.buy_toggle_desc','Signed-in visitors can order a gift. Until payment is connected, orders wait for payment and do not appear by the candle')
ON DUPLICATE KEY UPDATE value = VALUES(value), section = VALUES(section);

-- Оплата через LiqPay (етап 6); оновлені описи перемикачів модуля й купівлі
INSERT INTO i18n_translations (lang, section, `key`, value) VALUES
('uk','gifts','gifts.confirm_pay','Перейти до оплати'),
('uk','gifts','gifts.pay_note','Оплата через LiqPay (ПриватБанк). Після оплати ви повернетеся на цю сторінку'),
('uk','gifts','gifts.redirecting','Переходимо до оплати…'),
('uk','gifts','gifts.pay_unavailable','Оплата тимчасово недоступна. Спробуйте пізніше'),
('uk','gifts','gifts.pay_btn','Оплатити'),
('uk','gifts','gifts.check_btn','Перевірити оплату'),
('uk','gifts','gifts.check_again','Перевірити ще раз'),
('uk','gifts','gifts.checking','Перевіряємо оплату…'),
('uk','gifts','gifts.check_failed','Не вдалося звʼязатися з банком. Спробуйте за хвилину'),
('uk','gifts','gifts.cancel_failed','Не вдалося скасувати замовлення'),
('uk','gifts','gifts.result_paid_title','Дякуємо!'),
('uk','gifts','gifts.result_paid','Подарунок «{gift}» покладено біля свічки'),
('uk','gifts','gifts.result_pending','Оплата ще обробляється. Подарунок зʼявиться біля свічки одразу після підтвердження'),
('uk','gifts','gifts.result_created','Оплату не завершено'),
('uk','gifts','gifts.result_error','Оплата не пройшла. Можна спробувати ще раз — оберіть подарунок у каталозі'),
('uk','gifts','gifts.result_cancelled','Замовлення скасовано'),
('uk','admin','adm.gifts.liqpay','Оплата LiqPay (ПриватБанк)'),
('uk','admin','adm.gifts.buy_toggle_desc','Авторизовані відвідувачі можуть купити подарунок і оплатити його через LiqPay. Працює лише коли в .env задано ключі LiqPay'),
('uk','admin','adm.card.gifts_module_desc','Кнопка й каталог подарунків біля свічки на сторінці меморіалу')
ON DUPLICATE KEY UPDATE value = VALUES(value), section = VALUES(section);

INSERT INTO i18n_translations (lang, section, `key`, value) VALUES
('en','gifts','gifts.confirm_pay','Proceed to payment'),
('en','gifts','gifts.pay_note','Payment via LiqPay (PrivatBank). After paying you will return to this page'),
('en','gifts','gifts.redirecting','Redirecting to payment…'),
('en','gifts','gifts.pay_unavailable','Payment is temporarily unavailable. Please try again later'),
('en','gifts','gifts.pay_btn','Pay'),
('en','gifts','gifts.check_btn','Check payment'),
('en','gifts','gifts.check_again','Check again'),
('en','gifts','gifts.checking','Checking the payment…'),
('en','gifts','gifts.check_failed','Could not reach the bank. Please try again in a minute'),
('en','gifts','gifts.cancel_failed','Could not cancel the order'),
('en','gifts','gifts.result_paid_title','Thank you!'),
('en','gifts','gifts.result_paid','The gift “{gift}” has been laid by the candle'),
('en','gifts','gifts.result_pending','The payment is still being processed. The gift will appear by the candle as soon as it is confirmed'),
('en','gifts','gifts.result_created','The payment was not completed'),
('en','gifts','gifts.result_error','The payment did not go through. You can try again — choose the gift in the catalog'),
('en','gifts','gifts.result_cancelled','The order has been cancelled'),
('en','admin','adm.gifts.liqpay','LiqPay payments (PrivatBank)'),
('en','admin','adm.gifts.buy_toggle_desc','Signed-in visitors can buy a gift and pay for it via LiqPay. Works only when LiqPay keys are set in .env'),
('en','admin','adm.card.gifts_module_desc','The gifts button and catalog by the candle on the memorial page')
ON DUPLICATE KEY UPDATE value = VALUES(value), section = VALUES(section);

-- Кілька подарунків (етап 8): список усіх подарунків біля свічки («ще N»)
INSERT INTO i18n_translations (lang, section, `key`, value) VALUES
('uk','gifts','gifts.all_title','Подарунки біля свічки')
ON DUPLICATE KEY UPDATE value = VALUES(value), section = VALUES(section);

INSERT INTO i18n_translations (lang, section, `key`, value) VALUES
('en','gifts','gifts.all_title','Gifts by the candle')
ON DUPLICATE KEY UPDATE value = VALUES(value), section = VALUES(section);

-- Налаштування модуля (етап 9)
INSERT INTO i18n_translations (lang, section, `key`, value) VALUES
('uk','admin','adm.gifts.button_toggle','Кнопка «Подарунки загиблому» й каталог'),
('uk','admin','adm.gifts.button_toggle_desc','Вимкнено — нового подарунка не обрати (і не купити), але вже покладені подарунки лишаються біля свічки'),
('uk','admin','adm.gifts.anim_toggle','Анімація покладання (GIF)'),
('uk','admin','adm.gifts.anim_toggle_desc','Покупець один раз бачить, як руки кладуть подарунок біля свічки. Вимкнено — одразу статичний подарунок'),
('uk','admin','adm.gifts.anim_scale','Розмір GIF відносно подарунка'),
('uk','admin','adm.gifts.anim_scale_desc','У скільки разів GIF ширший за подарунок біля свічки (1.5–5). Стандарт 2.8 — коли подарунок наприкінці займає ≈⅓ ширини кадру'),
('uk','admin','adm.gifts.size','Розмір подарунків біля свічки, %'),
('uk','admin','adm.gifts.size_desc','70–140%. На вузьких екранах подарунки ще й зменшуються самі, щоб уміститись'),
('uk','admin','adm.gifts.notify','Лист про оплачений подарунок'),
('uk','admin','adm.gifts.texts','Тексти модуля'),
('uk','admin','adm.gifts.texts_desc','Кнопки, повідомлення й підписи сторінки меморіалу (українською й англійською) — у розділі «Локалізація», секція gifts'),
('uk','admin','adm.gifts.texts_btn','Редагувати')
ON DUPLICATE KEY UPDATE value = VALUES(value), section = VALUES(section);

INSERT INTO i18n_translations (lang, section, `key`, value) VALUES
('en','admin','adm.gifts.button_toggle','The “Gifts for the fallen” button and catalog'),
('en','admin','adm.gifts.button_toggle_desc','Off — no new gift can be chosen (or bought), but gifts already laid stay by the candle'),
('en','admin','adm.gifts.anim_toggle','Laying animation (GIF)'),
('en','admin','adm.gifts.anim_toggle_desc','The buyer sees once how hands lay the gift by the candle. Off — the static gift right away'),
('en','admin','adm.gifts.anim_scale','GIF size relative to the gift'),
('en','admin','adm.gifts.anim_scale_desc','How many times wider the GIF is than the gift by the candle (1.5–5). The default 2.8 fits a gift that ends up taking ≈⅓ of the frame width'),
('en','admin','adm.gifts.size','Size of gifts by the candle, %'),
('en','admin','adm.gifts.size_desc','70–140%. On narrow screens gifts also shrink automatically to fit'),
('en','admin','adm.gifts.notify','Email about a paid gift'),
('en','admin','adm.gifts.texts','Module texts'),
('en','admin','adm.gifts.texts_desc','Buttons, messages and labels of the memorial page (Ukrainian and English) — in the “Localization” section, gifts'),
('en','admin','adm.gifts.texts_btn','Edit')
ON DUPLICATE KEY UPDATE value = VALUES(value), section = VALUES(section);
