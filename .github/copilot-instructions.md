# Project general coding guidelines

## How
1. Use .venv if you need to run code.

## Test
- Use 'source .venv/bin/activate && INTEGRATION_TEST_MODE=MOCK python -m pytest tests' to run tests.
- If some test case failed with: 'No mock data found for LLM with parameters hash '
  - Rerun the case with 'INTEGRATION_TEST_MODE=REAL' to record the data.
  - Try again with 'INTEGRATION_TEST_MODE=MOCK' to see if it works.
- Run test before your implementation, so that you know what test is passed and what is failed.
- Run test after your code change, make sure you don't break anything.
- If you need to test a new feature for python code, write unittest first and add it to ./tests directory.
- Clean up temporary test files before finishing work.

## Code Guide
- Try to only make minimum amount of code change when implementing new feature.
- Do not catch the exception that you don't know how to deal with, do not use fallback value unless we designed to do so.
- Propose your change plan before implement.
- Implement test in ./tests directory.
- Unless you need to trace the error, do not capture the exception, let it float to top of program. 
- If you see code not following this guide, point it out and propose change plan.
- For any task which might take more than 1 hour for a developer, plan first by explicitly list out todo list, then execute them. You can regenerate todo list if you see plan needs to change.
- Do not reinvent the wheel, use mature library if the functionality has been implemented before.
- Do not repeat yourself, when you see duplicate code, try to deduplicate it.