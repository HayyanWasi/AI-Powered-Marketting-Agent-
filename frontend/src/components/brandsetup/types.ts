export interface BrandProfileData {
  companyName: string;
  industry: string;
  website: string;
  targetAudience: string;
  description: string;
  trackRecord: string;
  specializations: string[];
  toneMessage: string; // Natural language input message describing the brand tone & voice
  sampleMessage: string; // An example message or phrase showing the voice in action
  selectedTraits: string[];
  negativeGuardrails: string[];
}

export interface AIPersonaGuess {
  archetype: string;
  personaSummary: string;
  tonePillars: {
    name: string;
    percentage: number;
    color: string;
  }[];
  simulatedAgentGreeting: string;
  keyDifferentiators: string[];
  confidenceScore: number;
}
