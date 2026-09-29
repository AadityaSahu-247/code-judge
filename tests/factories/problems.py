"""Problem and test-case factories."""

from app.models import Problem, TestCase


def make_problem(
    db,
    *,
    title: str = "Sum of Two Numbers",
    statement: str = "Read two integers a and b from stdin and print their sum.",
    constraints: str | None = "a, b in [-10^9, 10^9].",
    difficulty: str = "easy",
) -> Problem:
    problem = Problem(
        title=title,
        statement=statement,
        constraints=constraints,
        difficulty=difficulty,
    )
    db.add(problem)
    db.commit()
    db.refresh(problem)
    return problem


def make_test_case(
    db,
    problem_id: int,
    *,
    input_: str = "2 3",
    expected_output: str = "5",
    is_hidden: bool = False,
    weight: float = 1.0,
) -> TestCase:
    tc = TestCase(
        problem_id=problem_id,
        input=input_,
        expected_output=expected_output,
        is_hidden=is_hidden,
        weight=weight,
    )
    db.add(tc)
    db.commit()
    db.refresh(tc)
    return tc


def make_problem_with_cases(db, *, hidden: bool = True, num_cases: int = 2):
    problem = make_problem(db)
    visible = make_test_case(db, problem.id, input_="2 3", expected_output="5")
    hidden_case = None
    if hidden:
        hidden_case = make_test_case(
            db, problem.id, input_="1000000000 1", expected_output="1000000001", is_hidden=True
        )
    for _ in range(max(0, num_cases - 2)):
        make_test_case(db, problem.id, input_="1 1", expected_output="2")
    return problem, [tc for tc in (visible, hidden_case) if tc]
