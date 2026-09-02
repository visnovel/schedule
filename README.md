# 📅 Автономный iCalendar УрГПУ (uspu.ru) для GitHub

Этот репозиторий автоматически генерирует и обновляет файлы расписания в формате **iCalendar (.ics)** для подписки на **iPhone, Android, Mac и Google Календарь**.

---

## 🔗 Ваша вечная ссылка для iPhone

После загрузки репозитория на GitHub скопируйте нужную ссылку (замените `ВАШ_НИК` на ваш логин GitHub):

* **Только 1 подгруппа (+ лекции):**
  ```text
  https://raw.githubusercontent.com/ВАШ_НИК/uspu-schedule/main/ИТмт-207_sub1.ics
  ```

* **Только 2 подгруппа (+ лекции):**
  ```text
  https://raw.githubusercontent.com/ВАШ_НИК/uspu-schedule/main/ИТмт-207_sub2.ics
  ```

* **Все подгруппы:**
  ```text
  https://raw.githubusercontent.com/ВАШ_НИК/uspu-schedule/main/ИТмт-207_all.ics
  ```

---

## 📲 Как добавить на iPhone

1. Откройте на iPhone: **Настройки ➡️ Календарь ➡️ Учетные записи ➡️ Добавить ➡️ Другое ➡️ Подписной календарь**.
2. Вставьте скопированную ссылку выше.
3. Включите **«Автообновление»** (Каждый день / каждые 15 минут).
4. Вынесите стандартный виджет **«Календарь»** на рабочий стол или экран блокировки.

---

## 🚀 Как залить проект на GitHub

1. Создайте новый **публичный (Public)** репозиторий на [GitHub.com](https://github.com/new) с именем `uspu-schedule`.
2. В папке `C:\Users\qwe\uspu_github_calendar` выполните:
   ```bash
   git init
   git add .
   git commit -m "Initial schedule feed"
   git branch -M main
   git remote add origin https://github.com/ВАШ_НИК/uspu-schedule.git
   git push -u origin main
   ```
3. GitHub Actions (`.github/workflows/update.yml`) будет автоматически обновлять расписание по расписанию.
