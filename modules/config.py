import os
import datetime
from dotenv import load_dotenv

load_dotenv()
OPENALEX_EMAIL = os.getenv("OPENALEX_EMAIL", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
WEB_PASSWORD = os.getenv("WEB_PASSWORD", "rehab2026")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin2026")
CURRENT_YEAR = datetime.datetime.now().year

GLOBAL_PRESETS = {
    "👑 General Science & Multidisciplinary": {"Nature": "0028-0836", "Science": "0036-8075", "Cell": "0092-8674", "PNAS": "0027-8424"},
    "🩺 Clinical Medicine": {"NEJM": "0028-4793", "The Lancet": "0140-6736", "JAMA": "0098-7484", "BMJ": "0959-8138"},
    "🤖 Medical AI (Med-AI)": {"NPJ Digit Med": "2397-3374", "Lancet Digit Health": "2589-7500", "Nat Mach Intell": "2522-5839", "IEEE J Biomed Health Inform": "2168-2194"},
    "💻 Engineering & AI (CS)": {"IEEE TPAMI": "0162-8828", "Expert Syst Appl": "0957-4174", "IEEE Access": "2169-3536", "Sensors": "1424-8220"},
    "🏃 Rehabilitation & Sports": {"Arch Phys Med Rehabil": "0003-9993", "Neurorehabil Neural Repair": "1545-9683", "Am J Sports Med": "0363-5465", "Br J Sports Med": "0306-3674"},
    "🧠 Neuroscience & Psychiatry": {"Lancet Neurology": "1474-4422", "Brain": "0006-8950", "Stroke": "0039-2499", "Am J Psychiatry": "0002-953X"}
}
