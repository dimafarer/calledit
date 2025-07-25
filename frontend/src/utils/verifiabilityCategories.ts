/**
 * Verifiability Categories Utility
 * 
 * This module provides utilities for working with the 5 verifiability categories
 * used in the CalledIt prediction verification system.
 */

export const VERIFIABILITY_CATEGORIES = {
  AGENT_VERIFIABLE: 'agent_verifiable',
  CURRENT_TOOL_VERIFIABLE: 'current_tool_verifiable', 
  STRANDS_TOOL_VERIFIABLE: 'strands_tool_verifiable',
  API_TOOL_VERIFIABLE: 'api_tool_verifiable',
  HUMAN_VERIFIABLE_ONLY: 'human_verifiable_only'
} as const;

export type VerifiabilityCategory = typeof VERIFIABILITY_CATEGORIES[keyof typeof VERIFIABILITY_CATEGORIES];

export const CATEGORY_CONFIG = {
  [VERIFIABILITY_CATEGORIES.AGENT_VERIFIABLE]: {
    icon: '🧠',
    label: 'Agent Verifiable',
    color: '#155724',
    bgColor: '#d4edda',
    description: 'Can be verified using pure reasoning/knowledge without external tools'
  },
  [VERIFIABILITY_CATEGORIES.CURRENT_TOOL_VERIFIABLE]: {
    icon: '⏰',
    label: 'Time-Tool Verifiable',
    color: '#004085',
    bgColor: '#cce7ff',
    description: 'Can be verified using only the current_time tool'
  },
  [VERIFIABILITY_CATEGORIES.STRANDS_TOOL_VERIFIABLE]: {
    icon: '🔧',
    label: 'Strands-Tool Verifiable',
    color: '#721c24',
    bgColor: '#f8d7da',
    description: 'Requires Strands library tools (calculator, python_repl, etc.)'
  },
  [VERIFIABILITY_CATEGORIES.API_TOOL_VERIFIABLE]: {
    icon: '🌐',
    label: 'API Verifiable',
    color: '#856404',
    bgColor: '#fff3cd',
    description: 'Requires external API calls or custom MCP integrations'
  },
  [VERIFIABILITY_CATEGORIES.HUMAN_VERIFIABLE_ONLY]: {
    icon: '👤',
    label: 'Human Verifiable Only',
    color: '#6f42c1',
    bgColor: '#e2d9f3',
    description: 'Requires human observation, judgment, or subjective assessment'
  }
};

/**
 * Check if a string is a valid verifiability category
 */
export function isValidVerifiabilityCategory(category: string): category is VerifiabilityCategory {
  return Object.values(VERIFIABILITY_CATEGORIES).includes(category as VerifiabilityCategory);
}

/**
 * Get the configuration (icon, label, colors) for a verifiability category
 * Returns default config for invalid categories
 */
export function getVerifiabilityCategoryConfig(category: string) {
  if (!isValidVerifiabilityCategory(category)) {
    // Return default config for invalid categories
    return CATEGORY_CONFIG[VERIFIABILITY_CATEGORIES.HUMAN_VERIFIABLE_ONLY];
  }
  return CATEGORY_CONFIG[category];
}

/**
 * Validate a verifiability category and return validation result
 */
export function validateVerifiabilityCategory(category: string): {
  isValid: boolean;
  category: VerifiabilityCategory;
  error?: string;
} {
  if (!category) {
    return {
      isValid: false,
      category: VERIFIABILITY_CATEGORIES.HUMAN_VERIFIABLE_ONLY,
      error: 'Category is required'
    };
  }

  if (!isValidVerifiabilityCategory(category)) {
    return {
      isValid: false,
      category: VERIFIABILITY_CATEGORIES.HUMAN_VERIFIABLE_ONLY,
      error: `Invalid category: ${category}. Must be one of: ${Object.values(VERIFIABILITY_CATEGORIES).join(', ')}`
    };
  }

  return {
    isValid: true,
    category
  };
}

/**
 * Get example predictions for a given verifiability category
 */
export function getCategoryExamples(category: VerifiabilityCategory): string[] {
  const examples = {
    [VERIFIABILITY_CATEGORIES.AGENT_VERIFIABLE]: [
      'The sun will rise tomorrow morning',
      'Christmas 2025 falls on Thursday',
      '2 + 2 equals 4'
    ],
    [VERIFIABILITY_CATEGORIES.CURRENT_TOOL_VERIFIABLE]: [
      "It's currently past 11:00 PM",
      'Today is a weekday',
      "We're in January 2025"
    ],
    [VERIFIABILITY_CATEGORIES.STRANDS_TOOL_VERIFIABLE]: [
      'Calculate: 15% compound interest on $1000 over 5 years will exceed $2000',
      'The square root of 144 is 12',
      "Parse this JSON: {'key': 'value'}"
    ],
    [VERIFIABILITY_CATEGORIES.API_TOOL_VERIFIABLE]: [
      'Bitcoin will hit $100k tomorrow',
      'It will be sunny in New York tomorrow',
      'Apple stock will close above $200 today'
    ],
    [VERIFIABILITY_CATEGORIES.HUMAN_VERIFIABLE_ONLY]: [
      'I will feel happy when I wake up tomorrow',
      'This movie will be entertaining',
      'The meeting will go well'
    ]
  };

  return examples[category] || [];
}