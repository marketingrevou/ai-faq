import os
import json
from flask import Flask, request, jsonify, send_from_directory
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = """Anda adalah ahli automation workflow untuk profesional dan pebisnis Indonesia.
Tugas Anda: menganalisis profil pengguna dan merekomendasikan 3-5 automation workflow yang relevan
menggunakan n8n dan ChatGPT/OpenAI API.

Aturan output:
- Balas HANYA dengan JSON valid, tanpa markdown code block, tanpa teks tambahan
- Format: array JSON dengan 3-5 objek workflow
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


@app.route("/")
def index():
    return send_from_directory(".", "index.html")


@app.route("/images/<path:filename>")
def images(filename):
    return send_from_directory("images", filename)


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

Berikan 3-5 rekomendasi workflow automation yang paling relevan untuk profil ini."""

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
