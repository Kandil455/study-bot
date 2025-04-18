import logging
import json # <-- لاستخدام ملفات JSON
import os   # <-- للتعامل مع مسار الملف

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from telegram.constants import ChatType, ParseMode # <-- استيراد ParseMode

# --- إعدادات أساسية ---
BOT_TOKEN = "7959190815:AAGFP2w4MaHiXduNvE67cLheb-7qFzLwfaE" # <-- التوكن بتاعك
ADMIN_USER_IDS = {5923929978} # <-- الـ Admin ID بتاعك (ممكن تضيف أكتر)

# --- إعدادات ملف المستخدمين الموافق عليهم ---
APPROVED_USERS_FILE = "approved_users.json"
# استخدام set لسهولة الإضافة والتحقق (in)
approved_user_ids = set()

# إعداد تسجيل الأخطاء
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# --- دوال تحميل وحفظ المستخدمين الموافق عليهم ---
def load_approved_users():
    """تحميل قائمة المستخدمين الموافق عليهم من ملف JSON."""
    global approved_user_ids
    try:
        # التأكد من أن المسار صحيح ويعمل على أنظمة مختلفة
        script_dir = os.path.dirname(__file__) # مسار المجلد الحالي للسكربت
        file_path = os.path.join(script_dir, APPROVED_USERS_FILE)
        logger.info(f"Attempting to load approved users from: {file_path}")
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                user_ids_list = json.load(f)
                approved_user_ids = set(user_ids_list) # تحويل القائمة إلى set
                logger.info(f"Loaded {len(approved_user_ids)} approved user IDs.")
        else:
            logger.warning(f"{APPROVED_USERS_FILE} not found. Starting with an empty set.")
            approved_user_ids = set() # البدء بـ set فارغ إذا لم يوجد الملف
            # إضافة الأدمنز تلقائيًا للقائمة عند عدم وجود الملف
            approved_user_ids.update(ADMIN_USER_IDS)
            save_approved_users() # حفظ الملف الجديد بالأدمنز
            logger.info("Admin users automatically added to the new approved list.")

    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Error loading {APPROVED_USERS_FILE}: {e}. Starting with an empty set.", exc_info=True)
        approved_user_ids = set()
        # محاولة إضافة الأدمنز حتى لو فشل التحميل
        approved_user_ids.update(ADMIN_USER_IDS)
        save_approved_users()

def save_approved_users():
    """حفظ القائمة الحالية للمستخدمين الموافق عليهم في ملف JSON."""
    global approved_user_ids
    try:
        script_dir = os.path.dirname(__file__)
        file_path = os.path.join(script_dir, APPROVED_USERS_FILE)
        logger.info(f"Saving approved users to: {file_path}")
        with open(file_path, 'w') as f:
            # تحويل الـ set إلى list قبل الحفظ في JSON
            json.dump(list(approved_user_ids), f, indent=4)
        logger.info(f"Successfully saved {len(approved_user_ids)} approved user IDs.")
    except IOError as e:
        logger.error(f"Error saving {APPROVED_USERS_FILE}: {e}", exc_info=True)

# --- هيكل البيانات ---
content_map = {
    # --- المواد البسيطة (مستوى واحد) ---
    "Anatomy": {
        "أسئلة محلولة": "BQACAgQAAxkBAAMaaAI42tBWGzn8b-u1yieO_k4_R80AAmoeAAKj7hFQ9Eaa4kxGUt82BA",
        "أسئلة غير محلولة": "BQACAgQAAxkBAAMYaAI4xsQYuoR35wqK41p896Vics0AAmkeAAKj7hFQPJuhR81aNB02BA"
    },
    "Histo": {"أسئلة": "PLACEHOLDER_HISTO_QUESTIONS_ID"},
    "Micro": {
        "أسئلة محلولة": "BQACAgQAAxkBAAMgaAI_bRwnQjiZU69181CcwosoAdEAAnAeAAKj7hFQ6jnSp5xgl-82BA",
        "أسئلة غير محلولة": "BQACAgQAAxkBAAMeaAI_acE4MRsH48MRbA98hCg2fyoAAm8eAAKj7hFQgBcgV4cGDfM2BA"
    },
    "Commu": {"أسئلة": "BQACAgQAAxkBAAMOaAHqYfBUrFCIwZxgDqtGi_NTgR8AArEbAAI1_BFQCwVrUptMaAw2BA"},
    "Family": {"أسئلة": "BQACAgQAAxkBAAMiaAJAmHfkopxWulNSlt3ENhNcNF4AAnIeAAKj7hFQmVYpbggEVYg2BA"},
    # --- المواد المعقدة (مستوى المحاضرات) ---
    "Para": {
        "Lecture 1": {"شرح": "BQACAgQAAxkBAANMaAJT0Z1nAYkxgz2gNLFKGHWEA90AAsAeAAKj7hFQQ4RlMPaU35c2BA", "أسئلة": "BQACAgQAAxkBAANKaAJT0Rk6hV-ZgWIhY8dwB-zQM4gAAr0eAAKj7hFQPnCBjgVP2A42BA", "تلخيص": "BQACAgQAAxkBAANLaAJT0XuQwQg4AAGlzwbKUEygM0wNAAK-HgACo-4RUKd4pUPLnhaqNgQ"},
        "Lecture 2": {"شرح": "BQACAgQAAxkBAAMoaAJKZQVTj__Ube7coZpItZsRzNoAAoIeAAKj7hFQ9dctgB5nrok2BA", "أسئلة": "BQACAgQAAxkBAAMnaAJKZfxxVJObl2DwS11NJonhOz0AAoEeAAKj7hFQWNYKQs-EAsY2BA", "تلخيص": "BQACAgQAAxkBAAMraAJLwk5Az5pxWNn24S51upFBCzkAAoMeAAKj7hFQajeMm1IrNZ02BA"}
    },
    "Physio": {
        "Lecture 1": {"شرح": "PLACEHOLDER_PHYSIO_L1_LECTURE_ID", "أسئلة": "PLACEHOLDER_PHYSIO_L1_QUESTIONS_ID", "تلخيص": "PLACEHOLDER_PHYSIO_L1_SUMMARY_ID"},
        "Lecture 2": {"شرح": "PLACEHOLDER_PHYSIO_L2_LECTURE_ID", "أسئلة": "PLACEHOLDER_PHYSIO_L2_QUESTIONS_ID", "تلخيص": "PLACEHOLDER_PHYSIO_L2_SUMMARY_ID"},
        "Lecture 3": {"شرح": "PLACEHOLDER_PHYSIO_L3_LECTURE_ID", "أسئلة": "PLACEHOLDER_PHYSIO_L3_QUESTIONS_ID", "تلخيص": "PLACEHOLDER_PHYSIO_L3_SUMMARY_ID"},
        "Lecture 4": {"شرح": "PLACEHOLDER_PHYSIO_L4_LECTURE_ID", "أسئلة": "PLACEHOLDER_PHYSIO_L4_QUESTIONS_ID", "تلخيص": "PLACEHOLDER_PHYSIO_L4_SUMMARY_ID"},
        "Lecture 5": {"شرح": "PLACEHOLDER_PHYSIO_L5_LECTURE_ID", "أسئلة": "PLACEHOLDER_PHYSIO_L5_QUESTIONS_ID", "تلخيص": "PLACEHOLDER_PHYSIO_L5_SUMMARY_ID"},
    },
    "Bio": {
        "Lecture 1": {"شرح": "PLACEHOLDER_BIO_L1_LECTURE_ID", "أسئلة": "PLACEHOLDER_BIO_L1_QUESTIONS_ID", "تلخيص": "PLACEHOLDER_BIO_L1_SUMMARY_ID"},
        "Lecture 2": {"شرح": "PLACEHOLDER_BIO_L2_LECTURE_ID", "أسئلة": "PLACEHOLDER_BIO_L2_QUESTIONS_ID", "تلخيص": "PLACEHOLDER_BIO_L2_SUMMARY_ID"},
        "Lecture 3": {"شرح": "PLACEHOLDER_BIO_L3_LECTURE_ID", "أسئلة": "PLACEHOLDER_BIO_L3_QUESTIONS_ID", "تلخيص": "PLACEHOLDER_BIO_L3_SUMMARY_ID"},
        "Lecture 4": {"شرح": "PLACEHOLDER_BIO_L4_LECTURE_ID", "أسئلة": "PLACEHOLDER_BIO_L4_QUESTIONS_ID", "تلخيص": "PLACEHOLDER_BIO_L4_SUMMARY_ID"},
        "Lecture 5": {"شرح": "PLACEHOLDER_BIO_L5_LECTURE_ID", "أسئلة": "PLACEHOLDER_BIO_L5_QUESTIONS_ID", "تلخيص": "PLACEHOLDER_BIO_L5_SUMMARY_ID"},
        "Lecture 6": {"شرح": "PLACEHOLDER_BIO_L6_LECTURE_ID", "أسئلة": "PLACEHOLDER_BIO_L6_QUESTIONS_ID", "تلخيص": "PLACEHOLDER_BIO_L6_SUMMARY_ID"},
    },
    "Pharma": {
        "Lecture 1": {"شرح": "PLACEHOLDER_PHARMA_L1_LECTURE_ID", "أسئلة": "PLACEHOLDER_PHARMA_L1_QUESTIONS_ID", "تلخيص": "PLACEHOLDER_PHARMA_L1_SUMMARY_ID"},
        "Lecture 2": {"شرح": "PLACEHOLDER_PHARMA_L2_LECTURE_ID", "أسئلة": "PLACEHOLDER_PHARMA_L2_QUESTIONS_ID", "تلخيص": "PLACEHOLDER_PHARMA_L2_SUMMARY_ID"},
        "Lecture 3": {"شرح": "PLACEHOLDER_PHARMA_L3_LECTURE_ID", "أسئلة": "PLACEHOLDER_PHARMA_L3_QUESTIONS_ID", "تلخيص": "PLACEHOLDER_PHARMA_L3_SUMMARY_ID"},
    },
    "Patho": {
        "Lecture 1": {"شرح": "PLACEHOLDER_PATHO_L1_LECTURE_ID", "أسئلة": "PLACEHOLDER_PATHO_L1_QUESTIONS_ID", "تلخيص": "PLACEHOLDER_PATHO_L1_SUMMARY_ID"},
        "Lecture 2": {"شرح": "PLACEHOLDER_PATHO_L2_LECTURE_ID", "أسئلة": "PLACEHOLDER_PATHO_L2_QUESTIONS_ID", "تلخيص": "PLACEHOLDER_PATHO_L2_SUMMARY_ID"},
        "Lecture 3": {"شرح": "PLACEHOLDER_PATHO_L3_LECTURE_ID", "أسئلة": "PLACEHOLDER_PATHO_L3_QUESTIONS_ID", "تلخيص": "PLACEHOLDER_PATHO_L3_SUMMARY_ID"},
        "Lecture 4": {"شرح": "PLACEHOLDER_PATHO_L4_LECTURE_ID", "أسئلة": "PLACEHOLDER_PATHO_L4_QUESTIONS_ID", "تلخيص": "PLACEHOLDER_PATHO_L4_SUMMARY_ID"},
        "Lecture 5": {"شرح": "PLACEHOLDER_PATHO_L5_LECTURE_ID", "أسئلة": "PLACEHOLDER_PATHO_L5_QUESTIONS_ID", "تلخيص": "PLACEHOLDER_PATHO_L5_SUMMARY_ID"},
    }
}
content_types_order = ["شرح", "أسئلة محلولة", "أسئلة غير محلولة", "أسئلة", "تلخيص"]

# --- دالة إرسال طلب الموافقة للأدمن ---
async def send_approval_request_to_admins(user_to_approve: Update.effective_user, context: ContextTypes.DEFAULT_TYPE):
    """إرسال رسالة للأدمنز لطلب الموافقة على مستخدم جديد."""
    if not user_to_approve: return

    user_id = user_to_approve.id
    first_name = user_to_approve.first_name
    last_name = user_to_approve.last_name or ""
    username = f"@{user_to_approve.username}" if user_to_approve.username else "لا يوجد"
    mention = user_to_approve.mention_html()

    text = (
        f"⚠️ **طلب دخول جديد** ⚠️\n\n"
        f"المستخدم: {mention} ({first_name} {last_name})\n"
        f"اسم المستخدم: {username}\n"
        f"ID: `{user_id}`\n\n"
        f"هل توافق على دخوله للبوت؟"
    )
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ موافقة", callback_data=f"admin_approve_{user_id}"),
            InlineKeyboardButton("❌ رفض", callback_data=f"admin_reject_{user_id}")
        ]
    ])

    # إرسال الرسالة لكل أدمن
    for admin_id in ADMIN_USER_IDS:
        try:
            await context.bot.send_message(chat_id=admin_id, text=text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
            logger.info(f"Sent approval request for user {user_id} to admin {admin_id}")
        except Exception as e:
            logger.error(f"Failed to send approval request to admin {admin_id} for user {user_id}: {e}")

# --- دالة البدء /start (مع التحقق من الموافقة) ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ترسل رسالة ترحيبية وتعرض أزرار المواد أو تطلب الموافقة."""
    if not update.message or not update.effective_user:
        logger.warning("Start command received without message or user.")
        return

    user = update.effective_user
    user_id = user.id

    # --- التحقق من الموافقة ---
    if user_id not in approved_user_ids:
        logger.info(f"User {user.first_name} ({user_id}) - NOT APPROVED - tried to start.")
        await update.message.reply_text(
            "أهلاً بك! 👋\n"
            "هذا البوت يتطلب موافقة الأدمن للوصول إلى المحتوى.\n"
            "تم إرسال طلبك للموافقة. سيتم إعلامك عند قبوله.\n\n"
            "برجاء الانتظار... ⏳"
        )
        # إرسال طلب الموافقة للأدمن
        await send_approval_request_to_admins(user, context)
        return # إيقاف الدالة هنا للمستخدم غير الموافق عليه
    # --- نهاية التحقق ---

    # إذا وصل الكود لهنا، فالمستخدم موافق عليه
    logger.info(f"Approved user {user.first_name} ({user.id}) started the bot.")
    keyboard = []
    row = []
    subjects = list(content_map.keys())
    for i, subject in enumerate(subjects):
        row.append(InlineKeyboardButton(subject, callback_data=f"subject_{subject}"))
        if len(row) == 2 or i == len(subjects) - 1:
             keyboard.append(row)
             row = []
    reply_markup = InlineKeyboardMarkup(keyboard)
    try:
        await update.message.reply_text(
            f'أهلاً بك يا {user.mention_html()}!\nاختر المادة الدراسية:',
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.error(f"Failed to send start message to approved user {user.id}: {e}")


# --- دالة button_click (مع التحقق من الموافقة ومعالجة قرارات الأدمن) ---
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """تعالج ضغطات الأزرار للمواد/المحاضرات/الأنواع وقرارات الأدمن."""
    query = update.callback_query
    if not query or not update.effective_user or not update.effective_chat:
        logger.warning("Button click update received without query, user, or chat.")
        if query:
            try: await query.answer("حدث خطأ بسيط، حاول مرة أخرى.")
            except Exception: pass
        return

    user = update.effective_user
    user_id = user.id
    chat_id = update.effective_chat.id
    user_info = user.username or user.first_name
    callback_data = query.data

    # --- التحقق من الموافقة (إلا إذا كان الإجراء خاص بالأدمن) ---
    # لا نتحقق إذا كان callback_data يبدأ بـ "admin_" لأن هذه ضغطات الأدمن
    if not callback_data.startswith("admin_"):
        if user_id not in approved_user_ids:
            logger.warning(f"User {user_info} ({user_id}) - NOT APPROVED - clicked a button: {callback_data}")
            try:
                # نرد على الـ query عشان الزرار ميفضلش معلق
                await query.answer("أنت بحاجة لموافقة الأدمن أولاً لاستخدام البوت.", show_alert=True)
            except Exception as e:
                logger.error(f"Failed to answer query for unapproved user {user_id}: {e}")
            # ممكن نبعتله رسالة تذكير كمان
            try:
                await context.bot.send_message(chat_id=chat_id, text="لم تتم الموافقة على طلبك بعد. يرجى الانتظار.")
            except Exception as e:
                logger.error(f"Failed to send reminder message to unapproved user {user_id}: {e}")
            return # إيقاف المعالجة للمستخدم غير الموافق عليه
    # --- نهاية التحقق ---

    # محاولة الرد على الـ query مبكرًا إذا لم يكن خاصًا بالأدمن
    if not callback_data.startswith("admin_"):
        try:
            await query.answer()
        except Exception as answer_err:
            logger.warning(f"Could not answer callback query '{callback_data}': {answer_err}")


    logger.info(f"Processing callback query '{callback_data}' from user {user_info} ({user_id}) in chat {chat_id}.")

    try:
        parts = callback_data.split("_", 3)
        action = parts[0] if parts else None

        # =================================================
        # == القسم الخاص بمعالجة قرارات الأدمن ==
        # =================================================
        if action == "admin" and len(parts) == 3:
            # --- التحقق أن من قام بالضغط هو أدمن ---
            if user_id not in ADMIN_USER_IDS:
                logger.warning(f"Non-admin user {user_id} tried to perform admin action: {callback_data}")
                await query.answer("هذه الأزرار خاصة بالأدمن فقط!", show_alert=True)
                return
            # --- نهاية التحقق ---

            admin_action = parts[1] # approve or reject
            try:
                 user_id_to_process = int(parts[2])
            except ValueError:
                 logger.error(f"Invalid user ID in admin callback data: {callback_data}")
                 await query.answer("خطأ في بيانات المستخدم المطلوب معالجته.")
                 return

            if admin_action == "approve":
                logger.info(f"Admin {user_id} trying to approve user {user_id_to_process}")
                if user_id_to_process not in approved_user_ids:
                    approved_user_ids.add(user_id_to_process)
                    save_approved_users() # *** حفظ التغيير فورًا ***
                    logger.info(f"User {user_id_to_process} approved by admin {user_id}. List saved.")
                    try:
                        await query.edit_message_text(f"✅ تم الموافقة على المستخدم `{user_id_to_process}` بنجاح.", parse_mode=ParseMode.MARKDOWN_V2)
                    except Exception as e:
                        logger.error(f"Failed to edit admin message after approval: {e}")
                        await query.answer("تمت الموافقة.") # رد بسيط
                    # إبلاغ المستخدم بأنه تمت الموافقة عليه
                    try:
                        await context.bot.send_message(
                            chat_id=user_id_to_process,
                            text="🎉 تمت الموافقة على طلبك! 🎉\nيمكنك الآن استخدام البوت بحرية.\nابدأ باستخدام /start"
                        )
                    except Exception as e:
                        logger.error(f"Failed to notify user {user_id_to_process} about approval: {e}")
                else:
                    logger.info(f"User {user_id_to_process} is already approved (Admin: {user_id}).")
                    try:
                        await query.edit_message_text(f"ℹ️ المستخدم `{user_id_to_process}` موافق عليه بالفعل.", parse_mode=ParseMode.MARKDOWN_V2)
                    except Exception as e:
                        logger.error(f"Failed to edit admin message for already approved user: {e}")
                        await query.answer("المستخدم موافق عليه بالفعل.")

            elif admin_action == "reject":
                logger.info(f"Admin {user_id} rejected user {user_id_to_process}")
                # لا نحتاج لإضافته لقائمة المرفوضين حاليًا، فقط لا نضيفه للموافق عليهم
                # إذا كان موجودًا بالخطأ في قائمة الموافقين، نزيله (احتياطي)
                if user_id_to_process in approved_user_ids:
                    approved_user_ids.discard(user_id_to_process)
                    save_approved_users()
                    logger.warning(f"User {user_id_to_process} was mistakenly in approved list and has been removed after rejection by admin {user_id}.")

                try:
                    await query.edit_message_text(f"❌ تم رفض طلب المستخدم `{user_id_to_process}`.", parse_mode=ParseMode.MARKDOWN_V2)
                except Exception as e:
                    logger.error(f"Failed to edit admin message after rejection: {e}")
                    await query.answer("تم الرفض.")
                # إبلاغ المستخدم بأنه تم رفضه (اختياري)
                try:
                    await context.bot.send_message(
                        chat_id=user_id_to_process,
                        text="للأسف، لم تتم الموافقة على طلبك للوصول للبوت حاليًا."
                    )
                except Exception as e:
                    logger.error(f"Failed to notify user {user_id_to_process} about rejection: {e}")
            else:
                logger.warning(f"Unknown admin action: {admin_action} in callback {callback_data}")
                await query.answer("إجراء غير معروف.")

            return # *** إنهاء المعالجة بعد إجراء الأدمن ***

        # =================================================
        # == القسم الخاص بتصفح المحتوى للمستخدم الموافق عليه ==
        # =================================================

        # (نفس الكود السابق لـ subject, lecture, content, back actions)
        # ... (الكود من ردودي السابقة يبدأ من هنا) ...

        # -----------------------------------------------------
        # Action 1: User selected a subject (subject_SubjectName)
        # -----------------------------------------------------
        if action == "subject" and len(parts) == 2:
            subject = parts[1]
            logger.info(f"Approved user {user_id} selected subject: {subject}")

            if subject not in content_map:
                logger.warning(f"Subject '{subject}' not found in content_map (User: {user_id}).")
                await query.edit_message_text(text="عذراً، المادة غير موجودة.")
                return
            subject_content = content_map[subject]
            if not subject_content:
                 await query.edit_message_text(text=f"لا يوجد محتوى متاح لمادة {subject} حالياً.")
                 return
            keyboard = []
            row = []
            first_level_keys = list(subject_content.keys())
            if not first_level_keys:
                await query.edit_message_text(text=f"لا يوجد محتوى متاح لمادة {subject} حالياً.")
                return
            is_complex_subject = isinstance(subject_content.get(first_level_keys[0]), dict)

            if is_complex_subject:
                # Complex Subject: Show Lecture Buttons
                text = f"اختر المحاضرة المطلوبة لمادة {subject}:"
                try:
                    lecture_keys = sorted(first_level_keys, key=lambda x: int(''.join(filter(str.isdigit, x))) if any(char.isdigit() for char in x) else float('inf'))
                except ValueError:
                     lecture_keys = sorted(first_level_keys)
                for lecture_name in lecture_keys:
                    button_data = f"lecture_{subject}_{lecture_name}"
                    row.append(InlineKeyboardButton(lecture_name, callback_data=button_data))
                    if len(row) == 1:
                         keyboard.append(row); row = []
                if row: keyboard.append(row)
                keyboard.append([InlineKeyboardButton("⬅️ العودة للمواد", callback_data="back_to_subjects")])
            else:
                # Simple Subject: Show Content Type Buttons
                text = f"اختر نوع المحتوى المطلوب لمادة {subject}:"
                available_types = first_level_keys
                sorted_types = [t for t in content_types_order if t in available_types]
                other_types = [t for t in available_types if t not in content_types_order]
                display_types = sorted_types + other_types
                for content_type in display_types:
                    button_data = f"content_{subject}_{content_type}"
                    row.append(InlineKeyboardButton(content_type, callback_data=button_data))
                    if len(row) == 1:
                         keyboard.append(row); row = []
                if row: keyboard.append(row)
                keyboard.append([InlineKeyboardButton("⬅️ العودة للمواد", callback_data="back_to_subjects")])

            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text=text, reply_markup=reply_markup)

        # -----------------------------------------------------------
        # Action 2: User selected a lecture (lecture_Subject_LectureName)
        # -----------------------------------------------------------
        elif action == "lecture" and len(parts) == 3:
            subject = parts[1]
            lecture = parts[2]
            logger.info(f"Approved user {user_id} selected lecture: {lecture} for subject {subject}")

            if subject not in content_map or lecture not in content_map.get(subject, {}):
                logger.warning(f"Lecture '{lecture}' or Subject '{subject}' not found (User: {user_id}).")
                await query.edit_message_text(text="عذراً، المحاضرة أو المادة غير موجودة.")
                return
            lecture_content = content_map[subject][lecture]
            if not lecture_content or not isinstance(lecture_content, dict):
                logger.error(f"Content for lecture '{lecture}' in subject '{subject}' is missing or not a dictionary.")
                await query.edit_message_text(text=f"لا يوجد محتوى متاح لمحاضرة {lecture} في مادة {subject}.")
                return
            keyboard = []
            row = []
            text = f"اختر نوع المحتوى المطلوب لمحاضرة {lecture} في مادة {subject}:"
            available_types = list(lecture_content.keys())
            if not available_types:
                await query.edit_message_text(text=f"لا يوجد محتوى متاح لمحاضرة {lecture} في مادة {subject}.")
                return
            sorted_types = [t for t in content_types_order if t in available_types]
            other_types = [t for t in available_types if t not in content_types_order]
            display_types = sorted_types + other_types
            for content_type in display_types:
                button_data = f"content_{subject}_{lecture}_{content_type}"
                row.append(InlineKeyboardButton(content_type, callback_data=button_data))
                if len(row) == 1:
                     keyboard.append(row); row = []
            if row: keyboard.append(row)
            keyboard.append([InlineKeyboardButton(f"⬅️ العودة لمحاضرات {subject}", callback_data=f"back_to_lectures_{subject}")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text=text, reply_markup=reply_markup)

        # --------------------------------------------------------------------
        # Action 3: User selected a content type
        # --------------------------------------------------------------------
        elif action == "content" and len(parts) >= 3:
            file_id = None
            display_name = "الملف المطلوب"
            if len(parts) == 3: # Simple subject
                subject, content_type = parts[1], parts[2]
                display_name = f"'{content_type}' لمادة '{subject}'"
                logger.info(f"Approved user {user_id} selected content (simple): {display_name}")
                subject_data = content_map.get(subject, {})
                if isinstance(subject_data.get(content_type), str): file_id = subject_data[content_type]
                else: logger.error(f"Simple subject data error for {subject} - {content_type}.")
            elif len(parts) == 4: # Complex subject
                subject, lecture, content_type = parts[1], parts[2], parts[3]
                display_name = f"'{content_type}' لمحاضرة '{lecture}' في مادة '{subject}'"
                logger.info(f"Approved user {user_id} selected content (complex): {display_name}")
                lecture_data = content_map.get(subject, {}).get(lecture, {})
                if isinstance(lecture_data.get(content_type), str): file_id = lecture_data[content_type]
                else: logger.error(f"Complex subject data error for {subject} - {lecture} - {content_type}.")

            if file_id and isinstance(file_id, str) and not file_id.startswith("PLACEHOLDER_"):
                logger.info(f"Sending file_id: {file_id} for {display_name} to user {user_id}")
                try:
                    await context.bot.send_document(chat_id=chat_id, document=file_id)
                    try:
                        success_text = f"✅ تم إرسال {display_name}.\nهل تحتاج شيئًا آخر؟"
                        await query.edit_message_text(text=success_text, reply_markup=query.message.reply_markup if query.message else None)
                    except Exception as edit_err:
                        logger.warning(f"Could not edit message after sending file {file_id}: {edit_err}")
                        await context.bot.send_message(chat_id=chat_id, text=f"✅ تم إرسال {display_name}.")
                except Exception as e:
                    logger.error(f"Error sending document {file_id}: {e}", exc_info=True)
                    await context.bot.send_message(chat_id=chat_id, text=f"حدث خطأ أثناء إرسال {display_name}.")
            elif file_id and isinstance(file_id, str) and file_id.startswith("PLACEHOLDER_"):
                logger.warning(f"Placeholder file_id requested for {display_name} by user {user_id}")
                await context.bot.send_message(chat_id=chat_id, text=f"عذراً، {display_name} غير متاح بعد.")
            else:
                logger.error(f"File ID not found or invalid for {callback_data}. Resolved file_id: {file_id}")
                await context.bot.send_message(chat_id=chat_id, text="عذراً، لم يتم العثور على الملف المطلوب.")

        # -----------------------------------------------------
        # Action 4: User clicked back to main subjects list
        # -----------------------------------------------------
        elif callback_data == "back_to_subjects":
            logger.info(f"Approved user {user_id} clicked back to subjects.")
            keyboard = []
            row = []
            subjects = list(content_map.keys())
            for i, subject in enumerate(subjects):
                row.append(InlineKeyboardButton(subject, callback_data=f"subject_{subject}"))
                if len(row) == 2 or i == len(subjects) - 1:
                    keyboard.append(row); row = []
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text('اختر المادة الدراسية:', reply_markup=reply_markup)

        # -----------------------------------------------------
        # Action 5: User clicked back to lecture list for a subject
        # -----------------------------------------------------
        elif action == "back" and len(parts) == 4 and parts[1] == "to" and parts[2] == "lectures":
            subject = parts[3]
            logger.info(f"Approved user {user_id} clicked back to lectures for subject {subject}")
            # Re-display lecture list (same logic as Action 1 for complex subjects)
            if subject in content_map and isinstance(content_map[subject].get(list(content_map[subject].keys())[0], None), dict) :
                subject_content = content_map[subject]
                keyboard = []
                row = []
                text = f"اختر المحاضرة المطلوبة لمادة {subject}:"
                try: lecture_keys = sorted(list(subject_content.keys()), key=lambda x: int(''.join(filter(str.isdigit, x))) if any(char.isdigit() for char in x) else float('inf'))
                except ValueError: lecture_keys = sorted(list(subject_content.keys()))
                for lecture_name in lecture_keys:
                    button_data = f"lecture_{subject}_{lecture_name}"
                    row.append(InlineKeyboardButton(lecture_name, callback_data=button_data))
                    if len(row) == 1:
                         keyboard.append(row); row = []
                if row: keyboard.append(row)
                keyboard.append([InlineKeyboardButton("⬅️ العودة للمواد", callback_data="back_to_subjects")])
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(text=text, reply_markup=reply_markup)
            else:
                logger.error(f"Attempted back to lectures for non-complex/non-existent subject '{subject}'")
                # Fallback to main list
                keyboard_main = []
                row_main = []
                subjects_main = list(content_map.keys())
                for i_main, sub_main in enumerate(subjects_main):
                     row_main.append(InlineKeyboardButton(sub_main, callback_data=f"subject_{sub_main}"))
                     if len(row_main) == 2 or i_main == len(subjects_main) - 1:
                         keyboard_main.append(row_main); row_main = []
                reply_markup_main = InlineKeyboardMarkup(keyboard_main)
                await query.edit_message_text("حدث خطأ، تم إرجاعك للقائمة الرئيسية:", reply_markup=reply_markup_main)

        # -----------------------------------------------------
        # Fallback for unknown actions or formats
        # -----------------------------------------------------
        else:
            if not callback_data.startswith("admin_"): # Avoid logging admin clicks as unknown here
                logger.warning(f"Unhandled or unknown callback_data format: '{callback_data}' from user {user_id}")
                try:
                    await query.edit_message_text(text="حدث خطأ غير متوقع في الاختيار. حاول البدء من جديد.")
                except Exception:
                    await context.bot.send_message(chat_id=chat_id, text="حدث خطأ غير متوقع في الاختيار. حاول البدء من جديد باستخدام /start")

    except Exception as e:
        logger.error(f"An critical error occurred in button_click (Callback: {callback_data}, User: {user_id}): {e}", exc_info=True)
        try:
             await context.bot.send_message(chat_id=chat_id, text="عذراً، حدث خطأ فني كبير. يرجى المحاولة مرة أخرى لاحقاً أو إبلاغ الأدمن.")
        except Exception as final_e:
             logger.error(f"Failed even to send the critical error message to user {user_id}: {final_e}")


# دالة للحصول على File ID (للأدمن فقط - تعمل في الشات الخاص)
# لا تحتاج لتعديل هنا، لأنها بالفعل تتحقق من الأدمن
async def get_file_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    ترد بالـ file_id عند إرسال ملف أو صورة للبوت في الشات الخاص،
    فقط إذا كان المرسل هو أحد الأدمنز المحددين.
    """
    if not update.message or update.message.chat.type != ChatType.PRIVATE: return
    user = update.effective_user
    if not user: return
    user_id = user.id
    user_info = user.username or user.first_name
    if user_id not in ADMIN_USER_IDS:
        logger.warning(f"User {user_info} ({user_id}) - NOT an admin - tried to send message/file in private chat. Ignoring.")
        return
    logger.info(f"Admin user {user_info} ({user_id}) sent a message in private chat.")
    file_id = None; file_name = "غير محدد"; file_type = "غير معروف"
    if update.message.document: file_id = update.message.document.file_id; file_name = update.message.document.file_name or "ملف"; file_type = "Document"; logger.info(f"Admin {user_id} sent Document '{file_name}'. file_id: {file_id}")
    elif update.message.photo: file_id = update.message.photo[-1].file_id; file_name = f"صورة_{file_id[:10]}.jpg"; file_type = "Photo"; logger.info(f"Admin {user_id} sent Photo. file_id: {file_id}")
    elif update.message.video: file_id = update.message.video.file_id; file_name = update.message.video.file_name or f"فيديو_{file_id[:10]}.mp4"; file_type = "Video"; logger.info(f"Admin {user_id} sent Video '{file_name}'. file_id: {file_id}")
    elif update.message.audio: file_id = update.message.audio.file_id; file_name = update.message.audio.file_name or f"صوت_{file_id[:10]}.mp3"; file_type = "Audio"; logger.info(f"Admin {user_id} sent Audio '{file_name}'. file_id: {file_id}")
    if file_id:
        reply_text = (f"تم استقبال {file_type} (من الأدمن).\nاسم الملف/النوع: {file_name}\nالـ File ID هو:\n```\n{file_id}\n```\n\nقم بنسخ هذا الـ ID وضعه في `content_map`.")
        try: await update.message.reply_text(reply_text, parse_mode=ParseMode.MARKDOWN_V2)
        except Exception as e: logger.error(f"Failed to reply with file_id {file_id} to admin {user_id} using MarkdownV2: {e}"); await update.message.reply_text(f"Type: {file_type}\nName: {file_name}\nID: {file_id}\n(Copy ID)")
    else: logger.info(f"Admin {user_id} sent a non-media message: '{update.message.text or '[Empty]'}'"); await update.message.reply_text("أهلاً أيها الأدمن! أرسل ملفًا للحصول على الـ ID.")

# --- تشغيل البوت ---
def main() -> None:
    """تحميل المستخدمين، بناء التطبيق، وبدء البوت."""
    logger.info("Loading approved users...")
    load_approved_users() # *** تحميل المستخدمين عند البدء ***

    logger.info("Starting bot application...")
    logger.info(f"Admin User IDs: {ADMIN_USER_IDS}")
    logger.info(f"Initial approved User IDs: {approved_user_ids}")

    try:
        application = Application.builder().token(BOT_TOKEN).build()
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CallbackQueryHandler(button_click)) # معالج واحد لكل الضغطات
        application.add_handler(MessageHandler(filters.ChatType.PRIVATE & ~filters.COMMAND, get_file_id))
        logger.info("Bot is polling for updates...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        logger.critical(f"Failed to initialize or run the bot: {e}", exc_info=True)

if __name__ == '__main__':
    main()