"""
Модульные тесты для проверки функциональности аналитики задач JIRA.
Разработчик: Суханов С.С.
"""

import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime

from jira_analytics.jira_api import JiraClient, JiraAPIError
from jira_analytics.tasks import (
    calculate_open_durations,
    calculate_status_durations,
    calculate_daily_dynamics,
    calculate_top_users,
    calculate_logged_times,
    calculate_priorities,
)
from jira_analytics.utils import parse_jira_date


class TestJiraAPI(unittest.TestCase):
    """Тестирование взаимодействия с JIRA REST API и вспомогательных методов."""

    def setUp(self):
        """Подготовка тестовых данных."""
        self.project_key = "KAFKA"
        self.mock_response_data = {
            "total": 2,
            "issues": [
                {
                    "key": "KAFKA-1",
                    "fields": {
                        "summary": "First test task",
                        "created": "2026-10-01T10:00:00.000+0000",
                        "resolutiondate": "2026-10-05T10:00:00.000+0000",
                        "timespent": 7200,  # 2 hours
                        "priority": {"name": "Major"},
                        "assignee": {"displayName": "Ivan Ivanov", "name": "ivan"},
                        "reporter": {"displayName": "Petr Petrov", "name": "petr"},
                        "status": {"name": "Resolved"}
                    },
                    "changelog": {
                        "histories": [
                            {
                                "created": "2026-10-02T10:00:00.000+0000",
                                "items": [
                                    {"field": "status", "fromString": "Open", "toString": "In Progress"}
                                ]
                            },
                            {
                                "created": "2026-10-05T10:00:00.000+0000",
                                "items": [
                                    {"field": "status", "fromString": "In Progress", "toString": "Resolved"}
                                ]
                            }
                        ]
                    }
                },
                {
                    "key": "KAFKA-2",
                    "fields": {
                        "summary": "Second test task",
                        "created": "2026-10-02T12:00:00.000+0000",
                        "resolutiondate": "2026-10-04T12:00:00.000+0000",
                        "timespent": 14400,  # 4 hours
                        "priority": {"name": "Critical"},
                        "assignee": {"displayName": "Ivan Ivanov", "name": "ivan"},
                        "reporter": {"displayName": "Ivan Ivanov", "name": "ivan"},
                        "status": {"name": "Closed"}
                    },
                    "changelog": {
                        "histories": [
                            {
                                "created": "2026-10-04T12:00:00.000+0000",
                                "items": [
                                    {"field": "status", "fromString": "Open", "toString": "Closed"}
                                ]
                            }
                        ]
                    }
                }
            ]
        }

    @patch("requests.Session.get")
    def test_fetch_jira_issues(self, mock_get):
        """Тест функции выборки задач через REST API (JiraClient.search_issues)."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.mock_response_data
        mock_get.return_value = mock_response

        client = JiraClient(base_url="https://issues.apache.org/jira")
        result = client.search_issues(jql="project = KAFKA", max_results=10, use_cache=False)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["key"], "KAFKA-1")
        self.assertEqual(result[1]["key"], "KAFKA-2")
        print("fetch_jira_issues: Тест пройден успешно")

    @patch("requests.Session.get")
    def test_get_project_issues(self, mock_get):
        """Тест метода получения закрытых задач проекта."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.mock_response_data
        mock_get.return_value = mock_response

        client = JiraClient(base_url="https://issues.apache.org/jira")
        result = client.get_closed_project_issues(project_key=self.project_key, max_results=10, use_cache=False)

        self.assertEqual(len(result), 2)
        self.assertIn("resolutiondate", result[0]["fields"])
        print("get_project_issues: Тест пройден успешно")

    def test_get_assignee_issues(self):
        """Тест анализа активности пользователей (исполнители и авторы)."""
        issues = self.mock_response_data["issues"]
        top_users = calculate_top_users(issues, top_n=10)

        # Ivan Ivanov: 2 раза assignee, 1 раз reporter = 3
        # Petr Petrov: 1 раз reporter = 1
        self.assertEqual(len(top_users), 2)
        self.assertEqual(top_users[0][0], "Ivan Ivanov")
        self.assertEqual(top_users[0][1], 3)
        self.assertEqual(top_users[1][0], "Petr Petrov")
        self.assertEqual(top_users[1][1], 1)
        print("get_assignee_issues: Тест пройден успешно")

    def test_analyse_time_spent(self):
        """Тест анализа залогированного времени выполнения задач."""
        issues = self.mock_response_data["issues"]
        logged = calculate_logged_times(issues)

        # 7200 сек = 2.0 часа, 14400 сек = 4.0 часа
        self.assertEqual(len(logged), 2)
        self.assertAlmostEqual(logged[0], 2.0)
        self.assertAlmostEqual(logged[1], 4.0)
        print("analyse_time_spent: Тест пройден успешно")

    def test_analyse_issues_with_priority(self):
        """Тест анализа распределения задач по степени серьезности / приоритетам."""
        issues = self.mock_response_data["issues"]
        priorities = calculate_priorities(issues)

        self.assertEqual(priorities.get("Major"), 1)
        self.assertEqual(priorities.get("Critical"), 1)
        print("analyse_issues_with_priority: Тест пройден успешно")

    def test_calculate_open_durations(self):
        """Тест расчета времени нахождения задач в открытом состоянии."""
        issues = self.mock_response_data["issues"]
        durations = calculate_open_durations(issues)

        # KAFKA-1: с 1 по 5 октября = 4 дня
        # KAFKA-2: с 2 по 4 октября = 2 дня
        self.assertEqual(len(durations), 2)
        self.assertAlmostEqual(durations[0], 4.0)
        self.assertAlmostEqual(durations[1], 2.0)
        print("calculate_open_durations: Тест пройден успешно")

    def test_calculate_status_durations(self):
        """Тест расчета времени, проведенного в отдельных статусах."""
        issues = self.mock_response_data["issues"]
        status_durs = calculate_status_durations(issues)

        # KAFKA-1: Open с 1 по 2 октября (1 день), In Progress с 2 по 5 октября (3 дня)
        # KAFKA-2: Open с 2 по 4 октября (2 дня)
        self.assertIn("Open", status_durs)
        self.assertIn("In Progress", status_durs)
        self.assertEqual(len(status_durs["Open"]), 2)
        self.assertAlmostEqual(status_durs["Open"][0], 1.0)
        self.assertAlmostEqual(status_durs["Open"][1], 2.0)
        self.assertAlmostEqual(status_durs["In Progress"][0], 3.0)
        print("calculate_status_durations: Тест пройден успешно")

    def test_calculate_daily_dynamics(self):
        """Тест расчета ежедневной динамики заведения и закрытия с накопительным итогом."""
        issues = self.mock_response_data["issues"]
        dynamics = calculate_daily_dynamics(issues)

        self.assertIn("dates", dynamics)
        self.assertIn("created_daily", dynamics)
        self.assertIn("resolved_daily", dynamics)
        self.assertIn("created_cumulative", dynamics)
        self.assertIn("resolved_cumulative", dynamics)

        # Всего 2 создано, 2 закрыто
        self.assertEqual(dynamics["created_cumulative"][-1], 2)
        self.assertEqual(dynamics["resolved_cumulative"][-1], 2)
        print("calculate_daily_dynamics: Тест пройден успешно")


if __name__ == "__main__":
    unittest.main(verbosity=2)
