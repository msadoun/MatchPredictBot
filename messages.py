# Arabic UI strings

DRAW = "تعادل"
VS = "ضد"

STATUS_OPEN = "مفتوحة"
STATUS_CLOSED = "مغلقة"
KICKOFF = "موعد البداية"
RESULT = "النتيجة"
POINTS_SHORT = "نقطة"
PREDICTIONS = "توقعات"

START_TEXT = "مرحباً بك في بوت توقعات كأس العالم! ⚽\n\nاختر من الأزرار أدناه:"

BTN_MATCHES = "📅 مباريات اليوم"
BTN_PREDICT = "⚽ توقع مباراة"
BTN_CANCEL = "❌ إلغاء التوقع"
BTN_MY_PREDICTIONS = "📋 توقعاتي"
BTN_LEADERBOARD = "🏆 المتصدرين"
BTN_HELP = "❓ المساعدة"

GROUP_WELCOME = (
    "أهلاً بالجميع! أنا بوت توقعات كأس العالم 2026 ⚽\n\n"
    "📩 جميع الردود تصلك في رسالة خاصة فقط — ولن تزعج المجموعة.\n"
    "افتح محادثة خاصة معي واضغط /start للبدء."
)

DM_REQUIRED = (
    "لاستخدام البوت من المجموعة، افتح محادثة خاصة معي أولاً واضغط /start:\n"
    "@{bot}"
)

DM_REQUIRED_ALERT = "افتح محادثة خاصة مع @{bot} واضغط /start أولاً"

MATCHES_USAGE = (
    "الاستخدام: /matches [YYYY-MM-DD]\n"
    "مثال: /matches 2026-06-18"
)

NO_MATCHES_DATE = (
    "لا توجد مباريات مفتوحة في {date}.\n"
    "جرّب تاريخاً آخر، مثال: /matches 2026-06-18"
)

OPEN_MATCHES_HEADER = "المباريات المفتوحة في {date}:\n"
SHOWING_MATCHES = "\nيعرض {shown} من {total} مباراة لهذا التاريخ."

NO_MATCHES_TODAY = (
    "لا توجد مباريات مفتوحة اليوم ({date}).\n"
    "جرّب /matches 2026-06-18 أو /predict <رقم_المباراة>"
)

UPCOMING_OPEN_MATCHES = "لا توجد مباريات اليوم. المباريات المفتوحة القادمة:\n"
CHOOSE_MATCH_UPCOMING = "لا توجد مباريات اليوم. اختر مباراة مفتوحة:"
NO_OPEN_MATCHES = "لا توجد مباريات مفتوحة للتوقع حالياً."

CHOOSE_MATCH = "اختر مباراة للتوقع ({date}):"
WHO_WINS = "من سيفوز؟"
MATCH_HEADER = "المباراة #{id}\n{home} {vs} {away}"

PREDICT_USAGE = (
    "الاستخدام: /predict [رقم_المباراة] [النتيجة]\n"
    "مثال: /predict 18 4-0 — ثم اختر الفائز (الرقم الأعلى له)"
)

SCORING_RULES = (
    "📊 نظام النقاط:\n"
    "• 3 نقاط — النتيجة الدقيقة\n"
    "• 2 نقطة — الفائز + عدد أهداف الفائز صحيح\n"
    "• 1 نقطة — الفائز فقط\n"
    "• 0 — توقع خاطئ (التعادل يُحسب فقط بالنتيجة الدقيقة)"
)

MATCH_ID_NOT_NUMBER = "رقم المباراة يجب أن يكون رقماً."
MATCH_NOT_FOUND = "المباراة #{id} غير موجودة."
MATCH_CLOSED = "المباراة #{id} مغلقة. لم يعد بإمكانك التوقع."
MATCH_NO_LONGER_OPEN = "هذه المباراة بدأت أو أُغلقت — لم يعد بإمكانك التوقع."

PICK_WINNER_PROMPT = (
    "المباراة #{id}: {home} {vs} {away}\n"
    "توقعك: {winner}\n\n"
    "أدخل النتيجة برقمين مفصولين بشرطة.\n"
    "الرقم الأعلى يُحسب للفائز الذي اخترته.\n\n"
    "أمثلة:\n"
    "• 4-0\n"
    "• 2-1\n\n"
    "أرسل /cancel للإلغاء."
)

PICK_DRAW_PROMPT = (
    "المباراة #{id}: {home} {vs} {away}\n"
    "توقعك: {draw}\n\n"
    "أدخل النتيجة برقمين متساويين مفصولين بشرطة.\n\n"
    "أمثلة:\n"
    "• 0-0\n"
    "• 1-1\n"
    "• 2-2\n\n"
    "أرسل /cancel للإلغاء."
)

GROUP_SCORE_REPLY = "{name}، أدخل النتيجة هنا (مثال: 2-1):"

INVALID_SCORE_FORMAT = (
    "صيغة غير صحيحة. أدخل النتيجة مثل 2-1 أو 4-0.\n"
    "أرسل /cancel للإلغاء."
)

DRAW_SCORES_MUST_EQUAL = "للتعادل، يجب أن يكون الرقمان متساويين (مثال: 1-1)."
UNEAQUAL_SCORES_FOR_WINNER = "أدخل رقماً مختلفين — الأعلى يُحسب للفائز (مثال: 4-0)."
SEND_CANCEL = "أرسل /cancel للإلغاء."

PREDICTION_SAVED = "تم حفظ التوقع — {home} {vs} {away}\n{outcome}: {score}"
PREDICTION_UPDATED = "تم تحديث توقعك — {home} {vs} {away}\n{outcome}: {score}"
PREDICTION_ONCE_NOTE = "توقعك واحد لكل مباراة ويُحسب في جميع المجموعات."

NOTHING_TO_CANCEL = "لا يوجد توقع لإلغائه."
PREDICTION_CANCELLED = "تم إلغاء التوقع."

NOT_JOINED = "لم تسجّل بعد. استخدم /start أولاً."
NO_PREDICTIONS = "لم تقم بأي توقعات بعد."
PREDICTION_SAVE_FAILED = (
    "تعذّر حفظ التوقع. تأكد أن البوت يعمل على قاعدة بيانات دائمة، ثم حاول مرة أخرى."
)
YOUR_PREDICTIONS = "توقعاتك:\n"
YOUR_PICK = "توقعك"
ACTUAL = "النتيجة الفعلية"
POINTS_LABEL = "النقاط"
POINTS_PENDING = "⏳ بانتظار النتيجة"

LEADERBOARD_TITLE = "🏆 لوحة متصدرين كأس العالم 2026\n"
LEADERBOARD_TITLE_GROUP = "🏆 لوحة متصدرين المجموعة\n"
LEADERBOARD_TITLE_GROUP_NAMED = "🏆 لوحة متصدرين: {group}\n"
CHOOSE_GROUP_LEADERBOARD = "اختر مجموعة لعرض لوحة المتصدرين:"
BTN_SWITCH_GROUP = "🔄 تغيير المجموعة"
LEADERBOARD_PRIVATE_ONLY = (
    "لا توجد مجموعة مرتبطة بحسابك.\n"
    "استخدم البوت من مجموعة تيليغرام أو توقع من داخل المجموعة أولاً."
)
LEADERBOARD_EMPTY = "لا توجد توقعات بعد. كن الأول — استخدم /predict!"
LEADERBOARD_ROW = "{medal} {name} — {points} نقطة"
LEADERBOARD_TOP_N = "\nيعرض أفضل {shown} من {total} لاعب."
YOUR_RANK = "\n📍 ترتيبك: #{rank} · {points} نقطة"

ADMIN_ONLY = "هذا الأمر للمسؤولين فقط."
ADDMATCH_USAGE = (
    "الاستخدام: /addmatch <فريق_المنزل> <فريق_الضيف> [الموعد]\n"
    'مثال: /addmatch "ريال مدريد" برشلونة "2026-06-20 20:00"'
)
MATCH_CREATED = "تم إنشاء المباراة.\n\n{match}\n\nيمكن للمشاركين التوقع عبر:\n/predict {id}"

SETRESULT_USAGE = (
    "الاستخدام: /setresult <رقم_المباراة> <أهداف_المنزل> <أهداف_الضيف>\n"
    "مثال: /setresult 1 2 1"
)
SCORES_MUST_BE_NUMBERS = "رقم المباراة والأهداف يجب أن تكون أرقاماً."
RESULT_RECORDED = "تم تسجيل النتيجة وتحديث النقاط.\n\n{match}"

SETPREDICTION_USAGE = (
    "الاستخدام: /setprediction <telegram_id> <رقم_المباراة> <النتيجة>\n"
    "مثال: /setprediction 10140530 35 3-0"
)
PREDICTION_SET = "تم تعيين التوقع — {home} {vs} {away}: {score} ({points} نقطة)"
USER_NOT_FOUND = "المستخدم غير موجود."

SYNCSCORES_DONE = (
    "تم تحديث النقاط لجميع المستخدمين.\n"
    "• نتائج جديدة من ESPN: {results_updated}\n"
    "• توقعات أُعيد حسابها: {predictions_scored}\n"
    "• مباريات بدون تطابق ESPN: {espn_skipped}"
)

BTN_ADMIN_PREDICTIONS = "📋 تقارير التوقعات"
ADMIN_PREDICTIONS_MENU = (
    "📋 تقارير التوقعات (للمسؤول)\n\n"
    "اختر كيف تريد عرض أو حفظ توقعات اللاعبين:"
)
ADMIN_PREDICTIONS_BY_DAY = "📅 حسب اليوم"
ADMIN_PREDICTIONS_BY_STAGE = "🏆 حسب المرحلة/المجموعة"
ADMIN_PREDICTIONS_GROUP_STAGE = "⚽ دور المجموعات (كامل)"
ADMIN_PREDICTIONS_SAVED = "💾 التقارير المحفوظة"
ADMIN_PREDICTIONS_PICK_DAY = "اختر يوم المباريات:"
ADMIN_PREDICTIONS_PICK_STAGE = "اختر المرحلة أو المجموعة:"
ADMIN_PREDICTIONS_SCOPE_HEADER = "{summary}\n\nاختر إجراء:"
ADMIN_PREDICTIONS_BTN_VIEW = "👁 عرض في المحادثة"
ADMIN_PREDICTIONS_BTN_SAVE = "💾 حفظ وإرسال ملف Excel"
ADMIN_PREDICTIONS_BTN_BACK = "↩️ رجوع"
ADMIN_PREDICTIONS_SAVED_EMPTY = "لا توجد تقارير محفوظة بعد."
ADMIN_PREDICTIONS_SAVED_LIST = "💾 التقارير المحفوظة:\n"
ADMIN_PREDICTIONS_SAVED_ROW = "#{id} · {label} · {users} لاعب · {predictions} توقع · {saved_at}"
ADMIN_PREDICTIONS_EXPORT_DONE = (
    "✅ تم حفظ التقرير.\n\n"
    "{summary}\n\n"
    "📁 الملف: {filename}"
)
ADMIN_PREDICTIONS_FILE_CAPTION = "تقرير توقعات — {label}"

SETGROUPPOINTS_USAGE = (
    "الاستخدام:\n"
    "• /setgrouppoints load alkoram3na — الكورة معنا\n"
    "• /setgrouppoints load km3na — K m3na groub\n"
    "• /setgrouppoints <مجموعة> <مستخدم> <نقاط>\n"
    "• /setpoints <مستخدم> <نقاط> — K m3na (بدون مجموعة)\n"
    "مثال: /setpoints M2usab 27\n"
    "مثال: /setpoints 10140530 27 — برقم تيليجرام حتى بدون /start"
)
SETGROUPPOINTS_USER_NOT_FOUND = (
    "المستخدم غير موجود. اطلب منه /start للبوت، "
    "أو استخدم رقم تيليجرام: /setpoints <telegram_id> <نقاط>"
)
SETGROUPPOINTS_LOAD_DONE = (
    "تم تعيين نقاط المجموعة «{group}».\n\n"
    "✅ تم: {applied_count}\n"
    "❌ غير موجود: {missing_count}"
)
SETGROUPPOINTS_APPLIED_ROW = "• {line}"
SETGROUPPOINTS_MISSING_ROW = "• {ref}"
SETGROUPPOINTS_ONE_DONE = "تم تعيين {name}: {points} نقطة أساسية في المجموعة «{group}» (تُضاف لتوقعاته)."
SETGROUPPOINTS_GROUP_NOT_FOUND = (
    "تعذّر العثور على المجموعة. أضف البوت للمجموعة، أو شغّل الأمر من داخلها، "
    "أو عيّن ALKORAM3NA_GROUP_CHAT_ID / KM3NA_GROUP_CHAT_ID."
)
SETGROUPPOINTS_NOTE = (
    "ملاحظة: النقاط اليدوية = نقاط أساسية تُضاف فوق نقاط التوقعات الجديدة. "
    "التوقعات الفعلية وملفات Excel لا تُحذف."
)

CLEAR_USERDATA_DONE = (
    "تمت إعادة ضبط البوت كأول تشغيل.\n"
    "• مستخدمون: {users}\n"
    "• توقعات: {predictions}\n"
    "• أعضاء مجموعات: {group_members}\n"
    "• نقاط يدوية: {manual_points}\n"
    "• مباريات محذوفة: {matches}\n"
    "• مباريات جديدة: {seeded}\n\n"
    "لا مستخدمين ولا توقعات. شغّل /setgrouppoints load km3na عند الحاجة.\n"
    "لاسترجاع نسخة قديمة: /restorepredictions"
)
RESET_POINTS_DONE = (
    "تم تصفير نقاط الجميع.\n"
    "• مستخدمون: {users_zeroed}\n"
    "• توقعات مُصفّرة: {prediction_scores_cleared}\n\n"
    "التوقعات نفسها باقية. لتحميل نقاط K m3na: /setgrouppoints load km3na"
)
RESET_POINTS_CONFIRM = (
    "⚠️ تصفير نقاط الجميع إلى صفر:\n"
    "• النقاط اليدوية (الأساسية)\n"
    "• نقاط التوقعات من المباريات\n\n"
    "المستخدمون والتوقعات لا يُحذفون.\n"
    "أرسل: /resetpoints confirm"
)
CLEAR_GROUPS_DONE = (
    "تم حذف جميع المجموعات من البيانات.\n"
    "• عضويات مجموعات: {group_members}\n"
    "• مجموعات نشطة للمستخدمين: {active_groups_cleared}\n\n"
    "المستخدمون والتوقعات والنقاط باقية.\n"
    "لإعادة تسجيل K m3na: /setgrouppoints load km3na"
)
CLEAR_GROUPS_CONFIRM = (
    "⚠️ حذف جميع المجموعات من البيانات:\n"
    "• عضويات group_members\n"
    "• المجموعة النشطة لكل مستخدم\n\n"
    "المستخدمون والتوقعات والنقاط لا تُحذف.\n"
    "لن تُعاد المجموعات تلقائياً بعد إعادة التشغيل.\n"
    "أرسل: /cleargroups confirm"
)

CLEAR_USERDATA_USAGE = "الاستخدام: /clearuserdata confirm"
CLEAR_USERDATA_CONFIRM = (
    "⚠️ إعادة ضبط كاملة كأول تشغيل:\n"
    "حذف المستخدمين، المجموعات، التوقعات، والمباريات ثم تحميل مباريات كأس العالم من جديد.\n"
    "أرسل: /clearuserdata confirm"
)

RESTORE_PREDICTIONS_DONE = (
    "تم استرجاع {restored} توقع مفقود. "
    "لم يُمس {skipped} توقع موجود مسبقاً — لا يُحذف أو يُستبدل أي توقع."
)
RESTORE_PREDICTIONS_EMPTY = (
    "لا توجد نسخة احتياطية محلية. "
    "أرسل ملف predictions_*.json مع الأمر أو من رسالة النسخة الاحتياطية في تيليجرام."
)
RESTORE_PREDICTIONS_FILE_FAILED = "تعذّر قراءة ملف النسخة الاحتياطية."
RESTORE_PREDICTIONS_USAGE = (
    "الاستخدام: /restorepredictions\n"
    "أو أرسل /restorepredictions مع ملف JSON أو ردّ على رسالة النسخة الاحتياطية."
)

IMPORT_EXCEL_DONE = (
    "تم استيراد البيانات من Excel (دمج فقط — لم يُحذف أي توقع).\n"
    "• توقعات مضافة: {merged}\n"
    "• نقاط محدّثة: {points_updated}\n"
    "• موجود مسبقاً (لم يُمس): {skipped}\n"
    "• نقاط مجموعة أساسية: {group_points}\n"
    "• ملفات: {files}"
)
IMPORT_EXCEL_USERS_MISSING = "لم يُعثر على: {users}"
IMPORT_EXCEL_MATCHES_MISSING = "مباريات غير مطابقة: {matches}"
IMPORT_EXCEL_EMPTY = (
    "لا توجد ملفات Excel في data/imports أو data/exports.\n"
    "أرسل ملف .xlsx مع /importexcel أو ردّ على رسالة الملف."
)
IMPORT_EXCEL_FILE_FAILED = "تعذّر قراءة ملف Excel."
IMPORT_EXCEL_USAGE = (
    "الاستخدام: /importexcel\n"
    "أو أرسل /importexcel مع ملف Excel (.xlsx) أو ردّ على رسالة التقرير.\n"
    "يُدمج التوقعات والنقاط — لا يحذف أي بيانات موجودة."
)
PREDICTIONS_NEVER_DELETED = (
    "التوقعات وملفات Excel محفوظة. "
    "النقاط اليدوية للمجموعة تُضاف فوق نقاط التوقعات."
)

NO_MATCHES_YET = "لم تُنشأ أي مباريات بعد."
ALL_MATCHES = "جميع المباريات:\n"

CLOSEMATCH_USAGE = "الاستخدام: /closematch <رقم_المباراة>"
MATCH_NOW_CLOSED = "المباراة #{id} مغلقة الآن للتوقعات."
OPENMATCH_USAGE = (
    "الاستخدام: /openmatch <رقم_المباراة> [clear]\n"
    "مثال: /openmatch 36 — إعادة فتح مباراة منتهية للتوقعات\n"
    "مثال: /openmatch 36 clear — مسح النتيجة ثم استيرادها من ESPN"
)
MATCH_NOW_OPEN = "المباراة #{id} مفتوحة الآن للتوقعات.\n\n{match}"
MATCH_HAS_RESULT = (
    "المباراة #{id} لها نتيجة ({score}).\n"
    "لإعادة فتحها استخدم: /openmatch {id} clear"
)

WORLDCUP_LOADED = (
    "تم تحميل مباريات كأس العالم 2026.\n\n"
    "أُضيفت: {added}\n"
    "تُخطّت (موجودة مسبقاً): {skipped}\n"
    "مباريات سابقة أُغلقت: {closed}\n"
    "مفتوحة للتوقع: {open}\n\n"
    "يمكن للمشاركين استخدام /matches لعرض مباريات اليوم."
)
