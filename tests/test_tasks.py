"""
Модульные и интеграционные тесты для проверки аналитики задач JIRA на РЕАЛЬНЫХ данных.
Тесты выполняют прямое обращение к REST API Apache JIRA и проверяют расчет метрик
на реальных тикетах без использования фиктивных Mock-заглушек.

Разработчик: Суханов С.С.
"""

import unittest
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


class TestJiraRealAPI(unittest.TestCase):
    """
    Реальные тесты аналитического модуля на живых данных проектов Apache Kafka и HDFS.
    Все тесты работают с реальными сетевыми ответами и реальными структурами JSON.
    """

    @classmethod
    def setUpClass(cls):
        """
        Инициализация клиента и загрузка реальных данных из Apache JIRA.
        Используется реальный JIRA REST API (https://issues.apache.org/jira).
        """
        cls.client = JiraClient(base_url="https://issues.apache.org/jira", timeout=30)
        cls.project_key = "KAFKA"

        # Загружаем реальные закрытые задачи Kafka с историей changelog (10 задач для быстроты тестов)
        cls.real_closed_issues = cls.client.get_closed_project_issues(
            project_key="KAFKA",
            max_results=15,
            expand_changelog=True,
            use_cache=True
        )

        # Загружаем общий поток реальных задач Kafka
        cls.real_all_issues = cls.client.get_all_project_issues(
            project_key="KAFKA",
            max_results=20,
            use_cache=True
        )

        # Загружаем реальные задачи Apache HDFS с заполненным полем timespent
        cls.real_hdfs_timespent_issues = cls.client.search_issues(
            jql="project = HDFS AND status in (Closed, Resolved) AND timespent is not EMPTY",
            max_results=10,
            use_cache=True
        )

    def test_1_real_fetch_issues_from_jira(self):
        """1. Реальный тест поиска задач через REST API (GET /rest/api/2/search)."""
        issues = self.client.search_issues("project = KAFKA", max_results=5, use_cache=True)
        self.assertGreater(len(issues), 0, "REST API JIRA должен вернуть задачи")
        first_issue = issues[0]
        self.assertTrue(first_issue["key"].startswith("KAFKA-"), "Ключ тикета должен начинаться с 'KAFKA-'")
        self.assertIn("summary", first_issue["fields"], "В ответе API должно присутствовать поле summary")
        self.assertIn("created", first_issue["fields"], "В ответе API должно присутствовать поле created")
        print(f"test_1_real_fetch_issues_from_jira: OK (получен реальный тикет {first_issue['key']})")

    def test_2_real_get_closed_project_issues(self):
        """2. Реальный тест получения закрытых задач с changelog."""
        issues = self.real_closed_issues
        self.assertGreater(len(issues), 0, "Должны быть получены закрытые задачи Kafka")
        for issue in issues[:5]:
            status_name = issue["fields"]["status"]["name"]
            self.assertIn(status_name, ["Closed", "Resolved"], "Статус должен быть Closed или Resolved")
            self.assertIsNotNone(issue["fields"].get("resolutiondate"), "У закрытой задачи обязана быть дата закрытия")
            self.assertIn("changelog", issue, "У задачи с expand=changelog должна присутствовать история изменений")
        print("test_2_real_get_closed_project_issues: OK (все задачи проверены на статус Closed/Resolved и changelog)")

    def test_3_real_calculate_open_durations(self):
        """3. Реальный расчет времени задач в открытом состоянии (created -> resolutiondate)."""
        durations = calculate_open_durations(self.real_closed_issues)
        self.assertGreater(len(durations), 0, "Список длительностей не должен быть пустым")
        for d in durations:
            self.assertIsInstance(d, float, "Длительность должна быть числом с плавающей точкой")
            self.assertGreaterEqual(d, 0.0, "Длительность решения задачи не может быть отрицательной")
        print(f"test_3_real_calculate_open_durations: OK (рассчитано время для {len(durations)} реальных задач, min={min(durations):.1f}д, max={max(durations):.1f}д)")

    def test_4_real_calculate_status_durations(self):
        """4. Реальный расчет времени нахождения в статусах по changelog."""
        status_durations = calculate_status_durations(self.real_closed_issues)
        self.assertIsInstance(status_durations, dict, "Результат должен быть словарем статусов")
        self.assertIn("Open", status_durations, "Среди статусов Kafka обязательно должен присутствовать статус 'Open'")
        open_durs = status_durations["Open"]
        self.assertGreater(len(open_durs), 0, "Должны быть зафиксированы интервалы нахождения в статусе Open")
        for val in open_durs:
            self.assertGreaterEqual(val, 0.0, "Время в статусе не может быть отрицательным")
        print(f"test_4_real_calculate_status_durations: OK (найдены статусы: {list(status_durations.keys())[:4]}...)")

    def test_5_real_calculate_daily_dynamics(self):
        """5. Реальный расчет ежедневной динамики заведения/закрытия и накопительного итога."""
        dynamics = calculate_daily_dynamics(self.real_all_issues)
        self.assertIn("dates", dynamics)
        self.assertIn("created_daily", dynamics)
        self.assertIn("resolved_daily", dynamics)
        self.assertIn("created_cumulative", dynamics)
        self.assertIn("resolved_cumulative", dynamics)

        cum_created = dynamics["created_cumulative"]
        self.assertGreater(len(cum_created), 0)
        # Проверка свойства монотонности накопительного итога: каждое следующее значение >= предыдущего
        for i in range(len(cum_created) - 1):
            self.assertGreaterEqual(cum_created[i + 1], cum_created[i], "Накопительный итог должен быть монотонно неубывающим")
        print(f"test_5_real_calculate_daily_dynamics: OK (дней в выборке: {len(dynamics['dates'])}, суммарно создано: {cum_created[-1]})")

    def test_6_real_calculate_top_users(self):
        """6. Реальный расчет активности пользователей (топ авторов и исполнителей)."""
        top_users = calculate_top_users(self.real_all_issues, top_n=10)
        self.assertGreater(len(top_users), 0, "Список пользователей не должен быть пустым")
        first_user = top_users[0]
        # Кортеж: (имя, всего_задач, как_исполнитель, как_автор)
        self.assertEqual(len(first_user), 4, "Запись пользователя должна содержать 4 поля")
        user_name, total, assignee_cnt, reporter_cnt = first_user
        self.assertIsInstance(user_name, str)
        self.assertEqual(total, assignee_cnt + reporter_cnt, "Сумма задач должна равняться сумме исполнителя и автора")
        self.assertGreater(total, 0, "Количество задач топ-пользователя должно быть больше нуля")
        print(f"test_6_real_calculate_top_users: OK (топ-1 контрибьютор: {user_name}, задач: {total})")

    def test_7_real_calculate_logged_times(self):
        """7. Реальный расчет залогированного времени на тикетах Apache HDFS."""
        times = calculate_logged_times(self.real_hdfs_timespent_issues)
        self.assertGreater(len(times), 0, "Список залогированного времени HDFS не должен быть пустым")
        for hours in times:
            self.assertIsInstance(hours, float, "Время в часах должно быть числом с плавающей точкой")
            self.assertGreater(hours, 0.0, "Залогированное время должно быть положительным")
        print(f"test_7_real_calculate_logged_times: OK (получено {len(times)} записей трудозатрат HDFS, среднее: {sum(times)/len(times):.1f}ч)")

    def test_8_real_calculate_priorities(self):
        """8. Реальный расчет распределения задач по степени серьезности."""
        priorities = calculate_priorities(self.real_all_issues)
        self.assertIsInstance(priorities, dict)
        self.assertGreater(len(priorities), 0, "Должна быть хотя бы одна категория приоритета")
        total_counted = sum(priorities.values())
        self.assertGreater(total_counted, 0, "Сумма подсчитанных приоритетов должна быть больше 0")
        print(f"test_8_real_calculate_priorities: OK (найденные приоритеты: {priorities})")


if __name__ == "__main__":
    unittest.main(verbosity=2)
