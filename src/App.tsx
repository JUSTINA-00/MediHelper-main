/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import {
  FileText, Upload, User, AlertCircle, CheckCircle2,
  ChevronDown, ChevronUp, Loader2, X, Plus,
  Stethoscope, Pill, Activity, AlertTriangle, RefreshCw,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface PatientProfile {
  age: string;
  gender: string;
  diagnoses: string[];
  medications: string[];
  allergies: string[];
  surgeries: string[];
}

interface AnalysisResult {
  docType: string;
  summary: string;
  personalizedMeaning: string;
  allergyWarnings: string[];
  interactionWarnings: string[];
  technicalDetails: string;
  confidence: number;
}

const API_URL = 'http://localhost:5000';

const LOADING_STEPS = [
  'Reading your document…',
  'Extracting medical information…',
  'Checking allergies and interactions…',
  'Generating plain-language summary…',
];

export default function App() {
  const [profile, setProfile] = useState<PatientProfile>({
    age: '', gender: '', diagnoses: [], medications: [], allergies: [], surgeries: [],
  });
  const [isProfileSaved, setIsProfileSaved] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [filePreview, setFilePreview] = useState<string | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [showTechnical, setShowTechnical] = useState(false);
  const [loadingStep, setLoadingStep] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [diagInput, setDiagInput] = useState('');
  const [medInput, setMedInput] = useState('');
  const [allergyInput, setAllergyInput] = useState('');
  const [surgeryInput, setSurgeryInput] = useState('');

  const handleFileChange = (uploadedFile: File) => {
    setFile(uploadedFile);
    setAnalysisResult(null);
    setError(null);
    if (uploadedFile.type.startsWith('image/')) {
      const reader = new FileReader();
      reader.onload = (e) => setFilePreview(e.target?.result as string);
      reader.readAsDataURL(uploadedFile);
    } else {
      setFilePreview(null);
    }
  };

  const addTag = (field: keyof PatientProfile, value: string) => {
    if (!value.trim()) return;
    setProfile(prev => ({ ...prev, [field]: [...(prev[field] as string[]), value.trim()] }));
  };

  const removeTag = (field: keyof PatientProfile, index: number) => {
    setProfile(prev => ({ ...prev, [field]: (prev[field] as string[]).filter((_, i) => i !== index) }));
  };

  const analyzeDocument = async () => {
    if (!file) return;
    setIsAnalyzing(true);
    setAnalysisResult(null);
    setError(null);
    setLoadingStep(0);
    const stepInterval = setInterval(() => {
      setLoadingStep(prev => Math.min(prev + 1, LOADING_STEPS.length - 1));
    }, 2800);
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('profile', JSON.stringify(profile));
      const response = await fetch(`${API_URL}/api/analyse`, { method: 'POST', body: formData });
      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.error || `Server error: ${response.status}`);
      }
      const data = await response.json();
      setAnalysisResult(data);
    } catch (err: any) {
      setError(
        err.message?.includes('Failed to fetch')
          ? 'Cannot reach the MediPlain server. Make sure it is running with: npm run server'
          : err.message || 'Analysis failed. Please try again.'
      );
    } finally {
      clearInterval(stepInterval);
      setIsAnalyzing(false);
    }
  };

  const reset = () => { setAnalysisResult(null); setFile(null); setFilePreview(null); setError(null); };

  return (
    <div className="min-h-screen bg-[#FDFCFB] text-[#1A1A1A] font-sans text-[18px] selection:bg-[#0D7377]/20">
      <header className="bg-white border-b border-gray-100 py-8 px-6 sticky top-0 z-50 shadow-sm">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-[#0D7377] rounded-xl flex items-center justify-center shadow-lg shadow-[#0D7377]/20">
              <Stethoscope className="text-white w-7 h-7" />
            </div>
            <div>
              <h1 className="text-3xl font-bold tracking-tight text-[#0D7377]">MediPlain</h1>
              <p className="text-gray-500 font-medium">Your Medical Documents, In Plain Language</p>
            </div>
          </div>
          <button onClick={() => setIsProfileSaved(!isProfileSaved)}
            className="flex items-center gap-2 px-6 py-3 rounded-full border-2 border-gray-200 font-semibold hover:bg-gray-50 transition-colors">
            <User className="w-5 h-5" />
            {isProfileSaved ? 'Edit Profile' : 'Complete Profile'}
          </button>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-12 grid grid-cols-1 lg:grid-cols-12 gap-12">
        {/* Profile Sidebar */}
        <div className={`lg:col-span-4 space-y-8 ${isProfileSaved ? 'hidden lg:block opacity-60 pointer-events-none' : 'block'}`}>
          <section className="bg-white rounded-[32px] p-8 shadow-xl shadow-gray-200/50 border border-gray-100">
            <div className="flex items-center gap-3 mb-8">
              <Activity className="text-[#0D7377] w-6 h-6" />
              <h2 className="text-2xl font-bold">Patient Profile</h2>
            </div>
            <div className="space-y-6">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-sm font-bold uppercase tracking-wider text-gray-400">Age</label>
                  <input type="number" value={profile.age} onChange={(e) => setProfile({ ...profile, age: e.target.value })}
                    placeholder="e.g. 65" className="w-full p-4 bg-gray-50 rounded-2xl border-2 border-transparent focus:border-[#0D7377] outline-none transition-all" />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-bold uppercase tracking-wider text-gray-400">Gender</label>
                  <select value={profile.gender} onChange={(e) => setProfile({ ...profile, gender: e.target.value })}
                    className="w-full p-4 bg-gray-50 rounded-2xl border-2 border-transparent focus:border-[#0D7377] outline-none transition-all appearance-none">
                    <option value="">Select</option>
                    <option>Male</option><option>Female</option><option>Other</option>
                  </select>
                </div>
              </div>
              {[
                { label: 'Diagnoses', field: 'diagnoses' as const, icon: Activity, input: diagInput, setInput: setDiagInput, placeholder: 'e.g. Type 2 Diabetes' },
                { label: 'Current Medications', field: 'medications' as const, icon: Pill, input: medInput, setInput: setMedInput, placeholder: 'e.g. Metformin' },
                { label: 'Allergies', field: 'allergies' as const, icon: AlertCircle, input: allergyInput, setInput: setAllergyInput, placeholder: 'e.g. Penicillin', isCritical: true },
                { label: 'Past Surgeries', field: 'surgeries' as const, icon: FileText, input: surgeryInput, setInput: setSurgeryInput, placeholder: 'e.g. Appendectomy' },
              ].map((item) => (
                <div key={item.label} className="space-y-2">
                  <label className="text-sm font-bold uppercase tracking-wider text-gray-400 flex items-center gap-2">
                    <item.icon className="w-4 h-4" />{item.label}
                    {item.isCritical && <span className="text-red-500 text-xs">● Critical</span>}
                  </label>
                  <div className="flex gap-2">
                    <input type="text" value={item.input} onChange={(e) => item.setInput(e.target.value)}
                      onKeyDown={(e) => { if (e.key === 'Enter') { addTag(item.field, item.input); item.setInput(''); } }}
                      placeholder={item.placeholder}
                      className="flex-1 p-4 bg-gray-50 rounded-2xl border-2 border-transparent focus:border-[#0D7377] outline-none transition-all" />
                    <button onClick={() => { addTag(item.field, item.input); item.setInput(''); }}
                      className="p-4 bg-gray-100 rounded-2xl hover:bg-gray-200 transition-colors"><Plus className="w-6 h-6" /></button>
                  </div>
                  <div className="flex flex-wrap gap-2 mt-2">
                    {profile[item.field].map((tag, idx) => (
                      <span key={idx} className={`px-4 py-2 rounded-full flex items-center gap-2 text-sm font-semibold ${item.isCritical ? 'bg-red-100 text-red-700' : 'bg-[#0D7377]/10 text-[#0D7377]'}`}>
                        {tag}<button onClick={() => removeTag(item.field, idx)}><X className="w-4 h-4" /></button>
                      </span>
                    ))}
                  </div>
                </div>
              ))}
              <button onClick={() => setIsProfileSaved(true)}
                className="w-full py-5 bg-[#0D7377] text-white rounded-2xl font-bold text-xl shadow-lg shadow-[#0D7377]/30 hover:scale-[1.02] active:scale-[0.98] transition-all mt-4">
                Save Profile
              </button>
            </div>
          </section>
        </div>

        {/* Main Area */}
        <div className="lg:col-span-8 space-y-12">
          {/* Upload */}
          {!analysisResult && !isAnalyzing && (
            <section
              className="bg-white rounded-[32px] p-12 shadow-xl shadow-gray-200/50 border-4 border-dashed border-gray-100 flex flex-col items-center text-center space-y-8"
              onDrop={(e) => { e.preventDefault(); const f = e.dataTransfer.files?.[0]; if (f) handleFileChange(f); }}
              onDragOver={(e) => e.preventDefault()}
            >
              <div className="w-24 h-24 bg-gray-50 rounded-full flex items-center justify-center">
                <Upload className="w-12 h-12 text-[#0D7377]" />
              </div>
              <div className="space-y-2">
                <h2 className="text-3xl font-bold">Upload Medical Document</h2>
                <p className="text-gray-500 max-w-md mx-auto">Drag and drop any prescription, scan, or photo. Accepts PDF, JPG, PNG, and TXT.</p>
              </div>
              <div className="w-full max-w-md relative">
                <input type="file" onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFileChange(f); }}
                  className="absolute inset-0 opacity-0 cursor-pointer z-10" accept=".pdf,.png,.jpg,.jpeg,.txt,.webp" />
                <div className="p-8 bg-gray-50 rounded-[24px] border-2 border-gray-200 flex items-center justify-center gap-4 hover:border-[#0D7377] transition-all">
                  {file ? (
                    <div className="flex items-center gap-4">
                      {filePreview
                        ? <img src={filePreview} alt="Preview" className="w-16 h-16 object-cover rounded-lg" />
                        : <FileText className="w-12 h-12 text-[#0D7377]" />}
                      <div className="text-left">
                        <p className="font-bold truncate max-w-[200px]">{file.name}</p>
                        <p className="text-sm text-gray-500">{(file.size / 1024).toFixed(1)} KB</p>
                      </div>
                      <button onClick={(e) => { e.stopPropagation(); reset(); }} className="ml-2 p-2 rounded-full hover:bg-gray-200 transition-colors z-20 relative">
                        <X className="w-5 h-5 text-gray-500" />
                      </button>
                    </div>
                  ) : (
                    <span className="font-bold text-gray-400">Click or drag file here</span>
                  )}
                </div>
              </div>
              {error && (
                <div className="w-full max-w-md bg-red-50 border border-red-200 rounded-2xl p-4 flex items-start gap-3">
                  <AlertCircle className="text-red-500 w-5 h-5 mt-0.5 shrink-0" />
                  <p className="text-red-700 text-sm font-medium">{error}</p>
                </div>
              )}
              {file && (
                <button onClick={analyzeDocument}
                  className="px-12 py-5 bg-[#0D7377] text-white rounded-full font-bold text-xl shadow-lg shadow-[#0D7377]/30 hover:scale-[1.05] active:scale-[0.95] transition-all">
                  Analyse Document
                </button>
              )}
            </section>
          )}

          {/* Loading */}
          {isAnalyzing && (
            <section className="bg-white rounded-[32px] p-20 shadow-xl shadow-gray-200/50 flex flex-col items-center justify-center space-y-8">
              <motion.div animate={{ scale: [1, 1.1, 1] }} transition={{ repeat: Infinity, duration: 2 }}
                className="w-32 h-32 bg-[#0D7377]/10 rounded-full flex items-center justify-center">
                <Loader2 className="w-16 h-16 text-[#0D7377] animate-spin" />
              </motion.div>
              <div className="text-center space-y-2">
                <AnimatePresence mode="wait">
                  <motion.h3 key={loadingStep} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }}
                    className="text-2xl font-bold text-[#0D7377]">{LOADING_STEPS[loadingStep]}</motion.h3>
                </AnimatePresence>
                <p className="text-gray-500">Powered by Gemini AI — this usually takes 10–20 seconds</p>
              </div>
              <div className="flex gap-2">
                {LOADING_STEPS.map((_, i) => (
                  <div key={i} className={`h-2 rounded-full transition-all duration-500 ${i <= loadingStep ? 'bg-[#0D7377] w-6' : 'bg-gray-200 w-2'}`} />
                ))}
              </div>
            </section>
          )}

          {/* Results */}
          {analysisResult && (
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="space-y-8">
              <div className="flex items-center justify-between">
                <h2 className="text-3xl font-bold">Analysis Results</h2>
                <button onClick={reset} className="flex items-center gap-2 text-[#0D7377] font-bold hover:underline">
                  <RefreshCw className="w-4 h-4" />Upload Another
                </button>
              </div>

              {/* Allergy Warning */}
              {analysisResult.allergyWarnings.length > 0 && (
                <motion.div initial={{ scale: 0.97 }} animate={{ scale: 1 }}
                  className="bg-red-50 border-2 border-red-300 rounded-3xl p-8 flex items-start gap-6">
                  <div className="w-14 h-14 bg-red-100 rounded-2xl flex items-center justify-center shrink-0">
                    <AlertTriangle className="text-red-600 w-8 h-8" />
                  </div>
                  <div className="space-y-2">
                    <h3 className="text-2xl font-bold text-red-800 uppercase tracking-tight">🚨 Allergy Warning</h3>
                    <ul className="list-disc list-inside text-red-700 space-y-1">
                      {analysisResult.allergyWarnings.map((w, i) => <li key={i} className="font-semibold">{w}</li>)}
                    </ul>
                  </div>
                </motion.div>
              )}

              {/* Interaction Warning */}
              {analysisResult.interactionWarnings.length > 0 && (
                <div className="bg-amber-50 border-2 border-amber-200 rounded-3xl p-8 flex items-start gap-6">
                  <div className="w-14 h-14 bg-amber-100 rounded-2xl flex items-center justify-center shrink-0">
                    <Pill className="text-amber-600 w-8 h-8" />
                  </div>
                  <div className="space-y-2">
                    <h3 className="text-2xl font-bold text-amber-800">Drug Interactions Found</h3>
                    <ul className="space-y-3">
                      {analysisResult.interactionWarnings.map((w, i) => (
                        <li key={i} className="flex items-start gap-3 text-amber-900 font-medium">
                          <div className="w-2 h-2 rounded-full bg-amber-600 mt-2 shrink-0" />{w}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              )}

              {/* Doc Type + Confidence */}
              <div className="flex items-center gap-4 flex-wrap">
                <span className="text-sm font-bold uppercase tracking-widest text-gray-400">Document Type</span>
                <span className="px-6 py-2 bg-gray-100 rounded-full font-bold text-[#0D7377] border border-gray-200">{analysisResult.docType}</span>
                <div className="flex items-center gap-2 px-3 py-1 bg-green-50 text-green-700 rounded-lg text-sm font-bold ml-auto">
                  <CheckCircle2 className="w-4 h-4" />{analysisResult.confidence}% Confidence
                </div>
              </div>

              {/* Summary */}
              <section className="bg-white rounded-[32px] p-10 shadow-xl shadow-gray-200/50 border border-gray-100 space-y-6">
                <h3 className="text-2xl font-bold flex items-center gap-3"><FileText className="text-[#0D7377]" />Plain Language Summary</h3>
                <p className="text-xl leading-relaxed text-gray-700 whitespace-pre-line">{analysisResult.summary}</p>
              </section>

              {/* Personalised */}
              <section className="bg-white rounded-[32px] p-10 shadow-xl shadow-gray-200/50 border-l-[12px] border-[#0D7377] space-y-6">
                <h3 className="text-2xl font-bold flex items-center gap-3"><User className="text-[#0D7377]" />What This Means For You</h3>
                <p className="text-xl leading-relaxed text-gray-700 italic whitespace-pre-line">"{analysisResult.personalizedMeaning}"</p>
              </section>

              {/* No warnings indicator */}
              {analysisResult.allergyWarnings.length === 0 && analysisResult.interactionWarnings.length === 0 && (
                <div className="bg-green-50 border border-green-200 rounded-3xl p-6 flex items-center gap-4">
                  <CheckCircle2 className="text-green-600 w-8 h-8 shrink-0" />
                  <div>
                    <p className="font-bold text-green-800">No allergy or interaction warnings detected</p>
                    <p className="text-green-700 text-sm">Based on your profile, no immediate conflicts were found. Always confirm with your doctor.</p>
                  </div>
                </div>
              )}

              {/* Technical Details */}
              <section className="bg-gray-50 rounded-[32px] overflow-hidden border border-gray-200">
                <button onClick={() => setShowTechnical(!showTechnical)}
                  className="w-full p-8 flex items-center justify-between hover:bg-gray-100 transition-colors">
                  <span className="text-xl font-bold text-gray-500">For Your Doctor (Technical Details)</span>
                  {showTechnical ? <ChevronUp /> : <ChevronDown />}
                </button>
                <AnimatePresence>
                  {showTechnical && (
                    <motion.div initial={{ height: 0 }} animate={{ height: 'auto' }} exit={{ height: 0 }} className="px-8 pb-8">
                      <div className="p-6 bg-white rounded-2xl border border-gray-200 font-mono text-sm text-gray-600 overflow-auto max-h-[400px] whitespace-pre-wrap">
                        {analysisResult.technicalDetails}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </section>

              <p className="text-center text-gray-400 text-sm">⚕️ For informational purposes only. Always consult your physician before making any medical decisions.</p>
            </motion.div>
          )}
        </div>
      </main>

      <footer className="max-w-7xl mx-auto px-6 py-12 border-t border-gray-100 text-center text-gray-400 text-sm font-medium">
        <p>© 2026 MediPlain Document Intelligence. For informational purposes only. Always consult your physician.</p>
      </footer>
    </div>
  );
}
