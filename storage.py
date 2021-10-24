import datetime
from dataclasses import dataclass

import sheet


@dataclass
class Cell:
    idx: str
    data: str = ""


class _Storage:
    _sheet = sheet.Sheet()

    def __init__(self, _month_cell_name: str):
        self._month_cell_name = _month_cell_name
        self._cells = {
            "bath_cold": Cell(idx="3"),
            "bath_hot": Cell(idx="4"),
            "kitchen_cold": Cell(idx="6"),
            "kitchen_hot": Cell(idx="7"),
            "el_t1": Cell(idx="9"),
            "el_t2": Cell(idx="10"),
            "el_t3": Cell(idx="11"),
            "total_cold": Cell(idx="14"),
            "total_hot": Cell(idx="15"),
            "total_drain": Cell(idx="16"),
            "total_t1": Cell(idx="17"),
            "total_t2": Cell(idx="18"),
            "total_t3": Cell(idx="19"),
            "total_all": Cell(idx="20"),
        }

    def load(self):
        values = self._get_all()
        for k, cell in self._cells.items():
            v = values[int(cell.idx) - self._sheet.header_offset]
            self._cells[k].data = v

    def _get_all(self):
        cells = [int(c.idx) for c in self._cells.values()]
        start, end = min(cells), max(cells)
        month = self._month_cell_name
        res = self._sheet.gets(month + str(start), month + str(end))
        return res

    def _get_cell_value(self, name: str) -> float:
        val = self._cells[name].data
        return float(val.replace(",", "."))

    def _set_cell_value(self, name: str, value: str or float):
        if isinstance(value, float):
            value = f"{value:.2f}".replace(".", ",")

        cell = self._month_cell_name + self._cells[name].idx
        self._cells[name].data = value
        self._sheet.write(cell, value)

    @property
    def is_some_missing(self) -> bool:
        values = [v.data for v in self._cells.values()]
        return not all(values)

    @property
    def bath_hot(self) -> float:
        return self._get_cell_value("bath_hot")

    @bath_hot.setter
    def bath_hot(self, value: str or float):
        self._set_cell_value("bath_hot", value)

    @property
    def bath_cold(self) -> float:
        return self._get_cell_value("bath_cold")

    @bath_cold.setter
    def bath_cold(self, value: str or float):
        self._set_cell_value("bath_cold", value)

    @property
    def kitchen_cold(self) -> float:
        return self._get_cell_value("kitchen_cold")

    @kitchen_cold.setter
    def kitchen_cold(self, value: str or float):
        self._set_cell_value("kitchen_cold", value)

    @property
    def kitchen_hot(self) -> float:
        return self._get_cell_value("kitchen_hot")

    @kitchen_hot.setter
    def kitchen_hot(self, value: str or float):
        self._set_cell_value("kitchen_hot", value)

    @property
    def el_t1(self) -> float:
        return self._get_cell_value("el_t1")

    @el_t1.setter
    def el_t1(self, value: str or float):
        self._set_cell_value("el_t1", value)

    @property
    def el_t2(self) -> float:
        return self._get_cell_value("el_t2")

    @el_t2.setter
    def el_t2(self, value: str or float):
        self._set_cell_value("el_t2", value)

    @property
    def el_t3(self) -> float:
        return self._get_cell_value("el_t3")

    @el_t3.setter
    def el_t3(self, value: str or float):
        self._set_cell_value("el_t3", value)

    @property
    def total_cold(self) -> float:
        return self._get_cell_value("total_cold")

    @total_cold.setter
    def total_cold(self, value: str or float or float):
        self._set_cell_value("total_cold", value)

    @property
    def total_hot(self) -> float:
        return self._get_cell_value("total_hot")

    @total_hot.setter
    def total_hot(self, value: str or float):
        self._set_cell_value("total_hot", value)

    @property
    def total_drain(self) -> float:
        return self._get_cell_value("total_drain")

    @total_drain.setter
    def total_drain(self, value: str or float):
        self._set_cell_value("total_drain", value)

    @property
    def total_t1(self) -> float:
        return self._get_cell_value("total_t1")

    @total_t1.setter
    def total_t1(self, value: str or float):
        self._set_cell_value("total_t1", value)

    @property
    def total_t2(self) -> float:
        return self._get_cell_value("total_t2")

    @total_t2.setter
    def total_t2(self, value: str or float):
        self._set_cell_value("total_t2", value)

    @property
    def total_t3(self) -> float:
        return self._get_cell_value("total_t3")

    @total_t3.setter
    def total_t3(self, value: str or float):
        self._set_cell_value("total_t3", value)

    @property
    def total_all(self) -> float:
        return self._get_cell_value("total_all")

    @total_all.setter
    def total_all(self, value: str or float):
        self._set_cell_value("total_all", value)


class Storage:
    _months_cells_names = " FGHIJKLMNOP"

    def __init__(self):
        curr_month = datetime.datetime.today().month
        self._curr = _Storage(self._months_cells_names[curr_month])
        self._prev = _Storage(self._months_cells_names[curr_month - 1])
        self._last_current_month = curr_month
        self._last_prev_month = curr_month - 1

    @property
    def curr(self):
        curr_month = datetime.datetime.today().month
        if curr_month != self._last_current_month:
            self._curr = _Storage(self._months_cells_names[curr_month])

        return self._curr

    @property
    def prev(self):
        prev_month = datetime.datetime.today().month - 1
        if prev_month != self._last_prev_month:
            self._prev = _Storage(self._months_cells_names[prev_month])

        return self._prev


def _debug():
    s = Storage()
    print(s.curr.load())


if __name__ == '__main__':
    _debug()
