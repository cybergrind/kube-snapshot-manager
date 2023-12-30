from contextvars import ContextVar
from typing import Any, Dict
from datetime import datetime


class DebugObject:
    def __init__(self, parent, name=None):
        self.parent = parent
        if self.parent:
            self.parent.add_child(self)
        self.children = []
        self.name = name
        self.values = {}
        self.buttons = {}
        self.change_callbacks = []

    def add_child(self, child):
        self.children.append(child)

    def remove_child(self, child):
        self.children.remove(child)

    def track(self, name, value):
        self.values[name] = value
        if self.parent:
            self.notify_change()

    def serialize(self) -> Dict[str, Any]:
        out = {}
        if self.name:
            out[self.name] = {
                'values': self.values.copy(),
                'buttons': self.buttons,
            }
            out[self.name]['values']['timestamp'] = datetime.now().isoformat()
            return out
        out['global'] = {
            'values': {
                'change_callbacks': len(self.change_callbacks),
                'children': len(self.children),
            },
            'buttons': {},
        }
        for child in self.children:
            out.update(child.serialize())
        return out

    def add_notify(self, cb):
        self.change_callbacks.append(cb)

    def remove_notify(self, cb):
        self.change_callbacks.remove(cb)

    def notify_change(self):
        data = self.serialize()
        for cb in self.change_callbacks:
            cb(data)


DEBUG_GLOBAL = ContextVar('debug_global', default=DebugObject(None))
