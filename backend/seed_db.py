from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.config import settings
from app.database import Base
from app.models import Problem, TestCase, UserRole

# Sample problems with different difficulty levels
SAMPLE_PROBLEMS = [
    {
        "title": "Two Sum",
        "difficulty": "easy",
        "statement": "Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target.\n\nYou may assume that each input would have exactly one solution, and you may not use the same element twice.\n\nYou can return the answer in any order.",
        "constraints": "2 <= nums.length <= 10^4\n-10^9 <= nums[i] <= 10^9\n-10^9 <= target <= 10^9",
        "test_cases": [
            {"input": "nums = [2,7,11,15], target = 9", "expected_output": "[0,1]", "is_hidden": False},
            {"input": "nums = [3,2,4], target = 6", "expected_output": "[1,2]", "is_hidden": False},
            {"input": "nums = [3,3], target = 6", "expected_output": "[0,1]", "is_hidden": True},
        ]
    },
    {
        "title": "Add Two Numbers",
        "difficulty": "medium",
        "statement": "You are given two non-empty linked lists representing two non-negative integers. The digits are stored in reverse order, and each of their nodes contains a single digit. Add the two numbers and return the sum as a linked list.\n\nYou may assume the two numbers do not contain any leading zero, except the number 0 itself.",
        "constraints": "The number of nodes in each linked list is in the range [1, 100].\n0 <= Node.val <= 9\nIt is guaranteed that the list represents a number that does not have leading zeros.",
        "test_cases": [
            {"input": "l1 = [2,4,3], l2 = [5,6,4]", "expected_output": "[7,0,8]", "is_hidden": False},
            {"input": "l1 = [0], l2 = [0]", "expected_output": "[0]", "is_hidden": False},
            {"input": "l1 = [9,9,9,9,9,9,9], l2 = [9,9,9,9]", "expected_output": "[8,9,9,9,0,0,0,1]", "is_hidden": True},
        ]
    },
    {
        "title": "Longest Substring Without Repeating Characters",
        "difficulty": "medium",
        "statement": "Given a string s, find the length of the longest substring without repeating characters.",
        "constraints": "0 <= s.length <= 5 * 10^4\ns consists of English letters, digits, symbols and spaces.",
        "test_cases": [
            {"input": "s = \"abcabcbb\"", "expected_output": "3", "is_hidden": False},
            {"input": "s = \"bbbbb\"", "expected_output": "1", "is_hidden": False},
            {"input": "s = \"pwwkew\"", "expected_output": "3", "is_hidden": True},
        ]
    },
    {
        "title": "Median of Two Sorted Arrays",
        "difficulty": "hard",
        "statement": "Given two sorted arrays nums1 and nums2 of size m and n respectively, return the median of the two sorted arrays.\n\nThe overall run time complexity should be O(log (m+n)).",
        "constraints": "nums1.length == m\nnums2.length == n\n0 <= m <= 1000\n0 <= n <= 1000\n1 <= m + n <= 2000\n-10^6 <= nums1[i], nums2[i] <= 10^6",
        "test_cases": [
            {"input": "nums1 = [1,3], nums2 = [2]", "expected_output": "2.00000", "is_hidden": False},
            {"input": "nums1 = [1,2], nums2 = [3,4]", "expected_output": "2.50000", "is_hidden": False},
            {"input": "nums1 = [], nums2 = [1]", "expected_output": "1.00000", "is_hidden": True},
        ]
    },
    {
        "title": "Palindrome Number",
        "difficulty": "easy",
        "statement": "Given an integer x, return true if x is a palindrome, and false otherwise.",
        "constraints": "-2^31 <= x <= 2^31 - 1",
        "test_cases": [
            {"input": "x = 121", "expected_output": "true", "is_hidden": False},
            {"input": "x = -121", "expected_output": "false", "is_hidden": False},
            {"input": "x = 10", "expected_output": "false", "is_hidden": True},
        ]
    },
    {
        "title": "Regular Expression Matching",
        "difficulty": "hard",
        "statement": "Given an input string s and a pattern p, implement regular expression matching with support for '.' and '*' where:\n\n'.' Matches any single character.\n'*' Matches zero or more of the preceding element.\n\nThe matching should cover the entire input string (not partial).",
        "constraints": "1 <= s.length <= 20\n1 <= p.length <= 30\ns contains only lowercase English letters.\np contains only lowercase English letters, '.', and '*'.\nIt is guaranteed for each appearance of the character '*', there will be a previous valid character to match.",
        "test_cases": [
            {"input": "s = \"aa\", p = \"a\"", "expected_output": "false", "is_hidden": False},
            {"input": "s = \"aa\", p = \"a*\"", "expected_output": "true", "is_hidden": False},
            {"input": "s = \"ab\", p = \".*\"", "expected_output": "true", "is_hidden": True},
        ]
    },
    {
        "title": "Container With Most Water",
        "difficulty": "medium",
        "statement": "You are given an integer array height of length n. There are n vertical lines drawn such that the two endpoints of the ith line are (i, 0) and (i, height[i]).\n\nFind two lines that together with the x-axis form a container, such that the container contains the most water.\n\nReturn the maximum amount of water a container can store.",
        "constraints": "n == height.length\n2 <= n <= 10^5\n0 <= height[i] <= 10^4",
        "test_cases": [
            {"input": "height = [1,8,6,2,5,4,8,3,7]", "expected_output": "49", "is_hidden": False},
            {"input": "height = [1,1]", "expected_output": "1", "is_hidden": False},
            {"input": "height = [4,3,2,1,4]", "expected_output": "16", "is_hidden": True},
        ]
    },
    {
        "title": "3Sum",
        "difficulty": "medium",
        "statement": "Given an integer array nums, return all the triplets [nums[i], nums[j], nums[k]] such that i != j, i != k, and j != k, and nums[i] + nums[j] + nums[k] == 0.\n\nNotice that the solution set must not contain duplicate triplets.",
        "constraints": "3 <= nums.length <= 3000\n-10^5 <= nums[i] <= 10^5",
        "test_cases": [
            {"input": "nums = [-1,0,1,2,-1,-4]", "expected_output": "[[-1,-1,2],[-1,0,1]]", "is_hidden": False},
            {"input": "nums = [0,1,1]", "expected_output": "[]", "is_hidden": False},
            {"input": "nums = [0,0,0]", "expected_output": "[[0,0,0]]", "is_hidden": True},
        ]
    },
    {
        "title": "Merge K Sorted Lists",
        "difficulty": "hard",
        "statement": "You are given an array of k linked-lists lists, each linked-list is sorted in ascending order.\n\nMerge all the linked-lists into one sorted linked-list and return it.",
        "constraints": "k == lists.length\n0 <= k <= 10^4\n0 <= lists[i].length <= 500\n-10^4 <= lists[i][j] <= 10^4\nlists[i] is sorted in ascending order.\nThe sum of lists[i].length will not exceed 10^4.",
        "test_cases": [
            {"input": "lists = [[1,4,5],[1,3,4],[2,6]]", "expected_output": "[1,1,2,3,4,4,5,6]", "is_hidden": False},
            {"input": "lists = []", "expected_output": "[]", "is_hidden": False},
            {"input": "lists = [[]]", "expected_output": "[]", "is_hidden": True},
        ]
    },
    {
        "title": "Valid Parentheses",
        "difficulty": "easy",
        "statement": "Given a string s containing just the characters '(', ')', '{', '}', '[' and ']', determine if the input string is valid.\n\nAn input string is valid if:\n- Open brackets must be closed by the same type of brackets.\n- Open brackets must be closed in the correct order.\n- Every close bracket has a corresponding open bracket of the same type.",
        "constraints": "1 <= s.length <= 10^4\ns consists of parentheses only '()[]{}'.",
        "test_cases": [
            {"input": "s = \"()\"", "expected_output": "true", "is_hidden": False},
            {"input": "s = \"()[]{}\"", "expected_output": "true", "is_hidden": False},
            {"input": "s = \"(]\"", "expected_output": "false", "is_hidden": True},
        ]
    }
]

def seed_database():
    engine = create_engine(settings.database_url)
    Base.metadata.create_all(engine)
    
    session = Session(engine)
    try:
        from app.models import User
        from app.security import hash_password
        
        # Check if teacher account exists
        teacher = session.query(User).filter(User.email == "teacher@codejudge.com").first()
        if not teacher:
            print("Creating teacher account...")
            teacher = User(
                email="teacher@codejudge.com",
                password_hash=hash_password("teacher123"),
                full_name="Teacher User",
                role=UserRole.teacher,
            )
            session.add(teacher)
            session.commit()
            print("  Teacher: teacher@codejudge.com / teacher123")
        else:
            print("Teacher account already exists")
        
        # Check if admin account exists
        admin = session.query(User).filter(User.email == "admin@codejudge.com").first()
        if not admin:
            print("Creating admin account...")
            admin = User(
                email="admin@codejudge.com",
                password_hash=hash_password("admin123"),
                full_name="Admin User",
                role=UserRole.admin,
            )
            session.add(admin)
            session.commit()
            print("  Admin: admin@codejudge.com / admin123")
        else:
            print("Admin account already exists")
        
        # Check if problems already exist
        existing_count = session.query(Problem).count()
        if existing_count > 0:
            print(f"Database already has {existing_count} problems. Skipping problem seed.")
            return
        
        # Add sample problems
        for problem_data in SAMPLE_PROBLEMS:
            test_cases = problem_data.pop("test_cases")
            problem = Problem(**problem_data)
            session.add(problem)
            session.flush()  # Get the problem ID
            
            for tc_data in test_cases:
                test_case = TestCase(problem_id=problem.id, **tc_data)
                session.add(test_case)
        
        session.commit()
        print(f"Successfully seeded {len(SAMPLE_PROBLEMS)} problems with test cases.")
    finally:
        session.close()

if __name__ == "__main__":
    seed_database()
