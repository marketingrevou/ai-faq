import os
import json
from http.server import BaseHTTPRequestHandler
from anthropic import Anthropic

client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

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
  "contoh_skenario": "Satu kalimat skenario spesifik berdasarkan profil pengguna"
}

Aturan tambahan untuk field baru:
- contoh_skenario WAJIB menyebut profesi pengguna, tantangan utamanya, dan minimal satu tool yang mereka gunakan — bukan skenario generik
- langkah_awal WAJIB berisi tepat 3 langkah pendek dan konkret yang menggunakan tools yang sudah dimiliki pengguna

PENTING: Setiap workflow WAJIB memiliki semua 8 field. Jangan lewatkan langkah_awal atau contoh_skenario."""


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
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
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_profile}],
            )

            text_content = response.content[0].text if response.content else ""

            if not text_content.strip():
                self._json({"error": "AI tidak mengembalikan respons. Coba lagi."}, 500)
                return

            workflows = json.loads(text_content)
            self._json({"workflows": workflows}, 200)

        except json.JSONDecodeError as e:
            self._json({"error": f"Gagal memproses respons AI: {str(e)}"}, 500)
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
