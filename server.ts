import dotenv from 'dotenv';
dotenv.config({ path: '.env.local' });

import express from 'express';
import cors from 'cors';
import multer from 'multer';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const app = express();
app.use(cors());
app.use(express.json());

const upload = multer({ dest: 'uploads/' });

const GROQ_API_KEY = process.env.GROQ_API_KEY || '';

if (!GROQ_API_KEY) {
  console.warn('[MediPlain] WARNING: GROQ_API_KEY is not set. Set it in your .env.local file.');
}

// ─────────────────────────────────────────────
// Allergy synonym map
// ─────────────────────────────────────────────
const ALLERGEN_SYNONYMS: Record<string, string[]> = {
  penicillin: ['penicillin','amoxicillin','amoxycillin','ampicillin','flucloxacillin','co-amoxiclav','augmentin','phenoxymethylpenicillin','piperacillin','tazobactam','piptaz'],
  aspirin: ['aspirin','acetylsalicylic acid','asa','disprin','salicylate','salicylic acid'],
  nsaids: ['ibuprofen','naproxen','diclofenac','indomethacin','celecoxib','mefenamic acid','piroxicam','ketoprofen','nsaid'],
  sulfa: ['sulfonamide','sulfamethoxazole','trimethoprim-sulfamethoxazole','co-trimoxazole','septrin','bactrim','sulfa'],
  cephalosporins: ['cephalexin','cefalexin','cefuroxime','ceftriaxone','cefotaxime','cephalosporin','cefazolin'],
  latex: ['latex','rubber'],
  iodine: ['iodine','iodide','contrast dye','contrast medium','gadolinium'],
  codeine: ['codeine','co-codamol','co-dydramol','dihydrocodeine'],
  morphine: ['morphine','diamorphine','heroin','ms contin','oramorph'],
  opioids: ['opioid','oxycodone','hydrocodone','fentanyl','tramadol','buprenorphine','methadone'],
  metformin: ['metformin','glucophage','glucomet'],
  statins: ['statin','atorvastatin','simvastatin','rosuvastatin','pravastatin','fluvastatin','lipitor','crestor','zocor'],
  'ace inhibitors': ['ramipril','lisinopril','enalapril','perindopril','captopril','ace inhibitor','acei'],
  'beta blockers': ['bisoprolol','metoprolol','atenolol','propranolol','carvedilol','labetalol','beta blocker'],
  warfarin: ['warfarin','coumadin'],
  vancomycin: ['vancomycin'],
  gentamicin: ['gentamicin','aminoglycoside'],
  tetracycline: ['tetracycline','doxycycline','minocycline'],
  metronidazole: ['metronidazole','flagyl'],
  fluconazole: ['fluconazole','diflucan'],
  carbamazepine: ['carbamazepine','tegretol'],
  phenytoin: ['phenytoin','dilantin'],
  allopurinol: ['allopurinol','zyloric'],
};

function getSynonyms(allergen: string): string[] {
  const lower = allergen.toLowerCase().trim();
  if (ALLERGEN_SYNONYMS[lower]) return ALLERGEN_SYNONYMS[lower];
  for (const [key, synonyms] of Object.entries(ALLERGEN_SYNONYMS)) {
    if (synonyms.includes(lower) || key === lower) return synonyms;
  }
  return [lower];
}

function checkAllergies(docText: string, patientAllergies: string[]): string[] {
  if (!patientAllergies?.length) return [];
  const docLower = docText.toLowerCase();
  const warnings: string[] = [];
  for (const allergen of patientAllergies) {
    const synonyms = getSynonyms(allergen);
    const found = synonyms.filter(s => {
      const pattern = new RegExp(`\\b${s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'i');
      return pattern.test(docLower);
    });
    if (found.length > 0) {
      warnings.push(
        `⚠️ ALLERGY ALERT: This document mentions ${[...new Set(found)].join(', ')}. ` +
        `Your profile shows you are allergic to ${allergen}. ` +
        `Do NOT take this medication. Contact your prescriber immediately.`
      );
    }
  }
  return warnings;
}

// ─────────────────────────────────────────────
// Drug interaction database
// ─────────────────────────────────────────────
const DRUG_ALIASES: Record<string, string> = {
  warfarin:'warfarin', coumadin:'warfarin',
  aspirin:'aspirin', 'acetylsalicylic acid':'aspirin', disprin:'aspirin',
  ibuprofen:'ibuprofen', brufen:'ibuprofen', nurofen:'ibuprofen',
  naproxen:'naproxen', naprosyn:'naproxen',
  metformin:'metformin', glucophage:'metformin',
  contrast:'contrast dye', 'contrast medium':'contrast dye', gadolinium:'contrast dye',
  ramipril:'ace inhibitor', lisinopril:'ace inhibitor', enalapril:'ace inhibitor', perindopril:'ace inhibitor',
  fluoxetine:'ssri', sertraline:'ssri', escitalopram:'ssri', citalopram:'ssri', paroxetine:'ssri', prozac:'ssri',
  simvastatin:'simvastatin', zocor:'simvastatin',
  atorvastatin:'atorvastatin', lipitor:'atorvastatin',
  tramadol:'tramadol', tramal:'tramadol',
  amiodarone:'amiodarone',
  clarithromycin:'clarithromycin',
  lithium:'lithium',
  digoxin:'digoxin', lanoxin:'digoxin',
  clopidogrel:'clopidogrel', plavix:'clopidogrel',
  omeprazole:'omeprazole', losec:'omeprazole',
  tamoxifen:'tamoxifen',
  ciprofloxacin:'ciprofloxacin', cipro:'ciprofloxacin',
  rifampicin:'rifampicin', rifampin:'rifampicin',
  'oral contraceptive':'oral contraceptive', 'contraceptive pill':'oral contraceptive',
  "st john's wort":'st johns wort', hypericum:'st johns wort',
  alcohol:'alcohol', ethanol:'alcohol',
  metronidazole:'metronidazole', flagyl:'metronidazole',
  diazepam:'benzodiazepine', lorazepam:'benzodiazepine', clonazepam:'benzodiazepine', alprazolam:'benzodiazepine', temazepam:'benzodiazepine',
  potassium:'potassium', kcl:'potassium',
};

const INTERACTIONS: Record<string, [string, string]> = {
  'warfarin|aspirin': ['HIGH', 'Warfarin + Aspirin: Both thin the blood. Together they significantly increase the risk of serious bleeding.'],
  'warfarin|ibuprofen': ['HIGH', 'Warfarin + Ibuprofen: Ibuprofen can increase warfarin\'s effect and cause dangerous bleeding. Use paracetamol instead.'],
  'warfarin|naproxen': ['HIGH', 'Warfarin + Naproxen: Similar risk to warfarin + ibuprofen. Avoid naproxen.'],
  'metformin|ibuprofen': ['MODERATE', 'Metformin + Ibuprofen: Regular ibuprofen use can affect your kidneys, causing metformin to build up to unsafe levels. Use paracetamol where possible.'],
  'metformin|contrast dye': ['HIGH', 'Metformin + Contrast Dye (for scans): Metformin should usually be stopped before and after contrast dye. Tell your radiology team you take metformin.'],
  'ace inhibitor|potassium': ['MODERATE', 'ACE inhibitors + Potassium: ACE inhibitors already raise potassium. Adding supplements can cause dangerously high potassium.'],
  'ace inhibitor|ibuprofen': ['MODERATE', 'ACE inhibitors + NSAIDs (like ibuprofen): Reduces blood pressure medication effectiveness and can harm kidneys.'],
  'ssri|tramadol': ['HIGH', 'SSRIs + Tramadol: Can cause serotonin syndrome — agitation, rapid heart rate, high temperature.'],
  'ssri|aspirin': ['MODERATE', 'SSRIs + Aspirin: Both affect platelet function. Together they increase bleeding risk, especially stomach bleeding.'],
  'simvastatin|amiodarone': ['HIGH', 'Simvastatin + Amiodarone: Can cause serious muscle damage (rhabdomyolysis). Your doctor should review this combination.'],
  'simvastatin|clarithromycin': ['HIGH', 'Simvastatin + Clarithromycin: Raises simvastatin levels significantly, increasing risk of muscle damage.'],
  'lithium|ibuprofen': ['HIGH', 'Lithium + Ibuprofen: Ibuprofen can raise lithium to toxic levels. Use paracetamol.'],
  'lithium|ace inhibitor': ['HIGH', 'Lithium + ACE inhibitors: Can raise lithium to toxic levels. Regular monitoring is essential.'],
  'digoxin|amiodarone': ['HIGH', 'Digoxin + Amiodarone: Amiodarone raises digoxin levels, which can cause toxicity. Dose may need reducing.'],
  'clopidogrel|omeprazole': ['MODERATE', 'Clopidogrel + Omeprazole: Omeprazole can reduce how well clopidogrel works at preventing clots.'],
  'fluoxetine|tamoxifen': ['HIGH', 'Fluoxetine + Tamoxifen: Significantly reduces how well tamoxifen works. An alternative antidepressant is usually recommended.'],
  'ciprofloxacin|warfarin': ['HIGH', 'Ciprofloxacin + Warfarin: This antibiotic can more than double warfarin\'s blood-thinning effect. Close monitoring needed.'],
  'rifampicin|oral contraceptive': ['HIGH', 'Rifampicin + Oral Contraceptive: Makes the pill much less effective. Additional contraception is required.'],
  'st johns wort|ssri': ['HIGH', "St John's Wort + SSRIs: Both affect serotonin. Combining them can cause serotonin syndrome."],
  'st johns wort|warfarin': ['HIGH', "St John's Wort + Warfarin: Reduces warfarin's effectiveness, increasing clot risk."],
  'alcohol|metronidazole': ['HIGH', 'Alcohol + Metronidazole: Do NOT drink alcohol during this course and for 48 hours after. Causes severe nausea, vomiting, and flushing.'],
  'alcohol|benzodiazepine': ['HIGH', 'Alcohol + Benzodiazepines (e.g. diazepam, lorazepam): Dangerously suppresses breathing and the nervous system.'],
};

function extractDrugs(text: string): string[] {
  const textLower = text.toLowerCase();
  const found = new Set<string>();
  for (const [alias, canonical] of Object.entries(DRUG_ALIASES)) {
    const pattern = new RegExp(`\\b${alias.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'i');
    if (pattern.test(textLower)) found.add(canonical);
  }
  return [...found];
}

function checkInteractions(docText: string, patientMedications: string[]): string[] {
  if (!patientMedications?.length) return [];
  const patientCanonical = patientMedications.map(m => DRUG_ALIASES[m.toLowerCase().trim()] || m.toLowerCase().trim());
  const docDrugs = extractDrugs(docText);
  const warnings: string[] = [];
  const checked = new Set<string>();
  for (const docDrug of docDrugs) {
    for (const patDrug of patientCanonical) {
      const pairKey = [docDrug, patDrug].sort().join('|');
      if (checked.has(pairKey)) continue;
      checked.add(pairKey);
      const interaction = INTERACTIONS[`${docDrug}|${patDrug}`] || INTERACTIONS[`${patDrug}|${docDrug}`];
      if (interaction) {
        warnings.push(interaction[1]);
      }
    }
  }
  return warnings;
}

// ─────────────────────────────────────────────
// Groq analysis
// ─────────────────────────────────────────────
async function analyseWithGroq(
  fileBase64: string,
  mimeType: string,
  profile: Record<string, any>
): Promise<{ docType: string; summary: string; personalizedMeaning: string; technicalDetails: string; confidence: number }> {

  const profileParts: string[] = [];
  if (profile.age) profileParts.push(`Age: ${profile.age}, Gender: ${profile.gender || 'not specified'}`);
  if (profile.diagnoses?.length) profileParts.push(`Medical conditions: ${profile.diagnoses.join(', ')}`);
  if (profile.medications?.length) profileParts.push(`Current medications: ${profile.medications.join(', ')}`);
  if (profile.allergies?.length) profileParts.push(`Allergies: ${profile.allergies.join(', ')}`);
  if (profile.surgeries?.length) profileParts.push(`Past surgeries: ${profile.surgeries.join(', ')}`);
  const profileText = profileParts.length ? profileParts.join('\n') : 'No profile data provided.';

  const prompt = `You are MediPlain, a medical document assistant. Analyse this medical document and respond in STRICT JSON.

Patient profile:
${profileText}

Instructions:
- Identify the document type (e.g. Prescription, Lab Results, Radiology Report, Discharge Summary, Clinical Note, ECG Report, Operative Report, Medical Document)
- Write a plain-language summary at a Grade 6 reading level. Use short sentences. Explain medical terms. Convert abbreviations (od=once daily, bd=twice daily, tds=three times daily, prn=as needed, etc).
- Write a personalised section referencing the patient's specific conditions, medications, and history.
- Include the raw/technical text you extracted from the document.
- Rate your confidence 0-100.

Respond with ONLY this JSON (no markdown, no backticks):
{
  "docType": "...",
  "summary": "...",
  "personalizedMeaning": "...",
  "technicalDetails": "...",
  "confidence": 85
}`;

  // Build content array — include image only for supported mime types
  const isImage = mimeType.startsWith('image/');
  const contentParts: any[] = [];

  if (isImage) {
    contentParts.push({
      type: 'image_url',
      image_url: { url: `data:${mimeType};base64,${fileBase64}` },
    });
  } else {
    // For PDFs or other docs, tell the model we're passing text-only
    contentParts.push({
      type: 'text',
      text: `Note: A non-image file was uploaded (${mimeType}). The user is asking you to analyse a medical document. Please respond with the JSON structure as instructed, noting that you cannot see the document directly and should indicate low confidence.`,
    });
  }

  contentParts.push({ type: 'text', text: prompt });

  const response = await fetch('https://api.groq.com/openai/v1/chat/completions', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${GROQ_API_KEY}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      model: 'meta-llama/llama-4-scout-17b-16e-instruct',
      messages: [{ role: 'user', content: contentParts }],
      max_tokens: 1500,
    }),
  });

  const data = await response.json() as any;

  // Surface Groq errors clearly
  if (!data.choices || data.choices.length === 0) {
    const errMsg = data.error?.message || JSON.stringify(data);
    throw new Error(`Groq API error: ${errMsg}`);
  }

  const text = data.choices[0].message.content as string;

  // Strip markdown fences if present
  const clean = text.replace(/^```json\s*/i, '').replace(/^```\s*/i, '').replace(/```\s*$/i, '').trim();

  try {
    return JSON.parse(clean);
  } catch {
    throw new Error(`Failed to parse Groq response as JSON. Raw response: ${text.slice(0, 300)}`);
  }
}

// ─────────────────────────────────────────────
// Routes
// ─────────────────────────────────────────────
app.post('/api/analyse', upload.single('file'), async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({ error: 'No file uploaded' });
    }

    const profile = JSON.parse(req.body.profile || '{}');
    const filePath = req.file.path;
    const mimeType = req.file.mimetype || 'application/octet-stream';

    const fileBuffer = fs.readFileSync(filePath);
    const fileBase64 = fileBuffer.toString('base64');

    const result = await analyseWithGroq(fileBase64, mimeType, profile);

    const techText = result.technicalDetails || '';
    const allergyWarnings = checkAllergies(techText, profile.allergies || []);
    const interactionWarnings = checkInteractions(techText, profile.medications || []);

    fs.unlinkSync(filePath);

    res.json({
      docType: result.docType,
      summary: result.summary,
      personalizedMeaning: result.personalizedMeaning,
      technicalDetails: result.technicalDetails,
      confidence: result.confidence || 85,
      allergyWarnings,
      interactionWarnings,
    });
  } catch (err: any) {
    console.error('[MediPlain] Error:', err);
    if (req.file?.path && fs.existsSync(req.file.path)) {
      fs.unlinkSync(req.file.path);
    }
    res.status(500).json({ error: err.message || 'Analysis failed' });
  }
});

app.get('/api/health', (_req, res) => res.json({ status: 'ok' }));

const PORT = 5000;
app.listen(PORT, () => {
  console.log(`[MediPlain] API server running on http://localhost:${PORT}`);
});