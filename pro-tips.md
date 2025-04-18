# Pro Tips

## Keep files small and focused
- More targeted context for the llm
- Use consistent naming like `db/company` `api/company` `test/db/company` `test/api/company`

## Generate classes from yaml like pseudo code
```
Company:
    id
    name
    ...
```

## Linting, Testing, and Logging Early
- Make sure to instruct the llm to use dependency injection, etc
- Have the llm generate mocks, cover edge cases, etc
- Generate the boilerplate for structued / leveled logging

**After every generation: lint, test, review**
- Output results to a file for easy llm context

## Debugging
- Instruct the llm to add debug logging at critical points
- Pass the whole log (or the relevant section, if its large) back as context

## Leverage clever context sources
- Write your todos in a ROADMAP.md
- Leverage JSON Canvas to design databases, ui components, etc

## Periodic Review and Documentation
- Ask the llm to critique the codebase
- Ask the llm to describe implementation details in README.md's
- Ask the llm to generate design documents & feature planning task lists

**After every generation: lint, test, review**
