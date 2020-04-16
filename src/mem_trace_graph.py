"""
This plugin visualizes memory accesses.
X-axis is a row in trace, y-axis is an index in a list of memory addresses.
Green circle is a read, red is a write.
"""

import sys
from yapsy.IPlugin import IPlugin
import pyqtgraph as pg
from PyQt5.QtGui import QGraphicsProxyWidget

from core.api import Api


# if distance between 2 consecutive memory addresses is > MAX_DISTANCE,
# index will increase by MAX_DISTANCE
DEFAULT_MAX_DISTANCE = 30


class PluginMemTrace(IPlugin):
    def init_gui(self):
        self.win = pg.GraphicsWindow(title="Memory trace graph plugin")

        self.mem_combo_box = pg.ComboBox()
        self.mem_combo_box.setItems(["All", "Reads", "Writes"])
        self.mem_combo_box.currentIndexChanged.connect(self.mem_combo_box_changed)
        self.proxy = QGraphicsProxyWidget()
        self.proxy.setWidget(self.mem_combo_box)
        self.layout = self.win.addLayout(row=0, col=0)
        self.layout.addItem(self.proxy)

        self.plot_item = self.win.addPlot(title="Memory trace graph", row=1, col=0)
        self.plot_item.setLabel("left", "Memory address index")
        self.plot_item.setLabel("bottom", "Trace row id")

        self.scatter_plot_reads = pg.ScatterPlotItem(symbol="o")
        self.scatter_plot_reads.setBrush(None)
        self.scatter_plot_reads.setPen("g")
        self.scatter_plot_reads.sigClicked.connect(self.sig_clicked)

        self.scatter_plot_writes = pg.ScatterPlotItem(symbol="o")
        self.scatter_plot_writes.setBrush("r")
        self.scatter_plot_writes.setPen("r")
        self.scatter_plot_writes.sigClicked.connect(self.sig_clicked)

        self.plot_item.addItem(self.scatter_plot_writes)
        self.plot_item.addItem(self.scatter_plot_reads)

        self.plot_item.showGrid(y=True, x=True, alpha=1.0)

    def sig_clicked(self, points):
        spot_item = points.ptsClicked[0]
        row_id = int(spot_item.pos()[0])
        if len(points.ptsClicked) > 1:
            print(
                f"Multiple points clicked, rows: {[int(x.pos()[0]) for x in points.ptsClicked]}"
            )
        self.api.go_to_row_in_full_trace(row_id)

    def mem_combo_box_changed(self, index):
        self.plot_item.clear()
        if index == 0:
            self.plot_item.addItem(self.scatter_plot_writes)
            self.plot_item.addItem(self.scatter_plot_reads)
        elif index == 1:
            self.plot_item.addItem(self.scatter_plot_reads)
        elif index == 2:
            self.plot_item.addItem(self.scatter_plot_writes)

    def execute(self, api: Api):
        self.api = api

        max_distance = api.get_string_from_user(
            "Max distance",
            f"Give a max distance between addresses, leave empty for default ({DEFAULT_MAX_DISTANCE})",
        )
        try:
            max_distance = int(max_distance)
        except ValueError:
            max_distance = DEFAULT_MAX_DISTANCE

        self.init_gui()

        trace = api.get_visible_trace()
        row_id_min = sys.maxsize
        row_id_max = 0
        data_reads = []
        data_writes = []
        addresses = set()

        # get all memory accesses from trace
        for t in trace:
            if t["mem"]:
                if t["id"] > row_id_max:
                    row_id_max = t["id"]
                if t["id"] < row_id_min:
                    row_id_min = t["id"]
                for mem in t["mem"]:
                    if mem["access"] == "READ":
                        data_reads.append({"x": t["id"], "y": mem["addr"]})
                    elif mem["access"] == "WRITE":
                        data_writes.append({"x": t["id"], "y": mem["addr"]})
                    addresses.add(mem["addr"])

        # convert a set to sorted list
        addresses = sorted(addresses)

        # convert mem addresses to indexes (0..x)
        new_index = 0
        addr_indexes = {}
        i = 0
        for (i, addr) in enumerate(addresses):
            if i > 0:
                if abs(addr - addresses[i - 1]) > max_distance:
                    new_index += max_distance
            addr_indexes[addr] = new_index + i
        addr_max = new_index + i

        # replace addresses with indexes
        for d in data_reads:
            d["y"] = addr_indexes[d["y"]]
        for d in data_writes:
            d["y"] = addr_indexes[d["y"]]

        self.plot_item.setXRange(row_id_min, row_id_max, padding=0)
        self.plot_item.setYRange(1, addr_max, padding=0)

        self.scatter_plot_reads.setData(data_reads)
        self.scatter_plot_writes.setData(data_writes)
