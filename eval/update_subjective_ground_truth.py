"""Update golden dataset v3.1: subjective test case ground truth for two-track approach."""
import json

UPDATES = {
    "base-027": {
        "expected_verification_criteria": [
            "User self-reports a positive experience after watching the movie tonight, answering 'yes' to: 'Did you enjoy the movie?' prompted within 30 minutes of the movie ending"
        ],
        "expected_verification_method": "Schedule a self-report prompt for approximately 30 minutes after the estimated movie end time. Ask: 'You predicted you would enjoy the movie. Did you enjoy it? (yes/no)'. Enjoyment is a subjective internal state — only the viewer can assess it."
    },
    "base-028": {
        "expected_verification_criteria": [
            "The team meeting at 2pm tomorrow results in at least one concrete decision or action item, no unresolved conflicts requiring follow-up, and the user assesses it as productive (assuming 'go well' means productive outcomes — ReviewAgent should validate what 'well' means to this user)"
        ],
        "expected_verification_method": "Prompt the user after the meeting (approximately 3pm tomorrow) to report: (1) were concrete decisions or action items produced? (2) were there unresolved conflicts? (3) overall, did it feel productive? Combines observable meeting outcomes with participant assessment."
    },
    "base-030": {
        "expected_verification_criteria": [
            "User self-reports feeling happy upon waking tomorrow morning, answering 'yes' to: 'Are you feeling happy this morning?' prompted at approximately 8am"
        ],
        "expected_verification_method": "Schedule a self-report prompt for tomorrow at 8am. Ask: 'You predicted you would feel happy when you woke up. Are you feeling happy? (yes/no)'. Happiness is a subjective internal state — no external measurement applies."
    },
    "base-032": {
        "expected_verification_criteria": [
            "The user reports that their daughter expressed clear positive reaction (joy, excitement, or enthusiastic gratitude) upon receiving the birthday present, answering 'yes' to: 'Did your daughter love the present?'"
        ],
        "expected_verification_method": "Prompt the user the day after the birthday to report the daughter's reaction. Ask: 'Did your daughter love the birthday present? (yes/no)'. This requires the user's observation and interpretation of another person's emotional response — no tool can assess this."
    },
    "base-034": {
        "expected_verification_criteria": [
            "User self-reports that the dinner tasted good after eating, answering 'yes' to: 'Did the dinner taste good?' prompted after the meal"
        ],
        "expected_verification_method": "Schedule a self-report prompt for tonight at approximately 9pm (after dinner). Ask: 'You predicted dinner would taste good. Did it? (yes/no)'. Taste is an inherently personal sensory experience — no external tool can assess it."
    },
    "base-036": {
        "expected_verification_criteria": [
            "The user successfully completes (advances past) the video game level they are currently attempting, confirmed by the user reporting 'yes' to level completion before going to bed tonight"
        ],
        "expected_verification_method": "Prompt the user late tonight (approximately 11pm) to report: 'Did you beat the game level tonight? (yes/no/didn't play)'. Level completion is a binary objective outcome tracked by the game itself, but not externally accessible — requires user confirmation."
    },
    "base-041": {
        "expected_verification_criteria": [
            "The user's code compiles without errors on the first compilation attempt, confirmed by the user reporting 'yes' to: 'Did your code compile on the first try?'"
        ],
        "expected_verification_method": "Prompt the user after their next coding session to report: 'Did your code compile on the first try? (yes/no)'. Compilation success is a binary objective outcome, but without a CI/CD tool in the tool manifest, it requires user self-report."
    },
}

with open("eval/golden_dataset.json", "r") as f:
    data = json.load(f)

# Bump dataset version
data["dataset_version"] = "3.1"

updated = 0
for bp in data["base_predictions"]:
    if bp["id"] in UPDATES:
        bp["ground_truth"]["expected_verification_criteria"] = UPDATES[bp["id"]]["expected_verification_criteria"]
        bp["ground_truth"]["expected_verification_method"] = UPDATES[bp["id"]]["expected_verification_method"]
        updated += 1

with open("eval/golden_dataset.json", "w") as f:
    json.dump(data, f, indent=2)

print(f"Updated {updated}/7 subjective test cases")
print(f"Dataset version: {data['dataset_version']}")
