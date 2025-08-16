
import telebot
from telebot import types
import asyncio
import time
import random
from datetime import datetime, timedelta
from subscription_manager import SubscriptionManager

# استيراد الدوال والكلاسات اللازمة من كل سكريبت
from bot5 import CardChecker as AWSBlackbaudChecker, get_banner_text_bot5, get_status_message_bot5, parse_card_data_bot5, analyze_response_for_telegram_bot5, GATE_NAME as GATE_NAME_BOT5
from bot15d import BasecampCardChecker, get_banner_text_bot15d, get_status_message_bot15d, parse_card_data_bot15d, analyze_response_for_telegram_bot15d, GATE_NAME as GATE_NAME_BOT15D
from botlive import create_stripe_token, process_payment, analyze_response_for_telegram_botlive, get_banner_text_botlive, get_status_message_botlive, parse_card_data_botlive, GATE_NAME as GATE_NAME_BOTLIVE
from bot3d import CardChecker as ITSConnectChecker, get_banner_text_bot3d, get_status_message_bot3d, parse_card_data_bot3d, analyze_response_for_telegram_bot3d, GATE_NAME as GATE_NAME_BOT3D

# --- إعدادات البوت الرئيسية ---
API_TOKEN = "7707283677:AAH8e7ra41HA-SVwkTzgupoR5h2oXAJYQ-o"
bot = telebot.TeleBot(API_TOKEN)
subscription_manager = SubscriptionManager("keys.json")

# قاموس لتتبع حالة كل مستخدم والسكريبت النشط لديه
user_states = {}

# قاموس لتخزين إحصائيات كل بوابة بشكل منفصل
global_bot_stats = {
    'bot5': {'total': 0, 'approved': 0, 'declined': 0, 'unknown': 0, 'errors': 0},
    'bot15d': {'total': 0, 'approved': 0, 'declined': 0, 'unknown': 0, 'errors': 0},
    'botlive': {'total': 0, 'approved': 0, 'declined': 0, 'unknown': 0, 'errors': 0},
    'bot3d': {'total': 0, 'approved': 0, 'declined': 0, 'unknown': 0, 'errors': 0}
}

# قاموس لربط اسم السكريبت بالدوال والأسماء الخاصة به
script_configs = {
    'bot5': {
        'checker_class': AWSBlackbaudChecker,
        'banner_text_func': get_banner_text_bot5,
        'status_message_func': get_status_message_bot5,
        'parse_card_func': parse_card_data_bot5,
        'analyze_response_func': analyze_response_for_telegram_bot5,
        'gate_name': GATE_NAME_BOT5
    },
    'bot15d': {
        'checker_class': BasecampCardChecker,
        'banner_text_func': get_banner_text_bot15d,
        'status_message_func': get_status_message_bot15d,
        'parse_card_func': parse_card_data_bot15d,
        'analyze_response_func': analyze_response_for_telegram_bot15d,
        'gate_name': GATE_NAME_BOT15D
    },
    'botlive': {
        'checker_class': None,
        'banner_text_func': get_banner_text_botlive,
        'status_message_func': get_status_message_botlive,
        'parse_card_func': parse_card_data_botlive,
        'analyze_response_func': analyze_response_for_telegram_botlive,
        'gate_name': GATE_NAME_BOTLIVE
    },
    'bot3d': {
        'checker_class': ITSConnectChecker,
        'banner_text_func': get_banner_text_bot3d,
        'status_message_func': get_status_message_bot3d,
        'parse_card_func': parse_card_data_bot3d,
        'analyze_response_func': analyze_response_for_telegram_bot3d,
        'gate_name': GATE_NAME_BOT3D
    }
}

# --- دوال مساعدة للاشتراكات ---
def init_user_state(chat_id):
    """تهيئة حالة المستخدم الأولية"""
    user_states[chat_id] = {
        'current_script': None,
        'combo_cards': [],
        'checking_active': False,
        'stats_message_id': None,
        'stop_checking': False,
        'current_checker_instance': None,
        'current_card_index': 0
    }

def check_user_subscription(chat_id):
    """التحقق من اشتراك المستخدم عبر الملف المشترك"""
    is_subscribed, sub_data = subscription_manager.check_user_subscription(chat_id)
    return is_subscribed, sub_data

def require_subscription(func):
    """ديكوريتر للتحقق من الاشتراك قبل تنفيذ الدالة"""
    def wrapper(message):
        chat_id = message.chat.id
        is_subscribed, sub_data = check_user_subscription(chat_id)
        
        if not is_subscribed:
            msg = sub_data.get('message', 'لا يوجد اشتراك نشط')
            bot.send_message(
                chat_id, 
                f"""🚫 **{msg}**

💎 **لتفعيل الاشتراك:**
انتقل إلى بوت الاشتراكات: @YourSubscriptionBotUsername

🔑 احصل على مفتاح اشتراك وفعله هناك
🤖 ثم عد هنا لاستخدام البوت

📞 **الدعم:** تواصل مع المطور""",
                parse_mode="Markdown",
                reply_markup=get_subscription_info_keyboard()
            )
            return
        
        return func(message)
    return wrapper

def get_subscription_info_keyboard():
    """لوحة مفاتيح معلومات الاشتراك"""
    markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    btn1 = types.KeyboardButton('📞 كيفية الحصول على اشتراك')
    btn2 = types.KeyboardButton('🔄 تحقق من الاشتراك')
    markup.add(btn1, btn2)
    return markup

# --- دوال الواجهة ---
def get_main_menu_keyboard():
    """إنشاء لوحة المفاتيح الرئيسية"""
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn1 = types.KeyboardButton('⚡ Charge 5$ (AWS Blackbaud)')
    btn2 = types.KeyboardButton('⚡ Charge 15$ (Basecamp)')
    btn3 = types.KeyboardButton('⚡ Live Auth 0$ (Stripe)')
    btn4 = types.KeyboardButton('⚡ 3D Look Up (ITS Connect)')
    btn5 = types.KeyboardButton('📊 إحصائياتي')
    btn6 = types.KeyboardButton('🔄 مسح الإحصائيات')
    markup.add(btn1, btn2, btn3, btn4, btn5, btn6)
    return markup

# --- معالجات الأوامر والرسائل ---
@bot.message_handler(commands=['start'])
@require_subscription
def start_command(message):
    chat_id = message.chat.id
    init_user_state(chat_id)
    bot.send_message(
        chat_id,
        "🏠 **مرحباً بك في بوت الفحص!**\n\nاختر بوابة من القائمة:",
        parse_mode="Markdown",
        reply_markup=get_main_menu_keyboard()
    )

# إضافة معالجات أخرى للأوامر والرسائل هنا (تم اقتطاع الجزء الأصلي للاختصار)
# يمكن إكمال الكود بناءً على متطلباتك

# --- تنظيف دوري للمفاتيح المنتهية ---
def cleanup_expired_keys_periodically():
    """تنظيف دوري للمفاتيح المنتهية الصلاحية"""
    import threading
    def cleanup():
        while True:
            try:
                cleaned = subscription_manager.cleanup_expired_keys()
                if cleaned > 0:
                    print(f"تم تنظيف {cleaned} مفتاح منتهي الصلاحية")
                time.sleep(3600)  # كل ساعة
            except Exception as e:
                print(f"خطأ في التنظيف الدوري: {e}")
                time.sleep(3600)
    
    cleanup_thread = threading.Thread(target=cleanup, daemon=True)
    cleanup_thread.start()

if __name__ == "__main__":
    print("🚀 Checker Bot is starting...")
    print(f"🤖 Bot Token: {API_TOKEN}")
    print("📦 تأكد من تثبيت المكتبات المطلوبة:")
    print("   pip install -r requirements.txt")
    
    try:
        bot.remove_webhook()
        print("✅ تم إيقاف webhook بنجاح")
    except Exception as e:
        print(f"⚠️ خطأ في إيقاف webhook: {e}")
    
    cleanup_expired_keys_periodically()
    
    while True:
        try:
            print("🔄 بدء polling...")
            bot.polling(none_stop=True, interval=0, timeout=20)
        except Exception as e:
            print(f"❌ خطأ في البوت: {e}")
            print("🔄 إعادة المحاولة خلال 5 ثوان...")
            time.sleep(5)
            try:
                bot.stop_polling()
            except:
                pass
