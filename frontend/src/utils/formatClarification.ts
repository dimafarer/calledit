/**
 * Format Q&A pairs into a human-readable clarification string.
 *
 * This is what agents read when the user clarifies a prediction. The backend
 * appends it to the prompt as-is — agents see natural language, not JSON.
 *
 * Example output:
 *   Q: What city are you in?
 *   A: San Francisco
 *
 *   Q: Do you mean Eastern or Pacific time?
 *   A: Pacific
 *
 * WHY A STRING, NOT STRUCTURED DATA:
 * The backend's build_clarify_state puts user_input into the user_clarifications
 * list, which gets appended to the agent prompt verbatim. Agents reason about
 * natural language — a formatted Q&A string is exactly what they need to
 * understand the user's refinement intent.
 *
 * @param questions - The ReviewAgent's questions for the section
 * @param answers - The user's answers (may be empty strings for unanswered questions)
 * @returns Formatted clarification string with Q&A pairs separated by blank lines
 */
export function formatClarification(questions: string[], answers: string[]): string {
  return questions.map((q, i) => {
    const answer = i < answers.length ? answers[i] : '';
    const answerText = answer.trim() ? answer : '(no answer)';
    return `Q: ${q}\nA: ${answerText}`;
  }).join('\n\n');
}
