import { describe, it, expect } from 'vitest';

// First, let's create the utility functions we're testing
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

export function isValidVerifiabilityCategory(category: string): category is VerifiabilityCategory {
  return Object.values(VERIFIABILITY_CATEGORIES).includes(category as VerifiabilityCategory);
}

export function getVerifiabilityCategoryConfig(category: string) {
  if (!isValidVerifiabilityCategory(category)) {
    // Return default config for invalid categories
    return CATEGORY_CONFIG[VERIFIABILITY_CATEGORIES.HUMAN_VERIFIABLE_ONLY];
  }
  return CATEGORY_CONFIG[category];
}

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

// Tests
describe('Verifiability Categories', () => {
  describe('Constants', () => {
    it('should have all 5 required categories', () => {
      const categories = Object.values(VERIFIABILITY_CATEGORIES);
      
      expect(categories).toHaveLength(5);
      expect(categories).toContain('agent_verifiable');
      expect(categories).toContain('current_tool_verifiable');
      expect(categories).toContain('strands_tool_verifiable');
      expect(categories).toContain('api_tool_verifiable');
      expect(categories).toContain('human_verifiable_only');
    });

    it('should have configuration for all categories', () => {
      Object.values(VERIFIABILITY_CATEGORIES).forEach(category => {
        expect(CATEGORY_CONFIG[category]).toBeDefined();
        expect(CATEGORY_CONFIG[category].icon).toBeTruthy();
        expect(CATEGORY_CONFIG[category].label).toBeTruthy();
        expect(CATEGORY_CONFIG[category].color).toBeTruthy();
        expect(CATEGORY_CONFIG[category].bgColor).toBeTruthy();
        expect(CATEGORY_CONFIG[category].description).toBeTruthy();
      });
    });

    it('should have unique icons for each category', () => {
      const icons = Object.values(CATEGORY_CONFIG).map(config => config.icon);
      const uniqueIcons = new Set(icons);
      
      expect(uniqueIcons.size).toBe(icons.length);
    });

    it('should have unique colors for each category', () => {
      const colors = Object.values(CATEGORY_CONFIG).map(config => config.color);
      const uniqueColors = new Set(colors);
      
      expect(uniqueColors.size).toBe(colors.length);
    });
  });

  describe('isValidVerifiabilityCategory', () => {
    it('should return true for valid categories', () => {
      Object.values(VERIFIABILITY_CATEGORIES).forEach(category => {
        expect(isValidVerifiabilityCategory(category)).toBe(true);
      });
    });

    it('should return false for invalid categories', () => {
      const invalidCategories = [
        'invalid_category',
        'agent_verifiable_wrong',
        'api_verifiable', // Missing _tool_
        '',
        'AGENT_VERIFIABLE', // Wrong case
        'human_verifiable' // Missing _only
      ];

      invalidCategories.forEach(category => {
        expect(isValidVerifiabilityCategory(category)).toBe(false);
      });
    });

    it('should handle edge cases', () => {
      expect(isValidVerifiabilityCategory(null as any)).toBe(false);
      expect(isValidVerifiabilityCategory(undefined as any)).toBe(false);
      expect(isValidVerifiabilityCategory(123 as any)).toBe(false);
      expect(isValidVerifiabilityCategory({} as any)).toBe(false);
    });
  });

  describe('getVerifiabilityCategoryConfig', () => {
    it('should return correct config for valid categories', () => {
      const config = getVerifiabilityCategoryConfig(VERIFIABILITY_CATEGORIES.AGENT_VERIFIABLE);
      
      expect(config.icon).toBe('🧠');
      expect(config.label).toBe('Agent Verifiable');
      expect(config.color).toBe('#155724');
      expect(config.bgColor).toBe('#d4edda');
    });

    it('should return default config for invalid categories', () => {
      const config = getVerifiabilityCategoryConfig('invalid_category');
      const defaultConfig = CATEGORY_CONFIG[VERIFIABILITY_CATEGORIES.HUMAN_VERIFIABLE_ONLY];
      
      expect(config).toEqual(defaultConfig);
    });

    it('should return correct config for all valid categories', () => {
      const expectedConfigs = {
        [VERIFIABILITY_CATEGORIES.AGENT_VERIFIABLE]: { icon: '🧠', label: 'Agent Verifiable' },
        [VERIFIABILITY_CATEGORIES.CURRENT_TOOL_VERIFIABLE]: { icon: '⏰', label: 'Time-Tool Verifiable' },
        [VERIFIABILITY_CATEGORIES.STRANDS_TOOL_VERIFIABLE]: { icon: '🔧', label: 'Strands-Tool Verifiable' },
        [VERIFIABILITY_CATEGORIES.API_TOOL_VERIFIABLE]: { icon: '🌐', label: 'API Verifiable' },
        [VERIFIABILITY_CATEGORIES.HUMAN_VERIFIABLE_ONLY]: { icon: '👤', label: 'Human Verifiable Only' }
      };

      Object.entries(expectedConfigs).forEach(([category, expected]) => {
        const config = getVerifiabilityCategoryConfig(category);
        expect(config.icon).toBe(expected.icon);
        expect(config.label).toBe(expected.label);
      });
    });
  });

  describe('validateVerifiabilityCategory', () => {
    it('should validate correct categories', () => {
      Object.values(VERIFIABILITY_CATEGORIES).forEach(category => {
        const result = validateVerifiabilityCategory(category);
        
        expect(result.isValid).toBe(true);
        expect(result.category).toBe(category);
        expect(result.error).toBeUndefined();
      });
    });

    it('should handle empty/null categories', () => {
      const emptyResults = [
        validateVerifiabilityCategory(''),
        validateVerifiabilityCategory(null as any),
        validateVerifiabilityCategory(undefined as any)
      ];

      emptyResults.forEach(result => {
        expect(result.isValid).toBe(false);
        expect(result.category).toBe(VERIFIABILITY_CATEGORIES.HUMAN_VERIFIABLE_ONLY);
        expect(result.error).toBe('Category is required');
      });
    });

    it('should handle invalid categories', () => {
      const result = validateVerifiabilityCategory('invalid_category');
      
      expect(result.isValid).toBe(false);
      expect(result.category).toBe(VERIFIABILITY_CATEGORIES.HUMAN_VERIFIABLE_ONLY);
      expect(result.error).toContain('Invalid category: invalid_category');
      expect(result.error).toContain('Must be one of:');
    });

    it('should provide helpful error messages', () => {
      const result = validateVerifiabilityCategory('agent_verifiable_wrong');
      
      expect(result.error).toContain('agent_verifiable');
      expect(result.error).toContain('current_tool_verifiable');
      expect(result.error).toContain('strands_tool_verifiable');
      expect(result.error).toContain('api_tool_verifiable');
      expect(result.error).toContain('human_verifiable_only');
    });
  });

  describe('getCategoryExamples', () => {
    it('should return examples for all categories', () => {
      Object.values(VERIFIABILITY_CATEGORIES).forEach(category => {
        const examples = getCategoryExamples(category);
        
        expect(Array.isArray(examples)).toBe(true);
        expect(examples.length).toBeGreaterThan(0);
        examples.forEach(example => {
          expect(typeof example).toBe('string');
          expect(example.length).toBeGreaterThan(0);
        });
      });
    });

    it('should return appropriate examples for each category', () => {
      // Agent verifiable should include logical/factual statements
      const agentExamples = getCategoryExamples(VERIFIABILITY_CATEGORIES.AGENT_VERIFIABLE);
      expect(agentExamples.some(ex => ex.includes('sun will rise'))).toBe(true);

      // Current tool verifiable should include time-based statements
      const timeExamples = getCategoryExamples(VERIFIABILITY_CATEGORIES.CURRENT_TOOL_VERIFIABLE);
      expect(timeExamples.some(ex => ex.includes('currently') || ex.includes('today'))).toBe(true);

      // Strands tool verifiable should include calculations
      const strandsExamples = getCategoryExamples(VERIFIABILITY_CATEGORIES.STRANDS_TOOL_VERIFIABLE);
      expect(strandsExamples.some(ex => ex.includes('Calculate') || ex.includes('square root'))).toBe(true);

      // API tool verifiable should include external data requirements
      const apiExamples = getCategoryExamples(VERIFIABILITY_CATEGORIES.API_TOOL_VERIFIABLE);
      expect(apiExamples.some(ex => ex.includes('Bitcoin') || ex.includes('weather') || ex.includes('stock'))).toBe(true);

      // Human verifiable should include subjective statements
      const humanExamples = getCategoryExamples(VERIFIABILITY_CATEGORIES.HUMAN_VERIFIABLE_ONLY);
      expect(humanExamples.some(ex => ex.includes('feel') || ex.includes('entertaining'))).toBe(true);
    });

    it('should return empty array for invalid categories', () => {
      const examples = getCategoryExamples('invalid_category' as any);
      expect(examples).toEqual([]);
    });

    it('should have unique examples across categories', () => {
      const allExamples = Object.values(VERIFIABILITY_CATEGORIES)
        .flatMap(category => getCategoryExamples(category));
      
      const uniqueExamples = new Set(allExamples);
      expect(uniqueExamples.size).toBe(allExamples.length);
    });
  });

  describe('Integration', () => {
    it('should work together for complete category validation flow', () => {
      const testCategory = VERIFIABILITY_CATEGORIES.API_TOOL_VERIFIABLE;
      
      // Validate category
      const validation = validateVerifiabilityCategory(testCategory);
      expect(validation.isValid).toBe(true);
      
      // Get configuration
      const config = getVerifiabilityCategoryConfig(validation.category);
      expect(config.icon).toBe('🌐');
      expect(config.label).toBe('API Verifiable');
      
      // Get examples
      const examples = getCategoryExamples(validation.category);
      expect(examples.length).toBeGreaterThan(0);
    });

    it('should handle invalid category gracefully through entire flow', () => {
      const invalidCategory = 'invalid_category';
      
      // Validate category (should fail)
      const validation = validateVerifiabilityCategory(invalidCategory);
      expect(validation.isValid).toBe(false);
      
      // Get configuration (should return default)
      const config = getVerifiabilityCategoryConfig(invalidCategory);
      expect(config.icon).toBe('👤'); // Human verifiable icon
      
      // Use fallback category for examples
      const examples = getCategoryExamples(validation.category);
      expect(examples.length).toBeGreaterThan(0);
    });
  });
});