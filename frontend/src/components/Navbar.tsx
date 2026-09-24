import React from 'react';
import { ShieldCheck, FileText, Network, Database, Compass } from 'lucide-react';

interface NavbarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  caseId: string;
  isLiveMode: boolean;
  healthStatus?: string;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  setActiveTab,
  caseId,
  isLiveMode,
  healthStatus = 'online',
}) => {
  const tabs = [
    { id: 'investigation', label: 'Investigation', icon: Compass },
    { id: 'fundflow', label: 'Fund Flow', icon: Network },
    { id: 'intelligence', label: 'Intelligence', icon: ShieldCheck },
    { id: 'evidence', label: 'Evidence', icon: Database },
    { id: 'reports', label: 'Reports', icon: FileText },
  ];

  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-30 font-sans">
      <div className="max-w-[1440px] mx-auto px-6 h-14 flex items-center justify-between">

        {/* Left: Branding & Status */}
        <div className="flex items-center space-x-6">
          <div className="flex items-center space-x-2.5">
            <div className="w-6 h-6 rounded bg-[#3730A3] flex items-center justify-center text-white font-bold text-xs">
              S
            </div>

            <span className="font-semibold text-slate-900 tracking-tight text-sm font-sans">
              SPECTER
            </span>
          </div>

          <div className="h-4 w-px bg-slate-200" />

          {/* Live Mode Indicator */}
          <div className="flex items-center bg-slate-100 px-3 py-1 rounded border border-slate-200 text-xs">
            <span
              className={`w-1.5 h-1.5 rounded-full mr-1.5 ${
                isLiveMode ? 'bg-emerald-600' : 'bg-slate-400'
              }`}
            />

            <span className="font-medium text-slate-700">
              Live Mode
            </span>
          </div>
        </div>

        {/* Center: Navigation Tabs */}
        <nav className="flex items-center space-x-1">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;

            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-md text-xs font-medium transition-colors duration-150 ${
                  isActive
                    ? 'bg-[#3730A3]/10 text-[#3730A3] font-semibold'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                }`}
              >
                <Icon
                  className={`w-3.5 h-3.5 ${
                    isActive ? 'text-[#3730A3]' : 'text-slate-400'
                  }`}
                />

                <span>{tab.label}</span>
              </button>
            );
          })}
        </nav>

        {/* Right: Case ID & Health Indicator */}
        <div className="flex items-center space-x-3 text-xs">
          {caseId && (
            <div className="px-2.5 py-1 bg-slate-50 border border-slate-200 rounded text-slate-600">
              <span className="text-slate-400 font-sans">
                Case ID:{' '}
              </span>

              <span className="font-mono font-medium text-slate-800">
                {caseId}
              </span>
            </div>
          )}

          <div className="flex items-center space-x-1.5 text-slate-600 px-2 py-1">
            <span
              className={`w-2 h-2 rounded-full ${
                healthStatus === 'online'
                  ? 'bg-emerald-600'
                  : 'bg-amber-500'
              }`}
            />

            <span className="font-mono text-[11px] text-slate-500 uppercase tracking-tight">
              {healthStatus}
            </span>
          </div>
        </div>

      </div>
    </header>
  );
};