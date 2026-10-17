"""
Модуль взаимодействия с JIRA через REST API.
Разработчик: Суханов С.С.
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional
import requests
from requests.exceptions import RequestException

from jira_analytics.utils import ensure_dir, get_logger

logger = get_logger("jira_analytics.jira_api")


class JiraAPIError(Exception):
    """Исключение, возникающее при ошибках взаимодействия с JIRA REST API."""
    pass


class JiraClient:
    """
    Клиент для взаимодействия с сервером JIRA через REST API v2.
    Поддерживает пагинацию, кэширование, расширение changelog и обработку ошибок.
    """

    def __init__(self,
                 base_url: str = "https://issues.apache.org/jira",
                 timeout: int = 30,
                 cache_dir: str = "cache"):
        """
        Инициализирует клиента JIRA REST API.
        
        :param base_url: Базовый URL сервера JIRA (по умолчанию: Apache JIRA).
        :param timeout: Таймаут запросов в секундах.
        :param cache_dir: Каталог для кэширования ответов API.
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.cache_dir = cache_dir
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": "JiraAnalyticsClient/1.0"
        })
        ensure_dir(self.cache_dir)
        logger.info("JiraClient инициализирован для %s (таймаут: %dс)", self.base_url, self.timeout)

    def _get_cache_path(self, cache_key: str) -> str:
        """Формирует безопасный путь к файлу кэша."""
        safe_key = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in cache_key)
        return os.path.join(self.cache_dir, f"{safe_key}.json")

    def _save_to_cache(self, cache_key: str, data: Any) -> None:
        """Сохраняет данные в локальный кэш."""
        path = self._get_cache_path(cache_key)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.debug("Данные успешно сохранены в кэш: %s", path)
        except Exception as e:
            logger.warning("Не удалось сохранить кэш в %s: %s", path, e)

    def _load_from_cache(self, cache_key: str) -> Optional[Any]:
        """Загружает данные из локального кэша, если он существует."""
        path = self._get_cache_path(cache_key)
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                logger.info("Данные загружены из локального кэша: %s", path)
                return data
            except Exception as e:
                logger.warning("Ошибка чтения кэша %s: %s", path, e)
        return None

    def search_issues(self,
                      jql: str,
                      fields: Optional[List[str]] = None,
                      max_results: int = 500,
                      expand: Optional[str] = None,
                      use_cache: bool = True,
                      force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Выполняет поиск задач с использованием JQL-запроса через JIRA REST API.
        
        :param jql: Строка JQL-запроса.
        :param fields: Список требуемых полей (например, ['created', 'status']).
        :param max_results: Максимальное количество задач для выборки.
        :param expand: Дополнительные параметры раскрытия (например, 'changelog').
        :param use_cache: Использовать ли локальное кэширование.
        :param force_refresh: Принудительно обновить кэш запросом к серверу.
        :return: Список словарей с данными найденных задач.
        :raises JiraAPIError: При сетевых или протокольных ошибках.
        """
        cache_key = f"{jql}__limit_{max_results}__exp_{expand}"
        if use_cache and not force_refresh:
            cached_data = self._load_from_cache(cache_key)
            if cached_data is not None:
                return cached_data

        url = f"{self.base_url}/rest/api/2/search"
        fields_str = ",".join(fields) if fields else "*navigable"
        all_issues: List[Dict[str, Any]] = []
        start_at = 0
        batch_size = 100

        logger.info("Запуск выборки задач по JQL: '%s' (лимит: %d)", jql, max_results)

        while len(all_issues) < max_results:
            current_limit = min(batch_size, max_results - len(all_issues))
            params = {
                "jql": jql,
                "startAt": start_at,
                "maxResults": current_limit,
                "fields": fields_str
            }
            if expand:
                params["expand"] = expand

            try:
                logger.debug("HTTP GET %s (startAt=%d, maxResults=%d)", url, start_at, current_limit)
                response = self.session.get(url, params=params, timeout=self.timeout)
                if response.status_code != 200:
                    error_msg = f"Ошибка JIRA API (код {response.status_code}): {response.text[:200]}"
                    logger.error(error_msg)
                    raise JiraAPIError(error_msg)

                data = response.json()
            except RequestException as re:
                error_msg = f"Сетевая ошибка при обращении к {url}: {re}"
                logger.error(error_msg)
                raise JiraAPIError(error_msg) from re
            except json.JSONDecodeError as je:
                error_msg = f"Ошибка декодирования ответа JSON от JIRA API: {je}"
                logger.error(error_msg)
                raise JiraAPIError(error_msg) from je

            issues_batch = data.get("issues", [])
            if not issues_batch:
                break

            all_issues.extend(issues_batch)
            total = data.get("total", 0)
            logger.info("Получено задач: %d из %d (всего на сервере: %d)",
                        len(all_issues), min(max_results, total), total)

            start_at += len(issues_batch)
            if start_at >= total or len(issues_batch) < current_limit:
                break

        logger.info("Выборка завершена. Всего получено задач: %d", len(all_issues))

        if use_cache:
            self._save_to_cache(cache_key, all_issues)

        return all_issues

    def get_closed_project_issues(self,
                                  project_key: str,
                                  max_results: int = 500,
                                  expand_changelog: bool = True,
                                  use_cache: bool = True,
                                  force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Возвращает закрытые задачи указанного проекта с историей изменений.
        
        :param project_key: Ключ проекта в JIRA (например, 'KAFKA', 'HDFS').
        :param max_results: Максимальное количество задач.
        :param expand_changelog: Включать ли changelog для анализа состояний.
        :param use_cache: Использовать ли кэш.
        :param force_refresh: Принудительно обновить кэш.
        :return: Список закрытых задач.
        """
        jql = f"project = {project_key} AND status in (Closed, Resolved) ORDER BY created DESC"
        fields = [
            "key", "summary", "created", "resolutiondate", "status",
            "priority", "assignee", "reporter", "timespent", "timeoriginalestimate"
        ]
        expand = "changelog" if expand_changelog else None
        return self.search_issues(
            jql=jql,
            fields=fields,
            max_results=max_results,
            expand=expand,
            use_cache=use_cache,
            force_refresh=force_refresh
        )

    def get_all_project_issues(self,
                               project_key: str,
                               max_results: int = 500,
                               use_cache: bool = True,
                               force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Возвращает задачи проекта (как открытые, так и закрытые) для анализа динамики создания.
        
        :param project_key: Ключ проекта в JIRA.
        :param max_results: Максимальное количество задач.
        :param use_cache: Использовать ли кэш.
        :param force_refresh: Принудительно обновить кэш.
        :return: Список задач проекта.
        """
        jql = f"project = {project_key} ORDER BY created DESC"
        fields = [
            "key", "summary", "created", "resolutiondate", "status",
            "priority", "assignee", "reporter", "timespent"
        ]
        return self.search_issues(
            jql=jql,
            fields=fields,
            max_results=max_results,
            expand=None,
            use_cache=use_cache,
            force_refresh=force_refresh
        )
