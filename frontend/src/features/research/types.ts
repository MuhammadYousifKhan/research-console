export type Reliability = 'unknown' | 'low' | 'medium' | 'high'
export type Confidence = 'low' | 'medium' | 'high'
export type StepStatus = 'completed' | 'failed'

export type ResearchTask = {
  id: number
  description: string
  tool: 'search_web' | 'scrape_page' | 'search_arxiv' | 'search_scholar'
  input: string
  priority: 'low' | 'medium' | 'high'
}

export type ExecutionStep = {
  name: string
  status: StepStatus
  detail: string
}

export type Source = {
  citation_id: number | null
  title: string
  url: string
  snippet: string
  reliability: Reliability
  source_type: string
  authors: string[]
  year: number | null
}

export type Observation = {
  task_id: number
  task: string
  tool: string
  result: string
  sources: Source[]
  metadata: Record<string, unknown>
}

export type Evaluation = {
  is_supported: boolean
  confidence: Confidence
  missing_evidence: string[]
  notes: string
}

export type ResearchRun = {
  research_id: number | null
  query: string
  plan: ResearchTask[]
  steps: ExecutionStep[]
  sources: Source[]
  observations: Observation[]
  answer: string
  evaluation: Evaluation
}

export type ResearchHistoryItem = {
  research_id: number
  query: string
  created_at: string
}

export type ResearchHistoryResponse = {
  items: ResearchHistoryItem[]
}

export type CreateResearchRequest = {
  query: string
  max_tasks: number
}

export type CitationStyle = 'apa' | 'mla' | 'ieee' | 'harvard' | 'chicago' | 'bibtex'

export type CitationItem = {
  citation_id: number | null
  title: string
  url: string
  text: string
}

export type CitationsResponse = {
  research_id: number
  accessed: string
  styles: Record<CitationStyle, CitationItem[]>
}
