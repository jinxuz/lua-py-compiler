from lua_utils import convert_to_integer


class Table:

    def __init__(self):
        self.arr = []
        self.map = {}
        self.keys = {}
        self.modified = True

    def get(self, key):
        idx, int_flag = convert_to_integer(key)
        if int_flag and 1 <= idx <= len(self.arr):
            return self.arr[idx - 1]
        return self.map.get(key, None)

    def put(self, key, val):
        assert key is not None
        self.modified = True
        idx, int_flag = convert_to_integer(key)
        if int_flag and idx >= 1:
            if idx <= len(self.arr):
                self.arr[idx - 1] = val
                if idx == len(self.arr) and val is None:
                    self.arr.pop()
                return
            if idx == len(self.arr) + 1:
                self.map.pop(idx, 0)
                if val is not None:
                    self.arr.append(val)
                return
        if val is not None:
            self.map[key] = val

    def next_key(self, key):
        if key is None or self.modified:
            self.init_keys()
            self.modified = True
        return self.keys.get(key, None)

    def init_keys(self):
        key = None
        for i in range(len(self.arr)):
            if self.arr[i] is not None:
                self.keys[key] = i + 1
                key = i + 1
        for k, v in self.map.items():
            if v is not None:
                self.keys[key] = k
                key = k

    def __len__(self):
        return len(self.arr)

    def __repr__(self):
        return '-arr: ' + repr(self.arr) + ' -map: ' + repr(self.map)
