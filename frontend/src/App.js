import React, { useState, useCallback } from 'react';
import './App.css';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import axios from 'axios';
import { Button } from './components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './components/ui/card';
import { Badge } from './components/ui/badge';
import { Alert, AlertDescription } from './components/ui/alert';
import { Progress } from './components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './components/ui/tabs';
import { Separator } from './components/ui/separator';
import { toast } from 'sonner';
import { Toaster } from './components/ui/sonner';
import { 
  Upload, 
  FileText, 
  AlertTriangle, 
  CheckCircle, 
  XCircle, 
  Shield, 
  Brain,
  TrendingUp,
  AlertCircle,
  Download,
  Clock,
  Scale
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const getRiskColor = (level) => {
  switch (level) {
    case 'low': return 'bg-emerald-100 text-emerald-800 border-emerald-200';
    case 'medium': return 'bg-amber-100 text-amber-800 border-amber-200';
    case 'high': return 'bg-red-100 text-red-800 border-red-200';
    default: return 'bg-gray-100 text-gray-800 border-gray-200';
  }
};

const getRiskIcon = (level) => {
  switch (level) {
    case 'low': return <CheckCircle className="w-4 h-4" />;
    case 'medium': return <AlertTriangle className="w-4 h-4" />;
    case 'high': return <XCircle className="w-4 h-4" />;
    default: return <AlertCircle className="w-4 h-4" />;
  }
};

const DocumentUpload = ({ onAnalysisComplete }) => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);

  const handleDrag = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setSelectedFile(e.dataTransfer.files[0]);
    }
  }, []);

  const handleFileSelect = (e) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      toast.error('Please select a document to analyze');
      return;
    }

    setUploading(true);
    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const response = await axios.post(`${API}/analyze-document`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      toast.success('Document analyzed successfully!');
      onAnalysisComplete(response.data);
      setSelectedFile(null);
    } catch (error) {
      console.error('Analysis error:', error);
      toast.error(error.response?.data?.detail || 'Failed to analyze document');
    } finally {
      setUploading(false);
    }
  };

  return (
    <Card className="w-full max-w-2xl mx-auto">
      <CardHeader className="text-center">
        <CardTitle className="flex items-center justify-center gap-2 text-2xl">
          <Scale className="w-6 h-6 text-slate-700" />
          AI Legal Document Assistant
        </CardTitle>
        <CardDescription className="text-base">
          Upload your legal document for comprehensive risk analysis and plain-language explanations
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div
          className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
            dragActive
              ? 'border-slate-400 bg-slate-50'
              : 'border-slate-300 hover:border-slate-400'
          }`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
        >
          <Upload className="w-12 h-12 mx-auto mb-4 text-slate-400" />
          <div className="space-y-2">
            <p className="text-lg font-medium text-slate-700">
              Drop your document here or click to browse
            </p>
            <p className="text-sm text-slate-500">
              Supports PDF and TXT files up to 10MB
            </p>
          </div>
          <input
            type="file"
            accept=".pdf,.txt"
            onChange={handleFileSelect}
            className="hidden"
            id="file-upload"
          />
          <label
            htmlFor="file-upload"
            className="mt-4 inline-flex items-center px-4 py-2 bg-slate-700 text-white rounded-lg hover:bg-slate-800 transition-colors cursor-pointer"
          >
            <FileText className="w-4 h-4 mr-2" />
            Choose File
          </label>
        </div>

        {selectedFile && (
          <div className="flex items-center justify-between p-4 bg-slate-50 rounded-lg">
            <div className="flex items-center gap-3">
              <FileText className="w-5 h-5 text-slate-600" />
              <div>
                <p className="font-medium text-slate-800">{selectedFile.name}</p>
                <p className="text-sm text-slate-500">
                  {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                </p>
              </div>
            </div>
            <Button
              onClick={() => setSelectedFile(null)}
              variant="ghost"
              size="sm"
              className="text-slate-500 hover:text-slate-700"
            >
              Remove
            </Button>
          </div>
        )}

        <Button
          onClick={handleUpload}
          disabled={!selectedFile || uploading}
          className="w-full bg-slate-700 hover:bg-slate-800 text-white py-3"
          size="lg"
        >
          {uploading ? (
            <>
              <Brain className="w-5 h-5 mr-2 animate-pulse" />
              Analyzing Document...
            </>
          ) : (
            <>
              <Brain className="w-5 h-5 mr-2" />
              Analyze Document
            </>
          )}
        </Button>
      </CardContent>
    </Card>
  );
};

const AnalysisResults = ({ analysis }) => {
  if (!analysis) return null;

  const highRiskClauses = analysis.clauses.filter(c => c.risk_level === 'high');
  const mediumRiskClauses = analysis.clauses.filter(c => c.risk_level === 'medium');
  const lowRiskClauses = analysis.clauses.filter(c => c.risk_level === 'low');

  return (
    <div className="w-full max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-2xl flex items-center gap-2">
                <Shield className="w-6 h-6" />
                Risk Analysis Report
              </CardTitle>
              <CardDescription className="text-base mt-2">
                {analysis.filename} • {analysis.document_type}
              </CardDescription>
            </div>
            <div className="text-right">
              <div className="text-3xl font-bold text-slate-800">
                {analysis.overall_risk_score}/10
              </div>
              <div className="text-sm text-slate-500">Overall Risk Score</div>
            </div>
          </div>
        </CardHeader>
      </Card>

      {/* Risk Overview */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="border-red-200 bg-red-50">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-red-800">High Risk</p>
                <p className="text-2xl font-bold text-red-900">{highRiskClauses.length}</p>
              </div>
              <XCircle className="w-8 h-8 text-red-600" />
            </div>
          </CardContent>
        </Card>
        
        <Card className="border-amber-200 bg-amber-50">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-amber-800">Medium Risk</p>
                <p className="text-2xl font-bold text-amber-900">{mediumRiskClauses.length}</p>
              </div>
              <AlertTriangle className="w-8 h-8 text-amber-600" />
            </div>
          </CardContent>
        </Card>

        <Card className="border-emerald-200 bg-emerald-50">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-emerald-800">Low Risk</p>
                <p className="text-2xl font-bold text-emerald-900">{lowRiskClauses.length}</p>
              </div>
              <CheckCircle className="w-8 h-8 text-emerald-600" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Detailed Analysis */}
      <Tabs defaultValue="clauses" className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="clauses">Risk Meter Table</TabsTrigger>
          <TabsTrigger value="summary">Plain-Language Summary</TabsTrigger>
          <TabsTrigger value="recommendations">Recommendations</TabsTrigger>
        </TabsList>

        <TabsContent value="clauses" className="space-y-4 mt-6">
          <Card>
            <CardHeader>
              <CardTitle>Clause Risk Analysis</CardTitle>
              <CardDescription>
                Detailed breakdown of risky clauses found in your document
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {analysis.clauses.map((clause, index) => (
                <div key={clause.id} className="border rounded-lg p-4 space-y-3">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <Badge className={getRiskColor(clause.risk_level)}>
                          {getRiskIcon(clause.risk_level)}
                          {clause.risk_level.toUpperCase()} RISK
                        </Badge>
                        <Badge variant="outline">Score: {clause.risk_score}/10</Badge>
                        {clause.section && (
                          <Badge variant="secondary">{clause.section}</Badge>
                        )}
                      </div>
                      <p className="text-sm text-slate-600 bg-slate-50 p-3 rounded border-l-4 border-slate-300 mb-3">
                        "{clause.clause_text}"
                      </p>
                      <div className="bg-blue-50 p-3 rounded-lg border-l-4 border-blue-400">
                        <p className="text-sm text-blue-900 font-medium mb-1">Why this is risky:</p>
                        <p className="text-sm text-blue-800">{clause.explanation}</p>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="summary" className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle>Document Summary</CardTitle>
              <CardDescription>
                Plain-language explanation of your legal document
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="prose prose-slate max-w-none">
                <div className="bg-slate-50 p-6 rounded-lg border-l-4 border-slate-400">
                  <p className="text-slate-800 leading-relaxed whitespace-pre-line">
                    {analysis.summary}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="recommendations" className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle>Actionable Recommendations</CardTitle>
              <CardDescription>
                Steps you can take to reduce your legal risks
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {analysis.recommendations.map((recommendation, index) => (
                  <div key={index} className="flex items-start gap-3 p-4 bg-green-50 rounded-lg border-l-4 border-green-400">
                    <TrendingUp className="w-5 h-5 text-green-600 mt-0.5 flex-shrink-0" />
                    <p className="text-green-800 font-medium">{recommendation}</p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

const Home = () => {
  const [currentAnalysis, setCurrentAnalysis] = useState(null);
  const [showResults, setShowResults] = useState(false);

  const handleAnalysisComplete = (analysis) => {
    setCurrentAnalysis(analysis);
    setShowResults(true);
  };

  const handleNewAnalysis = () => {
    setCurrentAnalysis(null);
    setShowResults(false);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      <div className="container mx-auto px-4 py-8">
        {!showResults ? (
          <div className="space-y-8">
            <div className="text-center max-w-4xl mx-auto mb-12">
              <h1 className="text-4xl font-bold text-slate-800 mb-4">
                AI Legal Document Assistant
              </h1>
              <p className="text-xl text-slate-600 leading-relaxed">
                Get instant risk analysis, plain-language explanations, and actionable recommendations 
                for your legal documents. No legal expertise required.
              </p>
            </div>
            <DocumentUpload onAnalysisComplete={handleAnalysisComplete} />
            
            {/* Features */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-16 max-w-4xl mx-auto">
              <Card className="text-center">
                <CardContent className="pt-6">
                  <Brain className="w-12 h-12 mx-auto mb-4 text-slate-600" />
                  <h3 className="text-lg font-semibold mb-2">AI-Powered Analysis</h3>
                  <p className="text-sm text-slate-600">
                    Advanced AI identifies risky clauses and assigns risk scores from 1-10
                  </p>
                </CardContent>
              </Card>
              
              <Card className="text-center">
                <CardContent className="pt-6">
                  <FileText className="w-12 h-12 mx-auto mb-4 text-slate-600" />
                  <h3 className="text-lg font-semibold mb-2">Plain Language</h3>
                  <p className="text-sm text-slate-600">
                    Complex legal jargon translated into clear, understandable explanations
                  </p>
                </CardContent>
              </Card>
              
              <Card className="text-center">
                <CardContent className="pt-6">
                  <TrendingUp className="w-12 h-12 mx-auto mb-4 text-slate-600" />
                  <h3 className="text-lg font-semibold mb-2">Actionable Advice</h3>
                  <p className="text-sm text-slate-600">
                    Get specific recommendations to negotiate better terms and reduce risks
                  </p>
                </CardContent>
              </Card>
            </div>
          </div>
        ) : (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <Button
                onClick={handleNewAnalysis}
                variant="outline"
                className="flex items-center gap-2"
              >
                <Upload className="w-4 h-4" />
                Analyze New Document
              </Button>
            </div>
            <AnalysisResults analysis={currentAnalysis} />
          </div>
        )}
      </div>
      <Toaster position="top-right" />
    </div>
  );
};

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Home />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;