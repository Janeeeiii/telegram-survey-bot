from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import os
import sqlite3
from datetime import datetime

# Вопросы опроса (ваши вопросы без изменений)
QUESTIONS = [
    "Привет! Я помогаю создать новый бренд одежды. Давай познакомимся! 😊\n\nЯ — бот, который собирает идеи для идеального гардероба. Хочешь помочь?\n\nНажми «Да», чтобы начать опрос (займёт 5–7 минут).",
    "Отлично! Расскажи немного о себе — кто ты? Напиши свой ответ в виде короткого описания (например: «Модель, люблю активный стиль»).",
    "Что для тебя важнее всего в одежде? Напиши развёрнуто (3–5 предложений):\n- Важен ли комфорт и удобство?\n- Хочется ли подчеркнуть силуэт?\n- Какие ещё критерии для тебя ключевы при выборе одежды?",
    "Выбери несколько характеристик, которые для тебя важны (введи номера через пробел, например: 1 3 5):\n1) Невидимая посадка\n2) Подчёркивает силуэт\n3) Не мнётся\n4) Качественная ткань\n5) Незаметные швы\n6) Универсальный цвет",
    "С какими проблемами в «базовой» одежде ты сталкиваешься ЧАЩЕ ВСЕГО? (введи номера через пробел, например: 2 4 6)\n1) Виден бюстгальтер или его линии\n2) Жмёт в подмышках / плечах\n3) Тянется или скатывается после носки\n4) Ткань просвечивает\n5) Сидит мешковато, не подчёркивает фигуру\n6) Недолговечная (быстро теряет вид)\n7) Неудобные застёжки / бирки\n8) Другое (напиши свою проблему после номеров)",
    "Какие виды вещей тебе НАИБОЛЕЕ нужны в таком «идеальном» качестве?\n\nВведи для каждой вещи приоритет в формате:\nНомерВещи:Приоритет (1-критично, 2-желательно, 3-не важно)\n\nПример: \"1:2 3:1 5:2\"\n\nСписок вещей:\n1) Футболка/лонгслив\n2) Боди\n3) Топ без бретелек\n4) Топ на бретельках\n5) Классические брюки\n6) Брюки-слипоны",
    "О материалах. Что для тебя предпочтительнее? (введи номер):\n1) Натуральные ткани (хлопок, лён, вискоза)\n2) Современные смесовые материалы\n3) Не важно, главное — ощущение и внешний вид",
    "Твоя обязательная цветовая палитра. Выбери 3 основных цвета (введи номера через пробел, например: 1 3 5):\n1) Классический чёрный\n2) Белый / кремовый\n3) Тёплый беж / песочный\n4) Холодный серый\n5) Тёмно-синий / морской\n6) Шоколадный\n7) Другое (если выбрал 7, напиши цвета через запятую)",
    "Главный вопрос. Если бы ты могла описать ОЩУЩЕНИЕ от идеальной вещи для важного дня одним словом или короткой фразой, что бы это было?\n(Примеры: «вторая кожа», «тихая уверенность», «мой щит», «свобода движений», «безупречно»)",
    "Спасибо за участие! 🎉 Ваши ответы помогут создать коллекцию мечты. Следите за новостями в наших соцсетях:\n[ссылка на соцсети]"
]

# Инициализация базы данных
def init_database():
    """Создает базу данных для хранения ответов"""
    conn = sqlite3.connect('survey_responses.db')
    c = conn.cursor()
    
    # Создаем таблицу для ответов
    c.execute('''CREATE TABLE IF NOT EXISTS responses
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id TEXT,
                  username TEXT,
                  first_name TEXT,
                  last_name TEXT,
                  question_number INTEGER,
                  answer TEXT,
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    
    # Создаем таблицу для сессий
    c.execute('''CREATE TABLE IF NOT EXISTS user_sessions
                 (user_id TEXT PRIMARY KEY,
                  current_question INTEGER DEFAULT 0,
                  answers_json TEXT,
                  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    
    conn.commit()
    conn.close()
    print("✅ База данных инициализирована")

def save_response_to_db(user_id, username, first_name, last_name, question_num, answer):
    """Сохраняет ответ в базу данных"""
    try:
        conn = sqlite3.connect('survey_responses.db')
        c = conn.cursor()
        
        c.execute('''INSERT INTO responses 
                     (user_id, username, first_name, last_name, question_number, answer) 
                     VALUES (?, ?, ?, ?, ?, ?)''',
                  (str(user_id), username, first_name, last_name, question_num, answer))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Ошибка сохранения в БД: {e}")
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user_id = str(update.effective_user.id)
    
    # Начинаем новую сессию
    context.user_data['answers'] = []
    context.user_data['current_question'] = 0
    
    # Сохраняем в БД начало сессии
    try:
        conn = sqlite3.connect('survey_responses.db')
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO user_sessions 
                     (user_id, current_question, answers_json, updated_at)
                     VALUES (?, ?, ?, CURRENT_TIMESTAMP)''',
                  (user_id, 0, '[]'))
        conn.commit()
        conn.close()
    except:
        pass
    
    await update.message.reply_text(
        QUESTIONS[0],
        reply_markup=ReplyKeyboardMarkup(
            [['Да']],
            one_time_keyboard=True,
            resize_keyboard=True
        )
    )

async def handle_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ответов пользователя"""
    user_id = str(update.effective_user.id)
    username = update.effective_user.username or "нет"
    first_name = update.effective_user.first_name or "нет"
    last_name = update.effective_user.last_name or "нет"
    
    current_q = context.user_data.get('current_question', 0)
    
    # Сохраняем ответ в память
    if 'answers' not in context.user_data:
        context.user_data['answers'] = []
    context.user_data['answers'].append(update.message.text)
    
    # Сохраняем ответ в базу данных
    save_response_to_db(user_id, username, first_name, last_name, current_q + 1, update.message.text)
    
    # Обновляем сессию в БД
    try:
        conn = sqlite3.connect('survey_responses.db')
        c = conn.cursor()
        import json
        answers_json = json.dumps(context.user_data['answers'])
        c.execute('''UPDATE user_sessions 
                     SET current_question = ?, answers_json = ?, updated_at = CURRENT_TIMESTAMP
                     WHERE user_id = ?''',
                  (current_q + 1, answers_json, user_id))
        conn.commit()
        conn.close()
    except:
        pass
    
    # Если это был вопрос 0 (стартовый)
    if current_q == 0:
        context.user_data['current_question'] = 1
        await update.message.reply_text(QUESTIONS[1], reply_markup=ReplyKeyboardRemove())
        return
    
    # Переходим к следующему вопросу
    next_q = current_q + 1
    
    if next_q < len(QUESTIONS):
        context.user_data['current_question'] = next_q
        await update.message.reply_text(QUESTIONS[next_q], reply_markup=ReplyKeyboardRemove())
    else:
        # Завершение опроса
        await update.message.reply_text(QUESTIONS[-1], reply_markup=ReplyKeyboardRemove())
        
        # Выводим статистику
        print(f"\n{'='*60}")
        print(f"📊 ОПРОС ЗАВЕРШЕН")
        print(f"👤 Пользователь: {first_name} {last_name} (@{username})")
        print(f"🆔 ID: {user_id}")
        print(f"📝 Количество ответов: {len(context.user_data['answers'])}")
        print(f"{'='*60}")

def main():
    """Основная функция"""
    # Получаем токен из переменных окружения
    TOKEN = os.getenv('BOT_TOKEN', "8553356873:AAFVMlCRmmGbJA0t_iNM5z5ij_MLhCFsagY")
    
    if not TOKEN:
        print("❌ Ошибка: Не указан токен бота!")
        print("Добавьте BOT_TOKEN в переменные окружения")
        return
    
    # Инициализируем базу данных
    init_database()
    
    print("="*60)
    print("🤖 ТЕЛЕГРАМ БОТ ДЛЯ ОПРОСА")
    print("="*60)
    print(f"Токен: {TOKEN[:10]}...")
    print("📊 Ответы сохраняются в SQLite базу данных")
    print("⏳ Запускаю бота...")
    
    try:
        # Создаем приложение
        app = Application.builder().token(TOKEN).build()
        
        # Добавляем обработчики
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_response))
        
        print("✅ Бот успешно запущен!")
        print("="*60)
        print("📱 Теперь бот работает 24/7 на сервере")
        print("💾 Данные сохраняются в survey_responses.db")
        print("🛑 Для остановки нужно остановить сервер")
        print("="*60)
        
        # Запускаем бота
        app.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        print(f"❌ Ошибка запуска бота: {e}")
        print("\n🔧 Возможные решения:")
        print("1. Проверьте токен бота")
        print("2. Проверьте интернет-соединение сервера")
        print("3. Убедитесь, что Telegram не заблокирован")

if __name__ == '__main__':
    main()