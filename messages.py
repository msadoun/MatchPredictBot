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
    "• 2-1\n"
    "• 4-0\n"
    "• 1-1 (للتعادل)\n\n"
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
UNEAQUAL_SCORES_FOR_WINNER = "أدخل رقماً مختلفين — الأعلى يُحسب للفائز (مثال: 2-1)."
SEND_CANCEL = "أرسل /cancel للإلغاء."

PREDICTION_SAVED = "تم حفظ التوقع — {home} {vs} {away}\n{outcome}: {score}"

NOTHING_TO_CANCEL = "لا يوجد توقع لإلغائه."
PREDICTION_CANCELLED = "تم إلغاء التوقع."

NOT_JOINED = "لم تسجّل بعد. استخدم /start أولاً."
NO_PREDICTIONS = "لم تقم بأي توقعات بعد."
YOUR_PREDICTIONS = "توقعاتك:\n"
YOUR_PICK = "توقعك"
ACTUAL = "النتيجة الفعلية"
POINTS_LABEL = "النقاط"

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

NO_MATCHES_YET = "لم تُنشأ أي مباريات بعد."
ALL_MATCHES = "جميع المباريات:\n"

CLOSEMATCH_USAGE = "الاستخدام: /closematch <رقم_المباراة>"
MATCH_NOW_CLOSED = "المباراة #{id} مغلقة الآن للتوقعات."

WORLDCUP_LOADED = (
    "تم تحميل مباريات كأس العالم 2026.\n\n"
    "أُضيفت: {added}\n"
    "تُخطّت (موجودة مسبقاً): {skipped}\n"
    "مباريات سابقة أُغلقت: {closed}\n"
    "مفتوحة للتوقع: {open}\n\n"
    "يمكن للمشاركين استخدام /matches لعرض مباريات اليوم."
)
