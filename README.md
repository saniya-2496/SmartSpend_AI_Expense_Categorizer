# SmartSpend — Intelligent Expense Categorizer

## Overview
SmartSpend is a desktop expense-tracking mini-project built using Python's standard library only. It demonstrates a small, explainable rule-based AI system.

## Features
- Add expenses with description, amount, and date
- Automatically categorize descriptions using a built-in keyword knowledge base
- Show an explanation for each categorization
- Correct predictions and save the correction as a local rule
- Store expenses locally using SQLite
- Dashboard with total spending, transaction count, and top category
- Search and filter transaction history
- Delete transactions
- Export transaction history to CSV

## Requirements
- Python 3
- Tkinter (usually included with desktop Python installations)

No pandas, scikit-learn, external packages, internet connection, API key, or downloaded dataset is required.

## Run
1. Extract the project ZIP.
2. Open a terminal/command prompt in the extracted folder.
3. Run:
   ```bash
   python smartspend.py
   ```
4. A local `smartspend.db` file is created automatically the first time you run the app. It stores your expenses and corrections.

## Test examples
Try these descriptions:
- `Uber ride` -> Transport
- `Lunch at cafe` -> Food
- `College notebook` -> Education
- `Electricity bill` -> Bills
- `Medicine from pharmacy` -> Health
- `Unknown purchase` -> Other

Then correct a prediction and add the same description again to see the saved correction used.

## AI technique
The project uses an explainable, rule-based inference engine:
1. Check whether the description matches a correction saved by the user.
2. Otherwise match the description against keyword rules in the knowledge base.
3. Score matches by keyword length to prefer more specific matches.
4. If there is no match or an unresolved tie, use `Other` and explain why.

This is classical rule-based AI, not machine learning. The correction feature stores user feedback as local rules; it does not train a statistical model.

## Suggested academic report sections
1. Title and abstract
2. Problem statement
3. Objectives
4. Existing system and proposed system
5. System requirements
6. Architecture / flowchart
7. AI technique and algorithm
8. Implementation and UI screenshots
9. Test cases and results
10. Limitations
11. Conclusion and future scope

## Limitations
- Categorization is based on text keywords and can make mistakes.
- It does not connect to bank accounts.
- It does not provide financial advice.
- Learned corrections apply to the same normalized description, not every possible synonym.
