# MediPlain — Medical Document Assistant

Upload any medical document (prescription, lab results, radiology report, discharge summary) and get a **plain-language explanation**, personalised to your health profile, with allergy and drug interaction checking.

Powered by **Gemini 2.0 Flash** for document understanding.

---

## Quick Start

### 1. Prerequisites
- Node.js 18+
- A free [Gemini API key](https://aistudio.google.com/app/apikey)

### 2. Install dependencies

```bash
npm install
```

### 3. Set your API key

```bash
cp .env.example .env.local
```

Edit `.env.local` and replace `your_gemini_api_key_here` with your actual key:

```
GEMINI_API_KEY=AIza...your_key_here
```

### 4. Run the app

```bash
npm start
```

This starts **both** servers simultaneously:
- **Frontend** (React/Vite): http://localhost:3000
- **API server** (Express): http://localhost:5000

Open http://localhost:3000 in your browser.

---

## How to Use

1. **Fill in your Patient Profile** (optional but recommended)
   - Add your diagnoses, current medications, allergies, and past surgeries
   - Allergy and drug interaction warnings are based on this profile
   - Click **Save Profile**

2. **Upload a Medical Document**
   - Supported: PDF, JPG, PNG, WEBP, TXT
   - Prescriptions, lab results, discharge summaries, radiology reports, etc.

3. **Click "Analyse Document"**
   - Gemini reads and understands your document
   - You get a plain-language summary + personalised explanation
   - Any allergy conflicts or drug interactions are flagged immediately

---

## Architecture

```
Browser (React + Vite :3000)
        |
        |  POST /api/analyse  (multipart/form-data: file + profile)
        v
Express Server (:5000)
        |
        |-- Sends file to Gemini 2.0 Flash (multimodal)
        |   -> Returns: docType, summary, personalizedMeaning, technicalDetails
        |
        |-- Local allergy checker (synonym map, regex matching)
        +-- Local drug interaction checker (hardcoded critical pairs DB)
```

The allergy and interaction checks run **locally** — no patient data leaves your machine for those checks. Only the document is sent to Gemini.

---

## Scripts

| Command | Description |
|---|---|
| `npm start` | Run frontend + API server together |
| `npm run dev` | Frontend only (port 3000) |
| `npm run server` | API server only (port 5000) |
| `npm run build` | Build frontend for production |

---

## Important Disclaimer

MediPlain is for **informational purposes only**. It is not a substitute for professional medical advice, diagnosis, or treatment. Always consult your physician or pharmacist before making any medical decisions.
