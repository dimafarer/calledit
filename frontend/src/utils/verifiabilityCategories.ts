/**
 * Verifiability Categories Utility
 * 
 * This module provides utilities for working with the 3 verifiability categories
 * used in the CalledIt prediction verification system.
 * 
 * Categories:
 * - auto_verifiable: Agent can verify NOW with current tools + reasoning
 * - automatable: Could be verified with a tool that doesn't exist yet
 * - human_only: Requires subjective judgment, no tool can help
 */

export const VERIFIABILITY_CATEGORIES = {
  AUTO_VERIFIABLE: 'auto_verifiable',
  AUTOMATABLE: 'automatable',
  HUMAN_ONLY: 'human_only'
} as const;

export type VerifiabilityCategory = typeof VERIFIABILITY_CATEGORIES[keyof typeof VERIFIABILITY_CATEGORIES];

export const CATEGORY_CONFIG = {
  [VERIFIABILITY_CATEGORIES.AUTO_VERIFIABLE]: {
    icon: '🤖',
    label: 'Auto Verifiable',
    color: '#155724',
    bgColor: '#d4edda',
    description: 'Can be verified automatically using reasoning and current tools'
  },
  [VERIFIABILITY_CATEGORIES.AUTOMATABLE]: {
    icon: '🔧',
    label: 'Automatable',
    color: '#856404',
    bgColor: '#fff3cd',
    description: 'Could be automated with a tool that does not exist yet'
  },
  [VERIFIABILITY_CATEGORIES.HUMAN_ONLY]: {
    icon: '👤',
    label: 'Human Only',
    color: '#6f42c1',
    bgColor: '#e2d9f3',
    description: 'Requires human judgment or personal observation'
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
    return CATEGORY_CONFIG[VERIFIABILITY_CATEGORIES.HUMAN_ONLY];
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
      category: VERIFIABILITY_CATEGORIES.HUMAN_ONLY,
      error: 'Category is required'
    };
  }

  if (!isValidVerifiabilityCategory(category)) {
    return {
      isValid: false,
      category: VERIFIABILITY_CATEGORIES.HUMAN_ONLY,
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
    [VERIFIABILITY_CATEGORIES.AUTO_VERIFIABLE]: [
      'The sun will rise tomorrow morning',
      'Christmas 2025 falls on Thursday',
      '2 + 2 equals 4'
    ],
    [VERIFIABILITY_CATEGORIES.AUTOMATABLE]: [
      'Bitcoin will hit $100k tomorrow',
      'It will be sunny in New York tomorrow',
      'Apple stock will close above $200 today'
    ],
    [VERIFIABILITY_CATEGORIES.HUMAN_ONLY]: [
      'I will feel happy when I wake up tomorrow',
      'This movie will be entertaining',
      'The meeting will go well'
    ]
  };

  return examples[category] || [];
}
