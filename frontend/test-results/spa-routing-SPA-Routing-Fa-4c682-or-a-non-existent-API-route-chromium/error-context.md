# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: spa-routing.spec.ts >> SPA Routing Fallback Verification >> should return 404 for a non-existent API route
- Location: tests\spa-routing.spec.ts:43:7

# Error details

```
Error: page.evaluate: TypeError: Failed to execute 'fetch' on 'Window': Failed to parse URL from /api/v1/this/route/does/not/exist
    at eval (eval at evaluate (:302:30), <anonymous>:1:8)
    at UtilityScript.evaluate (<anonymous>:304:16)
    at UtilityScript.<anonymous> (<anonymous>:1:44)
```