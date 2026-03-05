import os
import json
from http.server import BaseHTTPRequestHandler
from anthropic import Anthropic

client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

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
Contoh: [7, 8] untuk workflow n8n dengan AI. Kosongkan array jika tidak ada yang relevan.

PENTING: Setiap workflow WAJIB memiliki semua 9 field. Jangan lewatkan langkah_awal, contoh_skenario, atau modul_terkait."""


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        text_content = ""
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            data = json.loads(body)

            if not data or "answers" not in data:
                self._json({"error": "Data profiling tidak ditemukan"}, 400)
                return

            answers = data["answers"]
            user_profile = f"""Profil pengguna:
- Profesi/Bidang usaha: {answers.get("profesi", "Tidak disebutkan")}
- Ukuran tim/bisnis: {answers.get("ukuran_tim", "Tidak disebutkan")}
- Tantangan terbesar: {answers.get("tantangan", "Tidak disebutkan")}
- Tools yang sudah dipakai: {answers.get("tools", "Tidak disebutkan")}
- Level kenyamanan teknologi: {answers.get("tech_level", "Tidak disebutkan")}
- Hal yang paling ingin diotomasi: {answers.get("keinginan") or "Tidak disebutkan"}

Berikan tepat 3 rekomendasi workflow automation yang paling relevan untuk profil ini."""

            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=2048,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_profile}],
            )

            text_content = response.content[0].text if response.content else ""

            if not text_content.strip():
                self._json({"error": "AI tidak mengembalikan respons. Coba lagi."}, 500)
                return

            # Strip markdown code block wrappers if model adds them
            cleaned = text_content.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[-1]
                cleaned = cleaned.rsplit("```", 1)[0].strip()

            workflows = json.loads(cleaned)
            self._json({"workflows": workflows}, 200)

        except json.JSONDecodeError as e:
            preview = text_content[:300] if text_content else "(empty)"
            self._json({"error": f"Gagal parse JSON. Raw: {preview}"}, 500)
        except Exception as e:
            self._json({"error": f"Terjadi kesalahan: {str(e)}"}, 500)

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors_headers()
        self.end_headers()

    def _json(self, obj, status):
        body = json.dumps(obj).encode()
        self.send_response(status)
        self._cors_headers()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def _cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
