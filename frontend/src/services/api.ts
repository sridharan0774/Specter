import type {
  InvestigationStartRequest,
  InvestigationJobResponse,
  FindingSchema,
  EvidenceGraphItemSchema,
  InvestigationSummarySchema,
  FullInvestigationDataset,
  SahyogPackage,
  SahyogRequestResponse,
  SahyogValidationResult,
  SahyogStatusContractResponse,
  CaseRead,
} from '../types/api';


const API_BASE = '/api/v1';

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let errorMsg = `HTTP Error ${response.status}: ${response.statusText}`;
    try {
      const errData = await response.json();
      if (errData.detail) {
        errorMsg = typeof errData.detail === 'string' ? errData.detail : JSON.stringify(errData.detail);
      }
    } catch {
      // Ignore JSON parse error
    }
    throw new Error(errorMsg);
  }
  return response.json();
}

export const apiService = {
  async checkHealth(): Promise<Record<string, any>> {
    try {
      const res = await fetch(`${API_BASE}/health`);
      return handleResponse(res);
    } catch (err) {
      return { status: 'offline', detail: String(err) };
    }
  },

  async getHealth(): Promise<Record<string, any>> {
    return this.checkHealth();
  },

  async listCases(): Promise<CaseRead[]> {
    const res = await fetch(`${API_BASE}/cases`);
    return handleResponse(res);
  },

  async createCase(data: {
    target_wallet: string;
    chain: string;
    asset: string;
    investigator_id?: string;
    description?: string;
  }): Promise<CaseRead> {
    const res = await fetch(`${API_BASE}/cases`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        investigator_id: data.investigator_id || 'INV-AGENT-001',
        reported_wallet: data.target_wallet,
        chain: data.chain,
        asset: data.asset,
        description: data.description,
      }),
    });
    return handleResponse(res);
  },

  async startInvestigation(
    caseId: string,
    request: InvestigationStartRequest
  ): Promise<InvestigationJobResponse> {
    const res = await fetch(`${API_BASE}/cases/${caseId}/investigate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });
    return handleResponse(res);
  },

  async getJobStatus(caseId: string): Promise<InvestigationJobResponse> {
    const res = await fetch(`${API_BASE}/cases/${caseId}/investigation`);
    return handleResponse(res);
  },

  async pollJobUntilComplete(
    caseId: string,
    onProgress?: (job: InvestigationJobResponse) => void
  ): Promise<InvestigationJobResponse> {
    const maxAttempts = 60;
    let attempts = 0;

    while (attempts < maxAttempts) {
      attempts++;
      try {
        const status = await this.getJobStatus(caseId);
        if (onProgress) onProgress(status);

        if (status.status === 'COMPLETED' || status.status === 'FAILED' || status.status === 'PARTIAL') {
          return status;
        }
      } catch (e) {
        console.warn(`Polling attempt ${attempts} failed`, e);
      }

      await new Promise((r) => setTimeout(r, 1000));
    }

    throw new Error('Investigation polling timed out after 60s');
  },

  async getFindings(caseId: string): Promise<FindingSchema[]> {
    const res = await fetch(`${API_BASE}/cases/${caseId}/findings`);
    return handleResponse(res);
  },

  async getEvidence(caseId: string): Promise<EvidenceGraphItemSchema[]> {
    const res = await fetch(`${API_BASE}/cases/${caseId}/evidence`);
    return handleResponse(res);
  },

  async getSummary(caseId: string): Promise<InvestigationSummarySchema> {
    const res = await fetch(`${API_BASE}/cases/${caseId}/summary`);
    return handleResponse(res);
  },

  async getFullDataset(caseId: string): Promise<FullInvestigationDataset> {
    try {
      const res = await fetch(`${API_BASE}/cases/${caseId}/dataset`);
      if (res.ok) return await res.json();
    } catch {
      // fallback to export/json
    }
    const res = await fetch(`${API_BASE}/cases/${caseId}/export/json`);
    return handleResponse(res);
  },

  async getFullInvestigationDataset(caseId: string): Promise<FullInvestigationDataset> {
    return this.getFullDataset(caseId);
  },

  async getSahyogPackage(caseId: string): Promise<SahyogPackage> {
    const res = await fetch(`${API_BASE}/cases/${caseId}/sahyog-package`);
    return handleResponse(res);
  },

  async prepareSahyogDisclosureRequest(
    caseId: string,
    investigatorId?: string,
    reason?: string
  ): Promise<SahyogRequestResponse> {
    const res = await fetch(`${API_BASE}/cases/${caseId}/sahyog/disclosure-request`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ investigator_id: investigatorId, reason_for_request: reason }),
    });
    return handleResponse(res);
  },

  async prepareSahyogFreezeRequest(
    caseId: string,
    investigatorId?: string,
    reason?: string,
    urgencyLevel?: string
  ): Promise<SahyogRequestResponse> {
    const res = await fetch(`${API_BASE}/cases/${caseId}/sahyog/freeze-request`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ investigator_id: investigatorId, reason_for_request: reason, urgency_level: urgencyLevel }),
    });
    return handleResponse(res);
  },

  async validateSahyogPackage(caseId: string, packageData?: any): Promise<SahyogValidationResult> {
    const res = await fetch(`${API_BASE}/cases/${caseId}/sahyog/validate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: packageData ? JSON.stringify(packageData) : undefined,
    });
    return handleResponse(res);
  },

  async getSahyogStatus(caseId: string): Promise<SahyogStatusContractResponse> {
    const res = await fetch(`${API_BASE}/cases/${caseId}/sahyog/status`);
    return handleResponse(res);
  },

  async listSahyogRequests(caseId: string): Promise<SahyogRequestResponse[]> {
    const res = await fetch(`${API_BASE}/cases/${caseId}/sahyog/requests`);
    return handleResponse(res);
  },

  async getCaseExportJson(caseId: string): Promise<any> {
    const res = await fetch(`${API_BASE}/cases/${caseId}/export/json`);
    return handleResponse(res);
  },

  async getCasePdfReport(caseId: string): Promise<Blob> {
    const res = await fetch(`${API_BASE}/cases/${caseId}/report`);
    if (!res.ok) throw new Error(`HTTP Error ${res.status}: Failed to generate PDF`);
    return res.blob();
  },

  getPdfReportDownloadUrl(caseId: string): string {
    return `${API_BASE}/cases/${caseId}/report`;
  },

  getJsonExportDownloadUrl(caseId: string): string {
    return `${API_BASE}/cases/${caseId}/export/json`;
  },
};