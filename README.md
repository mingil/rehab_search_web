# 🏛️ RehaBeyond Scholar (Enterprise Edition)

**RehaBeyond Scholar** is an advanced, AI-powered academic curation and analysis platform. Designed for researchers and clinicians, it leverages OpenAlex's massive open-source database and Google's Gemini LLM to automate literature discovery, generate systematic reviews, simulate peer-review defenses, and interact with papers through an AI Chatbot.

## ✨ Core Features
- **🚀 Ultra-fast Global Search:** Instantly fetches highly-cited papers and classic roots via the OpenAlex API.
- **🌌 3D Knowledge Network:** Automatically clusters research abstracts using Machine Learning (K-Means & PCA) into an interactive 3D universe.
- **🧠 AI Research Assistant:** Generates Evidence-Based Medicine (EBM) PICO tables, identifies research gaps, and drafts systematic review outlines.
- **🛡️ Desk-Reject Simulator:** Acts as a rigorous peer-reviewer (e.g., Nature/NEJM Editor) to critique your abstracts and provide defense strategies before submission.
- **📄 Local PDF Chatbot:** Upload a local PDF and chat with your document securely using AI, without storing files externally.
- **📥 One-Click Export:** Download clean `.xlsx` data, Zotero-ready `.ris` formats, and stylized `.docx` reports.

## 🛠️ Tech Stack & Architecture
- **Frontend:** Streamlit, Plotly, Altair
- **Backend & ML:** Python 3.11, Pandas, Scikit-Learn, NetworkX
- **AI Engine:** Google Generative AI (Gemini 2.5 Flash)
- **Infrastructure:** Docker & Docker Compose (Highly optimized for Synology NAS and Linux environments)

## 📦 Installation & Quick Start

This application is fully dockerized for easy deployment.

### 1. Clone the repository
```bash
git clone [https://github.com/mingil/rehab_search_web.git](https://github.com/mingil/rehab_search_web.git)
cd rehab_search_web
```

### 2. Configure Environment Variables
Copy the example environment file and fill in your details:

Bash
cp .env.example .env
Open .env and configure your keys:

GEMINI_API_KEY: Required for all AI features.

OPENALEX_EMAIL: Recommended for faster API responses.

WEB_PASSWORD & ADMIN_PASSWORD: Secure your portal access.

### 3. Build and Deploy
Bash
docker-compose up -d --build
Access the application at: http://localhost:18501

🔒 Security & Performance
Secure Authentication: Uses SHA-256 hashed cookies to prevent unauthorized admin access.

Memory Optimized: Features robust retry-logic for API fetching and prevents memory leaks during PDF parsing. Docker memory is securely limited to 8GB to prevent host system crashes (OOM).

### 📄 License
This project is licensed under the MIT License.
