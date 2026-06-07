# Bug Fix: Validation Endpoint

## Issue
When clicking the "Validate" button in demo mode, the server was crashing with:
```
TypeError: run_full_validation() got an unexpected keyword argument 'calculator'
```

## Root Cause
The `run_full_validation()` function in `src/validation.py` only accepts three parameters:
- `matches: list[Match]`
- `players: list[DraftPlayer]`
- `use_llm: bool = True`

However, in `src/server.py`, the demo mode validation endpoint was incorrectly passing a `calculator` parameter:
```python
report = run_full_validation(
    matches, 
    players, 
    calculator=calculator,  # ❌ This parameter doesn't exist
    use_llm=True
)
```

## Fix
Removed the `calculator` parameter from the function call in `src/server.py`:

```python
report = run_full_validation(
    matches, 
    players, 
    use_llm=True  # ✅ Only valid parameters
)
```

## Files Modified
- `src/server.py` (line ~399) - Removed `calculator` parameter from `run_full_validation()` call

## Testing
1. Restarted demo server
2. Clicked "Validate" button
3. Validation should now run successfully with OpenAI

## Note
The `validate_structural()` function (called internally by `run_full_validation()`) creates its own `ScoringCalculator` instance with default rules, so passing a calculator parameter was unnecessary anyway.
