import os
import json
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from anthropic import Anthropic
from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials

load_dotenv()

app = Flask(__name__)
client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

_GS_CREDS_RAW = os.environ.get("GOOGLE_SERVICE_ACCOUNT_CREDENTIALS", "")
GOOGLE_SHEETS_ID = os.environ.get("GOOGLE_SHEETS_ID", "")

print(f"[startup] GOOGLE_SHEETS_ID loaded: {bool(GOOGLE_SHEETS_ID)} → {GOOGLE_SHEETS_ID}")
print(f"[startup] GOOGLE_SERVICE_ACCOUNT_CREDENTIALS loaded: {bool(_GS_CREDS_RAW)}")

def _append_lead(row: list):
    """Append a row to the Leads sheet using the service account credentials."""
    creds_info = json.loads(_GS_CREDS_RAW)
    creds = Credentials.from_service_account_info(
        creds_info,
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    gc = gspread.authorize(creds)
    ws = gc.open_by_key(GOOGLE_SHEETS_ID).sheet1
    ws.append_row(row, value_input_option="USER_ENTERED")

MODULES = [
    {"week": 1,  "title": "Future of Work & AI Literacy",          "keywords": "digital transformation, AI impact, future skills, automation mindset, technology literacy"},
    {"week": 2,  "title": "Business Analytics & Problem Solving",   "keywords": "analytics, business problem, data-driven decision, metrics, KPI, reporting"},
    {"week": 3,  "title": "Data Foundations & EDA",                 "keywords": "data, database, structured data, data cleaning, exploratory analysis, spreadsheet"},
    {"week": 4,  "title": "Data Visualization & Communication",     "keywords": "visualization, dashboard, reporting, charts, storytelling, Google Sheets, Looker Studio"},
    {"week": 5,  "title": "AI Foundations & Prompt Engineering",    "keywords": "ChatGPT, prompt engineering, LLM, generative AI, zero-shot, few-shot, chain-of-thought, responsible AI, OpenAI"},
    {"week": 6,  "title": "Custom AI Assistants",                   "keywords": "custom AI chatbot, CustomGPT, no-code AI, knowledge base, AI assistant, chatbot, customer service"},
    {"week": 7,  "title": "Workflow Automation Basics (n8n)",       "keywords": "n8n, workflow automation, triggers, actions, integrations, auto-reporting, notifications, CRM update"},
    {"week": 8,  "title": "AI-Enhanced Automation",                 "keywords": "n8n, AI automation, API integration, GPT integration, automated workflows, data pipeline, email automation"},
    {"week": 9,  "title": "Agentic AI",                             "keywords": "AI agent, autonomous agent, multi-agent, agentic workflow, decision making, lead qualification, knowledge assistant"},
]

SYSTEM_PROMPT = """Anda adalah ahli automation workflow untuk profesional dan pebisnis Indonesia.
Tugas Anda: menganalisis profil pengguna dan merekomendasikan tepat 3 automation workflow yang relevan
menggunakan n8n dan ChatGPT/OpenAI API.

Aturan output:
- Balas HANYA dengan JSON valid, tanpa markdown code block, tanpa teks tambahan
- Format: array JSON dengan tepat 3 objek workflow
- Setiap workflow HARUS menggunakan n8n sebagai orchestrator dan ChatGPT/OpenAI sebagai AI engine
- Rekomendasikan workflow yang benar-benar bisa diimplementasikan dengan tools yang user miliki
- Gunakan Bahasa Indonesia yang natural dan mudah dipahami

Format setiap workflow:
{
  "nama": "Nama workflow yang catchy dan deskriptif",
  "deskripsi": "Penjelasan singkat apa yang dilakukan workflow ini (1-2 kalimat)",
  "manfaat": ["Manfaat 1", "Manfaat 2", "Manfaat 3"],
  "estimasi_waktu_hemat": "~X jam/minggu",
  "tingkat_kesulitan": "Mudah" | "Menengah" | "Lanjutan",
  "tools_dibutuhkan": ["n8n", "ChatGPT API", "tool lain yang relevan"],
  "langkah_awal": ["Langkah 1", "Langkah 2", "Langkah 3"],
  "contoh_skenario": "Satu kalimat skenario spesifik berdasarkan profil pengguna",
  "modul_terkait": [7, 8]
}

Aturan tambahan untuk field baru:
- contoh_skenario WAJIB menyebut profesi pengguna, tantangan utamanya, dan minimal satu tool yang mereka gunakan — bukan skenario generik
- langkah_awal WAJIB berisi tepat 3 langkah pendek dan konkret yang menggunakan tools yang sudah dimiliki pengguna

Program RevoU AI memiliki modul berikut (gunakan untuk field modul_terkait):
- Week 1: Future of Work & AI Literacy
- Week 2: Business Analytics & Problem Solving
- Week 3: Data Foundations & EDA
- Week 4: Data Visualization & Communication
- Week 5: AI Foundations & Prompt Engineering (ChatGPT, prompt engineering, OpenAI)
- Week 6: Custom AI Assistants (CustomGPT, no-code chatbot)
- Week 7: Workflow Automation Basics — n8n (triggers, actions, integrations)
- Week 8: AI-Enhanced Automation (n8n + AI, API integration)
- Week 9: Agentic AI (AI agents, multi-agent workflows)

Untuk setiap workflow, tambahkan field "modul_terkait": [nomor week yang relevan].
Aturan: SELALU sertakan Week 7 dan/atau 8 (karena semua workflow menggunakan n8n), PLUS minimal 1 modul dari Week 1-6 atau 9 yang paling relevan dengan domain/skill spesifik workflow tersebut.
Contoh: [5, 7, 8] untuk workflow n8n dengan prompt engineering. [6, 7, 8] untuk workflow chatbot. [9, 7, 8] untuk workflow agentic.

PENTING: Setiap workflow WAJIB memiliki semua 9 field. Jangan lewatkan langkah_awal, contoh_skenario, atau modul_terkait."""


@app.route("/")
def index():
    return send_from_directory(".", "index.html")


@app.route("/ac-932026")
def staff_access():
    return send_from_directory(".", "index.html")


@app.route("/images/<path:filename>")
def images(filename):
    return send_from_directory("images", filename)


@app.route("/submit-lead", methods=["POST"])
def submit_lead():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Data tidak valid"}), 400

    nama    = data.get("nama", "").strip()
    email   = data.get("email", "").strip()
    wa      = data.get("wa", "").strip()
    profesi = data.get("profesi", "").strip()

    print(f"[submit-lead] received: nama={nama}, email={email}, wa={wa}, profesi={profesi}")
    print(f"[submit-lead] creds ok={bool(_GS_CREDS_RAW)}, sheet_id ok={bool(GOOGLE_SHEETS_ID)}")

    if not nama or not email:
        return jsonify({"error": "Nama dan email wajib diisi"}), 400

    if _GS_CREDS_RAW and GOOGLE_SHEETS_ID:
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            _append_lead([timestamp, nama, email, wa, profesi])
            print(f"[submit-lead] sheet write OK")
        except Exception as e:
            print(f"[submit-lead] Google Sheets error: {e}")
            return jsonify({"success": True, "sheet_error": str(e)})
    else:
        print(f"[submit-lead] skipping sheet write — env vars missing")

    return jsonify({"success": True})


@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json()
    if not data or "answers" not in data:
        return jsonify({"error": "Data profiling tidak ditemukan"}), 400

    answers = data["answers"]
    user_profile = f"""Profil pengguna:
- Profesi/Bidang usaha: {answers.get("profesi", "Tidak disebutkan")}
- Ukuran tim/bisnis: {answers.get("ukuran_tim", "Tidak disebutkan")}
- Tantangan terbesar: {answers.get("tantangan", "Tidak disebutkan")}
- Tools yang sudah dipakai: {answers.get("tools", "Tidak disebutkan")}
- Level kenyamanan teknologi: {answers.get("tech_level", "Tidak disebutkan")}
- Hal yang paling ingin diotomasi: {answers.get("keinginan") or "Tidak disebutkan"}

Berikan tepat 3 rekomendasi workflow automation yang paling relevan untuk profil ini."""

    try:
        with client.messages.stream(
            model="claude-opus-4-6",
            max_tokens=16000,
            thinking={"type": "enabled", "budget_tokens": 8000},
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_profile}],
        ) as stream:
            response = stream.get_final_message()

        # Extract text content (skip thinking blocks)
        text_content = ""
        for block in response.content:
            if block.type == "text":
                text_content = block.text
                break

        workflows = json.loads(text_content)
        return jsonify({"workflows": workflows})

    except json.JSONDecodeError as e:
        return jsonify({"error": f"Gagal memproses respons AI: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": f"Terjadi kesalahan: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
