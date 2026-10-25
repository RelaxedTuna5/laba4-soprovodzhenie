"""
Главная точка входа для консольного приложения аналитики задач JIRA.
Разработчик: Суханов С.С.
"""

import os
import sys
import argparse
from typing import Optional

from jira_analytics.utils import load_config, setup_logging, get_logger, ensure_dir
from jira_analytics.jira_api import JiraClient, JiraAPIError
from jira_analytics.tasks import (
    plot_open_duration_histogram,
    calculate_status_durations,
    plot_status_time_distribution,
    calculate_daily_dynamics,
    plot_daily_dynamics,
    calculate_top_users,
    plot_top_users,
    calculate_logged_times,
    plot_logged_time_histogram,
    calculate_priorities,
    plot_priority_distribution
)


def run_full_pipeline(client: JiraClient, project_key: str, results_dir: str, force_refresh: bool = False) -> None:
    """
    Выполняет полный аналитический пайплайн и строит все 6 требуемых заданием графиков.
    
    :param client: Экземпляр клиента JiraClient.
    :param project_key: Ключ анализируемого проекта.
    :param results_dir: Корневая директория для сохранения графиков.
    :param force_refresh: Принудительное обновление кэша.
    """
    logger = get_logger("jira_analytics.main")
    print(f"\n========================================================")
    print(f"   Запуск полного аналитического цикла для проекта {project_key}")
    print(f"========================================================")

    proj_dir = os.path.join(results_dir, project_key.lower())
    ensure_dir(proj_dir)

    print("[1/5] Загрузка закрытых задач проекта из JIRA...")
    closed_issues = client.get_closed_project_issues(
        project_key=project_key,
        max_results=500,
        expand_changelog=True,
        force_refresh=force_refresh
    )
    print(f"      Загружено {len(closed_issues)} закрытых задач.")

    print("[2/5] Загрузка общего потока задач проекта...")
    all_issues = client.get_all_project_issues(
        project_key=project_key,
        max_results=500,
        force_refresh=force_refresh
    )
    print(f"      Загружено {len(all_issues)} задач для динамического анализа.")

    print("\n--- Построение отчетов и графиков ---")

    # График 1: Гистограмма времени в открытом состоянии
    try:
        p1 = plot_open_duration_histogram(closed_issues, project_key,
                                          save_path=os.path.join(proj_dir, "1_open_duration_histogram.png"))
        print(f"  [+] 1. Гистограмма времени в открытом состоянии построена: {p1}")
    except Exception as e:
        print(f"  [-] Ошибка при построении графика 1: {e}")

    # График 2: Диаграмма распределения времени по состояниям
    try:
        status_durations = calculate_status_durations(closed_issues)
        if status_durations:
            # Строим для первого доступного статуса (например, Open) и сохраняем
            st_list = list(status_durations.keys())
            main_status = "Open" if "Open" in status_durations else st_list[0]
            p2 = plot_status_time_distribution(closed_issues, main_status, project_key,
                                               save_path=os.path.join(proj_dir, f"2_status_{main_status}_distribution.png"))
            print(f"  [+] 2. Диаграмма распределения времени в статусе '{main_status}' построена: {p2}")
        else:
            print("  [-] График 2: Нет данных по истории переходов статусов.")
    except Exception as e:
        print(f"  [-] Ошибка при построении графика 2: {e}")

    # График 3: График создания и закрытия задач с накопительным итогом
    try:
        p3 = plot_daily_dynamics(all_issues, project_key,
                                 save_path=os.path.join(proj_dir, "3_daily_dynamics_cumulative.png"))
        print(f"  [+] 3. График создания/закрытия задач с накопительным итогом построен: {p3}")
    except Exception as e:
        print(f"  [-] Ошибка при построении графика 3: {e}")

    # График 4: График задач для пользователей (Топ-30)
    try:
        p4 = plot_top_users(all_issues, project_key, top_n=30,
                            save_path=os.path.join(proj_dir, "4_top_30_users.png"))
        print(f"  [+] 4. График активности топ-30 пользователей построен: {p4}")
    except Exception as e:
        print(f"  [-] Ошибка при построении графика 4: {e}")

    # График 5: Гистограмма времени выполнения задач (залогированное время)
    times = calculate_logged_times(closed_issues)
    if len(times) >= 10:
        try:
            p5 = plot_logged_time_histogram(closed_issues, project_key,
                                            save_path=os.path.join(proj_dir, "5_logged_time_spent_histogram.png"))
            print(f"  [+] 5. Гистограмма залогированного времени построена: {p5}")
        except Exception as e:
            print(f"  [-] Ошибка при построении графика 5: {e}")
    else:
        print(f"  [!] 5. В проекте {project_key} найдено всего {len(times)} задач с залогированным временем (нерепрезентативно).")
        fallback_proj = "HDFS"
        print(f"      -> Выполняем построение полноценного графика 5 на контрольном проекте Apache {fallback_proj} (выборка 'timespent is not EMPTY')...")
        try:
            hdfs_issues = client.search_issues(
                f"project = {fallback_proj} AND status in (Closed, Resolved) AND timespent is not EMPTY ORDER BY created DESC",
                max_results=300,
                use_cache=True
            )
            p5_fb = plot_logged_time_histogram(hdfs_issues, fallback_proj,
                                               save_path=os.path.join(proj_dir, f"5_logged_time_spent_{fallback_proj}.png"))
            print(f"      [+] 5. Полноценная гистограмма залогированного времени построена для {fallback_proj} ({len(hdfs_issues)} задач): {p5_fb}")
        except Exception as fb_err:
            print(f"      [-] Не удалось построить график для запасного проекта: {fb_err}")

    # График 6: График задач по степени серьезности
    try:
        p6 = plot_priority_distribution(all_issues, project_key,
                                        save_path=os.path.join(proj_dir, "6_priority_distribution.png"))
        print(f"  [+] 6. График распределения по степени серьезности построен: {p6}")
    except Exception as e:
        print(f"  [-] Ошибка при построении графика 6: {e}")

    print("\n[OK] Все аналитические отчеты успешно сформированы!")


def interactive_menu(client: JiraClient, default_project: str, results_dir: str) -> None:
    """
    Интерактивный консольный интерфейс для пользователя.
    
    :param client: Экземпляр клиента JIRA.
    :param default_project: Проект по умолчанию.
    :param results_dir: Директория результатов.
    """
    current_project = default_project.upper()
    proj_dir = os.path.join(results_dir, current_project.lower())
    ensure_dir(proj_dir)

    print("\n" + "=" * 65)
    print("  ПРОГРАММНОЕ СРЕДСТВО ДЛЯ АНАЛИТИКИ ЗАДАЧ JIRA")
    print("  Лабораторная работа №4 | Выполнил: Суханов С.С. (гр. 5140904/60401)")
    print("=" * 65)

    proj_input = input(f"Введите название проекта (по умолчанию '{current_project}'): ").strip()
    if proj_input:
        current_project = proj_input.upper()
        proj_dir = os.path.join(results_dir, current_project.lower())
        ensure_dir(proj_dir)

    print(f"\nВыбран проект: {current_project}")

    while True:
        print("\n" + "-" * 55)
        print("  Выберите команду для проекта", current_project + ":")
        print("-" * 55)
        print(" 1. Построить гистограмму времени задач в открытом состоянии")
        print(" 2. Построить диаграммы распределения времени по состояниям")
        print(" 3. Построить график создания и закрытия задач с накопительным итогом")
        print(" 4. Построить график задач для пользователей (Топ-30)")
        print(" 5. Построить гистограмму времени выполнения задач")
        print(" 6. Построить график задач по степени серьезности")
        print(" 7. Выполнить полный цикл (построить все 6 отчетов)")
        print(" 8. Сменить анализируемый проект")
        print(" 0. Завершить работу")
        print("-" * 55)

        choice = input("Ваш выбор: ").strip()

        if choice == "0":
            print("\nЗавершение работы программы. До свидания!")
            break
        elif choice == "1":
            print(f"\nЗагрузка данных для гистограммы времени в открытом состоянии ({current_project})...")
            issues = client.get_closed_project_issues(current_project)
            path = plot_open_duration_histogram(issues, current_project,
                                                save_path=os.path.join(proj_dir, "1_open_duration_histogram.png"),
                                                show=False)
            print(f"[OK] График сохранен: {path}")
        elif choice == "2":
            print(f"\nЗагрузка данных о состояниях задач ({current_project})...")
            issues = client.get_closed_project_issues(current_project, expand_changelog=True)
            status_durations = calculate_status_durations(issues)
            if not status_durations:
                print("[!] Нет данных о переходе состояний для этого проекта.")
                continue

            available = list(status_durations.keys())
            print("Доступные статусы:")
            for idx, st in enumerate(available, 1):
                print(f"  {idx}. {st} ({len(status_durations[st])} записей)")
            st_choice = input("Выберите номер статуса или введите название: ").strip()
            selected_st = None
            if st_choice.isdigit() and 1 <= int(st_choice) <= len(available):
                selected_st = available[int(st_choice) - 1]
            elif st_choice in status_durations:
                selected_st = st_choice
            else:
                selected_st = available[0]

            path = plot_status_time_distribution(issues, selected_st, current_project,
                                                 save_path=os.path.join(proj_dir, f"2_status_{selected_st}_distribution.png"),
                                                 show=False)
            print(f"[OK] График для статуса '{selected_st}' сохранен: {path}")
        elif choice == "3":
            print(f"\nЗагрузка данных для динамики заведения и закрытия ({current_project})...")
            issues = client.get_all_project_issues(current_project)
            path = plot_daily_dynamics(issues, current_project,
                                       save_path=os.path.join(proj_dir, "3_daily_dynamics_cumulative.png"),
                                       show=False)
            print(f"[OK] График динамики сохранен: {path}")
        elif choice == "4":
            print(f"\nЗагрузка пользователей ({current_project})...")
            issues = client.get_all_project_issues(current_project)
            path = plot_top_users(issues, current_project, top_n=30,
                                  save_path=os.path.join(proj_dir, "4_top_30_users.png"),
                                  show=False)
            print(f"[OK] Топ-30 пользователей сохранен: {path}")
        elif choice == "5":
            print(f"\nЗагрузка времени выполнения задач ({current_project})...")
            issues = client.get_closed_project_issues(current_project)
            times = calculate_logged_times(issues)
            if len(times) >= 10:
                path = plot_logged_time_histogram(issues, current_project,
                                                  save_path=os.path.join(proj_dir, "5_logged_time_spent_histogram.png"),
                                                  show=False)
                print(f"[OK] График залогированного времени сохранен: {path}")
            else:
                print(f"[!] В проекте {current_project} всего {len(times)} задач с залогированным временем (нерепрезентативно).")
                alt = input("Построить полноценную гистограмму на контрольном проекте HDFS (300 задач)? (y/n): ").strip().lower()
                if alt in ("y", "д", ""):
                    hdfs_issues = client.search_issues(
                        "project = HDFS AND status in (Closed, Resolved) AND timespent is not EMPTY ORDER BY created DESC",
                        max_results=300,
                        use_cache=True
                    )
                    path = plot_logged_time_histogram(hdfs_issues, "HDFS",
                                                      save_path=os.path.join(proj_dir, "5_logged_time_spent_HDFS.png"),
                                                      show=False)
                    print(f"[OK] Полноценный график для HDFS сохранен: {path}")
        elif choice == "6":
            print(f"\nЗагрузка приоритетов ({current_project})...")
            issues = client.get_all_project_issues(current_project)
            path = plot_priority_distribution(issues, current_project,
                                              save_path=os.path.join(proj_dir, "6_priority_distribution.png"),
                                              show=False)
            print(f"[OK] График приоритетов сохранен: {path}")
        elif choice == "7":
            run_full_pipeline(client, current_project, results_dir)
        elif choice == "8":
            new_proj = input("Введите новый ключ проекта JIRA: ").strip().upper()
            if new_proj:
                current_project = new_proj
                proj_dir = os.path.join(results_dir, current_project.lower())
                ensure_dir(proj_dir)
                print(f"Текущий проект изменен на {current_project}")
        else:
            print("[!] Неверный выбор, попробуйте еще раз.")


def main() -> None:
    """Точка входа в программу."""
    parser = argparse.ArgumentParser(description="JIRA Task Analytics CLI Tool (Лабораторная работа 4)")
    parser.add_argument("-p", "--project", type=str, help="Ключ проекта (по умолчанию из config.ini)")
    parser.add_argument("-c", "--config", type=str, default="config.ini", help="Путь к конфигурационному файлу")
    parser.add_argument("-a", "--all", action="store_true", help="Автоматически построить все 6 отчетов без интерактивного меню")
    parser.add_argument("-r", "--refresh", action="store_true", help="Принудительно обновить кэш запросов")
    args = parser.parse_args()

    cfg = load_config(args.config)
    setup_logging(log_file=cfg["log_file"], log_level=cfg["log_level"])

    project_key = args.project.upper() if args.project else cfg["default_project"]
    client = JiraClient(
        base_url=cfg["base_url"],
        timeout=cfg["timeout"],
        cache_dir=cfg["cache_dir"]
    )

    if args.all:
        run_full_pipeline(client, project_key, cfg["results_dir"], force_refresh=args.refresh)
    else:
        interactive_menu(client, project_key, cfg["results_dir"])


if __name__ == "__main__":
    main()
