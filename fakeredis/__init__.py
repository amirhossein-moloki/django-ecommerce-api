from collections import defaultdict


class FakeRedis:
    def __init__(self):
        self._data = defaultdict(dict)

    def zincrby(self, key, amount, value):
        value = str(value)
        self._data[key][value] = self._data[key].get(value, 0) + amount

    def zrange(self, key, start, end, desc=False):
        items = self._data.get(key, {})
        sorted_items = sorted(items.items(), key=lambda item: item[1], reverse=desc)
        members = [member for member, _score in sorted_items]
        if end == -1:
            end = len(members) - 1
        return members[start : end + 1]

    def zunionstore(self, dest, keys):
        combined = defaultdict(int)
        for key in keys:
            for member, score in self._data.get(key, {}).items():
                combined[member] += score
        self._data[dest] = dict(combined)

    def zrem(self, key, *values):
        for value in values:
            self._data.get(key, {}).pop(str(value), None)

    def delete(self, key):
        self._data.pop(key, None)
