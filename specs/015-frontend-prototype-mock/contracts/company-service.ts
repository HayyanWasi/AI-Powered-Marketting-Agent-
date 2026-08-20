// Company Service Interface
// Contract that mock AND future API implementations must satisfy.

export interface CompanyProfile {
  id: string
  companyName: string
  industry: string
  brandDescription: string
  brandVoice: string
  createdAt: Date
  updatedAt: Date
}

export interface CompanyService {
  getProfile(): Promise<CompanyProfile | null>
  createProfile(
    data: Omit<CompanyProfile, 'id' | 'createdAt' | 'updatedAt'>
  ): Promise<CompanyProfile>
  updateProfile(data: Partial<CompanyProfile>): Promise<CompanyProfile>
  deleteProfile(): Promise<void>
}
