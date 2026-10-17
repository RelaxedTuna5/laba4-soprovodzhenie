"""
Модуль аналитической обработки данных и построения визуализаций (графиков и диаграмм).
Разработчик: Суханов С.С.
"""

import os
from collections import defaultdict, Counter
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from jira_analytics.utils import parse_jira_date, ensure_dir, get_logger

logger = get_logger("jira_analytics.tasks")

# Настройка шрифтов для корректного отображения кириллицы
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Segoe UI', 'Liberation Sans']
plt.rcParams['axes.unicode_minus'] = False


def calculate_open_durations(issues: List[Dict[str, Any]]) -> List[float]:
    """
    Рассчитывает время нахождения закрытых задач в открытом состоянии (от created до resolutiondate) в днях.
    
    :param issues: Список словарей с данными закрытых задач JIRA.
    :return: Список длительностей в днях (float).
    """
    durations = []
    for issue in issues:
        fields = issue.get("fields", {})
        created_str = fields.get("created")
        res_str = fields.get("resolutiondate")
        if not created_str or not res_str:
            continue

        created = parse_jira_date(created_str)
        resolved = parse_jira_date(res_str)
        if created and resolved and resolved >= created:
            delta_days = (resolved - created).total_seconds() / 86400.0
            durations.append(delta_days)

    logger.debug("Рассчитана длительность открытого состояния для %d задач", len(durations))
    return durations


def plot_open_duration_histogram(issues: List[Dict[str, Any]],
                                 project_key: str,
                                 save_path: Optional[str] = None,
                                 bins: int = 40,
                                 show: bool = False) -> str:
    """
    Строит гистограмму распределения времени нахождения задач в открытом состоянии.
    
    :param issues: Список закрытых задач.
    :param project_key: Ключ проекта.
    :param save_path: Путь для сохранения графика.
    :param bins: Количество корзин гистограммы.
    :param show: Отображать ли интерактивное окно.
    :return: Путь к сохраненному файлу.
    """
    durations = calculate_open_durations(issues)
    if not durations:
        raise ValueError(f"Нет данных о длительности закрытых задач для проекта {project_key}")

    plt.figure(figsize=(9, 6), dpi=150)
    plt.hist(durations, bins=bins, color='#4A90E2', edgecolor='#003366', alpha=0.85)
    plt.title(f"Гистограмма времени в открытом состоянии (проект: {project_key})", fontsize=13, fontweight='bold', pad=12)
    plt.xlabel("Время в открытом состоянии (дни)", fontsize=11)
    plt.ylabel("Количество задач", fontsize=11)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()

    if not save_path:
        save_path = os.path.join("results", project_key.lower(), "open_duration_histogram.png")
    ensure_dir(os.path.dirname(save_path))
    plt.savefig(save_path, dpi=300)
    logger.info("Гистограмма времени в открытом состоянии сохранена в %s", save_path)
    if show:
        plt.show()
    plt.close()
    return save_path


def calculate_status_durations(issues: List[Dict[str, Any]]) -> Dict[str, List[float]]:
    """
    Рассчитывает время, проведенное задачами в каждом отдельном состоянии, на основе истории changelog.
    
    :param issues: Список задач с историей изменений (expand=changelog).
    :return: Словарь вида {имя_статуса: [длительность_в_днях, ...]}.
    """
    status_durations: Dict[str, List[float]] = defaultdict(list)

    for issue in issues:
        fields = issue.get("fields", {})
        created_str = fields.get("created")
        res_str = fields.get("resolutiondate")
        if not created_str:
            continue

        created_dt = parse_jira_date(created_str)
        if not created_dt:
            continue

        resolved_dt = parse_jira_date(res_str) if res_str else None

        # Сбор переходов статусов из changelog
        changelog = issue.get("changelog", {})
        histories = changelog.get("histories", [])
        status_transitions: List[Tuple[datetime, str, str]] = []

        for h in histories:
            h_created = parse_jira_date(h.get("created"))
            if not h_created:
                continue
            for item in h.get("items", []):
                if item.get("field") == "status":
                    from_status = item.get("fromString", "").strip()
                    to_status = item.get("toString", "").strip()
                    status_transitions.append((h_created, from_status, to_status))

        # Сортировка переходов по времени
        status_transitions.sort(key=lambda x: x[0])

        current_time = created_dt
        # Начальный статус (если не указан явно в первом переходе, по умолчанию 'Open')
        current_status = status_transitions[0][1] if status_transitions and status_transitions[0][1] else "Open"

        for trans_time, from_st, to_st in status_transitions:
            if trans_time > current_time:
                duration_days = (trans_time - current_time).total_seconds() / 86400.0
                status_durations[current_status].append(duration_days)
            current_time = trans_time
            current_status = to_st

        # Финальный интервал до закрытия
        end_dt = resolved_dt or datetime.now(created_dt.tzinfo)
        if end_dt > current_time:
            final_duration = (end_dt - current_time).total_seconds() / 86400.0
            status_durations[current_status].append(final_duration)

    return dict(status_durations)


def plot_status_time_distribution(issues: List[Dict[str, Any]],
                                  status_name: str,
                                  project_key: str,
                                  save_path: Optional[str] = None,
                                  bins: int = 30,
                                  show: bool = False) -> str:
    """
    Строит диаграмму распределения времени для конкретного состояния задачи.
    
    :param issues: Список задач с историей.
    :param status_name: Название статуса (например, 'Open', 'In Progress', 'Patch Available').
    :param project_key: Ключ проекта.
    :param save_path: Путь для сохранения графика.
    :param bins: Количество корзин.
    :param show: Отображать ли интерактивное окно.
    :return: Путь к сохраненному файлу.
    """
    all_status_durations = calculate_status_durations(issues)
    durations = all_status_durations.get(status_name, [])

    if not durations:
        # Поиск статуса без учета регистра
        for k, v in all_status_durations.items():
            if k.lower() == status_name.lower():
                durations = v
                status_name = k
                break

    if not durations:
        raise ValueError(f"Нет данных по состоянию '{status_name}' для проекта {project_key}")

    plt.figure(figsize=(9, 6), dpi=150)
    plt.hist(durations, bins=bins, color='#87CEEB', edgecolor='#0000FF', alpha=0.8)
    plt.title(f"Время в статусе {status_name} (проект: {project_key})", fontsize=13, fontweight='bold', pad=12)
    plt.xlabel("Время (дни)", fontsize=11)
    plt.ylabel("Количество задач", fontsize=11)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()

    if not save_path:
        safe_st = "".join(c if c.isalnum() else "_" for c in status_name)
        save_path = os.path.join("results", project_key.lower(), f"status_{safe_st}_distribution.png")
    ensure_dir(os.path.dirname(save_path))
    plt.savefig(save_path, dpi=300)
    logger.info("Диаграмма времени в статусе '%s' сохранена в %s", status_name, save_path)
    if show:
        plt.show()
    plt.close()
    return save_path


def calculate_daily_dynamics(issues: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Рассчитывает количество заведенных и закрытых задач по дням и накопительный итог.
    
    :param issues: Список задач проекта.
    :return: Словарь с датами, ежедневными значениями и накопительными итогами.
    """
    created_per_day = Counter()
    resolved_per_day = Counter()

    for issue in issues:
        fields = issue.get("fields", {})
        created_str = fields.get("created")
        res_str = fields.get("resolutiondate")

        if created_str:
            c_dt = parse_jira_date(created_str)
            if c_dt:
                created_per_day[c_dt.date()] += 1

        if res_str:
            r_dt = parse_jira_date(res_str)
            if r_dt:
                resolved_per_day[r_dt.date()] += 1

    all_dates = sorted(set(list(created_per_day.keys()) + list(resolved_per_day.keys())))
    if not all_dates:
        return {"dates": [], "created_daily": [], "resolved_daily": [],
                "created_cumulative": [], "resolved_cumulative": []}

    created_daily = [created_per_day[d] for d in all_dates]
    resolved_daily = [resolved_per_day[d] for d in all_dates]

    # Накопительный итог
    created_cum = []
    cum_c = 0
    for c in created_daily:
        cum_c += c
        created_cum.append(cum_c)

    resolved_cum = []
    cum_r = 0
    for r in resolved_daily:
        cum_r += r
        resolved_cum.append(cum_r)

    return {
        "dates": all_dates,
        "created_daily": created_daily,
        "resolved_daily": resolved_daily,
        "created_cumulative": created_cum,
        "resolved_cumulative": resolved_cum
    }


def plot_daily_dynamics(issues: List[Dict[str, Any]],
                        project_key: str,
                        save_path: Optional[str] = None,
                        show: bool = False) -> str:
    """
    Строит график количества заведенных и закрытых задач в день с накопительным итогом (4 кривые).
    
    :param issues: Список задач.
    :param project_key: Ключ проекта.
    :param save_path: Путь сохранения.
    :param show: Отображать ли окно.
    :return: Путь к сохраненному графику.
    """
    data = calculate_daily_dynamics(issues)
    dates = data["dates"]
    if not dates:
        raise ValueError(f"Нет дат для построения динамики задач проекта {project_key}")

    plt.figure(figsize=(11, 5.5), dpi=150)
    plt.plot(dates, data["created_daily"], label="Ежедневно создано", color="blue", linewidth=1.5)
    plt.plot(dates, data["resolved_daily"], label="Ежедневно закрыто", color="green", linewidth=1.5)
    plt.plot(dates, data["created_cumulative"], label="Накопленный итог созданных", color="blue", linestyle="--", linewidth=1.8)
    plt.plot(dates, data["resolved_cumulative"], label="Накопленный итог закрытых", color="red", linestyle="--", linewidth=1.8)

    plt.title(f"График создания и закрытия задач (проект: {project_key})", fontsize=13, fontweight='bold', pad=12)
    plt.xlabel("Дата", fontsize=11)
    plt.ylabel("Количество задач", fontsize=11)
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.legend(loc="upper left", frameon=True)

    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.gcf().autofmt_xdate()
    plt.tight_layout()

    if not save_path:
        save_path = os.path.join("results", project_key.lower(), "daily_dynamics_cumulative.png")
    ensure_dir(os.path.dirname(save_path))
    plt.savefig(save_path, dpi=300)
    logger.info("График динамики задач сохранен в %s", save_path)
    if show:
        plt.show()
    plt.close()
    return save_path


def calculate_top_users(issues: List[Dict[str, Any]], top_n: int = 30) -> List[Tuple[str, int, int, int]]:
    """
    Рассчитывает активность пользователей (исполнитель + репортер).
    
    :param issues: Список задач.
    :param top_n: Количество пользователей в топе.
    :return: Список кортежей (имя_пользователя, всего_задач, как_исполнитель, как_репортер).
    """
    user_total = Counter()
    user_assignee = Counter()
    user_reporter = Counter()

    for issue in issues:
        fields = issue.get("fields", {})
        assignee = fields.get("assignee")
        reporter = fields.get("reporter")

        if assignee:
            name = assignee.get("displayName") or assignee.get("name") or "Не назначен"
            user_assignee[name] += 1
            user_total[name] += 1

        if reporter:
            name = reporter.get("displayName") or reporter.get("name") or "Аноним"
            user_reporter[name] += 1
            user_total[name] += 1

    top_list = []
    for user, total in user_total.most_common(top_n):
        top_list.append((user, total, user_assignee[user], user_reporter[user]))

    return top_list


def plot_top_users(issues: List[Dict[str, Any]],
                   project_key: str,
                   top_n: int = 30,
                   save_path: Optional[str] = None,
                   show: bool = False) -> str:
    """
    Строит горизонтальную столбчатую диаграмму для 30 топовых пользователей (исполнитель + репортер).
    
    :param issues: Список задач.
    :param project_key: Ключ проекта.
    :param top_n: Количество пользователей.
    :param save_path: Путь сохранения.
    :param show: Отображать ли окно.
    :return: Путь к сохраненному файлу.
    """
    top_data = calculate_top_users(issues, top_n=top_n)
    if not top_data:
        raise ValueError(f"Нет данных о пользователях для проекта {project_key}")

    # Инвертируем порядок для корректного отображения снизу вверх
    users = [item[0] for item in reversed(top_data)]
    totals = [item[1] for item in reversed(top_data)]

    plt.figure(figsize=(9, 9), dpi=150)
    plt.barh(users, totals, color="#7BC8E2", edgecolor="#4682B4", height=0.7)
    plt.title(f"Топ-{len(users)} пользователей по задачам (проект: {project_key})", fontsize=13, fontweight='bold', pad=12)
    plt.xlabel("Количество задач", fontsize=11)
    plt.ylabel("Имя пользователя", fontsize=11)
    plt.grid(axis='x', linestyle='--', alpha=0.7)
    plt.tight_layout()

    if not save_path:
        save_path = os.path.join("results", project_key.lower(), f"top_{top_n}_users.png")
    ensure_dir(os.path.dirname(save_path))
    plt.savefig(save_path, dpi=300)
    logger.info("График топ пользователей сохранен в %s", save_path)
    if show:
        plt.show()
    plt.close()
    return save_path


def calculate_logged_times(issues: List[Dict[str, Any]]) -> List[float]:
    """
    Извлекает залогированное время (в часах) для закрытых задач с timespent > 0.
    
    :param issues: Список закрытых задач.
    :return: Список затраченного времени в часах.
    """
    times_hours = []
    for issue in issues:
        fields = issue.get("fields", {})
        spent = fields.get("timespent")
        if spent is not None and spent > 0:
            times_hours.append(spent / 3600.0)

    logger.debug("Найдено %d задач с залогированным временем", len(times_hours))
    return times_hours


def plot_logged_time_histogram(issues: List[Dict[str, Any]],
                               project_key: str,
                               save_path: Optional[str] = None,
                               bins: int = 25,
                               show: bool = False) -> str:
    """
    Строит гистограмму затраченного времени на основе залогированного времени (timespent).
    
    :param issues: Список закрытых задач.
    :param project_key: Ключ проекта.
    :param save_path: Путь сохранения.
    :param bins: Количество корзин.
    :param show: Отображать ли окно.
    :return: Путь к сохраненному файлу.
    """
    times = calculate_logged_times(issues)
    if not times:
        raise ValueError(
            f"В проекте {project_key} отсутствуют задачи с залогированным временем (timespent).\n"
            f"Рекомендуется использовать проект Apache HDFS или HADOOP, где ведется учет трудозатрат."
        )

    plt.figure(figsize=(9, 6), dpi=150)
    plt.hist(times, bins=bins, color='#66BB6A', edgecolor='#2E7D32', alpha=0.85)
    plt.title(f"Гистограмма затраченного времени на выполнение задач (проект: {project_key})",
              fontsize=12, fontweight='bold', pad=12)
    plt.xlabel("Затраченное время (часы)", fontsize=11)
    plt.ylabel("Количество задач", fontsize=11)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()

    if not save_path:
        save_path = os.path.join("results", project_key.lower(), "logged_time_spent_histogram.png")
    ensure_dir(os.path.dirname(save_path))
    plt.savefig(save_path, dpi=300)
    logger.info("Гистограмма залогированного времени сохранена в %s", save_path)
    if show:
        plt.show()
    plt.close()
    return save_path


def calculate_priorities(issues: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Рассчитывает распределение задач по степени серьезности / приоритетам.
    
    :param issues: Список задач.
    :return: Словарь вида {приоритет: количество_задач}.
    """
    priority_counts = Counter()
    for issue in issues:
        fields = issue.get("fields", {})
        priority = fields.get("priority")
        name = priority.get("name") if priority else "Не указан"
        priority_counts[name] += 1

    return dict(priority_counts)


def plot_priority_distribution(issues: List[Dict[str, Any]],
                               project_key: str,
                               save_path: Optional[str] = None,
                               show: bool = False) -> str:
    """
    Строит график (столбчатую диаграмму) распределения задач по степени серьезности (приоритетам).
    
    :param issues: Список задач.
    :param project_key: Ключ проекта.
    :param save_path: Путь сохранения.
    :param show: Отображать ли окно.
    :return: Путь к сохраненному файлу.
    """
    counts = calculate_priorities(issues)
    if not counts:
        raise ValueError(f"Нет данных о приоритетах задач для проекта {project_key}")

    # Желаемый логический порядок приоритетов в Jira
    desired_order = ["Blocker", "Critical", "Major", "Minor", "Trivial", "High", "Normal", "Low"]
    ordered_keys = [k for k in desired_order if k in counts]
    other_keys = [k for k in counts.keys() if k not in ordered_keys]
    labels = ordered_keys + other_keys
    values = [counts[k] for k in labels]

    plt.figure(figsize=(9, 6), dpi=150)
    bars = plt.bar(labels, values, color='#7EC0EE', edgecolor='#0000FF', width=0.7)
    plt.title(f"Распределение задач по приоритетам (проект: {project_key})",
              fontsize=13, fontweight='bold', pad=12)
    plt.xlabel("Приоритет задачи", fontsize=11)
    plt.ylabel("Количество задач", fontsize=11)
    plt.grid(axis='y', linestyle='--', alpha=0.7)

    # Подписи значений над столбцами
    for bar in bars:
        height = bar.get_height()
        plt.annotate(f'{height}',
                     xy=(bar.get_x() + bar.get_width() / 2, height),
                     xytext=(0, 3),  # смещение 3 точки вверх
                     textcoords="offset points",
                     ha='center', va='bottom', fontsize=10)

    plt.tight_layout()

    if not save_path:
        save_path = os.path.join("results", project_key.lower(), "priority_distribution.png")
    ensure_dir(os.path.dirname(save_path))
    plt.savefig(save_path, dpi=300)
    logger.info("График распределения по приоритетам сохранен в %s", save_path)
    if show:
        plt.show()
    plt.close()
    return save_path
