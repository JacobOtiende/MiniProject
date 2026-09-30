"""
In-memory stand-in for the Google Tasks API, used in demo mode and tests.
Implements just the call shapes tools/tasks_tool.py uses:
tasklists().list/insert and tasks().list/insert/patch(...).execute(),
including `previous=` placement so list order can be checked.
"""
from __future__ import annotations

import uuid


class _Exec:
    def __init__(self, result):
        self._result = result

    def execute(self):
        return self._result


class _TaskListsResource:
    def __init__(self, service):
        self._service = service

    def list(self, maxResults=100, pageToken=None):
        return _Exec({"items": [{"id": k, "title": v} for k, v in self._service.list_titles.items()]})

    def insert(self, body):
        list_id = str(uuid.uuid4())[:8]
        self._service.list_titles[list_id] = body["title"]
        self._service.lists[list_id] = []
        return _Exec({"id": list_id, "title": body["title"]})


class _TasksResource:
    def __init__(self, service):
        self._service = service

    def _list(self, tasklist):
        return self._service.lists.setdefault(tasklist, [])

    def list(self, tasklist, showCompleted=True, maxResults=100, pageToken=None, **kwargs):
        items = [
            {**t, "position": f"{i:020d}"}
            for i, t in enumerate(self._list(tasklist))
            if showCompleted or t.get("status") != "completed"
        ]
        return _Exec({"items": items})

    def insert(self, tasklist, body, previous=None):
        tasks = self._list(tasklist)
        task = {**body, "id": str(uuid.uuid4())[:8], "status": body.get("status", "needsAction")}
        if previous is None:
            tasks.insert(0, task)  # Google puts a task with no `previous` at the top
        else:
            index = next(i for i, t in enumerate(tasks) if t["id"] == previous)
            tasks.insert(index + 1, task)
        return _Exec({"id": task["id"]})

    def patch(self, tasklist, task, body):
        for t in self._list(tasklist):
            if t["id"] == task:
                t.update(body)
        return _Exec({})


class InMemoryTasksService:
    def __init__(self):
        self.list_titles: dict[str, str] = {"@default": "My Tasks"}
        self.lists: dict[str, list[dict]] = {"@default": []}

    def tasklists(self):
        return _TaskListsResource(self)

    def tasks(self):
        return _TasksResource(self)

    # Test helpers: ordered task dicts per list.
    @property
    def items(self) -> dict[str, dict]:
        return {t["id"]: t for t in self.lists["@default"]}

    def titles(self, tasklist: str = "@default") -> list[str]:
        return [t["title"] for t in self.lists.get(tasklist, [])]
