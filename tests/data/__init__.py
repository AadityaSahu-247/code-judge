# Dummy data used by the test suite. All of it is inert sample content.

# Deterministic "correct" solution markers used by the mocked grader so a
# submission is scored without executing anything.
ACCEPTED_PYTHON = "print('accepted')"
ACCEPTED_JAVASCRIPT = "console.log('accepted');"

WRONG_ANSWER_PYTHON = "print('wrong')"
INFINITE_LOOP_PYTHON = "while True: pass"

LARGE_PYTHON = "\n".join(f"# line {i}" for i in range(2000)) + "\nprint('ok')"
