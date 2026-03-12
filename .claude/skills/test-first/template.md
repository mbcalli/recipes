# Test First Template

## Bug Report

### Description
<!-- One sentence: what is broken and where -->

### Reproduction
<!-- Minimal code path or steps that trigger the bug -->

### Root Cause
<!-- What is actually wrong - be specific about the mechanism, not just the symptom -->

---

## Unit Test

### Test File
<!-- Path to test file, e.g., tests/services/test_user.py -->

### Test Case
```python
def test_():
    # Arrange

    # Act
    <!-- Call the function/method under test -->

    # Assert
```

### What This Test Verifies
<!-- One sentence: the invariant this test encodes, generalized beyond this specific bug -->

---

## Fix

### Change Description
<!-- What you changed and why - link cause to fix explicitly -->

### Files Modified
<!-- List each file and the nature of the change -->

---

## Iteration Log

### Attempt 1
**Test Result:** FAIL/PASS
**Failure Message:**
<!-- Exact error or assertion output -->

### Attempt N
**Test Result:** FAIL/PASS
**Failure Message:**
**Adjustment:**

---

## Resolution

### Final Test Result
PASS

### Regulation Check
<!-- Confirm existing test suite still passes. Note any newly broken tests and how they were resolved. -->

### Confidence Assessment
<!-- Low / Medium / High - justify briefly. Low = fix is narrow and britte. High = fix addresses root cause and test covers the general case. -->









