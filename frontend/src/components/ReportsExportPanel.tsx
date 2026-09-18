import React, { useState } from 'react';
import { Download, FileText, FileCode, Shield, FileSpreadsheet, Lock } from 'lucide-react';
import { apiService } from '../services/api';
import { MOCK_SAHYOG_PACKAGE } from '../services/mockData';

interface ReportsExportPanelProps {
  caseId: string;
  isLiveMode: boolean;
}

export const ReportsExportPanel: React.FC<ReportsExportPanelProps> = ({ caseId, isLiveMode }) => {
  const [downloadingPdf, setDownloadingPdf] = useState(false);
  const [downloadingJson, setDownloadingJson] = useState(false);
  const [downloadingSahyog, setDownloadingSahyog] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const handleDownloadPdf = async () => {
    setDownloadingPdf(true);
    setStatusMessage(null);
    try {
      if (isLiveMode && caseId) {
        const blob = await apiService.getCasePdfReport(caseId);
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `Specter_Report_${caseId}.pdf`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
        setStatusMessage('PDF Report downloaded successfully.');
      } else {
        setTimeout(() => {
          setStatusMessage('Demo Mode: PDF Report generation simulated for ' + caseId);
          setDownloadingPdf(false);
        }, 800);
        return;
      }
    } catch (e: any) {
      console.error(e);
      setStatusMessage('Failed to download PDF report: ' + (e.message || e));
    } finally {
      setDownloadingPdf(false);
    }
  };

  const handleDownloadJson = async () => {
    setDownloadingJson(true);
    setStatusMessage(null);
    try {
      let data: any;
      if (isLiveMode && caseId) {
        data = await apiService.getCaseExportJson(caseId);
      } else {
        data = MOCK_SAHYOG_PACKAGE;
      }
      const jsonStr = JSON.stringify(data, null, 2);
      const blob = new Blob([jsonStr], { type: 'application/json' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Specter_Export_${caseId}.json`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      setStatusMessage('JSON Export downloaded successfully.');
    } catch (e: any) {
      console.error(e);
      setStatusMessage('Failed to download JSON export: ' + (e.message || e));
    } finally {
      setDownloadingJson(false);
    }
  };

  const handleDownloadSahyogPackage = async () => {
    setDownloadingSahyog(true);
    setStatusMessage(null);
    try {
      let pkg: any;
      if (isLiveMode && caseId) {
        pkg = await apiService.getSahyogPackage(caseId);
      } else {
        pkg = MOCK_SAHYOG_PACKAGE;
      }
      const jsonStr = JSON.stringify(pkg, null, 2);
      const blob = new Blob([jsonStr], { type: 'application/json' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `SAHYOG_READY_PACKAGE_${caseId}.json`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      setStatusMessage('SAHYOG Export Package downloaded successfully.');
    } catch (e: any) {
      console.error(e);
      setStatusMessage('Failed to export SAHYOG Package: ' + (e.message || e));
    } finally {
      setDownloadingSahyog(false);
    }
  };

  return (
    <div className="space-y-6 mb-6 font-sans">
      {/* Download Action Strip */}
      <div className="bg-white border border-slate-200 rounded-lg p-6 shadow-xs">
        <div className="flex items-center justify-between border-b border-slate-100 pb-4 mb-6">
          <div>
            <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-900 font-sans">
              INVESTIGATION REPORT & FORENSIC EXPORTS
            </h2>
            <p className="text-xs text-slate-500 font-sans mt-0.5">
              Generate court-ready investigation reports, raw analytical datasets, and SAHYOG evidence packages.
            </p>
          </div>
          {statusMessage && (
            <div className="text-xs font-sans text-emerald-800 bg-emerald-50 border border-emerald-200 px-3 py-1 rounded-md font-semibold">
              {statusMessage}
            </div>
          )}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* PDF Report Option */}
          <div className="bg-slate-50/60 p-5 rounded-md border border-slate-200 flex flex-col justify-between space-y-4 font-sans">
            <div className="space-y-2">
              <div className="flex items-center space-x-2 text-[#3730A3] font-semibold text-xs uppercase font-sans">
                <FileText className="w-4 h-4" />
                <span>GENERATE INVESTIGATION REPORT</span>
              </div>
              <p className="text-xs text-slate-600 font-sans leading-relaxed">
                Complete investigation-ready report with target wallet details, VASP candidate breakdown, multi-hop path ledger, and verifiable evidence ledger.
              </p>
            </div>
            <button
              onClick={handleDownloadPdf}
              disabled={downloadingPdf}
              className="flex items-center justify-center space-x-2 w-full py-2.5 bg-[#3730A3] hover:bg-[#312E81] text-white font-semibold text-xs font-sans rounded-md transition-colors disabled:opacity-50 shadow-xs"
            >
              <Download className="w-3.5 h-3.5" />
              <span>{downloadingPdf ? 'GENERATING REPORT...' : 'GENERATE INVESTIGATION REPORT'}</span>
            </button>
          </div>

          {/* JSON Analytical Export Option */}
          <div className="bg-slate-50/60 p-5 rounded-md border border-slate-200 flex flex-col justify-between space-y-4 font-sans">
            <div className="space-y-2">
              <div className="flex items-center space-x-2 text-slate-800 font-semibold text-xs uppercase font-sans">
                <FileCode className="w-4 h-4 text-slate-600" />
                <span>EXPORT JSON</span>
              </div>
              <p className="text-xs text-slate-600 font-sans leading-relaxed">
                Structured JSON export containing complete trace paths, risk factors, and node role attributes.
              </p>
            </div>
            <button
              onClick={handleDownloadJson}
              disabled={downloadingJson}
              className="flex items-center justify-center space-x-2 w-full py-2.5 bg-slate-800 hover:bg-slate-900 text-white font-semibold text-xs rounded-md transition-colors disabled:opacity-50 font-sans shadow-xs"
            >
              <Download className="w-3.5 h-3.5" />
              <span>{downloadingJson ? 'EXPORTING JSON...' : 'EXPORT JSON'}</span>
            </button>
          </div>

          {/* CSV Datasets Option */}
          <div className="bg-slate-50/60 p-5 rounded-md border border-slate-200 flex flex-col justify-between space-y-4 font-sans">
            <div className="space-y-2">
              <div className="flex items-center space-x-2 text-slate-800 font-semibold text-xs uppercase font-sans">
                <FileSpreadsheet className="w-4 h-4 text-slate-600" />
                <span>EXPORT CSV</span>
              </div>
              <p className="text-xs text-slate-600 font-sans leading-relaxed">
                Tabular CSV data tables of all analyzed transactions, wallet sequences, and delta-t intervals.
              </p>
            </div>
            <button
              onClick={handleDownloadJson}
              className="flex items-center justify-center space-x-2 w-full py-2.5 bg-white hover:bg-slate-100 text-slate-800 border border-slate-200 font-semibold text-xs rounded-md transition-colors font-sans shadow-xs"
            >
              <Download className="w-3.5 h-3.5" />
              <span>EXPORT CSV</span>
            </button>
          </div>
        </div>
      </div>

      {/* SAHYOG-READY EXPORT PACKAGE CARD */}
      <div className="bg-white border border-[#3730A3] rounded-lg p-6 shadow-xs space-y-4 font-sans">
        {/* Banner Statement */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between bg-indigo-50/70 border border-indigo-200 p-4 rounded-md gap-2 font-sans">
          <div className="flex items-center space-x-3">
            <Shield className="w-5 h-5 text-[#3730A3] flex-shrink-0" />
            <div>
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-900 font-sans">
                SAHYOG INTEGRATION — DESIGNED FOR AUTHORISED API INTEGRATION
              </h3>
              <p className="text-xs text-slate-600 font-sans mt-0.5">
                Pre-formatted law enforcement evidence package compliant with SAHYOG schema specifications.
              </p>
            </div>
          </div>
          <span className="text-[10px] font-mono font-semibold bg-[#3730A3] text-white px-2.5 py-1 rounded-md self-start sm:self-auto">
            SAHYOG_READY_V1
          </span>
        </div>

        {/* Warning Notice */}
        <div className="flex items-start space-x-2.5 text-xs text-slate-700 bg-slate-50 p-3 rounded-md border border-slate-200 font-sans">
          <Lock className="w-4 h-4 text-slate-500 flex-shrink-0 mt-0.5" />
          <span className="font-sans text-xs font-semibold text-slate-800">
            CONFIDENTIAL LAW ENFORCEMENT EVIDENCE PACKAGE — AUTHORISED USE ONLY
          </span>
        </div>

        {/* Download SAHYOG Package CTA */}
        <div className="flex flex-col sm:flex-row items-center justify-between pt-2 gap-4 font-sans">
          <p className="text-xs text-slate-500 font-sans">
            Package includes verifiable cryptographic hashes, chain trace sequences, and attribution mappings.
          </p>

          <button
            onClick={handleDownloadSahyogPackage}
            disabled={downloadingSahyog}
            className="flex items-center space-x-2 px-5 py-2.5 bg-[#3730A3] hover:bg-[#312E81] text-white font-semibold font-sans text-xs rounded-md transition-colors shadow-xs flex-shrink-0 disabled:opacity-50"
          >
            <Download className="w-4 h-4" />
            <span>{downloadingSahyog ? 'PACKAGING...' : 'SAHYOG-READY PACKAGE'}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
