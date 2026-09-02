export type Job = { id: number; title: string; location: string; source: string; source_url: string; discovered_at: string; matched_signals: string[]; company: number }
export type Company = { id: number; name: string }
export type SearchProfile = { id: number; name: string; description: string; is_active: boolean; freshness_days: number }
export type SearchLocation = { id: number; search_profile: number; country: string; region: string; is_active: boolean }
export type SearchRole = { id: number; search_profile: number; name: string; weight: number; is_active: boolean }
export type SearchSignal = { id: number; search_profile: number; value: string; category: string; weight: number; is_active: boolean }
export type DiscoveryStatus = { task_id: string; status: string; result: { created?: number; updated?: number; queries?: number; provider_matches?: Record<string, number>; provider_errors?: Record<string, string> } | string | null }
export type ProspectResearch = { research_summary: string; demand_evidence: string; qantly_current_match: Array<{ name: string; category?: string; evidence?: string }>; customization_gap: string[]; source_urls: Array<{ url: string; title?: string; source_type: string }>; research_confidence: number; recommended_first_cta: string }
export type ProspectAssessment = { technical_fit: number; customization_opportunity: number; ease_of_entry: number; near_term_conversion: number; strategic_value: number; account_type: string; classification: string; reason: string; recommended_cta: string }
export type Prospect = { id: number; company: number; job_posting: number; fit_score: number; fit_reason: string; priority: string; status: string; research: ProspectResearch | null; assessment: ProspectAssessment | null }
export type OutreachEmail = { id: number; prospect: number; contact: number | null; subject: string; body: string; status: string; created_at?: string }

const csrf = () => document.cookie.split('; ').find((part) => part.startsWith('csrftoken='))?.split('=')[1] ?? ''
async function request<T>(path: string, init: RequestInit = {}) {
  const response = await fetch(path, { credentials: 'include', headers: { 'Content-Type': 'application/json', ...init.headers }, ...init })
  if (!response.ok) throw new Error((await response.json().catch(() => ({}))).detail ?? 'Request failed')
  return response.status === 204 ? undefined as T : response.json() as Promise<T>
}
const mutate = <T>(path: string, method: string, body?: object) => request<T>(path, { method, headers: { 'X-CSRFToken': csrf() }, body: body ? JSON.stringify(body) : undefined })

export const api = {
  currentUser: () => request<{ username: string }>('/api/prospecting/auth/user/'),
  async login(username: string, password: string) { await fetch('/api/prospecting/auth/csrf/', { credentials: 'include' }); return mutate<{ username: string }>('/api/prospecting/auth/login/', 'POST', { username, password }) },
  jobs: () => request<Job[]>('/api/prospecting/jobs/'), companies: () => request<Company[]>('/api/prospecting/companies/'),
  prospects: () => request<Prospect[]>('/api/prospecting/prospects/'),
  profiles: () => request<SearchProfile[]>('/api/prospecting/search-profiles/'), locations: () => request<SearchLocation[]>('/api/prospecting/search-locations/'),
  roles: () => request<SearchRole[]>('/api/prospecting/search-roles/'), signals: () => request<SearchSignal[]>('/api/prospecting/search-signals/'),
  createLocation: (data: Omit<SearchLocation, 'id'>) => mutate<SearchLocation>('/api/prospecting/search-locations/', 'POST', data),
  createRole: (data: Omit<SearchRole, 'id'>) => mutate<SearchRole>('/api/prospecting/search-roles/', 'POST', data),
  createSignal: (data: Omit<SearchSignal, 'id'>) => mutate<SearchSignal>('/api/prospecting/search-signals/', 'POST', data),
  deleteLocation: (id: number) => mutate<void>(`/api/prospecting/search-locations/${id}/`, 'DELETE'),
  deleteRole: (id: number) => mutate<void>(`/api/prospecting/search-roles/${id}/`, 'DELETE'),
  deleteSignal: (id: number) => mutate<void>(`/api/prospecting/search-signals/${id}/`, 'DELETE'),
  runDiscovery: (profileId: number) => mutate<{ task_id: string; profile: string }>(`/api/prospecting/search-profiles/${profileId}/run-discovery/`, 'POST'),
  discoveryStatus: (taskId: string) => request<DiscoveryStatus>(`/api/prospecting/discovery-status/${taskId}/`),
  researchProspect: (id: number, force = false) => mutate<{ research: number }>(`/api/prospecting/prospects/${id}/research/`, 'POST', { force }),
  assessProspect: (id: number, force = false) => mutate<{ assessment: number; classification: string }>(`/api/prospecting/prospects/${id}/assess/`, 'POST', { force }),
  generateOutreach: (id: number) => mutate<OutreachEmail>(`/api/prospecting/prospects/${id}/generate-outreach/`, 'POST'),
  outreach: () => request<OutreachEmail[]>('/api/prospecting/outreach/'),
  submitOutreach: (id: number) => mutate<OutreachEmail>(`/api/prospecting/outreach/${id}/submit-for-approval/`, 'POST'),
  approveOutreach: (id: number) => mutate<OutreachEmail>(`/api/prospecting/outreach/${id}/approve/`, 'POST'),
  rejectOutreach: (id: number) => mutate<OutreachEmail>(`/api/prospecting/outreach/${id}/reject/`, 'POST'),
  queueOutreach: (id: number) => mutate<{ outreach: number; task_id: string }>(`/api/prospecting/outreach/${id}/queue-send/`, 'POST'),
}
